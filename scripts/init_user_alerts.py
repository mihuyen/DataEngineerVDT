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
    #
    # RSI_ABOVE/RSI_BELOW/BB_BREAK all read fact_daily_price, which only gets
    # a new closing bar once a day (the 18:00 batch DAG). A 30-minute cooldown
    # meant the same unchanged daily value re-fired roughly every 30 minutes,
    # all day, for every one of the ~400 HOSE tickers that happened to match
    # -- with a real Telegram/email channel wired up, that is what actually
    # produced the spam. A 24h cooldown matches how often the underlying data
    # can change at all: one notification per ticker per day, not per cycle.
    #
    # Channel is EMAIL for these: they are end-of-day, report-style signals,
    # not something that needs an instant push -- an email digest once the
    # daily bar lands is a better fit than a phone notification.
    ("demo_user", "ALL", "RSI_ABOVE", 70.0, "EMAIL", 1440),
    ("demo_user", "ALL", "RSI_BELOW", 30.0, "EMAIL", 1440),
    ("demo_user", "ALL", "BB_BREAK", 0.0, "EMAIL", 1440),
    # VWAP_DEVIATION reads fact_realtime_vwap, which genuinely updates
    # intraday, so a much shorter cooldown is appropriate -- but 15 minutes
    # was still aggressive given deviation can oscillate across the 2%
    # threshold repeatedly; an hour is a more realistic personal-alert cadence.
    #
    # Channel stays TELEGRAM here: this is the one condition that's actually
    # time-sensitive intraday, so an instant push is the right fit.
    ("demo_user", "ALL", "VWAP_DEVIATION", 2.0, "TELEGRAM", 60),
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
