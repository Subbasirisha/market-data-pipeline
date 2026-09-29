-- Daily returns and moving averages per stock.
--   daily_return: (today's close / previous trading day's close) - 1
--   ma_7 / ma_20: average close over the last 7 / 20 *trading days* (rows, not calendar days)
-- Moving averages stay null until enough history exists, instead of silently averaging
-- fewer days.
with prices as (
    select symbol, trade_date, close_usd, volume
    from {{ ref('stg_stock_prices_daily') }}
),

windowed as (
    select
        symbol,
        trade_date,
        close_usd,
        volume,
        lag(close_usd) over w as prev_close_usd,
        avg(close_usd) over (w rows between 6 preceding and current row)  as ma_7_raw,
        avg(close_usd) over (w rows between 19 preceding and current row) as ma_20_raw,
        row_number() over w as day_number
    from prices
    window w as (partition by symbol order by trade_date)
)

select
    symbol,
    trade_date,
    close_usd,
    volume,
    prev_close_usd,
    round(close_usd / nullif(prev_close_usd, 0) - 1, 6)             as daily_return,
    case when day_number >= 7  then round(ma_7_raw, 4)  end         as ma_7_usd,
    case when day_number >= 20 then round(ma_20_raw, 4) end         as ma_20_usd
from windowed
