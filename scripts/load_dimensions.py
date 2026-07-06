from __future__ import annotations

import os
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"
DIMENSION_TABLES = ["dim_date", "dim_sector", "dim_stock", "dim_index"]
DIMENSION_DDL_FILES = [
    "dim_date.sql",
    "dim_sector.sql",
    "dim_stock.sql",
    "dim_index.sql",
]


def ensure_database_and_dimension_tables() -> None:
    """Create the ClickHouse database and dimension tables if they are missing."""
    database = os.getenv("CLICKHOUSE_DATABASE", "stock_lakehouse")
    default_client = create_client(database="default")
    execute(default_client, f"CREATE DATABASE IF NOT EXISTS {database}")

    client = create_client(database=database)
    for ddl_file_name in DIMENSION_DDL_FILES:
        ddl_path = DDL_DIR / ddl_file_name
        execute(client, ddl_path.read_text(encoding="utf-8"))
        print(f"- ensured: {ddl_file_name}")


def load_silver_company_profile(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame | None:
    """Read Silver company profile data for stock and sector dimensions."""
    paths = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not paths:
        return None
    return pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")


def load_silver_tickers(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> list[str]:
    """Read available Silver OHLCV tickers as a fallback for dim_stock."""
    paths = sorted((local_silver_dir / "ohlcv").glob("year=*/month=*/data.parquet"))
    if not paths:
        return []

    frame = pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")
    if "ticker" not in frame.columns:
        return []
    return sorted(
        frame.get_column("ticker").drop_nulls().cast(pl.Utf8).str.to_uppercase().unique().to_list()
    )


def truncate_dimension_tables(client: object) -> None:
    """Reload dimensions idempotently for local development."""
    for table_name in ["dim_stock", "dim_sector", "dim_index", "dim_date"]:
        execute(client, f"TRUNCATE TABLE IF EXISTS {table_name}")  # type: ignore[arg-type]


def dimension_counts(client: object) -> pl.DataFrame:
    """Return row counts for dimension tables."""
    queries = [
        f"SELECT '{table_name}' AS table_name, count() AS row_count FROM {table_name}"
        for table_name in DIMENSION_TABLES
    ]
    return query_dataframe(client, " UNION ALL ".join(queries))  # type: ignore[arg-type]


def main() -> None:
    """Create and load Gold dimension tables for Day 15."""
    ensure_database_and_dimension_tables()
    client = create_client()
    company_profile = load_silver_company_profile()
    fallback_tickers = load_silver_tickers()

    truncate_dimension_tables(client)
    load_dim_date(client)
    load_dim_sector(client, company_frame=company_profile)
    load_dim_stock(client, company_frame=company_profile, tickers=fallback_tickers)
    load_dim_index(client)

    print("Gold dimension load completed")
    print(dimension_counts(client).write_csv())


if __name__ == "__main__":
    main()
