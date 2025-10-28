# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from .config import Settings, get_settings
from .features import MarketFeatureBuilder, MarketFeatures
from .models import RateSnapshot, StrategyRecommendation, StrategyRecommendationRecord, Trade, TradeAction
from .repository import MarketRepository


class StrategyEngine:
    """Generador de recomendaciones basado en análisis técnico simple."""

    def __init__(self, repository: MarketRepository, settings: Optional[Settings] = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self._timezone = ZoneInfo(self.settings.timezone)
        self._feature_builder = MarketFeatureBuilder(repository)

    def generate_recommendation(self) -> StrategyRecommendation:
        features = self._feature_builder.compute()
        if features is None:
            return StrategyRecommendation(
                action=TradeAction.HOLD,
                score=0.0,
                expected_profit=0.0,
                reason="No hay datos almacenados todavía. Ejecuta una captura de mercado primero.",
            )

        if features.provider_count < 3:
            return StrategyRecommendation(
                action=TradeAction.HOLD,
                score=0.2,
                expected_profit=0.0,
                reason="Se requieren al menos tres proveedores activos para una recomendación confiable.",
            )

        recommendation = self._build_recommendation(features)
        self._persist_recommendation(recommendation)
        return recommendation

    def record_trade(
        self,
        action: TradeAction,
        usd_amount: float,
        rate_override: Optional[float] = None,
        fees: Optional[float] = None,
    ) -> Trade:
        snapshot = self.repository.get_latest_snapshot()
        if snapshot is None:
            raise RuntimeError("No hay datos de mercado para registrar una operación.")

        rate = rate_override or (
            snapshot.sell_rate if action is TradeAction.SELL else snapshot.buy_rate
        )
        fees_value = fees if fees is not None else usd_amount * self.settings.transaction_cost
        dop_amount = usd_amount * rate - fees_value if action is TradeAction.SELL else usd_amount * rate + fees_value

        profit = self._calculate_profit(action, usd_amount, rate, snapshot)

        trade = Trade(
            timestamp=datetime.now(tz=self._timezone),
            action=action,
            usd_amount=usd_amount,
            rate=rate,
            fees=fees_value,
            dop_amount=dop_amount,
            profit_dop=profit,
        )
        return self.repository.save_trade(trade)

    def _calculate_profit(
        self,
        action: TradeAction,
        usd_amount: float,
        rate: float,
        snapshot: RateSnapshot,
    ) -> float:
        if action is TradeAction.SELL:
            reference = snapshot.buy_rate
            return (rate - reference - self.settings.transaction_cost) * usd_amount
        reference = snapshot.sell_rate
        return (reference - rate - self.settings.transaction_cost) * usd_amount

    def _build_recommendation(self, features: MarketFeatures) -> StrategyRecommendation:
        gross_spread = features.best_sell_rate - features.best_buy_rate
        net_spread = gross_spread - (2 * self.settings.transaction_cost)
        expected_profit = max(net_spread, 0.0) * self.settings.trading_units
        spread_advantage = gross_spread - features.spread_market

        momentum_score = self._sigmoid(features.momentum_per_hour * 4)
        volatility_penalty = math.exp(-features.volatility * 12)
        base_score = momentum_score * volatility_penalty

        # Construir metadatos detallados para la justificación
        metadata = {
            "momentum_per_hour": round(features.momentum_per_hour, 4),
            "volatility": round(features.volatility, 4),
            "net_spread": round(net_spread, 4),
            "gross_spread": round(gross_spread, 4),
            "spread_advantage": round(spread_advantage, 4),
            "best_buy_rate": round(features.best_buy_rate, 4),
            "best_sell_rate": round(features.best_sell_rate, 4),
            "transaction_cost": self.settings.transaction_cost,
            "trading_units": self.settings.trading_units,
        }

        if expected_profit < self.settings.min_profit_margin * self.settings.trading_units:
            return StrategyRecommendation(
                action=TradeAction.HOLD,
                score=max(base_score * 0.4, 0.1),
                expected_profit=expected_profit,
                reason="El spread disponible no cubre el margen mínimo configurado tras costos.",
                suggested_buy_rate=features.best_buy_rate,
                suggested_sell_rate=features.best_sell_rate,
                spread_advantage=spread_advantage,
                metadata=metadata,
            )

        if features.momentum_per_hour >= 0:
            action = TradeAction.BUY
            suggested_buy = self._adjust_rate(features.best_buy_rate, tighten=True)
            suggested_sell = self._adjust_rate(features.best_sell_rate, tighten=False)
            reason = "Tendencia alcista y spread neto suficiente. Oportunidad de compra."
        else:
            action = TradeAction.SELL
            suggested_buy = features.best_buy_rate
            suggested_sell = self._adjust_rate(features.best_sell_rate, tighten=False)
            reason = "Presión bajista indica oportunidad para vender y capturar spread."

        return StrategyRecommendation(
            action=action,
            score=max(base_score, 0.2),
            expected_profit=expected_profit,
            reason=reason,
            suggested_buy_rate=suggested_buy,
            suggested_sell_rate=suggested_sell,
            spread_advantage=spread_advantage,
            metadata=metadata,
        )

    def _adjust_rate(self, rate: float, *, tighten: bool) -> float:
        """Ajusta ligeramente la tasa para mantener competitividad."""

        tick = max(0.02, self.settings.transaction_cost / 2)
        return rate + tick if not tighten else max(rate - tick, 0)

    @staticmethod
    def _sigmoid(value: float) -> float:
        """Función sigmoide numéricamente estable para evitar overflow."""

        if value >= 0:
            exp_neg = math.exp(-value)
            return 1 / (1 + exp_neg)
        exp_pos = math.exp(value)
        return exp_pos / (1 + exp_pos)

    def _persist_recommendation(self, recommendation: StrategyRecommendation) -> None:
        record = StrategyRecommendationRecord(
            generated_at=datetime.now(tz=self._timezone),
            action=recommendation.action,
            score=recommendation.score,
            expected_profit=recommendation.expected_profit,
            reason=recommendation.reason,
            suggested_buy_rate=recommendation.suggested_buy_rate,
            suggested_sell_rate=recommendation.suggested_sell_rate,
            spread_advantage=recommendation.spread_advantage,
            metadata=recommendation.metadata,
        )
        self.repository.save_recommendation(record)
