-- Staging: a thin, renamed, typed layer over the raw table. No business logic here;
-- every downstream model reads from this instead of from raw directly.
select
    coin_id,
    price_ts,
    price_usd,
    market_cap_usd,
    volume_usd,
    loaded_at
from {{ source('raw', 'crypto_prices') }}
