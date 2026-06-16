CREATE TABLE IF NOT EXISTS fact_daily_price
(
    ticker String,
    date_id UInt32,
    trading_date Date,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    value Float64,
    shares_outstanding UInt64,
    market_cap Float64,
    price_change Float64,
    pct_change Float64,
    sma_20 Nullable(Float64),
    ema_12 Nullable(Float64),
    ema_26 Nullable(Float64),
    macd Nullable(Float64),
    macd_signal Nullable(Float64),
    rsi_14 Nullable(Float64),
    bb_upper Nullable(Float64),
    bb_middle Nullable(Float64),
    bb_lower Nullable(Float64),
    volume_sma_20 Nullable(Float64),
    overbought_flag UInt8,
    oversold_flag UInt8,
    breakout_flag UInt8,
    breakdown_flag UInt8,
    created_at DateTime,
    updated_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (ticker, trading_date);
