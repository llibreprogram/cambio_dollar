from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cambio_dollar.analytics import ProviderReliabilityAggregator, ProviderWeightCalculator
from cambio_dollar.config import ProviderSettings, Settings
from cambio_dollar.models import ProviderErrorSample, ProviderFetchMetric
from cambio_dollar.repository import MarketRepository


@pytest.fixture()
def reliability_settings(tmp_path: Path) -> Settings:
    base = Settings()
    return base.model_copy(
        update={
            "db_path": tmp_path / "rollup.sqlite",
            "timezone": "UTC",
            "scheduler_interval_seconds": 600,
            "providers": [
                ProviderSettings(name="Banco Central", endpoint="https://mock.local", enabled=True),
                ProviderSettings(name="Banco Inactivo", endpoint="https://disabled", enabled=False),
            ],
        }
    )


def _metric(
    *,
    provider: str,
    timestamp: datetime,
    success: bool,
    latency_ms: float | None,
    status_code: int | None,
    attempts: int,
    retries: int,
    error: str | None,
) -> ProviderFetchMetric:
    return ProviderFetchMetric(
        timestamp=timestamp,
        provider=provider,
        latency_ms=latency_ms,
        status_code=status_code,
        success=success,
        attempts=attempts,
        retries=retries,
        error=error,
        metadata={"source": "test"},
    )


def test_provider_reliability_rollup_persisted(reliability_settings: Settings) -> None:
    repository = MarketRepository(reliability_settings.db_path)
    aggregator = ProviderReliabilityAggregator(repository, reliability_settings)
    now = datetime.now(tz=UTC)

    metrics = [
        _metric(provider="Banco Central", timestamp=now - timedelta(minutes=50), success=True, latency_ms=120, status_code=200, attempts=1, retries=0, error=None),
        _metric(provider="Banco Central", timestamp=now - timedelta(minutes=40), success=False, latency_ms=350, status_code=500, attempts=2, retries=1, error="HTTP 500"),
        _metric(provider="Banco Central", timestamp=now - timedelta(minutes=10), success=True, latency_ms=95, status_code=200, attempts=1, retries=0, error=None),
    ]
    repository.save_provider_metrics(metrics)

    error_samples = [
        ProviderErrorSample(
            timestamp=now - timedelta(minutes=55 - idx * 5),
            provider="Banco Central",
            delta_vs_weighted=delta,
            delta_vs_consensus=delta,
            provider_mid=58.40 + idx * 0.02,
            weighted_mid=58.50,
            consensus_mid=58.48,
            weight=0.33,
            metadata={"source": "test"},
        )
        for idx, delta in enumerate([0.12, 0.08, -0.04])
    ]
    repository.record_provider_error_samples(error_samples)

    records = aggregator.compute_and_store(window_minutes=60, reference=now)
    assert len(records) == 1
    record = records[0]

    assert record.provider == "Banco Central"
    assert pytest.approx(record.coverage_ratio, rel=1e-3) == (2 / 6)
    assert pytest.approx(record.success_ratio, rel=1e-3) == (2 / 3)
    assert record.captures == 2
    assert record.failure_count == 1
    assert record.latency_p95_ms is not None
    assert record.latency_p50_ms is not None
    assert record.latency_p95_ms >= record.latency_p50_ms
    assert record.mean_error is not None and pytest.approx(record.mean_error, rel=1e-3) == 0.0533333333
    assert record.std_error is not None and pytest.approx(record.std_error, rel=1e-3) == 0.0680413817

    stored = repository.list_provider_reliability_metrics(provider="Banco Central")
    assert len(stored) == 1
    stored_record = stored[0]
    assert stored_record.captures == record.captures
    assert stored_record.expected_captures == 6
    assert stored_record.metadata is not None
    assert Counter(stored_record.metadata.get("status_codes", {})) == Counter({"200": 2, "500": 1})
    assert stored_record.metadata.get("total_retries") == 1
    assert "sin datos" not in " ".join(stored_record.metadata.get("notes", []))
    assert stored_record.metadata.get("pricing_error_sample_count") == 3
    assert stored_record.mean_error == pytest.approx(record.mean_error, rel=1e-6)
    assert stored_record.std_error == pytest.approx(record.std_error, rel=1e-6)

    # Idempotent update
    aggregator.compute_and_store(window_minutes=60, reference=now)
    assert len(repository.list_provider_reliability_metrics(provider="Banco Central")) == 1


def test_provider_reliability_handles_empty_window(reliability_settings: Settings) -> None:
    repository = MarketRepository(reliability_settings.db_path)
    aggregator = ProviderReliabilityAggregator(repository, reliability_settings)

    now = datetime.now(tz=UTC)
    records = aggregator.compute_and_store(window_minutes=30, reference=now)
    assert len(records) == 1
    record = records[0]
    assert record.captures == 0
    assert record.coverage_ratio == 0
    assert record.metadata is not None
    assert "sin datos" in " ".join(record.metadata.get("notes", []))

    stored = repository.list_provider_reliability_metrics(provider=record.provider)
    assert stored[0].captures == 0


def test_weight_calculator_penalizes_error(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "weights.sqlite",
        timezone="UTC",
        providers=[
            ProviderSettings(name="Proveedor Estable", endpoint="https://mock.local/stable", enabled=True),
            ProviderSettings(name="Proveedor Erratico", endpoint="https://mock.local/volatile", enabled=True),
        ],
        scheduler_interval_seconds=600,
        weight_window_minutes=60,
        weight_floor=0.0,
        weight_delta=0.5,
    )

    repository = MarketRepository(settings.db_path)
    aggregator = ProviderReliabilityAggregator(repository, settings)
    calculator = ProviderWeightCalculator(repository, settings)

    now = datetime.now(tz=UTC)
    for provider in settings.providers:
        metrics = [
            _metric(
                provider=provider.name,
                timestamp=now - timedelta(minutes=idx * 10 + 5),
                success=True,
                latency_ms=120,
                status_code=200,
                attempts=1,
                retries=0,
                error=None,
            )
            for idx in range(3)
        ]
        repository.save_provider_metrics(metrics)

    stable_errors = [0.01, -0.01, 0.02]
    volatile_errors = [0.35, -0.40, 0.50]
    repository.record_provider_error_samples(
        [
            ProviderErrorSample(
                timestamp=now - timedelta(minutes=idx * 10 + 3),
                provider="Proveedor Estable",
                delta_vs_weighted=delta,
                delta_vs_consensus=delta,
                provider_mid=58.40 + delta,
                weighted_mid=58.50,
                consensus_mid=58.48,
                weight=0.5,
            )
            for idx, delta in enumerate(stable_errors)
        ]
        + [
            ProviderErrorSample(
                timestamp=now - timedelta(minutes=idx * 10 + 3),
                provider="Proveedor Erratico",
                delta_vs_weighted=delta,
                delta_vs_consensus=delta,
                provider_mid=58.40 + delta,
                weighted_mid=58.50,
                consensus_mid=58.48,
                weight=0.5,
            )
            for idx, delta in enumerate(volatile_errors)
        ]
    )

    aggregator.compute_and_store(window_minutes=60, reference=now)
    weights = calculator.compute([provider.name for provider in settings.providers], reference=now)

    assert weights["Proveedor Estable"] > weights["Proveedor Erratico"]
    assert pytest.approx(sum(weights.values()), rel=1e-6) == 1.0