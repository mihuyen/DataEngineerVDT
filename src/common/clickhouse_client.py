from __future__ import annotations

import os
from typing import Any

import polars as pl
from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client
from dotenv import load_dotenv

load_dotenv()


def create_client(database: str | None = None) -> Client:
    """Create a ClickHouse client from environment variables."""
    return get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=database or os.getenv("CLICKHOUSE_DATABASE", "stock_lakehouse"),
    )


def execute(client: Client, sql: str) -> Any:
    """Execute a SQL statement."""
    return client.command(sql)


def insert_dataframe(client: Client, table_name: str, frame: pl.DataFrame) -> None:
    """Insert a Polars DataFrame into ClickHouse."""
    if frame.is_empty():
        return
    client.insert_df(table_name, frame.to_pandas())


def query_dataframe(client: Client, sql: str) -> pl.DataFrame:
    """Query ClickHouse and return a Polars DataFrame."""
    result = client.query_df(sql)
    return pl.from_pandas(result)
