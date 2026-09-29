"""Postgres access: connection, schema setup, and idempotent upserts."""

from importlib.resources import files

import psycopg

from market_pipeline.parsers import CryptoPrice, StockPriceDaily


def connect(dsn: str) -> psycopg.Connection:
    # autocommit=True: nothing is held open implicitly. Where several statements must
    # succeed or fail together, the caller wraps them in `with conn.transaction():`.
    return psycopg.connect(dsn, autocommit=True)


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(files("market_pipeline").joinpath("sql/schema.sql").read_text())


# Upsert = INSERT, or UPDATE if the primary key already exists ("ON CONFLICT").
# Loading the same data twice therefore leaves the table unchanged: the load is idempotent.
# If the source revises a value (e.g. the latest, still-moving price point), the newer
# value wins.
UPSERT_CRYPTO = """
INSERT INTO raw.crypto_prices
    (coin_id, price_ts, price_usd, market_cap_usd, volume_usd, source_file)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (coin_id, price_ts) DO UPDATE SET
    price_usd      = EXCLUDED.price_usd,
    market_cap_usd = EXCLUDED.market_cap_usd,
    volume_usd     = EXCLUDED.volume_usd,
    source_file    = EXCLUDED.source_file,
    loaded_at      = now()
"""

UPSERT_STOCK = """
INSERT INTO raw.stock_prices_daily
    (symbol, trade_date, open, high, low, close, volume, source_file)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (symbol, trade_date) DO UPDATE SET
    open        = EXCLUDED.open,
    high        = EXCLUDED.high,
    low         = EXCLUDED.low,
    close       = EXCLUDED.close,
    volume      = EXCLUDED.volume,
    source_file = EXCLUDED.source_file,
    loaded_at   = now()
"""


def upsert_crypto(conn: psycopg.Connection, rows: list[CryptoPrice], source_file: str) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            UPSERT_CRYPTO,
            [
                (r.coin_id, r.price_ts, r.price_usd, r.market_cap_usd, r.volume_usd, source_file)
                for r in rows
            ],
        )
    return len(rows)


def upsert_stocks(conn: psycopg.Connection, rows: list[StockPriceDaily], source_file: str) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            UPSERT_STOCK,
            [
                (r.symbol, r.trade_date, r.open, r.high, r.low, r.close, r.volume, source_file)
                for r in rows
            ],
        )
    return len(rows)


def loaded_file_paths(conn: psycopg.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT file_path FROM raw.loaded_files")}


def record_loaded_file(
    conn: psycopg.Connection, file_path: str, source: str, entity: str, row_count: int
) -> None:
    conn.execute(
        "INSERT INTO raw.loaded_files (file_path, source, entity, row_count)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (file_path) DO NOTHING",
        (file_path, source, entity, row_count),
    )
