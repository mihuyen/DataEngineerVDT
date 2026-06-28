{{ config(materialized='table') }}

select
    upper(ticker) as ticker,
    toUInt32(date_id) as date_id,
    toDate(trading_date) as trading_date,
    toFloat64(open) as open,
    toFloat64(high) as high,
    toFloat64(low) as low,
    toFloat64(close) as close,
    toUInt64(volume) as volume,
    toFloat64(value) as source_value,
    toUInt64(shares_outstanding) as shares_outstanding,
    toFloat64(market_cap) as source_market_cap,
    toFloat64(price_change) as source_price_change,
    toFloat64(pct_change) as source_pct_change,
    toFloat64(sma_20) as source_sma_20,
    toFloat64(ema_12) as source_ema_12,
    toFloat64(ema_26) as source_ema_26,
    toFloat64(macd) as source_macd,
    toFloat64(macd_signal) as source_macd_signal,
    toFloat64(rsi_14) as source_rsi_14,
    toFloat64(bb_upper) as source_bb_upper,
    toFloat64(bb_middle) as source_bb_middle,
    toFloat64(bb_lower) as source_bb_lower,
    toFloat64(volume_sma_20) as source_volume_sma_20
from {{ source('gold', 'fact_daily_price') }}
