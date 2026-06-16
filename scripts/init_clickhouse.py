from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"


def main() -> None:
    """Create ClickHouse database and run all Gold Layer DDL files."""
    database = os.getenv("CLICKHOUSE_DATABASE", "stock_lakehouse")
    default_client = create_client(database="default")
    execute(default_client, f"CREATE DATABASE IF NOT EXISTS {database}")

    client = create_client(database=database)
    ddl_files = sorted(DDL_DIR.glob("*.sql"))
    for ddl_file in ddl_files:
        execute(client, ddl_file.read_text(encoding="utf-8"))
        print(f"- applied: {ddl_file.name}")

    print(f"ClickHouse database ready: {database}")


if __name__ == "__main__":
    main()
