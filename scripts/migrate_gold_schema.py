from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"
GOLD_TABLES = [
    "fact_alert_event",
    "fact_realtime_vwap",
    "fact_news_sentiment_daily",
    "fact_market_index",
    "fact_daily_price",
    "dim_stock",
    "dim_sector",
    "dim_index",
    "dim_date",
]


def main() -> None:
    """Recreate Gold tables from the current DDL files.

    Local development note: this drops and recreates Gold tables so schema changes
    from the design document are applied cleanly.
    """
    client = create_client()
    for table_name in GOLD_TABLES:
        execute(client, f"DROP TABLE IF EXISTS {table_name}")
        print(f"- dropped: {table_name}")

    for ddl_file in sorted(DDL_DIR.glob("*.sql")):
        execute(client, ddl_file.read_text(encoding="utf-8"))
        print(f"- created: {ddl_file.name}")

    print("Gold schema recreated from DDL")


if __name__ == "__main__":
    main()
