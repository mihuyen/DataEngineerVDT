from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.postgres_client import create_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl_postgres" / "user_alerts.sql"

DEMO_ALERTS = [
    # ticker = "ALL" means the rule scans every HOSE ticker, not one fixed stock.
    ("demo_user", "ALL", "RSI_ABOVE", 70.0, "TELEGRAM", 30),
    ("demo_user", "ALL", "RSI_BELOW", 30.0, "TELEGRAM", 30),
    ("demo_user", "ALL", "BB_BREAK", 0.0, "TELEGRAM", 30),
    ("demo_user", "ALL", "VWAP_DEVIATION", 2.0, "TELEGRAM", 15),
]


def create_table() -> None:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(DDL_PATH.read_text(encoding="utf-8"))


def seed_demo_alerts() -> int:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM user_alerts")
        (existing,) = cur.fetchone()
        if existing:
            return 0
        for user_id, ticker, condition_type, threshold, channel, cooldown in DEMO_ALERTS:
            cur.execute(
                """
                INSERT INTO user_alerts
                    (alert_id, user_id, ticker, condition_type, threshold_value, channel, cooldown_minutes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), user_id, ticker, condition_type, threshold, channel, cooldown),
            )
        return len(DEMO_ALERTS)


def main() -> None:
    create_table()
    print("- table user_alerts ready")
    inserted = seed_demo_alerts()
    print(f"- seeded {inserted} demo alert rule(s)")


if __name__ == "__main__":
    main()
