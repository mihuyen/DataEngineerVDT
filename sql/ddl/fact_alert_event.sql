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
    -- One of: sent, send_failed, channel_not_configured, unknown_channel.
    -- A single is_sent boolean could not tell "the channel rejected/failed
    -- the request" apart from "no channel was configured at all" -- both
    -- showed up identically as is_sent=0, which made the alert history
    -- useless for diagnosing why notifications weren't going out.
    delivery_status LowCardinality(String),
    sent_at Nullable(DateTime),
    created_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(triggered_at)
ORDER BY (user_id, triggered_at);
