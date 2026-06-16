CREATE TABLE IF NOT EXISTS fact_news_sentiment_daily
(
    ticker String,
    date_id UInt32,
    news_date Date,
    news_count UInt32,
    source_count UInt8,
    positive_count UInt32,
    negative_count UInt32,
    neutral_count UInt32,
    avg_sentiment_score Float64,
    top_headline String,
    created_at DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(news_date)
ORDER BY (ticker, news_date);
