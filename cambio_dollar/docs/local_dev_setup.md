# Local Development Setup

This guide walks through preparing a reproducible development environment for **Cambio Dollar** on Linux, macOS, or WSL. The same steps apply to any POSIX-compliant shell (Bash, Zsh, Fish).

## 1. Prerequisites

- Python 3.12 (3.10+ works, but the project is validated on 3.12) with `python3-venv` module installed.
- GNU Make 4.x (`make --version`).
- SQLite 3.38+ (bundled with most OSes).
- Git for cloning the repository.

If you plan to run the dashboard locally, modern browsers (Chromium/Firefox) are recommended.

## 2. Clone the repository

```bash
git clone https://github.com/<org>/cambio_dollar.git
cd cambio_dollar
```

> Replace `<org>` with the actual organization or user that hosts your fork.

## 3. Bootstrap the virtual environment

The project comes with a `Makefile` that automates environment creation and dependency installation.

```bash
make bootstrap
```

This target will:

1. Create a virtual environment inside `.venv` using `python3 -m venv`.
2. Upgrade `pip` inside the virtual environment.
3. Install the package in editable mode along with development dependencies (`pip install -e .[dev]`).

A marker file `.venv/.bootstrap-complete` is written so subsequent calls are near-instant.

### Activating the environment manually (optional)

Most `make` targets activate the virtual environment for you. If you want a manual shell session:

```bash
source .venv/bin/activate
```

Deactivate later with `deactivate`.

## 4. Configure environment variables

Settings are managed through `pydantic-settings`. To customize values, copy the example file and tweak it.

```bash
cp .env.example .env
```

Key variables worth reviewing:

| Variable | Purpose | Default |
| --- | --- | --- |
| `CAMBIO_LOG_LEVEL` | Root logging level (`DEBUG`, `INFO`, `WARNING`, etc.). | `INFO` |
| `CAMBIO_SCHEDULER_ENABLED` | Enables the background scheduler when serving the API. | `false` |
| `CAMBIO_SCHEDULER_INTERVAL_SECONDS` | Interval in seconds for automatic captures. | `600` |
| `CAMBIO_TRANSACTION_COST` | Per-trade cost used in profitability calculations. | `0.10` |
| `CAMBIO_PROVIDERS__*_` | Declarative provider configuration (endpoints, credentials). | See `config.Settings` |
| `CAMBIO_PROVIDERS__2__ENABLED` | Toggles the Banco Central RD API v2 connector. | `false` |
| `BCRD_API_KEY` | Subscription key required by the Banco Central API gateway. | _(empty)_ |
| `CAMBIO_PROVIDERS__3__ENABLED` | Enables Banco Popular's OAuth connector. | `false` |
| `CAMBIO_PROVIDERS__5__ENABLED` | Enables the Remesas Caribe connector. | `false` |

> Tip: Variables with double underscores (`__`) map to nested fields. For example, `CAMBIO_PROVIDERS__0__ENABLED=false` disables the first provider.

Providers that define `max_retries` and `backoff_seconds` automatically retry transient failures with exponential backoff for HTTP status codes like `429` or `503`, and for connection timeouts when `retry_on_timeout=true`.

## 5. Apply database migrations

After configuring the environment, align your SQLite schema with the current migrations:

```bash
make migrate
```

This command runs Alembic against the path specified by `CAMBIO_DB_PATH` (default: `data/cambio_dollar.sqlite`). Existing databases without an Alembic history are stamped automatically before applying pending revisions.

To create a new migration while developing a feature:

```bash
make revision message="add provider weights"
```

Review the generated file under `src/cambio_dollar/migrations/versions/` and adjust as needed.

## 6. Seed sample data (optional)

For demos or first-time setup, import the included CSV to the local SQLite database:

```bash
make fetch          # captures fresh data using configured providers
# or load the historical sample
sqlite3 data/cambio_dollar.sqlite < data/sample_rates.sql  # if you have SQL dumps
```

The repository already ships with `data/sample_rates.csv`, which the application can ingest via `make fetch` and subsequent analyses.

## 7. Run core workflows

- **Fetch market data**
  ```bash
  make fetch
  ```
- **Generate recommendations**
  ```bash
  make analyze
  ```
- **Inspect providers and history**
  ```bash
  make providers
  make history
  ```
- **Start the API + dashboard**
  ```bash
  make serve
  ```
  Visit `http://localhost:8000` to see the dashboard; JSON endpoints are under `/api`.

All these commands execute the CLI via `.venv/bin/cambio-dollar` with logging configured according to your `.env`.

## 8. Run the automated tests

After making code changes, execute the test suite. The `Makefile` exposes a convenient target:

```bash
make test
```

This runs `pytest` inside the virtual environment. You can also call `.venv/bin/pytest` directly if the environment is already active.

## 9. Useful make targets at a glance

| Target | Description |
| --- | --- |
| `make bootstrap` | Create the virtual environment and install dependencies. |
| `make serve` | Launch FastAPI + dashboard on port 8000. |
| `make fetch` | Capture and persist fresh exchange-rate snapshots. |
| `make analyze` | Produce the AI-driven recommendation summary. |
| `make forecast` | Run the forecast module for projected profit. |
| `make compare` | Compare spreads between providers. |
| `make providers` | Display provider configuration and health. |
| `make history` | Show trade history stored in SQLite. |
| `make test` | Execute the entire pytest suite. |
| `make clean` | Remove the virtual environment and temporary artifacts. |

## 10. Troubleshooting tips

- **`make bootstrap` fails with SSL errors**: update `pip` and the system certificates, then rerun `make bootstrap`.
- **Providers returning errors**: ensure the relevant `CAMBIO_PROVIDERS__*` variables are correctly populated and the provider is enabled.
- **Scheduler not firing**: verify `CAMBIO_SCHEDULER_ENABLED=true` and check logs for APScheduler warnings.
- **Logging too verbose**: adjust `CAMBIO_LOG_LEVEL` to `WARNING` or `ERROR`.

## 11. Next steps

- Explore the modernization roadmap at `docs/modernization_roadmap.md` for upcoming initiatives.
- Review `docs/data_pipeline.md` to understand ingestion flow and extension points.
- Run the notebook `notebooks/monitor_mercado.ipynb` for interactive visualizations.
