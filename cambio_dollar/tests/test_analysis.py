import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest
import numpy as np

from cambio_dollar.analytics import PerformanceAnalyzer, ZScoreAnomalyDetector
from cambio_dollar.config import Settings
from cambio_dollar.forecast import ForecastService
from cambio_dollar.models import (
    AnomalySeverity,
    ConsensusSnapshot,
    ProviderValidation,
    RateSnapshot,
    Trade,
    TradeAction,
)
from cambio_dollar.repository import MarketRepository
from cambio_dollar.strategy import StrategyEngine
from cambio_dollar.features import MarketFeatureBuilder


@pytest.fixture()
def sample_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "cambio.sqlite",
        min_profit_margin=0.05,
        transaction_cost=0.02,
        trading_units=500,
        forecast_points=5,
        timezone="UTC",
    )


@pytest.fixture()
def repository(sample_settings: Settings) -> MarketRepository:
    repo = MarketRepository(Path(sample_settings.db_path))
    load_sample_snapshots(repo)
    return repo


def load_sample_snapshots(repo: MarketRepository) -> None:
    sample_file = Path(__file__).resolve().parents[1] / "data" / "sample_rates.csv"
    with sample_file.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            snapshot = RateSnapshot(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                buy_rate=float(row["buy_rate"]),
                sell_rate=float(row["sell_rate"]),
                source=row["source"],
                confidence=float(row["confidence"]),
            )
            repo.save_snapshot(snapshot)


def test_strategy_generates_action(repository: MarketRepository, sample_settings: Settings) -> None:
    engine = StrategyEngine(repository, sample_settings)
    recommendation = engine.generate_recommendation()
    assert recommendation.action in {TradeAction.BUY, TradeAction.SELL, TradeAction.HOLD}
    assert recommendation.score >= 0


def test_forecast_returns_projection(repository: MarketRepository, sample_settings: Settings) -> None:
    service = ForecastService(repository, sample_settings)
    result = service.project_end_of_day_profit()
    assert result.best_case >= result.worst_case
    assert result.details


def test_analyzer_summarizes_profit(
    repository: MarketRepository, sample_settings: Settings
) -> None:
    repo = repository
    trade = Trade(
        timestamp=datetime.now(UTC),
        action=TradeAction.SELL,
        usd_amount=500,
        rate=58.0,
        fees=5.0,
        dop_amount=500 * 58.0 - 5.0,
        profit_dop=250.0,
    )
    repo.save_trade(trade)
    analyzer = PerformanceAnalyzer(repo, sample_settings)
    summary = analyzer.summarize_day()
    assert summary.realized_profit >= 0
    assert summary.total_trades >= 1


def test_market_features_use_correct_spread(repository: MarketRepository) -> None:
    builder = MarketFeatureBuilder(repository)
    features = builder.compute()
    assert features is not None

    latest_snapshots = list(repository.latest_by_provider().values())
    expected_best_buy = min(s.buy_rate for s in latest_snapshots)
    expected_best_sell = max(s.sell_rate for s in latest_snapshots)
    expected_market_spread = (
        float(np.mean([s.sell_rate for s in latest_snapshots]))
        - float(np.mean([s.buy_rate for s in latest_snapshots]))
    )

    assert features.best_buy_rate == pytest.approx(expected_best_buy, rel=1e-6)
    assert features.best_sell_rate == pytest.approx(expected_best_sell, rel=1e-6)
    assert features.spread_market == pytest.approx(expected_market_spread, rel=1e-6)


def test_zscore_detector_flags_outliers(sample_settings: Settings) -> None:
    tuned_settings = sample_settings.model_copy(
        update={"anomaly_z_threshold": 2.5, "anomaly_critical_deviation": 1.0}
    )
    detector = ZScoreAnomalyDetector(tuned_settings)
    timestamp = datetime.now(UTC)

    consensus = ConsensusSnapshot(
        timestamp=timestamp,
        buy_rate=58.20,
        sell_rate=58.60,
        mid_rate=58.40,
        weighted_buy_rate=58.15,
        weighted_sell_rate=58.55,
        weighted_mid_rate=58.35,
        providers_considered=["Banco A", "Banco B", "Banco Outlier"],
        validations=[
            ProviderValidation(
                provider="Banco A",
                buy_rate=58.10,
                sell_rate=58.50,
                difference_vs_consensus=0.20,
                flagged=False,
                difference_vs_weighted=0.15,
                weight=0.45,
                delta_vs_consensus=-0.20,
                delta_vs_weighted=-0.15,
            ),
            ProviderValidation(
                provider="Banco B",
                buy_rate=58.25,
                sell_rate=58.65,
                difference_vs_consensus=0.25,
                flagged=False,
                difference_vs_weighted=0.30,
                weight=0.35,
                delta_vs_consensus=0.25,
                delta_vs_weighted=0.30,
            ),
            ProviderValidation(
                provider="Banco Outlier",
                buy_rate=60.20,
                sell_rate=60.60,
                difference_vs_consensus=2.20,
                flagged=True,
                difference_vs_weighted=2.25,
                weight=0.20,
                delta_vs_consensus=2.20,
                delta_vs_weighted=2.25,
            ),
        ],
        divergence_range=2.50,
        provider_weights={"Banco A": 0.45, "Banco B": 0.35, "Banco Outlier": 0.20},
        anomalies=[],
    )

    events = detector.detect(consensus)
    assert len(events) == 1
    event = events[0]
    assert event.provider == "Banco Outlier"
    assert event.severity in {AnomalySeverity.WARN, AnomalySeverity.CRITICAL}
    assert event.score >= tuned_settings.anomaly_z_threshold
