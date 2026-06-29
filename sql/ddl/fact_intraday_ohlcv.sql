CREATE TABLE IF NOT EXISTS fact_intraday_ohlcv
(
    ticker String,
    minute_ts DateTime,
    trading_date Date,
    resolution LowCardinality(String),
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    is_final UInt8,
    data_source LowCardinality(String),
    ingested_at DateTime
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMMDD(trading_date)
ORDER BY (ticker, resolution, minute_ts);
