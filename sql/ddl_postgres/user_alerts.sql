CREATE TABLE IF NOT EXISTS user_alerts (
    alert_id UUID PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    condition_type VARCHAR(32) NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    channel VARCHAR(16) NOT NULL DEFAULT 'TELEGRAM',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    cooldown_minutes INT NOT NULL DEFAULT 30,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_alerts_active ON user_alerts (is_active);
