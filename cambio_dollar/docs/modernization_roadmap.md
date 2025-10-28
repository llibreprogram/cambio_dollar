# Cambio Dollar · Modernization Roadmap

> Living document tracking the evolution of the project towards a state-of-the-art FX assistant with production-grade AI.

_Last updated: 2025-10-09_

---

## 1. Project snapshot (Q4 2025)

- **Core scope**: data ingestion for USD/DOP, recommendation engine, forecast module, CLI + FastAPI dashboard.
- **Strengths**
  - Clean separation between configuration, data providers, analytics, and presentation.
  - Extensive Pydantic models and repository abstractions for persistence.
  - Functional FastAPI layer with dashboard and REST endpoints.
  - Good automated test coverage for providers, strategy, forecast, repository, and web.
  - Real-time provider weighting, anomaly detection, and drift monitoring wired into capture workflow with persistence and CLI visibility.
- **Current risks & gaps**
  - `MarketFeatureBuilder` inversions (`best_buy_rate` vs `best_sell_rate`) impacting spreads.
  - HTML scraping brittle against InfoDolar markup changes.
  - Logging always set to DEBUG in CLI, noisy for production.
  - Forecast assumes evenly spaced data and simple linear trend; needs robustness.
  - Missing MLOps hygiene (model registry, experiment tracking, automated retraining).
  - No CI pipeline or packaging automation documented.

## 2. Vision statement

Deliver the most reliable, real-time USD/DOP trading companion in the Dominican Republic, powered by:

1. **Trusted market intelligence** sourced from official APIs, banks, and alternative channels with automated validation.
2. **Adaptive AI strategies** that learn from historical trades, macro indicators, and user feedback.
3. **Unified experiences** across CLI, REST, and a responsive web dashboard with proactive alerts.
4. **Operational excellence** with automated testing, continuous deployment, and observability.

## 3. Modernization pillars

| Pillar | Objective | Key Outcomes |
| --- | --- | --- |
| **Data Reliability** | Expand & harden provider ingestion | OAuth-ready connectors, parser resilience, anomaly detection |
| **AI & Analytics** | Upgrade recommendation/forecast engines | Feature store, ML experiments, reinforcement learning loops |
| **Product Experience** | Elevate UX across channels | Real-time dashboard, alerting, mobile-friendly UI |
| **Platform Engineering** | Streamline operations & deployment | CI/CD, packaging, containerization, observability |

## 4. Phased roadmap

### Phase 0 · Foundations (Weeks 1-3)

- [x] Fix spread calculation bug in `MarketFeatureBuilder` and add regression tests.
- [x] Harden InfoDolar parser using structured HTML parsing (e.g., `selectolax`).
- [x] Implement configurable logging levels (env-based) for CLI & services.
- [x] Document local dev bootstrap (make targets, `.env`, pytest install).
- [x] Set up GitHub Actions for lint + tests (pytest, mypy, ruff).

### Phase 1 · Data platform (Weeks 4-8)

- [x] Add new providers (Banco Central API v2, remittance APIs) with retries/backoff.
- [x] Design Alembic-based migration strategy for persistence layer (`docs/persistence_migration_strategy.md`).
- [x] Document workflow for running Alembic migrations (`docs/database_migrations.md`, README, Makefile).
- [ ] Normalize storage schema with migrations (Alembic) and versioned snapshots.
- [x] Introduce anomaly detection & provider weighting (Z-scores, EWMA).
  - Z-score detector + weighted consensus operational with persistence of `AnomalyEvent`s and CLI/API exposure.
  - EWMA + CUSUM drift monitor persisting `ConsensusSnapshot`/`DriftEvent` records, severity tiers classified and surfaced across CLI/API/dashboard.
- [ ] Create data quality reports and dashboards (Superset or Metabase).

### Phase 2 · AI evolution (Weeks 9-14)

- [ ] Establish feature store versioning and orchestrated pipeline (Prefect or Dagster).
- [ ] Build supervised models for action recommendation (LightGBM baseline) and compare vs rule-based strategy.
- [ ] Launch reinforcement-learning experiment loop using historical trades.
- [ ] Implement model registry & experiment tracking (MLflow).
- [ ] Deploy forecast ensemble (ARIMA + Prophet + LSTM) with automated evaluation.

### Phase 3 · Experience & automation (Weeks 15-20)

- [ ] Redesign dashboard with real-time WebSocket updates and responsive layout.
- [ ] Add alert channels (email, Telegram, SMS) driven by profitability thresholds.
- [ ] Package CLI + API into Docker images; publish to container registry.
- [ ] Provide IaC (Terraform) for cloud deployments (API + DB + scheduler worker).
- [ ] Integrate observability stack (Prometheus metrics, OpenTelemetry traces, structured logs).

### Phase 4 · Continuous innovation (Post-Launch)

- [ ] Marketplace for plugin providers (community connectors).
- [ ] Multi-currency support and portfolio optimization.
- [ ] LLM-based narrative reports summarizing daily strategy and market context.
- [ ] Automated risk management (VaR, scenario stress testing).

## 5. AI/ML backlog

| Category | Initiative | Notes |
| --- | --- | --- |
| Feature Engineering | Seasonality & holiday features | Leverage Dominican banking holidays, US Fed announcements |
| Feature Engineering | Macroeconomic ingestion | FRED, DXY, commodities |
| Modeling | Trade outcome classifier | Predict win/loss probability per action |
| Modeling | Price trajectory forecasting | Sequence models with attention |
| Monitoring | Drift detection | Statistical tests on feature distributions |
| Monitoring | Drift event surfacing | CLI/API/dashboard now expose severity-tiered EWMA + CUSUM signals; next step: proactive alerting |
| Monitoring | Post-trade analytics | Compare realized vs expected profit |

## 6. Developer experience upgrades

- Coding standards: adopt Ruff + Black + mypy (strict optional).
- Testing: property-based tests for parsers, integration tests with recorded HTTP fixtures (httpretty / respx).
- Packaging: `uv` or `poetry` evaluation for dependency coordination.
- Docs: MkDocs or Docusaurus site with API + tutorials.
- Automation: pre-commit hooks, conventional commits, release drafter.

## 7. Open questions & research

- Optimal provider mix vs cost / latency trade-offs.
- Data licensing for official bank APIs.
- Hosting plan (self-managed vs managed PaaS) and cost modelling.
- User segmentation (retail vs corporate) and personalized recommendations.

## 8. Update workflow

1. Treat this document as the single source of truth for roadmap updates.
2. For each completed initiative, mark checkbox ✅ and add summary in changelog.
3. When adding new tasks, include rationale and target timeframe.
4. Reference related issues/PRs for traceability.
5. Review bi-weekly to align priorities and surface blockers.

## 9. Changelog

| Date | Update | Owner |
| --- | --- | --- |
| 2025-10-08 | Initial roadmap drafted. | GitHub Copilot |
| 2025-10-08 | Corregido cálculo de spread y agregado test de regresión. | GitHub Copilot |
| 2025-10-08 | Parser de InfoDolar reforzado con selectolax y suite de pruebas dedicada. | GitHub Copilot |
| 2025-10-08 | Logging configurable con niveles controlados por `CAMBIO_LOG_LEVEL` y cobertura de pruebas. | GitHub Copilot |
| 2025-10-08 | Documentación del onboarding local en `docs/local_dev_setup.md` y README actualizado. | GitHub Copilot |
| 2025-10-08 | Nuevos conectores (BCRD API v2 y Remesas Caribe) con reintentos exponenciales y casos de prueba. | GitHub Copilot |
| 2025-10-08 | Alembic integrado: migración base, targets `make migrate`/`make revision` y guía `docs/database_migrations.md`. | GitHub Copilot |
| 2025-10-08 | Workflow CI (`ci.yml`) agregando Ruff (lint + format-check) y pytest en pushes/PRs. | GitHub Copilot |
| 2025-10-09 | Weighted consensus + z-score anomaly detector con persistencia `anomaly_events`, CLI y API actualizados, suite pytest (41) verde. | GitHub Copilot |
| 2025-10-09 | Drift monitor (EWMA + CUSUM) integrado: captura persiste `consensus_snapshots`/`drift_events`, migración 0006 creada, pruebas ampliadas. | GitHub Copilot |
| 2025-10-09 | Clasificación de severidad para `DriftEvent`s (LOW/MEDIUM/HIGH), migración 0007 + CLI/API/dashboard mostrando intensidad×umbral; suite pytest (46) verde. | GitHub Copilot |
