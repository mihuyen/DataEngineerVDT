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

-- Raw tick landing table. TTL keeps only the trailing 30 days: this module
-- only serves the live/intraday view, not long-term history (batch OHLCV
-- already covers daily granularity in fact_daily_price).
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
ORDER BY (ticker, trade_ts)
TTL trade_ts + INTERVAL 30 DAY;

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

-- Per-minute VWAP state, kept as partial aggregate states (`-State` combinators)
-- so ClickHouse can merge them incrementally as more ticks for the same minute
-- arrive across separate Kafka batches, instead of a Python job recomputing the
-- whole day from scratch every 15s. AggregatingMergeTree is the engine built
-- for exactly this: each background merge combines states with the matching
-- `-Merge` combinator, so intermediate results are always query-correct even
-- before a background merge has run (ClickHouse merges states on read too).
CREATE TABLE IF NOT EXISTS fact_realtime_vwap_1m_state
(
    data_source LowCardinality(String),
    ticker String,
    trading_date Date,
    minute_ts DateTime,
    open_state AggregateFunction(argMin, Float64, DateTime),
    close_state AggregateFunction(argMax, Float64, DateTime),
    high_price AggregateFunction(max, Float64),
    low_price AggregateFunction(min, Float64),
    total_volume AggregateFunction(sum, UInt64),
    total_value AggregateFunction(sum, Float64),
    trade_count AggregateFunction(count)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMMDD(trading_date)
ORDER BY (data_source, ticker, minute_ts)
TTL trading_date + INTERVAL 30 DAY;

DROP TABLE IF EXISTS mv_fact_realtime_vwap_1m_state;

CREATE MATERIALIZED VIEW mv_fact_realtime_vwap_1m_state
TO fact_realtime_vwap_1m_state
AS
SELECT
    data_source,
    ticker,
    toDate(trade_ts) AS trading_date,
    toStartOfMinute(trade_ts) AS minute_ts,
    argMinState(price, trade_ts) AS open_state,
    argMaxState(price, trade_ts) AS close_state,
    maxState(price) AS high_price,
    minState(price) AS low_price,
    sumState(volume) AS total_volume,
    sumState(price * volume) AS total_value,
    countState() AS trade_count
FROM kafka_realtime_trade_ticks
GROUP BY data_source, ticker, trading_date, minute_ts;

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

-- ReplacingMergeTree(ingested_at): DNSE occasionally re-emits a "closed"
-- candle for the same minute (late trade correction) -- keeping the row with
-- the newest ingested_at on merge is the cheap way to converge to a single
-- version per (ticker, resolution, minute_ts) without a manual dedup step.
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
ORDER BY (ticker, resolution, minute_ts)
TTL trading_date + INTERVAL 30 DAY;

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

-- Published VWAP surface: a plain VIEW (not materialized) merging the
-- AggregatingMergeTree states with `-Merge` combinators and adding the
-- session-cumulative columns via a window function. Cumulative sums across
-- an unbounded number of prior minutes aren't something a row-triggered
-- Materialized View can maintain incrementally, so that part is intentionally
-- computed at query time -- ClickHouse evaluates it lazily against the (small,
-- pre-aggregated) per-minute state table rather than the raw tick stream, so
-- this stays cheap even though it's not itself materialized.
DROP TABLE IF EXISTS fact_realtime_vwap;

CREATE VIEW fact_realtime_vwap AS
WITH per_minute AS (
    SELECT
        data_source,
        ticker,
        trading_date,
        minute_ts,
        argMinMerge(open_state) AS open_price,
        argMaxMerge(close_state) AS close_price,
        maxMerge(high_price) AS high_price,
        minMerge(low_price) AS low_price,
        sumMerge(total_volume) AS total_volume,
        sumMerge(total_value) AS total_value,
        countMerge(trade_count) AS trade_count
    FROM fact_realtime_vwap_1m_state
    GROUP BY data_source, ticker, trading_date, minute_ts
)
SELECT
    ticker,
    minute_ts,
    trading_date,
    data_source,
    open_price,
    high_price,
    low_price,
    close_price,
    total_value / total_volume AS vwap_1m,
    sum(total_value) OVER session AS session_value,
    sum(total_volume) OVER session AS session_volume,
    sum(total_value) OVER session / sum(total_volume) OVER session AS session_vwap,
    total_volume,
    total_value,
    total_value / total_volume AS avg_price,
    trade_count,
    (close_price - total_value / total_volume) / (total_value / total_volume) * 100 AS price_vs_vwap_pct,
    (close_price - sum(total_value) OVER session / sum(total_volume) OVER session)
        / (sum(total_value) OVER session / sum(total_volume) OVER session) * 100 AS price_vs_session_vwap_pct,
    now() AS created_at
FROM per_minute
WINDOW session AS (PARTITION BY data_source, ticker, trading_date ORDER BY minute_ts
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
