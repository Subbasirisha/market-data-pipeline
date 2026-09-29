-- Hourly OHLC ("candles") per coin, built from ~5-minute price points.
--
-- Incremental: instead of rebuilding the whole table every run, only hours that received
-- new or updated rows since the last run are recomputed (delete+insert on the unique key).
-- The filter is on loaded_at (when a row arrived), not price_ts (what time it describes),
-- so a backfill of last week's hours is picked up too. Filtering on price_ts would
-- silently skip those late-arriving rows.
{{
    config(
        materialized='incremental',
        unique_key=['coin_id', 'hour_ts'],
        incremental_strategy='delete+insert',
    )
}}

with prices as (
    select
        coin_id,
        date_trunc('hour', price_ts) as hour_ts,
        price_ts,
        price_usd,
        volume_usd,
        loaded_at
    from {{ ref('stg_crypto_prices') }}
),

{% if is_incremental() %}
changed_hours as (
    select distinct coin_id, hour_ts
    from prices
    where loaded_at > (select max(max_loaded_at) from {{ this }})
),
{% endif %}

hourly as (
    select
        p.coin_id,
        p.hour_ts,
        (array_agg(p.price_usd order by p.price_ts asc))[1]  as open_usd,
        max(p.price_usd)                                     as high_usd,
        min(p.price_usd)                                     as low_usd,
        (array_agg(p.price_usd order by p.price_ts desc))[1] as close_usd,
        avg(p.volume_usd)                                    as avg_volume_24h_usd,
        count(*)                                             as price_points,
        max(p.loaded_at)                                     as max_loaded_at
    from prices as p
    {% if is_incremental() %}
    join changed_hours as c using (coin_id, hour_ts)
    {% endif %}
    group by p.coin_id, p.hour_ts
)

select * from hourly
