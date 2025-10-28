from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from ..models import RateSnapshot
from ..repository import MarketRepository


@dataclass
class TechnicalIndicators:
    """Indicadores técnicos calculados para el mercado de divisas."""

    generated_at: datetime
    rsi: Optional[float] = None  # Relative Strength Index (0-100)
    macd: Optional[float] = None  # MACD line
    macd_signal: Optional[float] = None  # MACD signal line
    macd_histogram: Optional[float] = None  # MACD histogram
    bb_upper: Optional[float] = None  # Bollinger Band superior
    bb_middle: Optional[float] = None  # Bollinger Band media (SMA 20)
    bb_lower: Optional[float] = None  # Bollinger Band inferior
    bb_width: Optional[float] = None  # Ancho de las bandas de Bollinger
    atr: Optional[float] = None  # Average True Range (volatilidad)


@dataclass
class RiskMetrics:
    """Métricas de riesgo del portafolio/simulaciones de trading."""

    generated_at: datetime
    value_at_risk_95: Optional[float] = None  # VaR 95% (1 día)
    value_at_risk_99: Optional[float] = None  # VaR 99% (1 día)
    expected_shortfall_95: Optional[float] = None  # ES 95%
    expected_shortfall_99: Optional[float] = None  # ES 99%
    sharpe_ratio: Optional[float] = None  # Sharpe ratio (anualizado)
    sortino_ratio: Optional[float] = None  # Sortino ratio (anualizado)
    maximum_drawdown: Optional[float] = None  # Drawdown máximo
    calmar_ratio: Optional[float] = None  # Calmar ratio
    win_rate: Optional[float] = None  # Ratio de operaciones ganadoras
    profit_factor: Optional[float] = None  # Factor de profit (ganancias/pérdidas)


@dataclass
class CorrelationAnalysis:
    """Análisis de correlación entre proveedores."""

    generated_at: datetime
    provider_correlations: Dict[str, Dict[str, float]]  # Matriz de correlación
    avg_correlation: float  # Correlación promedio entre proveedores
    max_correlation: float  # Correlación máxima encontrada
    min_correlation: float  # Correlación mínima encontrada
    correlation_clusters: List[List[str]]  # Grupos de proveedores altamente correlacionados


class TechnicalAnalyzer:
    """Analizador técnico avanzado para series de tiempo de divisas."""

    def __init__(self, repository: MarketRepository):
        self.repository = repository

    def compute_indicators(self, *, window_hours: int = 24) -> Optional[TechnicalIndicators]:
        """Calcula indicadores técnicos para la ventana de tiempo especificada."""

        cutoff = datetime.now() - timedelta(hours=window_hours)
        snapshots = list(self.repository.iter_snapshots(since=cutoff))

        if len(snapshots) < 50:  # Necesitamos suficientes datos
            return None

        # Convertir a DataFrame para análisis
        df = self._snapshots_to_dataframe(snapshots)
        if df.empty:
            return None

        # Calcular indicadores
        rsi = self._calculate_rsi(df['mid'])
        macd, macd_signal, macd_hist = self._calculate_macd(df['mid'])
        bb_upper, bb_middle, bb_lower, bb_width = self._calculate_bollinger_bands(df['mid'])
        atr = self._calculate_atr(df)

        return TechnicalIndicators(
            generated_at=datetime.now(),
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_hist,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            bb_width=bb_width,
            atr=atr
        )

    def compute_risk_metrics(self, *, window_days: int = 30) -> Optional[RiskMetrics]:
        """Calcula métricas de riesgo basadas en el historial de operaciones."""

        # Obtener historial de trades
        trades = list(self.repository.list_trades(limit=1000))

        if len(trades) < 10:  # Necesitamos suficientes operaciones
            return None

        # Calcular retornos
        returns = []
        cumulative_returns = [0.0]

        for trade in trades:
            if trade.profit_dop != 0:
                # Calcular retorno como porcentaje del "capital" (usando monto USD como proxy)
                ret = trade.profit_dop / (trade.usd_amount * trade.rate) if trade.rate > 0 else 0
                returns.append(ret)
                cumulative_returns.append(cumulative_returns[-1] + ret)

        if not returns:
            return None

        returns = np.array(returns)
        cumulative_returns = np.array(cumulative_returns[1:])  # Remover el 0 inicial

        # Calcular métricas de riesgo
        var_95, var_99 = self._calculate_var(returns)
        es_95, es_99 = self._calculate_expected_shortfall(returns, var_95, var_99)
        sharpe = self._calculate_sharpe_ratio(returns)
        sortino = self._calculate_sortino_ratio(returns)
        max_dd = self._calculate_maximum_drawdown(cumulative_returns)
        calmar = self._calculate_calmar_ratio(returns, max_dd)
        win_rate = self._calculate_win_rate(trades)
        profit_factor = self._calculate_profit_factor(trades)

        return RiskMetrics(
            generated_at=datetime.now(),
            value_at_risk_95=var_95,
            value_at_risk_99=var_99,
            expected_shortfall_95=es_95,
            expected_shortfall_99=es_99,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            maximum_drawdown=max_dd,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor
        )

    def analyze_correlations(self, *, window_hours: int = 24) -> Optional[CorrelationAnalysis]:
        """Analiza correlaciones entre diferentes proveedores."""

        cutoff = datetime.now() - timedelta(hours=window_hours)
        provider_data = {}

        # Obtener datos por proveedor
        for provider_name in self._get_provider_names():
            snapshots = list(self.repository.iter_snapshots_by_provider(
                provider_name, since=cutoff, limit=1000
            ))
            if len(snapshots) > 10:
                df = self._snapshots_to_dataframe(snapshots)
                provider_data[provider_name] = df['mid']

        if len(provider_data) < 2:
            return None

        # Crear DataFrame con todos los proveedores
        combined_df = pd.DataFrame(provider_data)
        combined_df = combined_df.dropna()

        if combined_df.empty or len(combined_df.columns) < 2:
            return None

        # Calcular matriz de correlación
        corr_matrix = combined_df.corr()

        # Estadísticas de correlación
        correlations = {}
        for col1 in corr_matrix.columns:
            correlations[col1] = {}
            for col2 in corr_matrix.columns:
                correlations[col1][col2] = corr_matrix.loc[col1, col2]

        # Correlación promedio (excluyendo diagonal)
        avg_corr = 0.0
        count = 0
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                avg_corr += corr_matrix.iloc[i, j]
                count += 1
        avg_corr = avg_corr / count if count > 0 else 0.0

        # Máxima y mínima correlación
        max_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].max()
        min_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].min()

        # Identificar clusters (proveedores con correlación > 0.8)
        clusters = self._find_correlation_clusters(correlations, threshold=0.8)

        return CorrelationAnalysis(
            generated_at=datetime.now(),
            provider_correlations=correlations,
            avg_correlation=avg_corr,
            max_correlation=max_corr,
            min_correlation=min_corr,
            correlation_clusters=clusters
        )

    def _snapshots_to_dataframe(self, snapshots: List[RateSnapshot]) -> pd.DataFrame:
        """Convierte snapshots a DataFrame."""
        data = {
            'timestamp': [s.timestamp for s in snapshots],
            'mid': [s.mid_rate for s in snapshots],
            'buy': [s.buy_rate for s in snapshots],
            'sell': [s.sell_rate for s in snapshots]
        }
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calcula el RSI (Relative Strength Index)."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else None
        except Exception:
            return None

    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calcula MACD (Moving Average Convergence Divergence)."""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal).mean()
            macd_hist = macd - macd_signal

            return (
                macd.iloc[-1] if not macd.empty else None,
                macd_signal.iloc[-1] if not macd_signal.empty else None,
                macd_hist.iloc[-1] if not macd_hist.empty else None
            )
        except Exception:
            return None, None, None

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Calcula Bandas de Bollinger."""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            width = (upper - lower) / sma * 100  # Ancho como porcentaje

            return (
                upper.iloc[-1] if not upper.empty else None,
                sma.iloc[-1] if not sma.empty else None,
                lower.iloc[-1] if not lower.empty else None,
                width.iloc[-1] if not width.empty else None
            )
        except Exception:
            return None, None, None, None

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calcula Average True Range."""
        try:
            high = df['sell']  # Usar sell rate como high
            low = df['buy']   # Usar buy rate como low
            close = df['mid']

            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()

            return atr.iloc[-1] if not atr.empty else None
        except Exception:
            return None

    def _calculate_var(self, returns: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
        """Calcula Value at Risk (VaR) al 95% y 99%."""
        try:
            if len(returns) < 10:
                return None, None

            var_95 = np.percentile(returns, 5)  # 5% peor escenario
            var_99 = np.percentile(returns, 1)  # 1% peor escenario

            return float(var_95), float(var_99)
        except Exception:
            return None, None

    def _calculate_expected_shortfall(self, returns: np.ndarray, var_95: Optional[float], var_99: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
        """Calcula Expected Shortfall (ES)."""
        try:
            if var_95 is None or var_99 is None:
                return None, None

            # ES 95%: promedio de retornos por debajo del VaR 95%
            tail_95 = returns[returns <= var_95]
            es_95 = tail_95.mean() if len(tail_95) > 0 else var_95

            # ES 99%: promedio de retornos por debajo del VaR 99%
            tail_99 = returns[returns <= var_99]
            es_99 = tail_99.mean() if len(tail_99) > 0 else var_99

            return float(es_95), float(es_99)
        except Exception:
            return None, None

    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> Optional[float]:
        """Calcula Sharpe Ratio anualizado."""
        try:
            if len(returns) < 2:
                return None

            # Asumir retornos diarios, anualizar multiplicando por sqrt(252)
            daily_rf = risk_free_rate / 252
            excess_returns = returns - daily_rf

            if excess_returns.std() == 0:
                return None

            sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            return float(sharpe)
        except Exception:
            return None

    def _calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> Optional[float]:
        """Calcula Sortino Ratio anualizado."""
        try:
            if len(returns) < 2:
                return None

            daily_rf = risk_free_rate / 252
            excess_returns = returns - daily_rf

            # Solo considerar retornos negativos para el denominador
            downside_returns = excess_returns[excess_returns < 0]

            if len(downside_returns) == 0 or downside_returns.std() == 0:
                return None

            sortino = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
            return float(sortino)
        except Exception:
            return None

    def _calculate_maximum_drawdown(self, cumulative_returns: np.ndarray) -> Optional[float]:
        """Calcula Maximum Drawdown."""
        try:
            if len(cumulative_returns) < 2:
                return None

            peak = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - peak) / peak
            max_dd = drawdown.min()

            return float(abs(max_dd))  # Retornar valor positivo
        except Exception:
            return None

    def _calculate_calmar_ratio(self, returns: np.ndarray, max_dd: Optional[float]) -> Optional[float]:
        """Calcula Calmar Ratio."""
        try:
            if max_dd is None or max_dd == 0 or len(returns) < 2:
                return None

            # Retorno anualizado
            annual_return = returns.mean() * 252

            calmar = annual_return / max_dd
            return float(calmar)
        except Exception:
            return None

    def _calculate_win_rate(self, trades: List) -> Optional[float]:
        """Calcula el ratio de operaciones ganadoras."""
        try:
            if not trades:
                return None

            winning_trades = sum(1 for trade in trades if trade.profit_dop > 0)
            total_trades = len(trades)

            return winning_trades / total_trades if total_trades > 0 else None
        except Exception:
            return None

    def _calculate_profit_factor(self, trades: List) -> Optional[float]:
        """Calcula el factor de profit (ganancias totales / pérdidas totales)."""
        try:
            if not trades:
                return None

            total_wins = sum(trade.profit_dop for trade in trades if trade.profit_dop > 0)
            total_losses = abs(sum(trade.profit_dop for trade in trades if trade.profit_dop < 0))

            return total_wins / total_losses if total_losses > 0 else None
        except Exception:
            return None

    def _get_provider_names(self) -> List[str]:
        """Obtiene lista de nombres de proveedores disponibles."""
        try:
            # Obtener proveedores únicos del historial
            providers = set()
            for snapshot in self.repository.iter_snapshots(limit=1000):
                providers.add(snapshot.source)
            return list(providers)
        except Exception:
            return []

    def _find_correlation_clusters(self, correlations: Dict[str, Dict[str, float]], threshold: float = 0.8) -> List[List[str]]:
        """Encuentra clusters de proveedores altamente correlacionados."""
        try:
            providers = list(correlations.keys())
            clusters = []

            # Algoritmo simple de clustering basado en correlación
            visited = set()

            for provider in providers:
                if provider in visited:
                    continue

                cluster = [provider]
                visited.add(provider)

                # Encontrar proveedores altamente correlacionados
                for other_provider in providers:
                    if other_provider not in visited:
                        corr = correlations[provider].get(other_provider, 0)
                        if abs(corr) >= threshold:
                            cluster.append(other_provider)
                            visited.add(other_provider)

                if len(cluster) > 1:  # Solo clusters con más de un proveedor
                    clusters.append(cluster)

            return clusters
        except Exception:
            return []
