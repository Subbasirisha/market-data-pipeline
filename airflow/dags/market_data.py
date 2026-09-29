"""Airflow DAGs for the market data pipeline.

Two DAGs, because the two sources have very different budgets:
  crypto_prices_hourly   CoinGecko, every hour, fetching exactly that hour's window
  stock_prices_daily     Alpha Vantage (25 requests/day free), once per weekday after close

DAG files should stay thin: they only wire tasks together. All real logic lives in
the market_pipeline package, where it's unit-tested and also runnable without Airflow.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task
from airflow.timetables.interval import CronDataIntervalTimetable

from market_pipeline import db
from market_pipeline.config import load_settings
from market_pipeline.extract import run_crypto_interval_extract, run_stock_extract
from market_pipeline.load import run_load

DEFAULT_ARGS = {
    "owner": "data-eng",
    # Transient API/network failures usually clear up; retry before paging anyone.
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _raise_if_failed(step: str, failed: dict[str, str]) -> None:
    # Raising marks the task failed in Airflow, which triggers retries and alerts.
    if failed:
        raise RuntimeError(f"{step} failed for {len(failed)} item(s): {failed}")


@task
def load_raw_files() -> int:
    settings = load_settings()
    with db.connect(settings.postgres_dsn) as conn:
        summary = run_load(conn, settings.raw_data_dir)
    _raise_if_failed("load", summary.failed)
    return summary.rows_upserted


@dag(
    dag_id="crypto_prices_hourly",
    # Airflow 3 gotcha: schedule="@hourly" alone gives each run a zero-length interval
    # (start == end: a point in time). The interval timetable gives every run a real
    # one-hour window, [start, end), which is what window-based extraction needs.
    schedule=CronDataIntervalTimetable("@hourly", timezone="UTC"),
    start_date=datetime(2026, 9, 1, tzinfo=UTC),
    # catchup=False: when the DAG is first switched on, don't run every missed hour since
    # start_date. Past hours can still be backfilled on purpose, from the UI or the CLI.
    catchup=False,
    max_active_runs=3,
    default_args=DEFAULT_ARGS,
    tags=["crypto", "coingecko"],
)
def crypto_prices_hourly():
    @task
    def extract_crypto(data_interval_start=None, data_interval_end=None) -> int:
        # Each run owns a fixed window: [data_interval_start, data_interval_end).
        # Re-running or backfilling the 14:00 run always fetches 14:00-15:00,
        # no matter when it actually executes.
        if data_interval_end is None:  # manual runs may have no interval
            data_interval_end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
            data_interval_start = data_interval_end - timedelta(hours=1)
        if data_interval_start >= data_interval_end:
            raise ValueError(f"empty interval {data_interval_start}..{data_interval_end}")
        settings = replace(load_settings(), stock_symbols=[])
        summary = run_crypto_interval_extract(settings, data_interval_start, data_interval_end)
        _raise_if_failed("extract", summary.failed)
        return len(summary.written)

    # trigger_rule="all_done": load whatever landed, even if the extract task failed
    # partway (same design as pipeline.py). The run is still marked failed.
    extract_crypto() >> load_raw_files.override(trigger_rule="all_done")()


@dag(
    dag_id="stock_prices_daily",
    # 22:00 UTC, Monday-Friday: after the US market closes (16:00 New York time).
    schedule="0 22 * * 1-5",
    start_date=datetime(2026, 9, 29, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["stocks", "alpha_vantage"],
)
def stock_prices_daily():
    @task
    def extract_stocks() -> int:
        # Alpha Vantage's free endpoint returns the latest 100 trading days, so this is
        # a snapshot rather than a window; upserts make the overlap between days harmless.
        settings = replace(load_settings(), crypto_ids=[])
        summary = run_stock_extract(settings)
        _raise_if_failed("extract", summary.failed)
        return len(summary.written)

    extract_stocks() >> load_raw_files.override(trigger_rule="all_done")()


crypto_prices_hourly()
stock_prices_daily()
