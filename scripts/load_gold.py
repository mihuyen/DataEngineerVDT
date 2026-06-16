from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, query_dataframe
from src.loaders.load_dimensions import (
    DEFAULT_LOCAL_SILVER_DIR,
    load_dim_date,
    load_dim_index,
    load_dim_sector,
    load_dim_stock,
)
from src.loaders.load_fact_daily_price import load_fact_daily_price, load_silver_ohlcv
from src.loaders.load_fact_market_index import load_fact_market_index
from src.loaders.load_fact_news_sentiment import load_fact_news_sentiment_daily
from src.loaders.load_fact_realtime_vwap import load_fact_realtime_vwap


TABLES = [
    "dim_date",
    "dim_sector",
    "dim_stock",
    "dim_index",
    "fact_daily_price",
    "fact_market_index",
    "fact_news_sentiment_daily",
    "fact_realtime_vwap",
    "fact_alert_event",
]


def verify_counts(client: object) -> pl.DataFrame:
    """Return row counts for Gold tables."""
    queries = [
        f"SELECT '{table_name}' AS table_name, count() AS row_count FROM {table_name}"
        for table_name in TABLES
    ]
    return query_dataframe(client, " UNION ALL ".join(queries))  # type: ignore[arg-type]


def truncate_gold_tables(client: object) -> None:
    """Make Gold load idempotent for local batch reloads."""
    for table_name in reversed(TABLES):
        execute(client, f"TRUNCATE TABLE IF EXISTS {table_name}")  # type: ignore[arg-type]


def load_silver_company_profile(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame | None:
    paths = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not paths:
        return None
    return pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")


def main() -> None:
    """Load Gold Layer dimensions and available batch facts."""
    client = create_client()
    silver_ohlcv = load_silver_ohlcv()
    silver_company_profile = load_silver_company_profile()
    tickers = sorted(silver_ohlcv.get_column("ticker").str.to_uppercase().unique().to_list())

    truncate_gold_tables(client)
    load_dim_date(client)
    load_dim_sector(client, company_frame=silver_company_profile)
    load_dim_stock(client, company_frame=silver_company_profile, tickers=tickers)
    load_dim_index(client)
    load_fact_daily_price(client, silver_ohlcv=silver_ohlcv)
    load_fact_market_index(
        client,
        silver_ohlcv=silver_ohlcv,
        company_profile=silver_company_profile,
    )
    try:
        load_fact_news_sentiment_daily(client)
    except FileNotFoundError as exc:
        print(f"- skipped fact_news_sentiment_daily: {exc}")
    load_fact_realtime_vwap(client)

    counts = verify_counts(client)
    print("Gold Layer load completed")
    print(counts.write_csv())


if __name__ == "__main__":
    main()
