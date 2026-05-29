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
from .models import ForecastResult, RateSnapshot, ConsensusSnapshotRecord
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
        # Intentamos obtener primero los consensus_snapshots históricos
        consensus_records = self.repository.list_consensus_snapshots(limit=self.settings.forecast_points)
        
        if len(consensus_records) >= 5:
            points = [(r.timestamp, r.mid_rate) for r in consensus_records]
            model = self._fit_trend_model_points(points)
            latest_time = consensus_records[0].timestamp
            latest_mid = consensus_records[0].mid_rate
        else:
            # Obtener suficientes rate snapshots
            raw_snapshots = self.repository.iter_snapshots(limit=self.settings.forecast_points * 25)
            
            # Agrupar por timestamp
            grouped: dict[datetime, list[float]] = {}
            for s in raw_snapshots:
                grouped.setdefault(s.timestamp, []).append(s.mid_rate)
            
            # Promediar
            points = [
                (ts, sum(rates) / len(rates))
                for ts, rates in grouped.items()
            ]
            # Ordenar cronológicamente (más recientes primero)
            points.sort(key=lambda x: x[0], reverse=True)
            
            # Limitar al número de forecast points configurado
            points = points[:self.settings.forecast_points]
            
            if len(points) < 5:
                raise RuntimeError(
                    "Se requieren al menos 5 observaciones recientes para generar un pronóstico confiable."
                )
            
            model = self._fit_trend_model_points(points)
            latest_time = points[0][0]
            latest_mid = points[0][1]

        start_of_day = datetime.combine(
            latest_time.astimezone(self._timezone).date(),
            time.min,
            tzinfo=self._timezone,
        )

        realized_profit = self.repository.get_profit_summary(since=start_of_day)
        remaining_hours = self._hours_until_close(latest_time)
        expected_rate = model.intercept + model.slope_per_hour * remaining_hours
        projected_increment = expected_rate - latest_mid

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
                f"{len(points)} observaciones para estimar la variación del tipo de cambio."
            ),
        )

    # ------------------------------------------------------------------
    def _fit_trend_model_points(self, points: list[tuple[datetime, float]]) -> TrendModel:
        # points es una lista de (timestamp, mid_rate), ordenada cronológicamente
        ordered = list(sorted(points, key=lambda p: p[0]))
        base = ordered[0][0]
        hours = np.array([
            (p[0] - base).total_seconds() / 3600.0 for p in ordered
        ])
        if len(hours) < 2 or (hours.max() - hours.min()) < 1e-5:
            raise RuntimeError("Variación temporal insuficiente para calcular tendencia.")
        mid_rates = np.array([p[1] for p in ordered])
        try:
            slope, intercept = np.polyfit(hours, mid_rates, 1)
        except (np.linalg.LinAlgError, ValueError) as exc:
            raise RuntimeError(f"Error de ajuste algebraico en el modelo de forecast: {exc}") from exc
        predicted = intercept + slope * hours
        residuals = mid_rates - predicted
        std_error = float(np.std(residuals))
        return TrendModel(intercept=float(intercept), slope_per_hour=float(slope), std_error=std_error)

    def _hours_until_close(self, timestamp: datetime) -> float:
        local_ts = timestamp.astimezone(self._timezone)
        end_of_day = datetime.combine(local_ts.date(), time(hour=23, minute=59), tzinfo=self._timezone)
        delta = end_of_day - local_ts
        return max(delta.total_seconds() / 3600.0, 0.0)
