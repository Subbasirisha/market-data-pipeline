select
    symbol,
    trade_date,
    open  as open_usd,
    high  as high_usd,
    low   as low_usd,
    close as close_usd,
    volume,
    loaded_at
from {{ source('raw', 'stock_prices_daily') }}
