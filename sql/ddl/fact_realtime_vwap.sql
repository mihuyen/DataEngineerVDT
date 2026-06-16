CREATE TABLE IF NOT EXISTS fact_realtime_vwap
(
    ticker String,
    minute_ts DateTime,
    trading_date Date,
    open_price Float64,
    high_price Float64,
    low_price Float64,
    close_price Float64,
    vwap_1m Float64,
    session_vwap Float64,
    total_volume UInt64,
    total_value Float64,
    session_volume UInt64,
    session_value Float64,
    avg_price Float64,
    trade_count UInt32,
    price_vs_vwap_pct Float64,
    price_vs_session_vwap_pct Float64,
    created_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trading_date)
ORDER BY (ticker, minute_ts);
