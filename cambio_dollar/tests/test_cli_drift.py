from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from cambio_dollar.cli import app
from cambio_dollar.config import get_settings
from cambio_dollar.models import DriftDirection, DriftEvent, DriftSeverity
from cambio_dollar.repository import MarketRepository


def _prepare_repo(db_path: Path) -> None:
    repository = MarketRepository(db_path)
    event = DriftEvent(
        timestamp=datetime.now(UTC),
        direction=DriftDirection.UP,
        metric="weighted_mid_rate",
        value=59.25,
        ewma=59.10,
        threshold=0.4,
        cusum_pos=0.52,
        cusum_neg=0.0,
        severity=DriftSeverity.MEDIUM,
        metadata={"providers": 5, "intensity": 2.1},
    )
    repository.record_drift_events([event])


def test_cli_lists_drift_events(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cli_drift.sqlite"
    monkeypatch.setenv("CAMBIO_DB_PATH", str(db_path))
    get_settings.cache_clear()  # type: ignore[attr-defined]
    _prepare_repo(db_path)

    runner = CliRunner()
    result = runner.invoke(app, ["drift"])

    assert result.exit_code == 0
    assert "Eventos de drift" in result.stdout
    assert "UP" in result.stdout or "↑" in result.stdout


def test_cli_help_includes_drift_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "drift" in result.stdout
