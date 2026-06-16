CREATE TABLE IF NOT EXISTS dim_stock
(
    ticker String,
    company_name String,
    exchange LowCardinality(String),
    sector_id String,
    listed_date Nullable(Date),
    status LowCardinality(String),
    shares_outstanding UInt64,
    free_float_rate Nullable(Float64),
    market_cap_latest Nullable(Float64),
    pe_latest Nullable(Float64),
    eps_latest Nullable(Float64),
    roe_latest Nullable(Float64),
    roa_latest Nullable(Float64),
    updated_at DateTime
)
ENGINE = MergeTree
ORDER BY ticker;
