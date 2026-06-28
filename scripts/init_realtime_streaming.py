from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STREAMING_SQL_PATH = PROJECT_ROOT / "sql" / "streaming" / "realtime_vwap_kafka_engine.sql"


def main() -> None:
    client = create_client()
    sql_text = STREAMING_SQL_PATH.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql_text.split(";") if statement.strip()]
    for statement in statements:
        execute(client, statement)
        print(f"- applied: {statement.splitlines()[0][:60]}...")
    print(f"Realtime streaming objects ready ({len(statements)} statements).")


if __name__ == "__main__":
    main()
