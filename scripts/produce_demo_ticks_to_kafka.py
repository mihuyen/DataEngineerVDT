from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.loaders.load_fact_realtime_vwap import generate_demo_trade_ticks
from src.streaming.kafka_producer import create_producer, publish_trade_tick


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish synthetic trade ticks to the dnse-trades-raw Kafka topic for demo/testing."
    )
    parser.add_argument("--tickers", default="VCB,FPT,HPG")
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--trades-per-minute", type=int, default=4)
    parser.add_argument("--topic", default="dnse-trades-raw")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    ticks = generate_demo_trade_ticks(
        tickers=tickers,
        minutes=args.minutes,
        trades_per_minute=args.trades_per_minute,
    )

    producer = create_producer()
    for row in ticks.iter_rows(named=True):
        publish_trade_tick(
            producer,
            ticker=row["ticker"],
            trade_ts=row["trade_ts"],
            price=row["price"],
            volume=row["volume"],
            topic=args.topic,
        )
    producer.flush()
    print(f"Published {ticks.height} demo ticks to topic '{args.topic}'")


if __name__ == "__main__":
    main()
