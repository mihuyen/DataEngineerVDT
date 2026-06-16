CREATE TABLE IF NOT EXISTS dim_index
(
    index_id String,
    index_name LowCardinality(String),
    exchange LowCardinality(String),
    description String
)
ENGINE = MergeTree
ORDER BY index_id;
