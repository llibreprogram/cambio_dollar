# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd

from .models import RateSnapshot
from .repository import MarketRepository


@dataclass
class MarketFeatures:
    generated_at: datetime
    provider_count: int
    best_buy_rate: float
    best_sell_rate: float
    avg_buy_rate: float
    avg_sell_rate: float
    spread_market: float
    spread_best: float
    divergence: float
    momentum_per_hour: float
    volatility: float


class MarketFeatureBuilder:
    """Calcula indicadores clave para la toma de decisiones."""

    def __init__(self, repository: MarketRepository) -> None:
        self.repository = repository

    def compute(self, *, window_minutes: int = 240) -> Optional[MarketFeatures]:
        latest = self.repository.latest_by_provider()
        if not latest:
            return None

        latest_snapshots: List[RateSnapshot] = list(latest.values())
        generated_at = max(s.timestamp for s in latest_snapshots)

        # Métricas instantáneas
        best_buy_rate = min(s.buy_rate for s in latest_snapshots)
        best_sell_rate = max(s.sell_rate for s in latest_snapshots)
        avg_buy_rate = float(np.mean([s.buy_rate for s in latest_snapshots]))
        avg_sell_rate = float(np.mean([s.sell_rate for s in latest_snapshots]))
        spread_market = avg_sell_rate - avg_buy_rate
        spread_best = best_sell_rate - best_buy_rate
        divergence = max(s.mid_rate for s in latest_snapshots) - min(s.mid_rate for s in latest_snapshots)

        # Historial reciente para momentum/volatilidad
        cutoff = generated_at - timedelta(minutes=window_minutes)
        history = self.repository.iter_snapshots(since=cutoff)
        volatility = 0.0
        momentum = 0.0
        if len(history) > 1:
            df = _snapshots_to_frame(history)
            df = df.sort_index()
            pct = df["mid"].pct_change().dropna()
            if not pct.empty:
                volatility = float(pct.std())
            elapsed = (df.index - df.index[0]).total_seconds() / 3600.0
            if len(df) > 1 and np.ptp(elapsed) > 0:
                slope, _ = np.polyfit(elapsed, df["mid"].to_numpy(), 1)
                momentum = float(slope)

        return MarketFeatures(
            generated_at=generated_at,
            provider_count=len(latest_snapshots),
            best_buy_rate=best_buy_rate,
            best_sell_rate=best_sell_rate,
            avg_buy_rate=avg_buy_rate,
            avg_sell_rate=avg_sell_rate,
            spread_market=spread_market,
            spread_best=spread_best,
            divergence=divergence,
            momentum_per_hour=momentum,
            volatility=volatility,
        )


def _snapshots_to_frame(history: Iterable[RateSnapshot]) -> pd.DataFrame:
    data = {
        "timestamp": [snap.timestamp for snap in history],
        "mid": [snap.mid_rate for snap in history],
    }
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    return df
