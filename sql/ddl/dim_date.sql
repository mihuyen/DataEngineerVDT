CREATE TABLE IF NOT EXISTS dim_date
(
    date_id UInt32,
    date Date,
    year UInt16,
    quarter UInt8,
    month UInt8,
    week UInt8,
    day_of_week LowCardinality(String),
    is_trading_day UInt8
)
ENGINE = MergeTree
ORDER BY date_id;
