CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id UUID PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist (user_id);
