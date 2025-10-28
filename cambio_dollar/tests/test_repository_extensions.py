from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cambio_dollar.models import (
    AnomalyEvent,
    AnomalySeverity,
    ExternalMacroMetric,
    FeatureVectorRecord,
    ModelEvaluationRecord,
    PerformanceLabel,
)
from cambio_dollar.repository import MarketRepository


@pytest.fixture()
def repository(tmp_path: Path) -> MarketRepository:
    return MarketRepository(tmp_path / "repo.sqlite")


def test_feature_vector_filters_and_limit(repository: MarketRepository) -> None:
    base = datetime(2025, 10, 8, 12, tzinfo=UTC)
    first = FeatureVectorRecord(
        timestamp=base - timedelta(minutes=10),
        feature_version="v1",
        scope="consensus",
        payload={"lag_1": 0.12, "rsi": 55.0},
        metadata={"window": "10m"},
    )
    second = FeatureVectorRecord(
        timestamp=base - timedelta(minutes=5),
        feature_version="v1",
        scope="provider:banreservas",
        payload={"lag_1": 0.20},
        metadata=None,
    )
    third = FeatureVectorRecord(
        timestamp=base - timedelta(minutes=1),
        feature_version="v2",
        scope="consensus",
        payload={"lag_1": -0.05},
        metadata={"window": "1m"},
    )

    repository.save_feature_vector(first)
    repository.save_feature_vector(second)
    repository.save_feature_vector(third)

    consensus_only = repository.list_feature_vectors(scope="consensus")
    assert [record.scope for record in consensus_only] == ["consensus", "consensus"]
    assert consensus_only[0].timestamp == third.timestamp
    assert consensus_only[0].metadata == {"window": "1m"}

    filtered = repository.list_feature_vectors(scope="consensus", feature_version="v1")
    assert len(filtered) == 1
    assert filtered[0].payload["lag_1"] == pytest.approx(0.12, rel=1e-6)

    recent = repository.list_feature_vectors(since=base - timedelta(minutes=6))
    assert len(recent) == 2
    assert {record.scope for record in recent} == {"provider:banreservas", "consensus"}

    limited = repository.list_feature_vectors(limit=1)
    assert len(limited) == 1
    assert limited[0].scope == "consensus"
    assert limited[0].feature_version == "v2"


def test_performance_labels_filters(repository: MarketRepository) -> None:
    base = datetime(2025, 10, 8, 13, tzinfo=UTC)
    win_label = PerformanceLabel(
        snapshot_timestamp=base - timedelta(minutes=60),
        horizon_minutes=60,
        label="WIN",
        realized_profit=125.5,
        metadata={"threshold": 0.5},
        created_at=base,
    )
    loss_label = PerformanceLabel(
        snapshot_timestamp=base - timedelta(minutes=30),
        horizon_minutes=30,
        label="LOSS",
        realized_profit=-42.0,
        metadata=None,
        created_at=base + timedelta(minutes=5),
    )

    repository.save_performance_label(win_label)
    repository.save_performance_label(loss_label)

    sixty_minutes = repository.list_performance_labels(horizon_minutes=60)
    assert len(sixty_minutes) == 1
    assert sixty_minutes[0].label == "WIN"
    assert sixty_minutes[0].metadata == {"threshold": 0.5}

    since_recent = repository.list_performance_labels(since=base - timedelta(minutes=40))
    assert len(since_recent) == 1
    assert since_recent[0].label == "LOSS"

    limited = repository.list_performance_labels(limit=1)
    assert len(limited) == 1
    assert limited[0].label == "LOSS"


def test_external_macro_upsert(repository: MarketRepository) -> None:
    base = datetime(2025, 10, 8, 15, tzinfo=UTC)
    metric = ExternalMacroMetric(
        timestamp=base,
        source="fred",
        metric="dxy",
        value=101.2,
        metadata={"unit": "index"},
    )
    repository.upsert_macro_metric(metric)

    updated_metric = metric.model_copy(update={"value": 102.4, "metadata": {"unit": "index", "rev": 2}})
    repository.upsert_macro_metric(updated_metric)

    series = repository.get_macro_series(source="fred", metric="dxy")
    assert len(series) == 1
    assert series[0].value == pytest.approx(102.4, rel=1e-6)
    assert series[0].metadata == {"unit": "index", "rev": 2}

    earlier = repository.get_macro_series(since=base + timedelta(minutes=1))
    assert earlier == []


def test_model_evaluation_filters(repository: MarketRepository) -> None:
    base = datetime(2025, 10, 8, 16, tzinfo=UTC)
    first = ModelEvaluationRecord(
        model_name="lightgbm_baseline",
        model_version="v1",
        dataset_version="dataset_v1",
        metric_name="roc_auc",
        metric_value=0.81,
        recorded_at=base - timedelta(hours=2),
        metadata={"folds": 5},
    )
    second = ModelEvaluationRecord(
        model_name="lightgbm_baseline",
        model_version="v2",
        dataset_version="dataset_v1",
        metric_name="roc_auc",
        metric_value=0.84,
        recorded_at=base - timedelta(hours=1),
        metadata={"folds": 10},
    )
    third = ModelEvaluationRecord(
        model_name="xgboost_experimental",
        model_version="alpha",
        dataset_version="dataset_v2",
        metric_name="rmse",
        metric_value=1.25,
        recorded_at=base - timedelta(minutes=30),
        metadata=None,
    )

    repository.save_model_evaluation(first)
    repository.save_model_evaluation(second)
    repository.save_model_evaluation(third)

    baseline_only = repository.list_model_evaluations(model_name="lightgbm_baseline")
    assert len(baseline_only) == 2
    assert [record.model_version for record in baseline_only] == ["v2", "v1"]

    roc_auc_only = repository.list_model_evaluations(metric_name="roc_auc", limit=1)
    assert len(roc_auc_only) == 1
    assert roc_auc_only[0].metric_value == pytest.approx(0.84, rel=1e-6)
    assert roc_auc_only[0].metadata == {"folds": 10}


def test_anomaly_events_persistence(repository: MarketRepository) -> None:
    timestamp = datetime(2025, 10, 8, 17, tzinfo=UTC)
    events = [
        AnomalyEvent(
            timestamp=timestamp,
            provider="Banco Outlier",
            metric="mid_rate",
            detector="zscore_mad",
            score=4.2,
            severity=AnomalySeverity.CRITICAL,
            context={"delta": 2.1, "z_score": 4.2},
        ),
        AnomalyEvent(
            timestamp=timestamp - timedelta(minutes=5),
            provider="Banco B",
            metric="mid_rate",
            detector="zscore_mad",
            score=3.1,
            severity=AnomalySeverity.WARN,
            context=None,
        ),
    ]

    repository.record_anomaly_events(events)

    stored = repository.list_anomalies()
    assert len(stored) == 2
    assert stored[0].severity in {AnomalySeverity.CRITICAL, AnomalySeverity.WARN}
    assert stored[0].context is None or "delta" in stored[0].context

    filtered = repository.list_anomalies(provider="Banco Outlier")
    assert len(filtered) == 1
    assert filtered[0].severity is AnomalySeverity.CRITICAL

    recent = repository.list_anomalies(since=timestamp - timedelta(minutes=3))
    assert len(recent) == 1
    assert recent[0].provider == "Banco Outlier"
