from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cambio_dollar.config import ProviderSettings, Settings
from cambio_dollar.models import RateSnapshot
from cambio_dollar.repository import MarketRepository
from cambio_dollar.web.app import create_app


@pytest.fixture()
def web_app(tmp_path: Path) -> TestClient:
    settings = Settings(
        db_path=tmp_path / "web.sqlite",
        timezone="UTC",
        scheduler_enabled=False,
        providers=[
            ProviderSettings(name="Banco A", endpoint=None, enabled=False),
            ProviderSettings(name="Banco B", endpoint=None, enabled=False),
        ],
    )

    repository = MarketRepository(settings.db_path)
    now = datetime.now(UTC)
    for idx in range(6):
        ts = now - timedelta(minutes=idx * 15)
        repository.save_snapshot(
            RateSnapshot(
                timestamp=ts,
                buy_rate=58.10 + idx * 0.02,
                sell_rate=58.55 + idx * 0.02,
                source="Banco A",
                confidence=1.0,
            )
        )
        repository.save_snapshot(
            RateSnapshot(
                timestamp=ts,
                buy_rate=58.20 + idx * 0.01,
                sell_rate=58.70 + idx * 0.01,
                source="Banco B",
                confidence=1.0,
            )
        )

    app = create_app(settings)
    return TestClient(app)


def test_api_consensus_returns_data(web_app: TestClient) -> None:
    response = web_app.get("/api/consensus")
    assert response.status_code == 200
    payload = response.json()
    assert payload["buy_rate"] > 0
    assert payload["providers_considered"] == ["Banco A", "Banco B"]
    assert isinstance(payload.get("anomalies"), list)


def test_api_snapshots_filters_by_minutes(web_app: TestClient) -> None:
    response = web_app.get("/api/snapshots", params={"minutes": 60})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert {snap["source"] for snap in data}.issuperset({"Banco A", "Banco B"})


def test_api_providers_lists_configured(web_app: TestClient) -> None:
    response = web_app.get("/api/providers")
    assert response.status_code == 200
    providers = response.json()
    names = [item["name"] for item in providers]
    assert "Banco A" in names
    assert "Banco B" in names


def test_api_drift_returns_list(web_app: TestClient) -> None:
    response = web_app.get("/api/drift")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dashboard_renders_html(web_app: TestClient) -> None:
    response = web_app.get("/")
    assert response.status_code == 200
    assert "Consenso" in response.text
    assert "IA" in response.text


def test_api_recommendation_returns_payload(web_app: TestClient) -> None:
    response = web_app.get("/api/recommendation")
    assert response.status_code == 200
    body = response.json()
    assert body["action"] in {"buy", "sell", "hold"}
    assert "expected_profit" in body
    assert "reason" in body


def test_api_forecast_returns_projection(web_app: TestClient) -> None:
    response = web_app.get("/api/forecast")
    assert response.status_code == 200
    body = response.json()
    assert "expected_profit_end_day" in body
    assert "best_case" in body


def test_post_analyze_recalculates_recommendation(web_app: TestClient) -> None:
    response = web_app.post("/api/analyze")
    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] in {"buy", "sell", "hold"}


def test_post_forecast_returns_projection(web_app: TestClient) -> None:
    response = web_app.post("/api/forecast")
    assert response.status_code == 200
    payload = response.json()
    assert "expected_profit_end_day" in payload


def test_post_compare_returns_consensus(web_app: TestClient) -> None:
    response = web_app.post("/api/compare")
    assert response.status_code == 200
    payload = response.json()
    assert "providers_considered" in payload
    assert isinstance(payload.get("anomalies"), list)


def test_post_providers_refresh_lists_entries(web_app: TestClient) -> None:
    response = web_app.post("/api/providers/refresh")
    assert response.status_code == 200
    providers = response.json()
    assert isinstance(providers, list)
    assert providers


def test_post_history_returns_trades(web_app: TestClient) -> None:
    response = web_app.post("/api/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
