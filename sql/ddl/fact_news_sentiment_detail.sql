CREATE TABLE IF NOT EXISTS fact_news_sentiment_detail
(
    article_id String,
    ticker String,
    url String,
    title String,
    source LowCardinality(String),
    published_at Date,
    sentiment_label LowCardinality(String),
    sentiment_score Float64,
    confidence_score Float64,
    is_low_confidence UInt8,
    model_version LowCardinality(String),
    match_method LowCardinality(String),
    match_score UInt8,
    inferred_at DateTime
)
ENGINE = ReplacingMergeTree(inferred_at)
PARTITION BY toYYYYMM(published_at)
ORDER BY (ticker, published_at, article_id);
