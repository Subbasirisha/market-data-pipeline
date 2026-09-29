# Market Data Pipeline

An end-to-end data ingestion pipeline that pulls **crypto** (CoinGecko) and **stock**
(Alpha Vantage) prices, lands raw data, loads it into **PostgreSQL** with idempotent
incremental loads, and transforms it with **dbt**, orchestrated by **Airflow** and run in **Docker**.

```
 CoinGecko API ─┐
                ├─► Extract (Python) ─► raw JSON ─► Load (Python) ─► Postgres raw tables
 Alpha Vantage ─┘                                                          │
                                                                           ▼
                                             Transform + test (dbt) ─► analytics tables
                         Airflow schedules and monitors every step
```

## Roadmap

- [x] Phase 1: Project setup (config, tests, secrets handling)
- [x] Phase 2: Extract from APIs (retries, rate limits, raw landing zone)
- [x] Phase 3: Load into Postgres (upserts, incremental file manifest)
- [x] Phase 4: Docker Compose (containerized pipeline + Postgres)
- [x] Phase 5: Airflow orchestration (hourly + daily DAGs, retries, backfills)
- [ ] Phase 6: dbt models, data-quality tests, CI

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then add your API key
docker compose up -d --wait   # start Postgres
pytest                        # unit + integration tests
```

## Running the pipeline

**In Docker** (only Docker needed; no local Python):

```bash
cp .env.example .env
docker compose up -d --wait          # Postgres
docker compose run --rm pipeline     # extract + load, then exit
```

**Locally** (for development):

```bash
python -m market_pipeline.pipeline  # extract + load
python -m market_pipeline.extract   # APIs -> data/raw/<source>/<entity>/dt=YYYY-MM-DD/*.json
python -m market_pipeline.load      # new raw files -> Postgres (raw schema)
```

**With Airflow** (scheduled):

```bash
docker compose --profile airflow up -d --build   # UI at http://localhost:8080
```

| DAG | Schedule | What it does |
|---|---|---|
| `crypto_prices_hourly` | every hour | fetches exactly that run's hour from CoinGecko (`[data_interval_start, data_interval_end)`), then loads |
| `stock_prices_daily` | 22:00 UTC, Mon-Fri | fetches daily bars after the US close (fits Alpha Vantage's 25 requests/day), then loads |

Each task retries twice, 5 minutes apart. The load task runs even if its extract failed
partway (`trigger_rule="all_done"`), so whatever landed still reaches the database.
Because each crypto run owns a fixed time window, past hours can be backfilled:

```bash
docker compose exec airflow airflow backfill create --dag-id crypto_prices_hourly \
  --from-date 2026-09-26T10:00:00+00:00 --to-date 2026-09-26T12:59:00+00:00
```

Loads are **incremental** (a manifest table, `raw.loaded_files`, tracks which files are done)
and **idempotent** (rows are upserted on their natural key, so reloading never duplicates).
Each file loads in a single transaction together with its manifest entry.

| Table | Grain | Key |
|---|---|---|
| `raw.crypto_prices` | one coin, one ~5-minute price point | `(coin_id, price_ts)` |
| `raw.stock_prices_daily` | one stock, one trading day | `(symbol, trade_date)` |
| `raw.loaded_files` | one loaded raw file | `file_path` |

## Project layout

```
src/market_pipeline/   pipeline code (importable Python package)
  sources/             one module per API
  sql/schema.sql       Postgres DDL for the raw layer
tests/                 unit tests (pytest)
data/raw/              raw API responses (git-ignored)
.env.example           template for secrets/config; copy to .env
Dockerfile             pipeline image (slim, non-root, layer-cached deps)
docker-compose.yml     Postgres, one-shot pipeline job, Airflow (profile)
airflow/               Airflow image + DAGs
```
