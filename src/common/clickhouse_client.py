from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client
from dotenv import load_dotenv

from src.common.secrets import get_secret

if TYPE_CHECKING:
    import polars as pl

load_dotenv()


def create_client(database: str | None = None) -> Client:
    """Create a ClickHouse client from environment variables."""
    return get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=get_secret("CLICKHOUSE_PASSWORD", required=True),
        database=database or os.getenv("CLICKHOUSE_DATABASE", "stock_lakehouse"),
    )


def execute(client: Client, sql: str) -> Any:
    """Execute a SQL statement."""
    return client.command(sql)


def insert_dataframe(client: Client, table_name: str, frame: "pl.DataFrame") -> None:
    """Insert a Polars DataFrame into ClickHouse.

    polars/pandas are imported lazily here, not at module level, so services
    that only ever call create_client()/execute()/query()/insert() directly
    (e.g. the alert engine) don't need polars/pandas/pyarrow installed at
    all -- only callers that actually pass/receive a DataFrame do.
    """
    if frame.is_empty():
        return
    client.insert_df(table_name, frame.to_pandas())


def query_dataframe(client: Client, sql: str) -> "pl.DataFrame":
    """Query ClickHouse and return a Polars DataFrame."""
    import polars as pl

    result = client.query_df(sql)
    return pl.from_pandas(result)
