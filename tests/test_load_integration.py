"""End-to-end load tests against a real Postgres.

Each test run creates a throwaway database and drops it afterwards, so it never
touches the data in your real `market` database. Skipped if Postgres isn't running.
"""

import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from market_pipeline import db
from market_pipeline.config import load_settings
from market_pipeline.landing import RawRecord, write_raw
from market_pipeline.load import run_load

pytestmark = pytest.mark.integration


@pytest.fixture
def conn():
    settings = load_settings()
    test_db = f"market_test_{uuid.uuid4().hex[:8]}"
    try:
        admin = db.connect(settings.postgres_dsn)
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable; start it with: docker compose up -d")

    admin.execute(f'CREATE DATABASE "{test_db}"')
    test_dsn = settings.postgres_dsn.rsplit("/", 1)[0] + f"/{test_db}"
    try:
        with db.connect(test_dsn) as test_conn:
            yield test_conn
    finally:
        admin.execute(f'DROP DATABASE "{test_db}" WITH (FORCE)')
        admin.close()


def _crypto_file(root, extracted_at, prices):
    return write_raw(
        root,
        RawRecord(
            source="coingecko",
            entity="bitcoin",
            request_params={"days": 1},
            payload={"prices": prices, "market_caps": [], "total_volumes": []},
            extracted_at=extracted_at,
        ),
    )


def _count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_load_is_incremental_and_idempotent(conn, tmp_path):
    _crypto_file(tmp_path, datetime(2026, 9, 28, 10, tzinfo=UTC), [[1000, 1.0], [2000, 2.0]])

    first = run_load(conn, tmp_path)
    assert (first.files_loaded, first.rows_upserted) == (1, 2)

    # Second run: nothing new on disk, so nothing is loaded (incremental).
    second = run_load(conn, tmp_path)
    assert second.files_loaded == 0
    assert _count(conn, "raw.crypto_prices") == 2

    # Force a full reload by clearing the manifest: upserts must not duplicate rows.
    conn.execute("TRUNCATE raw.loaded_files")
    third = run_load(conn, tmp_path)
    assert third.files_loaded == 1
    assert _count(conn, "raw.crypto_prices") == 2


def test_overlapping_file_updates_existing_rows(conn, tmp_path):
    _crypto_file(tmp_path, datetime(2026, 9, 28, 10, tzinfo=UTC), [[1000, 1.0], [2000, 2.0]])
    run_load(conn, tmp_path)

    # A later extract overlaps the earlier window and revises the price at ts=2000.
    _crypto_file(tmp_path, datetime(2026, 9, 28, 11, tzinfo=UTC), [[2000, 2.5], [3000, 3.0]])
    run_load(conn, tmp_path)

    rows = conn.execute(
        "SELECT extract(epoch FROM price_ts) * 1000, price_usd"
        " FROM raw.crypto_prices ORDER BY price_ts"
    ).fetchall()
    assert [(int(ts), float(p)) for ts, p in rows] == [(1000, 1.0), (2000, 2.5), (3000, 3.0)]


def test_bad_file_fails_alone_and_is_retried(conn, tmp_path):
    good = _crypto_file(tmp_path, datetime(2026, 9, 28, 10, tzinfo=UTC), [[1000, 1.0]])
    bad = good.with_name("999999.json")
    bad.write_text("{not valid json")

    summary = run_load(conn, tmp_path)

    assert summary.files_loaded == 1
    assert list(summary.failed) == [str(bad)]
    # The bad file was not recorded as loaded, so the next run will try it again.
    assert _count(conn, "raw.loaded_files") == 1
