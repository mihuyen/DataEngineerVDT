from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_dnse_realtime_ingest import DEFAULT_TICKER_FILE, resolve_symbols
from src.common.clickhouse_client import create_client, execute
from src.streaming.dnse_websocket import DNSEOhlcCandle, DNSEWebSocketConfig, stream_market_events

DDL_PATH = Path(__file__).resolve().parents[1] / "sql" / "ddl" / "fact_intraday_ohlcv.sql"
BRONZE_DIR = Path("data/bronze_local/dnse/ohlcv_1m")
BATCH_SIZE = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest DNSE's finalized one-minute OHLC candles (ohlc_closed.1 channel) into fact_intraday_ohlcv."
    )
    parser.add_argument(
        "--symbols", default=None, help="Comma-separated symbols, or ALL for the local universe."
    )
    parser.add_argument("--ticker-file", type=Path, default=DEFAULT_TICKER_FILE)
    parser.add_argument("--max-messages", type=int, default=100_000)
    parser.add_argument("--timeout-seconds", type=float, default=3600)
    return parser.parse_args()


def candle_row(candle: DNSEOhlcCandle) -> list:
    minute_ts = candle.minute_ts
    return [
        candle.ticker,
        minute_ts,
        minute_ts.date(),
        candle.resolution,
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume,
        1,
        "DNSE",
        datetime.now(),
    ]


COLUMN_NAMES = [
    "ticker",
    "minute_ts",
    "trading_date",
    "resolution",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "is_final",
    "data_source",
    "ingested_at",
]


def save_bronze_batch(candles: list[DNSEOhlcCandle]) -> None:
    if not candles:
        return
    for trading_date in sorted({candle.minute_ts.date() for candle in candles}):
        selected = [
            candle.to_dict() for candle in candles if candle.minute_ts.date() == trading_date
        ]
        output_path = (
            BRONZE_DIR
            / f"year={trading_date:%Y}"
            / f"month={trading_date:%m}"
            / f"day={trading_date:%d}"
            / "data.parquet"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame = pl.DataFrame(selected)
        if output_path.exists():
            frame = pl.concat([pl.read_parquet(output_path), frame], how="diagonal_relaxed")
        frame.unique(subset=["ticker", "minute_ts", "resolution"], keep="last").sort(
            ["minute_ts", "ticker"]
        ).write_parquet(output_path)


def flush_candles(client: object, candles: list[DNSEOhlcCandle]) -> int:
    if not candles:
        return 0
    client.insert(
        "fact_intraday_ohlcv",
        [candle_row(candle) for candle in candles],
        column_names=COLUMN_NAMES,
    )
    save_bronze_batch(candles)
    count = len(candles)
    candles.clear()
    return count


async def main_async() -> None:
    args = parse_args()
    load_dotenv()
    client = create_client()
    execute(client, DDL_PATH.read_text(encoding="utf-8"))

    config = DNSEWebSocketConfig.from_env(symbols=resolve_symbols(args.symbols, args.ticker_file))

    # Insert each candle as it arrives instead of buffering for the whole
    # --timeout-seconds window (up to 1h) and writing once at the end --
    # the DNSE connection drops periodically (ConnectionClosedError is
    # routine over a long-lived WS), and `restart: unless-stopped` then
    # starts a fresh process with an empty buffer, silently losing
    # everything accumulated since the last flush.
    total = 0
    pending: list[DNSEOhlcCandle] = []
    try:
        async for event in stream_market_events(
            config,
            max_messages=args.max_messages,
            timeout_seconds=args.timeout_seconds,
            include_ohlc=True,
            include_trades=False,
        ):
            if isinstance(event, DNSEOhlcCandle):
                pending.append(event)
                if len(pending) >= BATCH_SIZE:
                    total += flush_candles(client, pending)
    finally:
        total += flush_candles(client, pending)

    print(f"DNSE 1m OHLC ingest completed: candles={total} date={date.today()}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
