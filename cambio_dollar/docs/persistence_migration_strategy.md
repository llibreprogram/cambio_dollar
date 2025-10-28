# Persistence Migration Strategy

_Last updated: 2025-10-08_

This document captures the plan for introducing Alembic-powered schema migrations to **Cambio Dollar** while preserving backward compatibility with existing SQLite deployments.

## 1. Current state recap

- The SQLite database is bootstrapped programmatically in `cambio_dollar.repository.MarketRepository._initialize`.
- Tables managed:
  - `rate_snapshots`
  - `trades`
  - `strategy_recommendations`
  - `feature_store`
  - `labels_performance`
  - `external_macro`
  - `model_evaluations`
- JSON blobs are stored in `TEXT` columns and decoded manually.
- Several read-heavy tables expose indexes (`feature_store`, `labels_performance`, `external_macro`, `model_evaluations`).
- No explicit schema versioning or migration history exists; deployments rely on the bootstrap script.

## 2. Design goals

1. **Deterministic schema evolution**: source-controlled migrations that can be replayed reproducibly across environments.
2. **Incremental rollout**: keep the repository’s bootstrap path operational while Alembic is introduced, then phase out direct DDL calls once the baseline migration is in place.
3. **SQLite affinity**: accommodate SQLite-specific quirks (lack of `ALTER COLUMN`, transactional DDL limitations, limited concurrent writes).
4. **Developer ergonomics**: provide make targets / scripts that hide environment variables and ensure migrations run against the configured database path (`Settings.db_path`).

## 3. Proposed approach

### 3.1 Tooling

- Adopt **Alembic** as the migration framework.
- Store migration artefacts under `migrations/` (standard Alembic layout with `env.py`, `script.py.mako`, and `versions/`).
- Configure Alembic to read the project settings to obtain the SQLite URL, e.g. `sqlite+pysqlite:///absolute/path/to/db`.

### 3.2 Baseline strategy

1. Generate an Alembic environment (`alembic init migrations`).
2. Author a baseline migration (`versions/0001_baseline.py`) that reflects the schema currently instantiated by `_initialize`.
   - Use explicit DDL (SQLAlchemy table metadata definitions mapped to existing tables).
   - Create indexes with the same names as in the bootstrap script.
3. Once the baseline migration is committed, update `MarketRepository._initialize` to:
   - Ensure the database folder exists.
   - Invoke Alembic (via a helper) to run migrations to head instead of executing inline DDL.
   - Retain the old `executescript` path behind a feature flag or fallback for environments that have not yet adopted Alembic (temporary measure for transition).

### 3.3 Future migrations

- Each schema change will incrementally modify the relevant tables via Alembic migrations (e.g., adding columns, introducing new tables for provider metadata, normalising JSON blobs).
- Because SQLite has limited `ALTER TABLE` support, complex operations may require creating temporary tables, copying data, and dropping originals. Provide helper utilities or macros in migrations to encapsulate this pattern.

### 3.4 Developer workflow

- New make targets:
  - `make migrate` → apply migrations to the configured database.
  - `make revision message="add provider weights"` → scaffold a new migration with autogeneration hints (optional).
- Provide a wrapper script (`scripts/run_migrations.py`) that pulls the database path from `Settings` and runs Alembic programmatically. The make targets will invoke this script so developers don’t need to manage ALEMBIC_CONFIG manually.

### 3.5 Environment parity

- CI pipeline will execute migrations against an ephemeral SQLite file before running pytest, ensuring scripts remain valid.
- Local onboarding docs (`docs/local_dev_setup.md`) will gain a section describing how to apply migrations and reset the database.

## 4. Implementation plan

1. **Introduce Alembic dependencies**
   - Add `alembic` to `pyproject.toml` under the dev extras.
   - Create the `migrations/` directory scaffold.
2. **Create baseline migration**
   - Reflect current schema into SQLAlchemy metadata (manual definitions or `MetaData(bind=engine, reflect=True)` as verification reference).
   - Ensure indexes and unique constraints match the repository script.
3. **Hook into repository initialization**
   - Replace direct `executescript` with a call to `upgrade()` helper that runs Alembic migrations.
   - Provide logging around migration execution.
4. **Developer ergonomics**
   - Add `make migrate` and optional `make revision` targets.
   - Update documentation with clear instructions.
5. **Cleanup**
   - Once baseline migration is validated, remove the inline DDL from `_initialize` to avoid drift (keeping a compatibility branch for a limited time if necessary).

## 5. Open questions

- Should we persist migration status in a dedicated table for non-Alembic consumers? (Alembic already uses `alembic_version`; no further action unless other tooling requires it.)
- Do we need to support multiple database backends in the near future (PostgreSQL)? If so, future migrations should aim to be backend-agnostic where possible.
- How will we back up or reset existing installations? Consider providing a `make reset-db` target that snapshots the current database before applying destructive changes.

## 6. Next steps

- Approve this strategy.
- Proceed with implementation of Alembic scaffolding and baseline migration (`Implement initial Alembic setup` todo item).
- Update roadmap documentation once the implementation lands.
