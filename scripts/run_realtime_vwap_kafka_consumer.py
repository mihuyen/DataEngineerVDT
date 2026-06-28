from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, insert_dataframe, query_dataframe
from src.loaders.load_fact_realtime_vwap import build_fact_realtime_vwap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate raw ticks landed by the Kafka Engine Materialized View "
            "(realtime_trade_ticks_raw) into fact_realtime_vwap."
        )
    )
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--run-once", action="store_true")
    return parser.parse_args()


def run_cycle(client: object) -> dict:
    today = date.today()
    ticks = query_dataframe(
        client,
        f"""
        SELECT ticker, trade_ts, price, volume, data_source
        FROM realtime_trade_ticks_raw
        WHERE toDate(trade_ts) = toDate('{today.isoformat()}')
        """,
    )
    if ticks.is_empty():
        return {"ticks": 0, "rows": 0}

    frame = build_fact_realtime_vwap(ticks)
    partition_id = today.strftime("%Y%m%d")
    existing_partitions = client.query(
        "SELECT countIf(partition = %(partition_id)s) "
        "FROM system.parts WHERE table = 'fact_realtime_vwap' AND active",
        parameters={"partition_id": partition_id},
    ).result_rows[0][0]
    if existing_partitions:
        execute(client, f"ALTER TABLE fact_realtime_vwap DROP PARTITION {partition_id}")
    insert_dataframe(client, "fact_realtime_vwap", frame)  # type: ignore[arg-type]
    return {"ticks": ticks.height, "rows": frame.height}


def main() -> None:
    args = parse_args()
    client = create_client()
    while True:
        stats = run_cycle(client)
        print(f"ticks={stats['ticks']} minute_rows={stats['rows']}", flush=True)
        if args.run_once:
            break
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
