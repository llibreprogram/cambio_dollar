from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from cambio_dollar.config import ProviderSettings, Settings
from cambio_dollar.data_provider import ExchangeRateClient, MarketDataService, ProviderFetchResult, _extract_from_path
from cambio_dollar.models import AnomalySeverity, DriftDirection, DriftSeverity, RateSnapshot
from cambio_dollar.repository import MarketRepository


@pytest.fixture()
def sample_providers() -> list[ProviderSettings]:
    return [
        ProviderSettings(
            name="Banco Central",
            endpoint="https://mock.local/bcrd",
            mid_path="rates.DOP",
            spread_adjust=0.30,
        ),
        ProviderSettings(
            name="Banreservas",
            endpoint="https://mock.local/banreservas",
            buy_path="data.buy",
            sell_path="data.sell",
        ),
        ProviderSettings(
            name="Banco Popular",
            endpoint="https://mock.local/popular",
            mid_path="payload.mid",
            spread_adjust=0.40,
        ),
    ]


@pytest.fixture()
def settings(tmp_path: Path, sample_providers: list[ProviderSettings]) -> Settings:
    return Settings(
        db_path=tmp_path / "cambio.sqlite",
        providers=sample_providers,
        timezone="UTC",
        validation_tolerance=0.2,
        divergence_threshold=1.0,
    )


def _mock_responses(now: datetime) -> dict[str, dict]:
    return {
        "https://mock.local/bcrd": {
            "timestamp": now.timestamp(),
            "rates": {"DOP": 58.40},
        },
        "https://mock.local/banreservas": {
            "timestamp": now.timestamp(),
            "data": {"buy": 58.10, "sell": 58.70},
        },
        "https://mock.local/popular": {
            "datetime": now.isoformat(),
            "payload": {"mid": 58.55},
        },
    }


def _transport_for(responses: dict[str, dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = responses.get(str(request.url))
        if payload is None:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_fetch_all_providers_and_consensus(settings: Settings, sample_providers: list[ProviderSettings]) -> None:
    now = datetime.now(UTC)
    transport = _transport_for(_mock_responses(now))

    with httpx.Client(transport=transport) as http_client:
        client = ExchangeRateClient(settings, http_client=http_client)
        results = client.fetch_all()
        assert len(results) == len(sample_providers)

        consensus = client.build_consensus([result.snapshot for result in results])
        assert consensus.providers_considered == [provider.name for provider in sample_providers]
        assert consensus.buy_rate == pytest.approx(58.25, rel=1e-3)
        assert consensus.sell_rate == pytest.approx(58.70, rel=1e-3)
        assert not any(validation.flagged for validation in consensus.validations)
        assert consensus.divergence_range == pytest.approx(0.15, rel=1e-3)
        assert consensus.mid_rate == pytest.approx(58.475, rel=1e-3)
        assert consensus.weighted_buy_rate == pytest.approx(consensus.buy_rate, rel=1e-3)
        assert consensus.weighted_sell_rate == pytest.approx(consensus.sell_rate, rel=1e-3)
        assert consensus.weighted_mid_rate == pytest.approx(58.45, rel=1e-3)
        assert sum(consensus.provider_weights.values()) == pytest.approx(1.0, rel=1e-6)
        assert consensus.anomalies == []


def test_consensus_from_repository(settings: Settings, sample_providers: list[ProviderSettings]) -> None:
    now = datetime.now(UTC)
    transport = _transport_for(_mock_responses(now))

    repo = MarketRepository(settings.db_path)
    with httpx.Client(transport=transport) as http_client:
        client = ExchangeRateClient(settings, http_client=http_client)
        for result in client.fetch_all():
            repo.save_snapshot(result.snapshot)
        client.close()

    service = MarketDataService(repo, settings)
    consensus = service.consensus_from_repository()
    assert len(consensus.validations) == len(sample_providers)
    assert consensus.buy_rate == pytest.approx(58.25, rel=1e-3)
    assert consensus.sell_rate == pytest.approx(58.70, rel=1e-3)
    assert consensus.anomalies == []
    service.close()


def test_build_consensus_flags_outlier(settings: Settings) -> None:
    custom_settings = settings.model_copy(update={"divergence_threshold": 0.5})
    client = ExchangeRateClient(custom_settings)
    base_time = datetime(2025, 10, 5, 15, tzinfo=UTC)
    snapshots = [
        RateSnapshot(
            timestamp=base_time,
            buy_rate=58.20,
            sell_rate=58.60,
            source="Banco A",
            confidence=1.0,
        ),
        RateSnapshot(
            timestamp=base_time.replace(hour=16),
            buy_rate=58.25,
            sell_rate=58.65,
            source="Banco B",
            confidence=1.0,
        ),
        RateSnapshot(
            timestamp=base_time.replace(hour=17),
            buy_rate=60.50,
            sell_rate=61.00,
            source="Proveedor outlier",
            confidence=1.0,
        ),
    ]

    consensus = client.build_consensus(snapshots)
    flagged = {validation.provider: validation.flagged for validation in consensus.validations}
    assert flagged["Proveedor outlier"] is True
    assert any(flagged.values())
    assert consensus.divergence_range == pytest.approx(2.35, rel=1e-3)
    assert consensus.weighted_buy_rate == pytest.approx(consensus.buy_rate, rel=1e-3)
    assert consensus.weighted_sell_rate == pytest.approx(consensus.sell_rate, rel=1e-3)
    assert consensus.anomalies == []
    client.close()


def test_build_consensus_respects_weights(settings: Settings) -> None:
    client = ExchangeRateClient(settings)
    base_time = datetime(2025, 10, 5, 15, tzinfo=UTC)
    snapshots = [
        RateSnapshot(
            timestamp=base_time,
            buy_rate=58.10,
            sell_rate=58.50,
            source="Proveedor A",
            confidence=1.0,
        ),
        RateSnapshot(
            timestamp=base_time,
            buy_rate=58.30,
            sell_rate=58.60,
            source="Proveedor B",
            confidence=1.0,
        ),
        RateSnapshot(
            timestamp=base_time,
            buy_rate=58.55,
            sell_rate=58.90,
            source="Proveedor C",
            confidence=1.0,
        ),
    ]

    weights = {"Proveedor A": 0.6, "Proveedor B": 0.3, "Proveedor C": 0.1}
    consensus = client.build_consensus(snapshots, provider_weights=weights)

    assert consensus.weighted_buy_rate == pytest.approx(58.10, rel=1e-3)
    assert consensus.weighted_sell_rate == pytest.approx(58.50, rel=1e-3)
    expected_mid = sum(snapshot.mid_rate * weights[snapshot.source] for snapshot in snapshots)
    assert consensus.weighted_mid_rate == pytest.approx(expected_mid, rel=1e-6)
    for provider, expected in weights.items():
        assert consensus.provider_weights[provider] == pytest.approx(expected, rel=1e-6)
    assert consensus.anomalies == []
    client.close()


def test_capture_market_records_anomaly_events(tmp_path: Path) -> None:
    providers = [
        ProviderSettings(name="Banco A", endpoint="https://mock.local/a", mid_path="rates.mid"),
        ProviderSettings(name="Banco B", endpoint="https://mock.local/b", mid_path="rates.mid"),
        ProviderSettings(name="Banco Outlier", endpoint="https://mock.local/c", mid_path="rates.mid"),
    ]

    settings = Settings(
        db_path=tmp_path / "anomaly.sqlite",
        providers=providers,
        timezone="UTC",
        anomaly_z_threshold=2.5,
        anomaly_critical_deviation=1.0,
    )

    now = datetime.now(UTC)
    responses = {
        "https://mock.local/a": {"timestamp": now.timestamp(), "rates": {"mid": 58.4}},
        "https://mock.local/b": {"timestamp": now.timestamp(), "rates": {"mid": 58.5}},
        "https://mock.local/c": {"timestamp": now.timestamp(), "rates": {"mid": 62.0}},
    }

    repo = MarketRepository(settings.db_path)
    service = MarketDataService(repo, settings)
    transport = _transport_for(responses)
    with httpx.Client(transport=transport) as http_client:
        service.client.close()
        service.client = ExchangeRateClient(settings, http_client=http_client)
        consensus = service.capture_market()

    service.close()

    assert consensus.anomalies
    providers_flagged = {event.provider for event in consensus.anomalies}
    assert providers_flagged == {"Banco Outlier"}
    assert consensus.anomalies[0].severity in {AnomalySeverity.WARN, AnomalySeverity.CRITICAL}

    stored = repo.list_anomalies()
    assert len(stored) == 1
    assert stored[0].provider == "Banco Outlier"
    assert stored[0].metric == "mid_rate"
    assert stored[0].severity in {AnomalySeverity.WARN, AnomalySeverity.CRITICAL}


def test_extract_from_path_supports_list_filters() -> None:
    payload = {
        "monedas": {
            "moneda": [
                {"descripcion": "USD", "compra": 58.1, "venta": 58.6},
                {"descripcion": "EUR", "compra": 60.0, "venta": 61.0},
            ]
        }
    }

    assert _extract_from_path(payload, "monedas.moneda[descripcion=USD].compra") == pytest.approx(
        58.1
    )
    assert _extract_from_path(payload, "monedas.moneda.1.venta") == pytest.approx(61.0)
    assert _extract_from_path(payload, "monedas.moneda[descripcion=CAD].compra") is None


def test_oauth_flow_fetches_token_and_reuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    provider = ProviderSettings(
        name="Banco Popular OAuth",
        endpoint="https://mock.local/consultatasa",
        buy_path="monedas.moneda[descripcion=USD].compra",
        sell_path="monedas.moneda[descripcion=USD].venta",
        auth_headers={"X-IBM-Client-Id": "BPD_CLIENT_ID"},
        oauth_token_url="https://mock.local/token",
        oauth_client_id_env="BPD_CLIENT_ID",
        oauth_client_secret_env="BPD_CLIENT_SECRET",
        oauth_scope="scope_1",
    )

    settings = Settings(
        db_path=tmp_path / "cambio.sqlite",
        providers=[provider],
        timezone="UTC",
        validation_tolerance=0.2,
        divergence_threshold=1.0,
    )

    monkeypatch.setenv("BPD_CLIENT_ID", "client-id")
    monkeypatch.setenv("BPD_CLIENT_SECRET", "client-secret")

    call_count = {"token": 0, "rates": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == provider.oauth_token_url:
            call_count["token"] += 1
            assert request.method == "POST"
            return httpx.Response(
                200,
                json={
                    "access_token": "abc123",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        if url == provider.endpoint:
            call_count["rates"] += 1
            assert request.headers["Authorization"] == "Bearer abc123"
            assert request.headers["X-IBM-Client-Id"] == "client-id"
            return httpx.Response(
                200,
                json={
                    "monedas": {
                        "moneda": [
                            {"descripcion": "USD", "compra": 58.12, "venta": 58.64},
                            {"descripcion": "EUR", "compra": 60.0, "venta": 61.0},
                        ]
                    }
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = ExchangeRateClient(settings, http_client=http_client)
        first = client.fetch_all()
        second = client.fetch_all()
        client.close()

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].snapshot.buy_rate == pytest.approx(58.12, rel=1e-3)
    assert first[0].snapshot.sell_rate == pytest.approx(58.64, rel=1e-3)
    assert second[0].snapshot.buy_rate == pytest.approx(58.12, rel=1e-3)
    assert second[0].snapshot.sell_rate == pytest.approx(58.64, rel=1e-3)
    assert call_count["token"] == 1
    assert call_count["rates"] == 2


def test_parse_infodolar_html(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "dummy.sqlite",
        providers=[],
        timezone="UTC",
    )
    client = ExchangeRateClient(settings)
    provider = ProviderSettings(name="InfoDolar", endpoint="https://mock.local", format="html")
    sample_html = (Path(__file__).resolve().parent / "data" / "infodolar_sample.html").read_text(encoding="utf-8")

    snapshots = client._parse_html_table(provider, sample_html)
    client.close()

    assert len(snapshots) == 4
    first = snapshots[0]
    assert first.source == "Banreservas"
    assert first.buy_rate == pytest.approx(58.10, rel=1e-6)
    assert first.sell_rate == pytest.approx(58.60, rel=1e-6)
    # Verifica formatos mixtos como comas y ausencia de símbolo
    assert any(s.source == "Casa de Cambio XYZ" and s.buy_rate == pytest.approx(58.20, rel=1e-6) for s in snapshots)


def test_parse_infodolar_html_without_table(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "dummy.sqlite", providers=[], timezone="UTC")
    client = ExchangeRateClient(settings)
    provider = ProviderSettings(name="InfoDolar", endpoint="https://mock.local", format="html")
    snapshots = client._parse_html_table(provider, "<html><body><p>No data</p></body></html>")
    client.close()

    assert snapshots == []


def test_fetch_provider_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ProviderSettings(
        name="Proveedor intermitente",
        endpoint="https://mock.local/intermitente",
        mid_path="rates.DOP",
        spread_adjust=0.3,
        max_retries=2,
        backoff_seconds=0.1,
    )
    settings = Settings(providers=[provider], timezone="UTC")

    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        count = len(attempts)
        attempts.append(1)
        if count == 0:
            return httpx.Response(500, json={"error": "upstream"})
        return httpx.Response(200, json={"rates": {"DOP": 58.45}, "timestamp": 1700000000})

    transport = httpx.MockTransport(handler)

    monkeypatch.setattr(
        ExchangeRateClient,
        "_sleep_backoff",
        staticmethod(lambda provider, attempt: attempts.append(0)),
    )

    with httpx.Client(transport=transport) as http_client:
        client = ExchangeRateClient(settings, http_client=http_client)
        results = client.fetch_all()
        client.close()

    assert len(results) == 1
    assert results[0].snapshot.sell_rate == pytest.approx(58.60, rel=1e-3)
    # Total attempts include initial call + retry; backoff hook registration adds zeros
    assert attempts.count(0) >= 1


    def test_capture_market_emits_drift_event(tmp_path: Path) -> None:
        provider = ProviderSettings(name="Banco Drift", endpoint="https://mock.local/drift", mid_path="rates.mid")
        settings = Settings(
            db_path=tmp_path / "drift.sqlite",
            providers=[provider],
            timezone="UTC",
            drift_ewma_lambda=0.2,
            drift_cusum_threshold=0.4,
            drift_cusum_drift=0.0,
            drift_cooldown_captures=0,
        )

        base_time = datetime.now(UTC)
        series = [
            [
                RateSnapshot(
                    timestamp=base_time,
                    buy_rate=58.0,
                    sell_rate=58.4,
                    source=provider.name,
                    confidence=1.0,
                )
            ],
            [
                RateSnapshot(
                    timestamp=base_time + timedelta(minutes=5),
                    buy_rate=60.5,
                    sell_rate=60.9,
                    source=provider.name,
                    confidence=1.0,
                )
            ],
        ]

        class StubClient(ExchangeRateClient):
            def __init__(self, settings: Settings, batches: list[list[RateSnapshot]]) -> None:
                super().__init__(settings)
                self._batches = batches
                self._index = 0
                self._provider_settings = settings.providers

            def fetch_all(self) -> list[ProviderFetchResult]:
                if self._index >= len(self._batches):
                    raise RuntimeError("Sin datos de prueba disponibles")
                batch = self._batches[self._index]
                self._index += 1
                results: list[ProviderFetchResult] = []
                for snapshot, provider_setting in zip(batch, self._provider_settings):
                    results.append(
                        ProviderFetchResult(
                            provider=provider_setting,
                            snapshots=[snapshot],
                            raw_payload={"test": True},
                        )
                    )
                return results

            def consume_metrics(self) -> list:  # type: ignore[override]
                return []

        repository = MarketRepository(settings.db_path)
        service = MarketDataService(repository, settings)
        service.client.close()
        service.client = StubClient(settings, series)

        first_consensus = service.capture_market()
        assert first_consensus.drift is None
        snapshots = repository.list_consensus_snapshots()
        assert len(snapshots) == 1
        assert repository.list_drift_events() == []

        second_consensus = service.capture_market()
        assert second_consensus.drift is not None
        assert second_consensus.drift.direction == DriftDirection.UP
        assert second_consensus.drift.severity == DriftSeverity.HIGH

        events = repository.list_drift_events()
        assert len(events) == 1
        assert events[0].direction == DriftDirection.UP
        assert events[0].value == pytest.approx(second_consensus.drift.value, rel=1e-6)
        assert events[0].severity == DriftSeverity.HIGH
        assert events[0].metadata is not None
        assert events[0].metadata.get("intensity") == pytest.approx(5.0, rel=1e-3)
        assert len(repository.list_consensus_snapshots()) == 2

        service.close()


def test_provider_metrics_persisted(settings: Settings, sample_providers: list[ProviderSettings], tmp_path: Path) -> None:
    now = datetime.now(UTC)
    responses = _mock_responses(now)
    transport = _transport_for(responses)

    settings_with_db = settings.model_copy(update={"db_path": tmp_path / "metrics.sqlite"})
    repo = MarketRepository(settings_with_db.db_path)
    service = MarketDataService(repo, settings_with_db)
    with httpx.Client(transport=transport) as http_client:
        service.client.close()
        service.client = ExchangeRateClient(settings_with_db, http_client=http_client)
        service.capture_market()
    service.close()

    metrics = repo.list_provider_metrics(limit=10)
    assert len(metrics) == len(sample_providers)
    for metric in metrics:
        assert metric.success is True
        assert metric.latency_ms is not None
        assert metric.attempts >= 1
        assert metric.retries >= 0


def test_provider_metrics_capture_failures(tmp_path: Path) -> None:
    providers = [
        ProviderSettings(
            name="Banco Bueno",
            endpoint="https://mock.local/bueno",
            buy_path="data.buy",
            sell_path="data.sell",
        ),
        ProviderSettings(
            name="Banco Malo",
            endpoint="https://mock.local/malo",
            buy_path="data.buy",
            sell_path="data.sell",
            max_retries=1,
        ),
    ]
    settings = Settings(
        db_path=tmp_path / "metrics_fail.sqlite",
        providers=providers,
        timezone="UTC",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/bueno"):
            return httpx.Response(200, json={"data": {"buy": 58.2, "sell": 58.8}, "timestamp": 1700000000})
        if url.endswith("/malo"):
            return httpx.Response(500, json={"error": "fail"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    repo = MarketRepository(settings.db_path)
    service = MarketDataService(repo, settings)
    with httpx.Client(transport=transport) as http_client:
        service.client.close()
        service.client = ExchangeRateClient(settings, http_client=http_client)
        consensus = service.capture_market()
        assert consensus.buy_rate == pytest.approx(58.2, rel=1e-3)
    service.close()

    metrics = repo.list_provider_metrics(limit=10)
    assert len(metrics) == 2
    failure = next(metric for metric in metrics if metric.provider == "Banco Malo")
    assert failure.success is False
    assert failure.status_code == 500 or failure.status_code is None
    assert failure.error is not None
    assert failure.retries >= 1 or failure.attempts >= 1


def test_capture_market_records_error_samples(
    settings: Settings,
    sample_providers: list[ProviderSettings],
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    responses = _mock_responses(now)
    transport = _transport_for(responses)

    settings_with_db = settings.model_copy(update={"db_path": tmp_path / "errors.sqlite"})
    repo = MarketRepository(settings_with_db.db_path)
    service = MarketDataService(repo, settings_with_db)
    with httpx.Client(transport=transport) as http_client:
        service.client.close()
        service.client = ExchangeRateClient(settings_with_db, http_client=http_client)
        consensus = service.capture_market()
    service.close()

    samples = repo.list_provider_error_samples()
    assert len(samples) == len(sample_providers)
    observed_providers = {sample.provider for sample in samples}
    assert observed_providers == {provider.name for provider in sample_providers}
    for sample in samples:
        assert sample.delta_vs_weighted is None or isinstance(sample.delta_vs_weighted, float)
        assert sample.delta_vs_consensus is None or isinstance(sample.delta_vs_consensus, float)
        assert sample.consensus_mid == pytest.approx(consensus.mid_rate, rel=1e-6)