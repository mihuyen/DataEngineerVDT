from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, query_dataframe


REQUIRED_TABLES = [
    "dim_date",
    "dim_sector",
    "dim_stock",
    "dim_index",
    "fact_daily_price",
    "fact_market_index",
    "fact_news_sentiment_daily",
    "fact_news_sentiment_detail",
    "fact_realtime_vwap",
    "fact_alert_event",
]


def main() -> None:
    """Validate basic Gold Layer table counts and print a sample query."""
    client = create_client()

    print("Gold Layer validation")
    for table_name in REQUIRED_TABLES:
        result = query_dataframe(client, f"SELECT count() AS row_count FROM {table_name}")
        row_count = result.item(0, "row_count")
        status = "OK" if row_count > 0 else "EMPTY"
        print(f"- {table_name}: {status} ({row_count})")

    sample = query_dataframe(client, "SELECT * FROM fact_daily_price LIMIT 10")
    print("Sample query: SELECT * FROM fact_daily_price LIMIT 10")
    print(sample)


if __name__ == "__main__":
    main()
