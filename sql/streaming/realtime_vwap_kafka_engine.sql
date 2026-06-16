CREATE TABLE IF NOT EXISTS kafka_realtime_trade_ticks
(
    ticker String,
    trade_ts DateTime,
    price Float64,
    volume UInt64
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'dnse-trades-raw',
    kafka_group_name = 'clickhouse-realtime-vwap',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_realtime_trade_ticks_to_vwap
TO fact_realtime_vwap
AS
SELECT
    ticker,
    toStartOfMinute(trade_ts) AS minute_ts,
    toDate(trade_ts) AS trading_date,
    any(price) AS open_price,
    max(price) AS high_price,
    min(price) AS low_price,
    anyLast(price) AS close_price,
    sum(price * volume) / sum(volume) AS vwap_1m,
    sum(price * volume) / sum(volume) AS session_vwap,
    sum(volume) AS total_volume,
    sum(price * volume) AS total_value,
    sum(volume) AS session_volume,
    sum(price * volume) AS session_value,
    avg(price) AS avg_price,
    count() AS trade_count,
    (close_price - vwap_1m) / vwap_1m * 100 AS price_vs_vwap_pct,
    (close_price - session_vwap) / session_vwap * 100 AS price_vs_session_vwap_pct,
    now() AS created_at
FROM kafka_realtime_trade_ticks
GROUP BY
    ticker,
    minute_ts,
    trading_date;
