from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, query_dataframe
from src.loaders.load_fact_realtime_vwap import generate_demo_trade_ticks, load_fact_realtime_vwap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load demo realtime VWAP rows into ClickHouse.")
    parser.add_argument("--tickers", default="VCB,FPT,HPG")
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--trades-per-minute", type=int, default=4)
    parser.add_argument("--append", action="store_true", help="Append instead of truncating fact_realtime_vwap.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = create_client()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    ticks = generate_demo_trade_ticks(
        tickers=tickers,
        minutes=args.minutes,
        trades_per_minute=args.trades_per_minute,
    )
    if not args.append:
        execute(client, "TRUNCATE TABLE IF EXISTS fact_realtime_vwap")
    frame = load_fact_realtime_vwap(client, trade_ticks=ticks)
    counts = query_dataframe(
        client,
        "SELECT count() AS row_count, uniqExact(ticker) AS ticker_count FROM fact_realtime_vwap",
    )
    print("Realtime VWAP demo load completed")
    print(f"- input_ticks: {ticks.height}")
    print(f"- loaded_rows: {frame.height}")
    print(counts.write_csv())


if __name__ == "__main__":
    main()
