# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class RateSnapshot(BaseModel):
    """Representa una lectura puntual del mercado."""

    timestamp: datetime = Field(description="Fecha y hora de la cotización.")
    buy_rate: float = Field(gt=0, description="Precio en DOP por 1 USD al comprar dólares.")
    sell_rate: float = Field(gt=0, description="Precio en DOP por 1 USD al vender dólares.")
    source: str = Field(description="Nombre del proveedor del dato.")
    confidence: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Confianza relativa (0-1) en la exactitud del dato.",
    )

    @property
    def mid_rate(self) -> float:
        return (self.buy_rate + self.sell_rate) / 2

    @property
    def spread(self) -> float:
        return self.sell_rate - self.buy_rate


class Trade(BaseModel):
    """Describe una operación de compra o venta de divisa."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Marca de tiempo de la operación")
    action: TradeAction = Field(description="Tipo de operación realizada")
    usd_amount: float = Field(gt=0, description="Monto de USD operado")
    rate: float = Field(gt=0, description="Tasa aplicada en DOP por USD")
    fees: float = Field(ge=0, description="Costos asociados en DOP")
    dop_amount: float = Field(description="Monto total en DOP luego de la operación")
    profit_dop: float = Field(description="Ganancia o pérdida realizada en DOP")


class StrategyRecommendation(BaseModel):
    """Recomendación emitida por la estrategia."""

    action: TradeAction
    score: float = Field(description="Intensidad de la recomendación (0-1)")
    expected_profit: float = Field(description="Ganancia estimada en DOP para el bloque estándar de USD")
    reason: str = Field(description="Explicación breve de la recomendación")
    suggested_buy_rate: Optional[float] = Field(default=None, description="Tasa sugerida para comprar USD")
    suggested_sell_rate: Optional[float] = Field(default=None, description="Tasa sugerida para vender USD")
    spread_advantage: Optional[float] = Field(
        default=None,
        description="Ventaja esperada (en DOP) frente al consenso actual",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos adicionales para la justificación detallada.",
    )


class StrategyRecommendationRecord(StrategyRecommendation):
    """Recomendación persistida en la base de datos."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    generated_at: datetime = Field(description="Marca de tiempo de la recomendación")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos adicionales para la justificación detallada.",
    )


class FeatureVectorRecord(BaseModel):
    """Representa un conjunto de features calculados para entrenamiento/inferencia."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Marca de tiempo asociada al conjunto de features")
    feature_version: str = Field(description="Versión del pipeline de features utilizado")
    scope: str = Field(description="Ámbito del feature set (consensus, provider, macro, etc.)")
    payload: Dict[str, float] = Field(description="Mapa de feature → valor numérico")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Información adicional (ventanas, proveedor, notas)",
    )


class PerformanceLabel(BaseModel):
    """Etiqueta derivada para entrenamiento supervisado."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    snapshot_timestamp: datetime = Field(description="Marca de tiempo de referencia del snapshot")
    horizon_minutes: int = Field(ge=1, description="Horizonte utilizado para calcular la etiqueta")
    label: str = Field(description="Clasificación asignada (ej. WIN, LOSS, HOLD)")
    realized_profit: Optional[float] = Field(
        default=None,
        description="Ganancia/pérdida observada en DOP para el horizonte definido",
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Datos adicionales")
    created_at: datetime = Field(description="Fecha de generación de la etiqueta")


class ExternalMacroMetric(BaseModel):
    """Dato macroeconómico o contextual externo al mercado local."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Marca de tiempo del dato externo")
    source: str = Field(description="Fuente del indicador (e.g. FRED, AlphaVantage)")
    metric: str = Field(description="Nombre del indicador (e.g. DXY, FED_FUNDS)")
    value: Optional[float] = Field(default=None, description="Valor numérico del indicador")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Detalle adicional")


class ModelEvaluationRecord(BaseModel):
    """Resultado de la evaluación o backtesting de un modelo."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    model_name: str = Field(description="Nombre lógico del modelo (e.g. lightgbm_baseline)")
    model_version: str = Field(description="Versión o hash del modelo")
    dataset_version: Optional[str] = Field(default=None, description="Versión del dataset utilizado")
    metric_name: str = Field(description="Nombre de la métrica registrada")
    metric_value: float = Field(description="Valor de la métrica")
    recorded_at: datetime = Field(description="Fecha de registro de la métrica")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales")


class ForecastResult(BaseModel):
    """Salida del módulo de pronósticos."""

    generated_at: datetime
    expected_profit_end_day: float
    best_case: float
    worst_case: float
    confidence_interval: float = Field(
        description="Amplitud del intervalo de confianza expresado en DOP"
    )
    details: str = Field(description="Explicación del método y supuestos utilizados")


class ProviderValidation(BaseModel):
    """Detalle de la validación cruzada entre proveedores."""

    provider: str = Field(description="Nombre del proveedor evaluado")
    buy_rate: float = Field(description="Tasa de compra reportada")
    sell_rate: float = Field(description="Tasa de venta reportada")
    difference_vs_consensus: float = Field(
        description="Diferencia absoluta frente a la tasa consenso"
    )
    flagged: bool = Field(description="Indica si el proveedor fue marcado como outlier")
    difference_vs_weighted: Optional[float] = Field(
        default=None,
        description="Diferencia absoluta frente a la tasa consenso ponderada",
    )
    weight: Optional[float] = Field(
        default=None,
        description="Peso asignado al proveedor en el consenso ponderado",
    )
    delta_vs_consensus: Optional[float] = Field(
        default=None,
        description="Diferencia firmada frente a la tasa consenso",
    )
    delta_vs_weighted: Optional[float] = Field(
        default=None,
        description="Diferencia firmada frente a la tasa consenso ponderada",
    )
    difference_vs_weighted: Optional[float] = Field(
        default=None,
        description="Diferencia absoluta frente a la tasa consenso ponderada",
    )
    weight: Optional[float] = Field(
        default=None,
        description="Peso asignado al proveedor en el consenso ponderado",
    )


class ConsensusSnapshot(BaseModel):
    """Resumen consolidado a partir de múltiples proveedores."""

    timestamp: datetime
    buy_rate: float
    sell_rate: float
    mid_rate: float = Field(description="Tasa media derivada del consenso no ponderado")
    weighted_buy_rate: Optional[float] = Field(
        default=None,
        description="Tasa de compra resultante del consenso ponderado",
    )
    weighted_sell_rate: Optional[float] = Field(
        default=None,
        description="Tasa de venta resultante del consenso ponderado",
    )
    weighted_mid_rate: Optional[float] = Field(
        default=None,
        description="Tasa media resultante del consenso ponderado",
    )
    providers_considered: List[str]
    validations: List[ProviderValidation]
    divergence_range: float = Field(
        description="Rango max-min observado entre proveedores"
    )
    provider_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapa proveedor → peso aplicado en el consenso ponderado",
    )
    anomalies: List["AnomalyEvent"] = Field(
        default_factory=list,
        description="Eventos de anomalía detectados durante la captura",
    )
    drift: Optional["DriftEvent"] = Field(
        default=None,
        description="Evento de drift detectado en la captura (si aplica).",
    )


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class AnomalyEvent(BaseModel):
    """Evento generado por un detector de anomalías."""

    id: Optional[int] = Field(default=None, description="Identificador de la anomalía")
    timestamp: datetime = Field(description="Instante en el que se produjo la anomalía")
    provider: str = Field(description="Proveedor evaluado")
    metric: str = Field(description="Nombre de la métrica observada")
    detector: str = Field(description="Nombre del detector que generó el evento")
    score: float = Field(description="Puntaje numérico del detector (ej. z-score absoluto)")
    severity: AnomalySeverity = Field(description="Nivel de severidad asignado")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detalles adicionales útiles para auditoría",
    )

class ProviderFetchMetric(BaseModel):
    """Métrica operacional por captura de proveedor."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Momento en que se completó la captura")
    provider: str = Field(description="Nombre del proveedor")
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Tiempo de respuesta de la última solicitud exitosa (ms)",
    )
    status_code: Optional[int] = Field(
        default=None,
        description="Código HTTP de la última respuesta recibida",
    )
    success: bool = Field(description="Indica si la captura obtuvo datos válidos")
    attempts: int = Field(ge=1, description="Número de intentos realizados")
    retries: int = Field(ge=0, description="Cantidad de reintentos luego del primer intento")
    error: Optional[str] = Field(
        default=None,
        description="Detalle del último error encontrado (si aplica)",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Información adicional (ej. backoff utilizado, tamaño del payload)",
    )


class ProviderReliabilityMetrics(BaseModel):
    """Resumen agregado de confiabilidad para un proveedor en una ventana de tiempo."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    provider: str = Field(description="Proveedor evaluado")
    window_start: datetime = Field(description="Inicio de la ventana evaluada")
    window_end: datetime = Field(description="Fin de la ventana evaluada")
    captures: int = Field(ge=0, description="Capturas exitosas registradas en la ventana")
    attempts: int = Field(ge=0, description="Total de intentos (exitosos o fallidos)")
    expected_captures: int = Field(ge=1, description="Capturas esperadas según scheduler")
    coverage_ratio: float = Field(ge=0, description="Porcentaje de capturas exitosas vs esperadas")
    success_ratio: float = Field(ge=0, description="Capturas exitosas sobre intentos totales")
    mean_latency_ms: Optional[float] = Field(default=None, ge=0, description="Latencia promedio observada")
    latency_p50_ms: Optional[float] = Field(default=None, ge=0, description="Percentil 50 de latencia")
    latency_p95_ms: Optional[float] = Field(default=None, ge=0, description="Percentil 95 de latencia")
    mean_error: Optional[float] = Field(default=None, description="Error medio vs. consenso (DOP)")
    std_error: Optional[float] = Field(default=None, description="Desviación estándar del error")
    failure_count: int = Field(ge=0, description="Intentos fallidos en la ventana")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Estadísticas auxiliares")
    created_at: Optional[datetime] = Field(default=None, description="Instante de generación del registro")


class ProviderErrorSample(BaseModel):
    """Registro granular del error de un proveedor frente al consenso."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Instante en el que se evaluó el proveedor")
    provider: str = Field(description="Nombre del proveedor evaluado")
    delta_vs_weighted: Optional[float] = Field(
        default=None,
        description="Diferencia firmada frente al consenso ponderado (mid).",
    )
    delta_vs_consensus: Optional[float] = Field(
        default=None,
        description="Diferencia firmada frente al consenso no ponderado (mid).",
    )
    provider_mid: Optional[float] = Field(
        default=None,
        description="Tasa media reportada por el proveedor en la captura.",
    )
    weighted_mid: Optional[float] = Field(
        default=None,
        description="Tasa media ponderada empleada como referencia en la captura.",
    )
    consensus_mid: float = Field(description="Tasa media del consenso no ponderado.")
    weight: Optional[float] = Field(
        default=None,
        description="Peso aplicado al proveedor en el consenso ponderado.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Información adicional (por ejemplo, divergencia absoluta).",
    )


class ConsensusSnapshotRecord(BaseModel):
    """Registro persistido de un consenso generado en una captura."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Instante del consenso")
    buy_rate: float = Field(description="Tasa de compra mediana")
    sell_rate: float = Field(description="Tasa de venta mediana")
    mid_rate: float = Field(description="Tasa media no ponderada")
    weighted_buy_rate: Optional[float] = Field(default=None, description="Tasa de compra ponderada")
    weighted_sell_rate: Optional[float] = Field(default=None, description="Tasa de venta ponderada")
    weighted_mid_rate: Optional[float] = Field(default=None, description="Tasa media ponderada")
    divergence_range: float = Field(description="Rango max-min observado")
    provider_count: int = Field(description="Cantidad de proveedores considerados")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Información adicional")


class DriftDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class DriftSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DriftEvent(BaseModel):
    """Evento que describe un cambio de régimen detectado por el monitor de drift."""

    id: Optional[int] = Field(default=None, description="Identificador de base de datos")
    timestamp: datetime = Field(description="Instante del evento")
    direction: DriftDirection = Field(description="Dirección del shift detectado")
    metric: str = Field(description="Nombre de la métrica monitoreada (ej. mid_rate)")
    value: float = Field(description="Valor observado del indicador en el evento")
    ewma: float = Field(description="Valor de la EWMA en el momento del evento")
    threshold: float = Field(description="Umbral CUSUM utilizado")
    cusum_pos: float = Field(description="Acumulador positivo tras el evento")
    cusum_neg: float = Field(description="Acumulador negativo tras el evento")
    severity: DriftSeverity = Field(description="Clasificación de severidad del evento")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Detalles adicionales")


ConsensusSnapshot.model_rebuild()
