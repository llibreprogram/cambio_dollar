# Anomaly Detection & Provider Weighting Plan

_Last updated: 2025-10-09_

## 1. Objectives

1. Detect and surface anomalous provider quotes in near real time.
2. Assign dynamic weights to providers based on historical reliability, stability, and latency.
3. Quantify market-wide drift so consensus calculations adapt to regime changes.
4. Provide audit trails for downstream strategy decisions (why a provider was down-weighted or flagged).

## 2. Scope & deliverables

| Deliverable | Description | Ownership |
| --- | --- | --- |
| Reliability metrics | Rolling statistics per provider (mean error, std dev vs consensus, availability) persisted for analysis. | Data platform |
| Anomaly engine | Heuristics + statistical detectors (z-score, EWMA, seasonal ESD) that emit `AnomalyEvent` records. | Analytics |
| Weighted consensus | `MarketDataService.build_consensus` accepts provider weights and returns both weighted and unweighted rates. | Analytics |
| Drift monitor | Module that measures global market drift (e.g., CUSUM/KS tests) and adjusts thresholds or triggers alerts. | Analytics |
| Observability | Dashboards/logs summarising provider health, anomalies, and drift state. | Web/API |

## 3. Data model extensions

### Implementado (Fase A · Octubre 2025)

- `provider_fetch_metrics`
   - `id INTEGER PK`, `timestamp TEXT`, `provider TEXT`, `latency_ms REAL`, `status_code INTEGER`, `success INTEGER`, `attempts INTEGER`, `retries INTEGER`, `error TEXT`, `metadata TEXT`
   - Índices en `(timestamp DESC)` y `provider` para consultas recientes.
   - Poblamiento automático desde `MarketDataService.capture_market()` con métricas por intento, incluso en fallos.
- `provider_metrics`
   - `id INTEGER PK`, `provider TEXT`, `window_start TEXT`, `window_end TEXT`, `captures INTEGER`, `attempts INTEGER`, `expected_captures INTEGER`, `coverage_ratio REAL`, `success_ratio REAL`, `mean_latency_ms REAL`, `latency_p50_ms REAL`, `latency_p95_ms REAL`, `mean_error REAL`, `std_error REAL`, `failure_count INTEGER`, `metadata TEXT`, `created_at TEXT`.
   - Restricción única `(provider, window_start, window_end)` + índices en `provider` y `window_end` para consultas rápidas.
   - Rollups generados por `ProviderReliabilityAggregator` (CLI `provider-metrics`) cubren cobertura, tasas de éxito y latencias; los campos de error permanecen `NULL` hasta que se integre el cálculo contra consenso.
- `anomaly_events`
   - `id INTEGER PK`, `timestamp TEXT`, `provider TEXT`, `metric TEXT`, `detector TEXT`, `score REAL`, `severity TEXT`, `context TEXT`
   - Índices en `timestamp DESC` y `provider` para filtros rápidos.
   - Poblamiento desde `ZScoreAnomalyDetector.detect()` vía `repository.record_anomaly_events()` con contexto serializado.

### Próximas migraciones

La tabla de captura sirve como fuente cruda para calcular los rollups de confiabilidad y alimentar el motor de anomalías, mientras que `provider_metrics` conserva los agregados listos para análisis histórico y ponderación. Las siguientes extensiones permanecen pendientes:

1. Campos derivados de error dentro de `provider_metrics` (mean/std) usando consenso leave-one-out.
2. Tabla `drift_events` para consolidar resultados de monitores CUSUM/EWMA (Phase C).

## 4. Provider weighting design

### 4.1 Metrics

For each provider `p` in rolling window `W` (default: last 7 days, fallback to 72 hours):

- **Coverage ratio**: number of captures received ÷ expected captures (per scheduler interval).
- **Stability score**: 1 − (|z-score| averaged across captures), clipped [0,1].
- **Latency P95**: 95th percentile of response time; inverted and normalised to [0,1].
- **Mean absolute error**: average |quote − consensus| using a leave-one-out consensus to avoid circularity.
- **Std deviation of error**: variability relative to peers.

### 4.2 Weight computation

```
w_p = softmax(α * stability_score + β * coverage_ratio + γ * latency_score − δ * mean_error)
```

- Default coefficients: α=0.5, β=0.2, γ=0.1, δ=0.2.
- Apply minimum floor `w_min = 0.05` to avoid zeroing a provider unless blacklisted.
- Optionally cap weights when provider is flagged for recurring anomalies.

### 4.3 Consensus integration

1. Compute weighted median for buy/sell.
2. Report both weighted and unweighted consensus fields for comparison.
3. Pass weights into downstream feature computation (spread, divergence).
4. Expose provider weights via API (`/api/providers`) and dashboard UI.

## 5. Anomaly detection stack

| Detector | Signal | Frequency | Notes |
| --- | --- | --- | --- |
| Z-score (robust median absolute deviation) | Single capture deviations | Realtime (per capture) | Flag when |z| ≥ 3; usa mediana ponderada y omite alertas si MAD < `anomaly_min_mad`. |
| EWMA control chart | Provider mean error | Rolling (every N captures) | Detect small sustained shifts (drift). |
| Seasonal ESD (optional) | Daily/weekly seasonality anomalies | Batch (hourly) | Requires storing history; use `statsmodels` or custom implementation. |
| Volatility spike | Global divergence range | Realtime | Trigger when divergence > threshold × EWMA divergence. |

Each detector emits an `AnomalyEvent` with severity levels (`INFO`, `WARN`, `CRITICAL`). Severity rules:

- CRITICAL if absolute deviation > 2 DOP or provider weight would drop below `w_min`.
- WARN for repeated WARN-level events within 3 hours.

## 6. Drift detection

1. Maintain EWMA of consensus mid-rate `m_t` with smoothing λ=0.2.
2. Compute CUSUM statistics for upward and downward shifts; trigger drift when `G_t` > `h` (e.g., 1.5 DOP).
3. Augment with two-sample KS test comparing last 3h vs prior 24h distribution; p-value < 0.05 indicates regime change.
4. When drift detected:
   - Expand anomaly thresholds temporarily (to avoid over-flagging).
   - Notify strategy module to recalibrate models or escalate risk.

## 7. Implementation phases

### Phase A · Instrumentation (1 sprint)
- ✅ `ExchangeRateClient` registra latencia, status code, reintentos y errores por proveedor.
- ✅ Métricas persistidas en `provider_fetch_metrics` junto a snapshots del mercado.
- ✅ Tests de unidad cubren captura exitosa, reintentos y fallos con verificación en repositorio.
- ✅ Agregador `ProviderReliabilityAggregator` genera rollups (`provider_metrics`) con cobertura, éxito y latencias, disponibles vía CLI `provider-metrics`.
- ⏳ Incorporar cálculo de error vs consenso (campos `mean_error`/`std_error`) y reportería avanzada.

### Phase B · Real-time detection (1 sprint)
- ✅ Implementar consenso ponderado y detector z-score (`ProviderWeightCalculator`, `ZScoreAnomalyDetector`) en `MarketDataService`.
- ✅ Crear modelo `AnomalyEvent` + repositorio (`record_anomaly_events`, `list_anomalies`) con migración `0004_anomaly_events`.
- ✅ Actualizar API/CLI para mostrar anomalías y pesos; suite de pruebas ampliada garantiza consenso estable y registros persistidos.

**Notas clave**

- El detector usa mediana robusta + MAD escalada (`z_threshold` por defecto = 3) y evita falsos positivos cuando `mad` → 0 mediante `anomaly_min_mad`.
- Eventos se serializan con contexto (`raw_quote`, `consensus`, `weight_before`) y severidad calculada según desviación y umbrales configurables.
- Configuración vía `Settings` (`anomaly_z_score_threshold`, `anomaly_min_mad`, `provider_weight_floor`, `provider_weight_window_minutes`) permite ajustes sin despliegues adicionales.

### Phase C · Drift & auto-tuning (1–2 sprints)
- Implement EWMA/CUSUM monitors (dedicated module `analytics/drift.py`).
- Introduce configuration fields: `anomaly_z_threshold`, `anomaly_window_minutes`, `drift_cusum_threshold`, `weight_coefficients`.
- Extend documentation & dashboard for drift insights.

### Phase D · Advanced (future)
- Experiment with Bayesian reliability scoring (Beta distribution on success rate).
- Integrate external macro signals into weighting (e.g., bank classification, liquidity tiers).
- Use anomaly outputs as features for the AI recommendation engine.

## 8. Testing strategy

- **Unit tests**: metrics calculator given synthetic provider histories; z-score/weighted consensus outputs.
- **Property tests**: ensure consensus monotonicity and weight normalisation (sum ≈ 1).
- **Integration tests**: simulate providers with injected anomalies; verify events recorded and weights adjusted.
- **Regression tests**: maintain baseline scenario to guarantee no false anomalies when providers align.

## 9. Operational concerns

- **Backfilling**: daily job to recompute metrics for past captures until rolling windows stabilise.
- **Alerting**: optional Slack/email integration using severity levels.
- **Performance**: metrics computation runs in-memory on latest N captures (< 500 rows), so overhead is minimal.
- **Config management**: new knobs added to `Settings` with environment overrides (`CAMBIO_ANOMALY_*`).

## 10. Dependencies & tooling

- `numpy`, `scipy` (`stats` for KS test, optional seasonal ESD implementation) — consider adding to dependencies.
- `pandas` already available for rolling windows.
- Potential future addition: `river` or `scikit-multiflow` for streaming anomaly detection (not immediate).

## 11. Risks & mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sparse data for new providers | Erroneous low weights | Use Bayesian priors / minimum window size before weighting. |
| False positives from market shocks | Alert fatigue, wrong decisions | Combine drift detection to raise thresholds temporarily. |
| Increased latency | Delays consensus | Pre-compute metrics asynchronously and cache weights for next capture. |
| SQLite limitations | Migration complexity | Use Alembic patterns (create temp table, copy data). |

## 12. Next steps

1. Calcular error vs consenso en `provider_metrics` (leave-one-out) y propagar pesos dinámicos a reportes históricos.
2. Expandir detectores: EWMA control chart + monitoreo global de divergencia; preparar tabla `drift_events`.
3. Exponer métricas de confiabilidad y anomalías en dashboard/API con visualizaciones y alertas configurables.
4. Ejecutar replays históricos para calibrar severidades y validar thresholds adaptativos.
