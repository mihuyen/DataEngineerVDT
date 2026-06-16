CREATE TABLE IF NOT EXISTS fact_alert_event
(
    alert_id UUID,
    user_id String,
    ticker String,
    date_id UInt32,
    triggered_at DateTime,
    condition_type LowCardinality(String),
    threshold_value Float64,
    actual_value Float64,
    channel LowCardinality(String),
    is_sent UInt8,
    sent_at Nullable(DateTime),
    created_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(triggered_at)
ORDER BY (user_id, triggered_at);
