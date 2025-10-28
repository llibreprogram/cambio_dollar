# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseModel):
    """Describe un proveedor de datos cambiarios."""

    name: str = Field(description="Nombre legible del proveedor.")
    endpoint: Optional[str] = Field(default=None, description="URL del API público o privado del proveedor.")
    format: Literal["json", "html"] = Field(
        default="json", description="Formato del endpoint del proveedor."
    )
    enabled: bool = Field(default=True, description="Permite activar/desactivar el proveedor.")
    method: Literal["GET", "POST"] = Field(
        default="GET", description="Método HTTP utilizado para solicitar los datos."
    )
    buy_path: Optional[str] = Field(
        default=None,
        description="Ruta dentro del payload para obtener la tasa de compra (dot notation).",
    )
    sell_path: Optional[str] = Field(
        default=None,
        description="Ruta dentro del payload para obtener la tasa de venta (dot notation).",
    )
    mid_path: Optional[str] = Field(
        default=None,
        description="Ruta opcional para tasa promedio si el API no expone compra/venta.",
    )
    spread_adjust: float = Field(
        default=0.30,
        ge=0,
        description="Ajuste en DOP para derivar compra/venta a partir de la tasa media.",
    )
    auth_header: Optional[str] = Field(
        default=None, description="Nombre del header para enviar el token del proveedor."
    )
    auth_token_env: Optional[str] = Field(
        default=None,
        description="Nombre de variable de entorno que contiene el token necesario.",
    )
    auth_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapa header → nombre de variable de entorno que contiene su valor.",
    )
    oauth_token_url: Optional[str] = Field(
        default=None,
        description="URL para obtener un token OAuth2 mediante client credentials.",
    )
    oauth_client_id_env: Optional[str] = Field(
        default=None,
        description="Variable de entorno con el client_id para la autenticación OAuth2.",
    )
    oauth_client_secret_env: Optional[str] = Field(
        default=None,
        description="Variable de entorno con el client_secret para la autenticación OAuth2.",
    )
    oauth_scope: Optional[str] = Field(
        default=None,
        description="Scope opcional solicitado al generar el token OAuth2.",
    )
    oauth_audience: Optional[str] = Field(
        default=None,
        description="Audiencia opcional para el flujo client credentials.",
    )
    timeout: float = Field(default=8.0, description="Timeout en segundos para la petición.")
    max_retries: int = Field(
        default=2,
        ge=0,
        description="Cantidad de reintentos ante fallos puntuales del proveedor.",
    )
    backoff_seconds: float = Field(
        default=0.5,
        ge=0,
        description="Tiempo base (en segundos) para el backoff exponencial entre reintentos.",
    )
    retry_status_codes: List[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504],
        description="Códigos HTTP que disparan reintentos automáticos.",
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Si es True, reintenta también ante timeouts o errores de conexión.",
    )


class Settings(BaseSettings):
    """Configuración principal del asistente."""

    model_config = SettingsConfigDict(
        env_prefix="CAMBIO_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    primary_endpoint: str = Field(
        default=(
            "https://api.exchangerate.host/latest"
            "?base=USD&symbols=DOP"
        ),
        description="Endpoint primario para obtener el tipo de cambio USD/DOP.",
    )
    secondary_endpoints: List[str] = Field(
        default_factory=list,
        description="Lista opcional de endpoints alternos para redundancia.",
    )
    providers: List[ProviderSettings] = Field(
        default_factory=lambda: [
            ProviderSettings(
                name="Banco Central RD",
                endpoint="https://api.exchangerate.host/latest?base=USD&symbols=DOP",
                mid_path="rates.DOP",
                spread_adjust=0.20,
                max_retries=1,
            ),
            ProviderSettings(
                name="Banreservas",
                endpoint="https://open.er-api.com/v6/latest/USD",
                mid_path="rates.DOP",
                spread_adjust=0.35,
                max_retries=1,
            ),
            ProviderSettings(
                name="Banco Central RD API v2",
                endpoint=(
                    "https://apis.bancentral.gov.do/indicadoreseconomicos/api/v1/series/3540/valores"
                    "?formato=json&ultimos=1"
                ),
                buy_path="results.0.valor_compra",
                sell_path="results.0.valor_venta",
                auth_headers={"Ocp-Apim-Subscription-Key": "BCRD_API_KEY"},
                timeout=10.0,
                max_retries=3,
                backoff_seconds=1.0,
                enabled=True,
            ),
            ProviderSettings(
                name="Banco Popular",
                endpoint=(
                    "https://api.us-east-a.apiconnect.ibmappdomain.cloud/"
                    "apiportalpopular/bpdsandbox/consultatasa/consultaTasa"
                ),
                buy_path="monedas.moneda[descripcion=USD].compra",
                sell_path="monedas.moneda[descripcion=USD].venta",
                spread_adjust=0.10,
                auth_headers={"X-IBM-Client-Id": "BPD_CLIENT_ID"},
                oauth_token_url=(
                    "https://api.us-east-a.apiconnect.ibmappdomain.cloud/"
                    "apiportalpopular/bpdsandbox/bpd/Authentication/oauth2/token"
                ),
                oauth_client_id_env="BPD_CLIENT_ID",
                oauth_client_secret_env="BPD_CLIENT_SECRET",
                oauth_scope="scope_1",
                enabled=True,
            ),
            ProviderSettings(
                name="InfoDolar",
                endpoint="https://www.infodolar.com.do/",
                format="html",
                enabled=True,
            ),
            ProviderSettings(
                name="Remesas Caribe",
                endpoint="https://api.remesascache.com/v1/rates/USD/DOP",
                buy_path="data.buy_rate",
                sell_path="data.sell_rate",
                max_retries=4,
                backoff_seconds=0.75,
                retry_status_codes=[408, 429, 500, 502, 503, 504],
                retry_on_timeout=True,
                enabled=True,
            ),
            ProviderSettings(name="Capla", enabled=True),
            ProviderSettings(name="Cambio Extranjero", enabled=True),
            ProviderSettings(name="Asociación Romana", enabled=True),
        ],
        description="Configuración de proveedores dominicanos para cotizaciones.",
    )
    db_path: Path = Field(
        default=Path("./data/cambio_dollar.sqlite"),
        description="Ruta del archivo SQLite utilizado para almacenar datos.",
    )
    min_profit_margin: float = Field(
        default=0.5,
        description="Margen mínimo (DOP) requerido por cada USD para considerar una operación rentable.",
    )
    transaction_cost: float = Field(
        default=0.15,
        description="Costo estimado por USD para cubrir comisiones, transporte o riesgo.",
    )
    forecast_points: int = Field(
        default=12,
        description="Cantidad de puntos históricos recientes a considerar en el pronóstico.",
    )
    forecast_interval_minutes: int = Field(
        default=60,
        description="Intervalo en minutos entre observaciones para proyectar el cierre del día.",
    )
    trading_units: float = Field(
        default=1000.0,
        description="Cantidad base de USD utilizada para simular operaciones.",
    )
    timezone: str = Field(
        default="America/Santo_Domingo",
        description="Zona horaria utilizada para reportes y pronósticos.",
    )
    validation_tolerance: float = Field(
        default=0.5,
        ge=0,
        description="Diferencia máxima en DOP aceptada entre proveedores antes de marcar alerta.",
    )
    divergence_threshold: float = Field(
        default=1.0,
        ge=0,
        description="Diferencia absoluta en DOP para considerar un proveedor como outlier.",
    )
    dashboard_refresh_seconds: int = Field(
        default=60,
        ge=10,
        description="Intervalo de actualización sugerido para dashboards en tiempo real.",
    )
    scheduler_enabled: bool = Field(
        default=False,
        description="Activa la captura automática mediante el scheduler embebido.",
    )
    scheduler_interval_seconds: int = Field(
        default=300,
        ge=60,
        description="Intervalo en segundos entre capturas automáticas.",
    )
    server_host: str = Field(
        default="127.0.0.1",
        description="Host de enlace para exponer la API y el dashboard.",
    )
    server_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Puerto TCP utilizado por el servidor web.",
    )
    log_level: str = Field(
        default="INFO",
        description="Nivel global de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    weight_window_minutes: int = Field(
        default=180,
        ge=30,
        description="Ventana en minutos utilizada para calcular pesos dinámicos por proveedor.",
    )
    weight_alpha: float = Field(
        default=0.5,
        ge=0.0,
        description="Coeficiente principal para cobertura en el cálculo de pesos.",
    )
    weight_beta: float = Field(
        default=0.25,
        ge=0.0,
        description="Coeficiente para ratio de éxito en el cálculo de pesos.",
    )
    weight_gamma: float = Field(
        default=0.15,
        ge=0.0,
        description="Coeficiente para latencia normalizada en el cálculo de pesos.",
    )
    weight_delta: float = Field(
        default=0.10,
        ge=0.0,
        description="Coeficiente de penalización por error medio vs consenso.",
    )
    weight_floor: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Peso mínimo asignado a cada proveedor para evitar exclusiones totales.",
    )
    weight_latency_cap_ms: float = Field(
        default=2000.0,
        ge=100.0,
        description="Latencia máxima considerada antes de penalizar completamente al proveedor.",
    )
    weight_error_cap: float = Field(
        default=1.5,
        ge=0.05,
        description="Error absoluto (DOP) a partir del cual se aplica la penalización máxima.",
    )
    weight_baseline_score: float = Field(
        default=0.35,
        ge=0.0,
        description="Puntaje base otorgado a proveedores sin historial suficiente.",
    )
    anomaly_z_threshold: float = Field(
        default=3.0,
        ge=0.5,
        description="Umbral absoluto de z-score a partir del cual se genera una anomalía.",
    )
    anomaly_min_providers: int = Field(
        default=3,
        ge=2,
        description="Cantidad mínima de proveedores para evaluar detección z-score.",
    )
    anomaly_critical_deviation: float = Field(
        default=2.0,
        ge=0.0,
        description="Desviación absoluta (DOP) que eleva la severidad a CRITICAL.",
    )
    drift_ewma_lambda: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="Factor de suavizado para la EWMA del consenso (0-1).",
    )
    drift_cusum_threshold: float = Field(
        default=1.5,
        ge=0.05,
        description="Umbral de CUSUM (DOP) requerido para declarar drift.",
    )
    drift_cusum_drift: float = Field(
        default=0.1,
        ge=0.0,
        description="Factor de corrección (k) aplicado en los acumuladores CUSUM.",
    )
    drift_cooldown_captures: int = Field(
        default=3,
        ge=0,
        description="Capturas durante las cuales se reduce a la mitad el CUSUM tras un evento para evitar rebotes.",
    )
    drift_window_minutes: int = Field(
        default=720,
        ge=30,
        description="Ventana histórica en minutos utilizada para evaluar drift.",
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna la configuración global, cachéada para eficiencia."""

    return Settings()
