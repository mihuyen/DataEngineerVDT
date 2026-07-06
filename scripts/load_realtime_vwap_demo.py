from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, insert_dataframe, query_dataframe
from src.loaders.load_fact_realtime_vwap import generate_demo_trade_ticks
from scripts.run_realtime_vwap_kafka_consumer import run_backfill


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load demo realtime trade ticks into ClickHouse and backfill "
            "fact_realtime_vwap_1m_state, the same path production ticks take "
            "via the Kafka Materialized View. fact_realtime_vwap itself is a "
            "VIEW computed on top of that state table -- nothing is inserted "
            "into it directly."
        )
    )
    parser.add_argument("--tickers", default="ALL", help="Comma-separated tickers, or ALL for dim_stock.")
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--trades-per-minute", type=int, default=4)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append instead of truncating realtime_trade_ticks_raw and fact_realtime_vwap_1m_state.",
    )
    return parser.parse_args()


def load_all_tickers(client: object) -> list[str]:
    frame = query_dataframe(
        client,
        """
        SELECT upper(ticker) AS ticker
        FROM dim_stock
        WHERE notEmpty(ticker)
        ORDER BY ticker
        """,
    )
    tickers = [str(ticker).strip().upper() for ticker in frame["ticker"].to_list() if str(ticker).strip()]
    if not tickers:
        raise ValueError("No tickers found in dim_stock. Run the dimension loader first.")
    return tickers


def parse_tickers(value: str, client: object) -> list[str]:
    if value.strip().upper() == "ALL":
        return load_all_tickers(client)
    return [ticker.strip().upper() for ticker in value.split(",") if ticker.strip()]


def main() -> None:
    args = parse_args()
    client = create_client()
    tickers = parse_tickers(args.tickers, client)
    ticks = generate_demo_trade_ticks(
        tickers=tickers,
        minutes=args.minutes,
        trades_per_minute=args.trades_per_minute,
    )
    if not args.append:
        execute(client, "TRUNCATE TABLE IF EXISTS realtime_trade_ticks_raw")
        execute(client, "TRUNCATE TABLE IF EXISTS fact_realtime_vwap_1m_state")

    insert_dataframe(client, "realtime_trade_ticks_raw", ticks)
    for session_date in ticks["trade_ts"].dt.date().unique().sort().to_list():
        run_backfill(client, session_date.isoformat())

    counts = query_dataframe(
        client,
        "SELECT count() AS row_count, uniqExact(ticker) AS ticker_count FROM fact_realtime_vwap",
    )
    print("Realtime VWAP demo load completed")
    print(f"- tickers: {len(tickers)}")
    print(f"- input_ticks: {ticks.height}")
    print(counts.write_csv())


if __name__ == "__main__":
    main()
