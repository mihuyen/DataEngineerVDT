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
