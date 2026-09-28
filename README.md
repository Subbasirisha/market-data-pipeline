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
- [ ] Phase 2: Extract from APIs (retries, rate limits, raw landing zone)
- [ ] Phase 3: Load into Postgres (upserts, incremental watermarks)
- [ ] Phase 4: Docker Compose
- [ ] Phase 5: Airflow orchestration
- [ ] Phase 6: dbt models, data-quality tests, CI

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then add your API key
pytest
```

## Project layout

```
src/market_pipeline/   pipeline code (importable Python package)
tests/                 unit tests (pytest)
data/raw/              raw API responses (git-ignored)
.env.example           template for secrets/config; copy to .env
```
