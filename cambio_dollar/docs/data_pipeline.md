# Diseño del pipeline de datos · Cambio Dollar

## 1. Arquitectura general

```
Providers/API → Ingesta (scheduler/manual) → Almacenamiento bruto (snapshots)
      │                                         ↓
      ├─ Enriquecimiento externo (macro, FX global, noticias)
      │                                         ↓
      └→ Construcción de features → Dataset maestro (training/inferencia)
                                              ↓
                                      Backtesting · Model Training · Serving
```

## 2. Componentes de almacenamiento

| Tabla/Vista | Propósito | Campos clave | Fuente |
|-------------|-----------|--------------|--------|
| `rate_snapshots` | Capturas originales por proveedor | timestamp, provider, buy/sell, confidence | `MarketDataService.capture_market()` |
| `consensus_snapshots` | Resumen consolidado por captura | timestamp, buy/sell consenso, divergence | Calculado tras captura |
| `provider_fetch_metrics` (nuevo) | Telemetría operativa por proveedor | timestamp, provider, latency_ms, status_code, success, attempts, retries, error, metadata | `MarketDataService.capture_market()` |
| `provider_metrics` (nuevo) | Rollups de confiabilidad por ventana deslizante | window_start, window_end, coverage_ratio, success_ratio, latencias p50/p95, failure_count, metadata | `ProviderReliabilityAggregator.compute_and_store()` |
| `features_runtime` | Features calculados por el motor actual | timestamp, spread, momentum, volatility, provider_count, etc. | `MarketFeatureBuilder.compute()` |
| `strategy_recommendations` | Recomendaciones emitidas | generated_at, action, score, expected_profit, suggested rates | `StrategyEngine.save_recommendation()` |
| `trades` | Operaciones reales/simuladas | timestamp, action, usd_amount, rate, profit | CLI/API trade |
| `feature_store` (nueva) | Features enriquecidos históricos | timestamp, provider-level signals, macro feats, technical indicators | ETL nocturna/scheduler |
| `labels_performance` (nueva) | Etiquetas de performance | timestamp, label (win/loss/hold), realized_profit, horizon | Post-backtest o paper trading |
| `external_macro` (nueva) | Datos macro/económicos | timestamp, indicadores (DXY, tasas, commodities) | API externas (e.g. FRED, AlphaVantage) |
| `news_sentiment` (opcional) | Señales de sentimiento | timestamp, fuente, score | NLP sobre RSS/Twitter |

### Formatos adicionales
- **Dataset maestro**: archivos Parquet/Delta/duckdb en `data/processed/` versionados por fecha/commit.  
- **Feature store ligera**: SQLite extendida o DuckDB; para escala mayor, contemplar Snowflake/BigQuery.

## 3. Flujos de ingestión

### Capturas primarias (existente)
1. Scheduler ejecuta `MarketDataService.capture_market()` cada X minutos.
2. Guarda snapshots y consenso.
3. Llama a pipeline de features runtime.
4. Almacena recomendación y triggers opcionales para notificaciones.

### Enriquecimiento externo (nuevo)
- **Frecuencia**: diaria u horaria según fuente.
- **Fuentes sugeridas**:
  - Índice DXY, tasas Fed Funds, bonos US10Y (FRED API).
  - Volatilidad FX (Bloomberg alternativo, Quandl).
  - Commodities (Gold, Oil), Crypto USD/USDT spreads.
  - Sentimiento (Twitter, Reddit) vía APIs o scraping controlado.
- **Procesamiento**: scripts ETL (Python) usando `requests`/`pandas`; validación de schema y valores.
- **Almacenamiento**: tabla `external_macro` y capa Parquet.

### Construcción de features
- Consolidar snapshots + macro + indicadores técnicos.  
- Generar series derivadas: medias móviles, RSI, MACD, bandas de Bollinger, momentum normalizado, spreads percentuales.  
- Guardar en `feature_store` con versión del pipeline (`feature_version` campo).

### Etiquetado
- Definir horizontes: H1, H4, D1.  
- Calcular profit potencial vs. consenso a futuro (look-ahead).  
- Etiquetar trades simulados como `WIN/LOSS/HOLD` o probabilidades continuas.
- Guardar en `labels_performance` con referencia a `feature_id`/`snapshot_id`.

## 4. Dataset maestro y versionado
- Script `scripts/build_dataset.py` que:
  1. Extrae datos brutos desde SQLite/DuckDB.
  2. Combina con features y etiquetas.
  3. Aplica limpieza (outliers, nulls), escalado opcional.
  4. Exporta a `data/processed/dataset_YYYYMMDD.parquet`.
  5. Registra metadatos (versión de features, fuentes, tamaño).
- Versionado: nombrar por fecha + hash corto; opcional usar `dvc` o `mlflow artifacts`.

## 5. Validación de datos
- **Tests automáticos** (pytest o `great_expectations`):
  - Rango válido para tasas (50–80 DOP).  
  - No faltantes en campos críticos (timestamp, buy/sell).  
  - Divergencia ≤ umbral configurado salvo alerta registrada.  
  - Consistencia temporal (timestamps ordenados).
- **Alertas**: notificar si falta data de proveedores clave o si API externa falla.

## 6. Integración con entrenamiento e inferencia
- **Entrenamiento**: notebooks/scripts leen dataset maestro con `pandas`/`polars`.  
- **Inferencia en producción**: 
  - Pipeline en `StrategyEngine` consulta `feature_store` y ejecuta modelo ML.  
  - Fallback heurístico si faltan features o modelo invalida.
- **Reentrenamiento**: scheduler semanal que reconstruye dataset, entrena y evalúa; si pasa umbral → versiona modelo.

## 7. Herramientas recomendadas
- `pandas`, `polars`, `sqlalchemy` para ETL con SQLite/DuckDB.  
- `mlflow`/`weights & biases` para versionar datasets y modelos.  
- `great_expectations` o `pandera` para validaciones.  
- `prefect`/`airflow` (futuro) para orquestar pipelines complejos.

## 8. Próximos pasos
1. Implementar tablas nuevas en `repository.py` + migraciones.  
2. Crear script ETL base para macro datos y guardado en `external_macro`.  
3. Construir función `compute_offline_features()` que alimente `feature_store`.  
4. Automatizar build del dataset maestro y validaciones iniciales.
