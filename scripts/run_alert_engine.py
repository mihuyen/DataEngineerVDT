from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.alert_engine.engine import run_check_cycle
from src.common.clickhouse_client import create_client as create_clickhouse_client
from src.common.postgres_client import create_connection as create_postgres_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Alert Engine checker loop.")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--run-once", action="store_true")
    return parser.parse_args()


def run_cycle() -> None:
    pg_conn = create_postgres_connection()
    try:
        ch_client = create_clickhouse_client()
        results = run_check_cycle(pg_conn, ch_client)
    finally:
        pg_conn.close()

    triggered = [r for r in results if r.triggered]
    sent = [r for r in triggered if r.sent]
    skipped = [r for r in triggered if r.skipped_cooldown]
    print(
        f"checked={len(results)} triggered={len(triggered)} sent={len(sent)} "
        f"skipped_cooldown={len(skipped)}",
        flush=True,
    )


def main() -> None:
    args = parse_args()
    while True:
        run_cycle()
        if args.run_once:
            break
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
