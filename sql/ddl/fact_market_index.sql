CREATE TABLE IF NOT EXISTS fact_market_index
(
    index_id String,
    date_id UInt32,
    trading_date Date,
    open_point Float64,
    high_point Float64,
    low_point Float64,
    close_point Float64,
    point_change Float64,
    pct_change Float64,
    total_volume UInt64,
    total_value Float64,
    advance_count UInt32,
    decline_count UInt32,
    unchanged_count UInt32,
    advance_decline_ratio Float64,
    sma_20 Nullable(Float64),
    rsi_14 Nullable(Float64),
    created_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (index_id, trading_date);
