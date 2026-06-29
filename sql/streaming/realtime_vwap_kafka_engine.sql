DROP TABLE IF EXISTS mv_realtime_trade_ticks_raw;

DROP TABLE IF EXISTS kafka_realtime_trade_ticks;

CREATE TABLE kafka_realtime_trade_ticks
(
    ticker String,
    trade_ts DateTime,
    price Float64,
    volume UInt64,
    data_source LowCardinality(String)
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'dnse-trades-raw',
    kafka_group_name = 'clickhouse-realtime-vwap',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS realtime_trade_ticks_raw
(
    ticker String,
    trade_ts DateTime,
    price Float64,
    volume UInt64,
    data_source LowCardinality(String) DEFAULT 'UNKNOWN',
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trade_ts)
ORDER BY (ticker, trade_ts);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_realtime_trade_ticks_raw
TO realtime_trade_ticks_raw
AS
SELECT
    ticker,
    trade_ts,
    price,
    volume,
    data_source
FROM kafka_realtime_trade_ticks;

DROP TABLE IF EXISTS mv_dnse_ohlcv_1m_fact;

DROP TABLE IF EXISTS kafka_dnse_ohlcv_1m;

CREATE TABLE kafka_dnse_ohlcv_1m
(
    ticker String,
    minute_ts DateTime,
    resolution LowCardinality(String),
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    is_final UInt8,
    data_source LowCardinality(String)
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'dnse-ohlcv-1m',
    kafka_group_name = 'clickhouse-dnse-ohlcv-1m',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

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

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dnse_ohlcv_1m_fact
TO fact_intraday_ohlcv
AS
SELECT
    ticker,
    minute_ts,
    toDate(minute_ts) AS trading_date,
    resolution,
    open,
    high,
    low,
    close,
    volume,
    is_final,
    data_source,
    now() AS ingested_at
FROM kafka_dnse_ohlcv_1m;
