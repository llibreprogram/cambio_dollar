# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional

import numpy as np
from zoneinfo import ZoneInfo

from .config import Settings, get_settings
from .models import ForecastResult, RateSnapshot
from .repository import MarketRepository


@dataclass
class TrendModel:
    intercept: float
    slope_per_hour: float
    std_error: float


class ForecastService:
    """Calcula proyecciones de beneficio al cierre del día."""

    def __init__(self, repository: MarketRepository, settings: Optional[Settings] = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self._timezone = ZoneInfo(self.settings.timezone)

    def project_end_of_day_profit(self) -> ForecastResult:
        snapshots = self.repository.iter_snapshots(limit=self.settings.forecast_points)
        if len(snapshots) < 5:
            raise RuntimeError(
                "Se requieren al menos 5 observaciones recientes para generar un pronóstico confiable."
            )
        model = self._fit_trend_model(snapshots)
        latest = snapshots[0]
        start_of_day = datetime.combine(
            latest.timestamp.astimezone(self._timezone).date(),
            time.min,
            tzinfo=self._timezone,
        )

        realized_profit = self.repository.get_profit_summary(since=start_of_day)
        remaining_hours = self._hours_until_close(latest.timestamp)
        expected_rate = model.intercept + model.slope_per_hour * remaining_hours
        current_mid = latest.mid_rate
        projected_increment = expected_rate - current_mid

        expected_unrealized = (
            projected_increment - self.settings.transaction_cost
        ) * self.settings.trading_units
        best_case = expected_unrealized + model.std_error * self.settings.trading_units
        worst_case = expected_unrealized - model.std_error * self.settings.trading_units

        return ForecastResult(
            generated_at=datetime.now(tz=self._timezone),
            expected_profit_end_day=realized_profit + expected_unrealized,
            best_case=realized_profit + best_case,
            worst_case=realized_profit + worst_case,
            confidence_interval=model.std_error * 2 * self.settings.trading_units,
            details=(
                "Regresión lineal sobre las últimas "
                f"{len(snapshots)} observaciones para estimar la variación del tipo de cambio."
            ),
        )

    # ------------------------------------------------------------------
    def _fit_trend_model(self, snapshots: list[RateSnapshot]) -> TrendModel:
        ordered = list(sorted(snapshots, key=lambda s: s.timestamp))
        base = ordered[0].timestamp
        hours = np.array([
            (snap.timestamp - base).total_seconds() / 3600.0 for snap in ordered
        ])
        mid_rates = np.array([snap.mid_rate for snap in ordered])
        slope, intercept = np.polyfit(hours, mid_rates, 1)
        predicted = intercept + slope * hours
        residuals = mid_rates - predicted
        std_error = float(np.std(residuals))
        return TrendModel(intercept=float(intercept), slope_per_hour=float(slope), std_error=std_error)

    def _hours_until_close(self, timestamp: datetime) -> float:
        local_ts = timestamp.astimezone(self._timezone)
        end_of_day = datetime.combine(local_ts.date(), time(hour=23, minute=59), tzinfo=self._timezone)
        delta = end_of_day - local_ts
        return max(delta.total_seconds() / 3600.0, 0.0)
