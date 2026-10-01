# homelab

[![CI](https://github.com/piercarloponci/homelab/actions/workflows/ci.yml/badge.svg)](https://github.com/piercarloponci/homelab/actions/workflows/ci.yml)

A monorepo for everything I self-host on my home server. Each service lives under `services/` or `shared/` and runs via Docker Compose, with shared infrastructure (Postgres, Airflow) factored out so multiple services can reuse it rather than each spinning up their own.

The first project in here is a stock-data pipeline: scheduled ingestion of minute-level OHLCV data, gap-filled into a clean per-minute series, orchestrated with Airflow and backed by Postgres. It's a first iteration — functional end to end, but still rough in places. See [Known limitations](#known-limitations).

## What it does

Daily, for a configurable list of tickers:

1. **Ingest** — pulls the last 6 days of 1-minute OHLCV bars per ticker from Yahoo Finance, writes a CSV backup, and inserts raw rows into Postgres.
2. **Gap-fill** — builds a continuous per-minute series per ticker, carrying the last traded close forward through non-trading minutes, into a second table for downstream analysis.

Both phases run as Airflow-orchestrated, per-ticker tasks with bounded concurrency rather than all tickers at once.

## Architecture

- **`services/stock-data`** — the actual pipeline logic (download, backup, gap-fill, DB access) as a standalone, independently testable Python package.
- **`shared/postgres`** — one Postgres instance with a dedicated database and user for stock-data.
- **`shared/airflow`** — orchestration. Runs its own, separate Postgres instance for Airflow's internal metadata (deliberately isolated from the stock-data database), plus the scheduler, API server, and DAG processor. The Airflow image is built from a small Dockerfile that installs the `stock_data` package directly, so the DAG can import it like any other dependency.

Each `shared/*` service is a standalone Compose file; the root `docker-compose.yaml` brings them together via `include:`.

## Tech stack

Python 3.12 (`uv` workspace) · Postgres 16 · Apache Airflow 3.2.2 (LocalExecutor) · Docker Compose · yfinance, pandas, psycopg2 · pytest, ruff, pyright in CI

## Repo layout

```
.
├── services/
│   └── stock-data/            # ingestion + gap-fill logic
│       ├── src/stock_data/
│       ├── tests/unit/
│       └── other/tickers.json
├── shared/
│   ├── airflow/                # DAG, Dockerfile, Airflow compose
│   └── postgres/                # stock-data's Postgres + init scripts
├── docker-compose.yaml         # root: includes both shared services
└── pyproject.toml              # uv workspace root
```

## Running locally

1. Copy each `.env.example` and fill in real values:
   ```bash
   cp services/stock-data/.env.example services/stock-data/.env
   cp shared/postgres/.env.example shared/postgres/.env
   cp shared/airflow/.env.example shared/airflow/.env
   ```
2. Create the bind-mounted directories Compose expects:
   ```bash
   mkdir -p shared/airflow/dags shared/airflow/csv_backups
   chmod +x shared/postgres/init/01_create_user.sh
   ```
3. Start everything:
   ```bash
   docker compose up -d
   ```
4. Airflow UI: [localhost:8081](http://localhost:8081)

## Testing

```bash
uv run pytest
uv run ruff check .
uv run ruff format --checks
uv run pyright
```

All four run in CI on every push.

## Known limitations

This is an early iteration — notable rough edges, roughly in order of priority:

- `gap_filler.py` builds SQL via string interpolation rather than parameterized queries. Low risk today (ticker values come from a trusted config file, not user input), but worth cleaning up.
- Single-node `LocalExecutor` deployment — no horizontal scaling if the ticker list grows significantly.
- No alerting beyond Airflow's own UI; a failed run currently requires manually checking the dashboard.