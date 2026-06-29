CREATE TABLE IF NOT EXISTS fact_alert_rule_state
(
    alert_id String,
    ticker String,
    metric_value Float64,
    updated_at DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (alert_id, ticker);
