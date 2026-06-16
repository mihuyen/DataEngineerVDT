from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

import polars as pl
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, query_dataframe
from src.loaders.load_fact_realtime_vwap import build_fact_realtime_vwap
from src.streaming.dnse_websocket import DNSEWebSocketConfig, collect_trade_ticks


DEFAULT_OUTPUT_DIR = Path("data/bronze_local/dnse/trades")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest real DNSE WebSocket trade ticks.")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols, e.g. VCB,FPT,HPG.")
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--load-vwap", action="store_true", help="Aggregate ticks and load fact_realtime_vwap.")
    parser.add_argument("--append", action="store_true", help="Append instead of truncating fact_realtime_vwap.")
    return parser.parse_args()


def parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    symbols = [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
    return symbols or None


def bronze_output_path(base_dir: Path, run_date: date | None = None) -> Path:
    selected_date = run_date or date.today()
    return (
        base_dir
        / f"year={selected_date:%Y}"
        / f"month={selected_date:%m}"
        / f"day={selected_date:%d}"
        / "data.parquet"
    )


def save_ticks_to_bronze(ticks: pl.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        existing = pl.read_parquet(output_path)
        ticks = pl.concat([existing, ticks], how="diagonal_relaxed").unique(
            subset=["ticker", "trade_ts", "price", "volume"],
            keep="last",
        )
    ticks.write_parquet(output_path)


async def main_async() -> None:
    args = parse_args()
    load_dotenv()
    config = DNSEWebSocketConfig.from_env(symbols=parse_symbols(args.symbols))
    ticks = await collect_trade_ticks(
        config,
        max_messages=args.max_messages,
        timeout_seconds=args.timeout_seconds,
    )

    output_path = bronze_output_path(args.output_dir)
    save_ticks_to_bronze(ticks, output_path)

    print("DNSE realtime ingest completed")
    print(f"- stream_url: {config.stream_url}")
    print(f"- channel: {config.trade_channel}")
    print(f"- symbols: {','.join(config.symbols)}")
    print(f"- ticks: {ticks.height}")
    print(f"- bronze_file: {output_path}")

    if args.load_vwap and not ticks.is_empty():
        client = create_client()
        if not args.append:
            execute(client, "TRUNCATE TABLE IF EXISTS fact_realtime_vwap")
        frame = build_fact_realtime_vwap(ticks.select(["ticker", "trade_ts", "price", "volume"]))
        client.insert_df("fact_realtime_vwap", frame.to_pandas())
        counts = query_dataframe(
            client,
            "SELECT count() AS row_count, uniqExact(ticker) AS ticker_count FROM fact_realtime_vwap",
        )
        print("- loaded_fact_realtime_vwap: yes")
        print(counts.write_csv())


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
