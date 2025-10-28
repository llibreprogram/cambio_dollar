# Drift Monitoring Playbook

> How we detect and operationalize market regime shifts in Cambio Dollar.

_Last updated: 2025-10-09_

---

## 1. Overview

Phase C introduces statistical drift monitoring so we can react whenever the USD/DOP market departs from the recent regime. We compute a weighted consensus mid-rate every capture, smooth it with an Exponentially Weighted Moving Average (EWMA), and run two-sided Cumulative Sum (CUSUM) detectors to flag persistent shifts.

Drift signals are persisted in SQLite, exposed via the CLI/API/UI, and annotated on the consensus output to keep all surfaces aligned.

## 2. Signal pipeline

1. **Capture** – `MarketDataService.capture_market()` fetches providers, applies weighting, and generates a `ConsensusSnapshot`.
2. **Monitoring** – The `DriftMonitor` ingests the weighted mid-rate (fallback: unweighted mid) and updates EWMA and both CUSUM accumulators.
3. **Decision** – When either CUSUM exceeds the configured threshold (and cooldown is 0), an up/down `DriftEvent` is emitted with supporting telemetry.
4. **Persistence** – Each consensus run is stored in `consensus_snapshots`; drift events land in `drift_events` via `MarketRepository.record_drift_events`.
5. **Surfacing** –
   - CLI: `cambio-dollar drift` lists events, while `fetch` output highlights the latest drift panel.
   - API: `GET /api/drift` returns recent events (default 25).
   - Dashboard: “Eventos de drift recientes” table plus consensus banner badge.

Events include EWMA, thresholds, residual CUSUM values, and metadata such as provider counts and divergence range.

## 3. Configuration cheatsheet

| Setting | Env var | Default | Notes |
| --- | --- | --- | --- |
| `drift_ewma_lambda` | `CAMBIO_DRIFT_EWMA_LAMBDA` | `0.2` | Smoothing factor (0-1). Lower values favor historical stability. |
| `drift_cusum_threshold` | `CAMBIO_DRIFT_CUSUM_THRESHOLD` | `1.5` | Absolute DOP deviation required to emit drift. Tune per market volatility. |
| `drift_cusum_drift` | `CAMBIO_DRIFT_CUSUM_DRIFT` | `0.1` | Slack parameter (k) reducing sensitivity to noise. |
| `drift_cooldown_captures` | `CAMBIO_DRIFT_COOLDOWN_CAPTURES` | `3` | Captures to wait before firing again; halves CUSUM on trigger to avoid double-counting. |
| `drift_window_minutes` | `CAMBIO_DRIFT_WINDOW_MINUTES` | `720` | Historical window to pre-warm monitor on service boot. |

All settings live in `Settings` (`src/cambio_dollar/config.py`). Override via `.env` or environment variables.

## 4. Operational runbook

### 4.1 Warm-up

- The service primes EWMA/CUSUM with the last `drift_window_minutes` of consensus history on startup.
- After configuration tweaks, restart the process or call `MarketDataService.drift_monitor.reset()` (manual scripts only).

### 4.2 Inspecting signals

- **CLI**
  - `make drift` (alias for `cambio-dollar drift`) to list recent events.
  - `make fetch repetitions=1` will show the drift panel when a new event fires.
- **API**
  - `GET /api/drift?limit=10` returns JSON payloads suitable for alerting pipelines.
- **Dashboard**
  - Drift table lists timestamp, direction, EWMA, and threshold so operators can assess confidence quickly.

### 4.3 Tuning guidance

- Start with higher thresholds (`≥ 2.0`) in volatile periods to avoid churn; gradually lower once false positive rate is acceptable.
- Increase `drift_cooldown_captures` if oscillating around the threshold produces repeated alerts.
- Keep `drift_cusum_drift` near zero when you expect clean jumps; raise (e.g., `0.2`) to suppress minor drifts.

### 4.4 Alerting hooks (future work)

- Add notifier services that consume `/api/drift` and push to email/Telegram (Phase 3 roadmap).
- Store drift metadata in monitoring dashboards (e.g., Grafana panel with EWMA vs actual mid).

## 5. Data model

### 5.1 `consensus_snapshots`

| Column | Type | Notes |
| --- | --- | --- |
| `timestamp` | TEXT (ISO) | Consensus capture time |
| `mid_rate` / `weighted_mid_rate` | REAL | Stored for quick EWMA comparisons |
| `divergence_range` | REAL | Spread between provider mids |
| `metadata` | JSON | Includes providers, weights, anomaly counts, optional drift summary |

### 5.2 `drift_events`

| Column | Type | Notes |
| --- | --- | --- |
| `timestamp` | TEXT (ISO) | Event instant (matches consensus timestamp) |
| `direction` | TEXT | `UP` or `DOWN` |
| `metric` | TEXT | `weighted_mid_rate` or `mid_rate` fallback |
| `value` | REAL | Observed mid-rate |
| `ewma` | REAL | Smoothed rate at event |
| `threshold` | REAL | Active CUSUM threshold |
| `cusum_pos` / `cusum_neg` | REAL | Accumulated residuals post-trigger |
| `metadata` | JSON | Cooldown, provider counts, divergence, additional context |

## 6. Validation & tests

- `tests/test_data_provider.py::test_capture_market_emits_drift_event` ensures capture flow emits and persists events.
- `tests/test_web_api.py::test_api_drift_returns_list` covers the REST endpoint contract.
- Full suite (`pytest`) passes, verifying migration #0006 and all integrations.

## 7. Next ideas

- Backfill historical drift events to bootstrap analytics dashboards.
- Add severity scoring (mild/moderate/severe) derived from CUSUM magnitude.
- Integrate drift signals with strategy engine to recalibrate recommendations post-regime change.
