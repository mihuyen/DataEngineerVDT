{{ config(
    materialized='incremental',
    incremental_strategy='delete_insert',
    unique_key=['ticker', 'date_id']
) }}

with base as (
    select
        ticker,
        date_id,
        trading_date,
        open,
        high,
        low,
        close,
        volume,
        shares_outstanding,
        lagInFrame(close, 1, close) over (
            partition by ticker
            order by trading_date
            rows between unbounded preceding and current row
        ) as previous_close,
        row_number() over (
            partition by ticker
            order by trading_date
        ) as ticker_row_number
    from {{ ref('stg_fact_daily_price') }}
),

daily_change as (
    select
        *,
        close - previous_close as price_change,
        if(previous_close = 0, 0, (close - previous_close) / previous_close * 100) as pct_change,
        greatest(close - previous_close, 0) as rsi_gain,
        greatest(previous_close - close, 0) as rsi_loss
    from base
),

rolling_indicators as (
    select
        *,
        avg(close) over (
            partition by ticker
            order by trading_date
            rows between 19 preceding and current row
        ) as sma_20_raw,
        avg(volume) over (
            partition by ticker
            order by trading_date
            rows between 19 preceding and current row
        ) as volume_sma_20_raw,
        stddevSamp(close) over (
            partition by ticker
            order by trading_date
            rows between 19 preceding and current row
        ) as bb_std_20,
        avg(rsi_gain) over (
            partition by ticker
            order by trading_date
            rows between 13 preceding and current row
        ) as avg_gain_14,
        avg(rsi_loss) over (
            partition by ticker
            order by trading_date
            rows between 13 preceding and current row
        ) as avg_loss_14
    from daily_change
),

final as (
    select
        ticker,
        date_id,
        trading_date,
        open,
        high,
        low,
        close,
        volume,
        ((open + high + low + close) / 4) * volume as value,
        shares_outstanding,
        close * shares_outstanding as market_cap,
        price_change,
        pct_change,
        if(ticker_row_number >= 20, sma_20_raw, null) as sma_20,
        -- EMA values are currently inherited from the Python Gold loader because
        -- ClickHouse SQL does not provide a simple exact recursive EMA window.
        source.source_ema_12 as ema_12,
        source.source_ema_26 as ema_26,
        source.source_ema_12 - source.source_ema_26 as macd,
        source.source_macd_signal as macd_signal,
        if(
            ticker_row_number >= 14,
            if(avg_loss_14 = 0, 100, 100 - (100 / (1 + (avg_gain_14 / avg_loss_14)))),
            null
        ) as rsi_14,
        if(ticker_row_number >= 20, sma_20_raw + 2 * bb_std_20, null) as bb_upper,
        if(ticker_row_number >= 20, sma_20_raw, null) as bb_middle,
        if(ticker_row_number >= 20, sma_20_raw - 2 * bb_std_20, null) as bb_lower,
        if(ticker_row_number >= 20, volume_sma_20_raw, null) as volume_sma_20,
        toUInt8(rsi_14 > 70) as overbought_flag,
        toUInt8(rsi_14 < 30) as oversold_flag,
        toUInt8(close > bb_upper) as breakout_flag,
        toUInt8(close < bb_lower) as breakdown_flag,
        now() as created_at,
        now() as updated_at
    from rolling_indicators
    inner join {{ ref('stg_fact_daily_price') }} as source
        using (ticker, date_id, trading_date)
)

select *
from final
{% if is_incremental() %}
-- Rolling indicators (SMA20/RSI14/Bollinger) above are computed over the
-- *entire* ticker history read from stg_fact_daily_price, so they are
-- always correct regardless of this filter. Only the output actually
-- written back is limited to a lookback window past this table's current
-- watermark, mirroring scripts/load_gold.py's INDICATOR_LOOKBACK_DAYS
-- approach: delete_insert matches by (ticker, date_id), not by partition,
-- so narrowing this filter cannot silently drop unrelated existing rows the
-- way a partition-level DROP would.
where trading_date >= (select dateAdd(day, -35, max(trading_date)) from {{ this }})
{% endif %}
