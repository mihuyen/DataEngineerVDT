CREATE TABLE IF NOT EXISTS dim_sector
(
    sector_id String,
    sector_name LowCardinality(String),
    industry_group LowCardinality(String),
    description String
)
ENGINE = MergeTree
ORDER BY sector_id;
