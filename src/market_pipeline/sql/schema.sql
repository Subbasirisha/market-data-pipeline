-- Raw layer: source data parsed into columns, but otherwise not reshaped.
-- Every statement is idempotent (IF NOT EXISTS), so running this again is always safe.

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per coin per price point (~5 minutes apart).
-- The primary key is the "natural key": what makes a row unique in the real world.
-- It is also what lets upserts detect "I've seen this row before".
CREATE TABLE IF NOT EXISTS raw.crypto_prices (
    coin_id         text           NOT NULL,
    price_ts        timestamptz    NOT NULL,
    price_usd       numeric        NOT NULL,
    market_cap_usd  numeric,
    volume_usd      numeric,
    source_file     text           NOT NULL,  -- lineage: which raw file this row came from
    loaded_at       timestamptz    NOT NULL DEFAULT now(),
    PRIMARY KEY (coin_id, price_ts)
);

-- One row per stock per trading day.
CREATE TABLE IF NOT EXISTS raw.stock_prices_daily (
    symbol       text         NOT NULL,
    trade_date   date         NOT NULL,
    open         numeric      NOT NULL,
    high         numeric      NOT NULL,
    low          numeric      NOT NULL,
    close        numeric      NOT NULL,
    volume       bigint       NOT NULL,
    source_file  text         NOT NULL,
    loaded_at    timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, trade_date)
);

-- Load manifest: which raw files have already been loaded.
-- This makes loads incremental: each run only processes files not listed here.
CREATE TABLE IF NOT EXISTS raw.loaded_files (
    file_path    text         PRIMARY KEY,  -- relative to the raw data root
    source       text         NOT NULL,
    entity       text         NOT NULL,
    row_count    integer      NOT NULL,
    loaded_at    timestamptz  NOT NULL DEFAULT now()
);
