from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"

# fact_alert_event and fact_intraday_ohlcv are owned by the continuous
# alert-engine service and the Kafka-engine Materialized View pipeline
# respectively. DROP TABLE here would destroy their history on every DAG run
# regardless of what load_gold.py does downstream (it ran before
# load_gold.py's own truncate-avoidance fix could matter at all) -- this
# table set must never be dropped, only created if missing.
#
# fact_realtime_vwap is not in sql/ddl at all: it is a plain VIEW defined in
# sql/streaming/realtime_vwap_kafka_engine.sql (applied by
# scripts/init_realtime_streaming.py), computed on top of the
# AggregatingMergeTree state table fact_realtime_vwap_1m_state -- there is no
# physical table for this loop to create or skip.
NO_DROP_TABLES = [
    "fact_alert_event",
    "fact_alert_rule_state",
    "fact_intraday_ohlcv",
]

GOLD_TABLES = [
    "fact_news_sentiment_daily",
    "fact_market_index",
    "fact_daily_price",
    "dim_stock",
    "dim_sector",
    "dim_index",
    "dim_date",
]


def main() -> None:
    """Recreate batch Gold tables from the current DDL files.

    Local development note: this drops and recreates the batch dimension/fact
    tables so schema changes from the design document are applied cleanly --
    they are always fully repopulated by load_gold.py anyway. Tables owned by
    continuous services (NO_DROP_TABLES) are only created if missing, never
    dropped, since they are not repopulated from Silver by anything.
    """
    client = create_client()
    for table_name in GOLD_TABLES:
        execute(client, f"DROP TABLE IF EXISTS {table_name}")
        print(f"- dropped: {table_name}")

    for ddl_file in sorted(DDL_DIR.glob("*.sql")):
        table_name = ddl_file.stem
        if table_name in NO_DROP_TABLES:
            print(f"- skipped drop (owned by continuous service): {table_name}")
        execute(client, ddl_file.read_text(encoding="utf-8"))
        print(f"- created: {ddl_file.name}")

    print("Gold schema recreated from DDL")


if __name__ == "__main__":
    main()
