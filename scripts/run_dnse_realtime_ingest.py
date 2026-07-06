from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import polars as pl
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, insert_dataframe, query_dataframe
from src.common.minio_client import create_bucket_if_missing, create_client as create_minio_client, upload_file
from scripts.run_realtime_vwap_kafka_consumer import run_backfill
from src.streaming.dnse_websocket import (
    DNSEOhlcCandle,
    DNSETradeTick,
    DNSEWebSocketConfig,
    collect_trade_ticks,
    stream_market_events,
)
from src.streaming.kafka_producer import create_producer, publish_ohlcv_candle, publish_trade_tick


DEFAULT_OUTPUT_DIR = Path("data/bronze_local/dnse/trades")
DEFAULT_OHLCV_OUTPUT_DIR = Path("data/bronze_local/dnse/ohlcv_1m")
DEFAULT_TICKER_FILE = Path("configs/tickers.csv")
DEFAULT_DNSE_SYMBOLS = [
    "ACB",
    "BCM",
    "BID",
    "BVH",
    "CTG",
    "FPT",
    "GAS",
    "GVR",
    "HDB",
    "HPG",
    "LPB",
    "MBB",
    "MSN",
    "MWG",
    "PLX",
    "POW",
    "SAB",
    "SHB",
    "SSB",
    "SSI",
    "STB",
    "TCB",
    "TPB",
    "VCB",
    "VHM",
    "VIB",
    "VIC",
    "VJC",
    "VNM",
    "VPB",
    "VRE",
    "BSR",
    "CEO",
    "CMG",
    "DGW",
    "DIG",
    "DXG",
    "FRT",
    "GMD",
    "HAG",
    "HAH",
    "HCM",
    "HSG",
    "KBC",
    "KDH",
    "NKG",
    "PDR",
    "PNJ",
    "PVD",
    "PVS",
    "VND",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest real DNSE WebSocket trade ticks.")
    parser.add_argument(
        "--symbols",
        default=None,
        help="Comma-separated symbols, e.g. VCB,FPT,HPG. Use ALL for the local universe.",
    )
    parser.add_argument(
        "--ticker-file",
        type=Path,
        default=DEFAULT_TICKER_FILE,
        help="CSV fallback for --symbols ALL when ClickHouse is unavailable.",
    )
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ohlcv-output-dir", type=Path, default=DEFAULT_OHLCV_OUTPUT_DIR)
    parser.add_argument(
        "--load-vwap", action="store_true", help="Aggregate ticks and load fact_realtime_vwap."
    )
    parser.add_argument(
        "--append", action="store_true", help="Append instead of truncating fact_realtime_vwap."
    )
    parser.add_argument(
        "--produce-to-kafka",
        action="store_true",
        help="Publish each tick to the dnse-trades-raw Kafka topic as it arrives.",
    )
    parser.add_argument("--kafka-topic", default="dnse-trades-raw")
    parser.add_argument("--ohlcv-kafka-topic", default="dnse-ohlcv-1m")
    parser.add_argument(
        "--no-ohlcv",
        action="store_true",
        help="Disable the finalized one-minute OHLCV subscription.",
    )
    return parser.parse_args()


def parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    if value.strip().upper() == "ALL":
        return ["ALL"]
    symbols = [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
    return symbols or None


def load_all_symbols() -> list[str]:
    """Load the stock universe from ClickHouse dim_stock for DNSE subscriptions."""
    result = create_client().query(
        """
        SELECT upper(ticker) AS ticker
        FROM dim_stock
        WHERE notEmpty(ticker) AND exchange = 'HOSE'
        ORDER BY ticker
        """,
    )
    symbols = [str(row[0]).strip().upper() for row in result.result_rows if str(row[0]).strip()]
    if not symbols:
        raise ValueError("No symbols found in dim_stock. Run the dimension loader first.")
    return symbols


def read_symbols_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []

    frame = pl.read_csv(path)
    columns = {column.lower(): column for column in frame.columns}
    symbol_column = columns.get("symbol") or columns.get("ticker")
    if symbol_column is None:
        return []

    return sorted(
        {
            str(symbol).strip().upper()
            for symbol in frame.get_column(symbol_column).to_list()
            if str(symbol).strip()
        }
    )


def load_symbols_from_vnstock() -> list[str]:
    from src.ingestion.vnstock_ohlcv import fetch_ticker_universe

    universe = fetch_ticker_universe(exchanges=["HOSE"], source="kbs")
    return [
        str(symbol).strip().upper()
        for symbol in universe.get_column("symbol").to_list()
        if str(symbol).strip()
    ]


def load_all_symbols_with_fallback(ticker_file: Path = DEFAULT_TICKER_FILE) -> list[str]:
    try:
        return load_all_symbols()
    except Exception as exc:
        file_symbols = read_symbols_from_file(ticker_file)
        if file_symbols:
            print(f"ClickHouse dim_stock unavailable ({exc}); using {ticker_file}.")
            return file_symbols

        try:
            vnstock_symbols = load_symbols_from_vnstock()
            if vnstock_symbols:
                print(
                    f"ClickHouse dim_stock unavailable ({exc}); "
                    f"using vnstock universe ({len(vnstock_symbols)} symbols)."
                )
                return vnstock_symbols
        except Exception as vnstock_exc:
            print(f"vnstock universe unavailable ({vnstock_exc}); using built-in liquid universe.")

        print(f"ClickHouse dim_stock unavailable ({exc}); using built-in liquid universe.")
        return DEFAULT_DNSE_SYMBOLS


def resolve_symbols(value: str | None, ticker_file: Path = DEFAULT_TICKER_FILE) -> list[str] | None:
    parsed = parse_symbols(value)
    if parsed == ["ALL"]:
        return load_all_symbols_with_fallback(ticker_file)
    if parsed is not None:
        return parsed

    env_symbols = os.getenv("DNSE_WS_SYMBOLS", "").strip()
    if env_symbols.upper() == "ALL":
        return load_all_symbols_with_fallback(ticker_file)
    return None


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
        ticks = pl.concat([existing, ticks], how="diagonal_relaxed")
        unique_key = (
            ["ticker", "minute_ts", "resolution"]
            if "minute_ts" in ticks.columns
            else ["ticker", "trade_ts", "price", "volume"]
        )
        ticks = ticks.unique(subset=unique_key, keep="last")
    ticks.write_parquet(output_path)


def upload_bronze_backup(local_path: Path, bucket_prefix: str, bucket_name: str = "bronze") -> None:
    """Best-effort backup of the realtime Bronze parquet to MinIO.

    ClickHouse is the primary store for this module (raw ticks land there via
    the Kafka Materialized View and are pruned after 30 days), so this is only
    a durability backstop for the raw source -- a MinIO outage should not
    interrupt the realtime ingest loop.
    """
    if not local_path.is_file():
        return
    try:
        client = create_minio_client()
        create_bucket_if_missing(client, bucket_name)
        object_name = f"{bucket_prefix}/{local_path.relative_to(local_path.parents[3]).as_posix()}"
        upload_file(
            client=client,
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=local_path,
            content_type="application/vnd.apache.parquet",
        )
    except Exception as exc:
        print(f"- minio_backup_failed: {bucket_prefix} ({exc})")


def save_subscription_metadata(symbols: tuple[str, ...], output_path: Path) -> None:
    metadata_path = output_path.parent / "subscription.json"
    metadata_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(),
                "symbol_count": len(symbols),
                "symbols": list(symbols),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


async def main_async() -> None:
    args = parse_args()
    load_dotenv()
    config = DNSEWebSocketConfig.from_env(symbols=resolve_symbols(args.symbols, args.ticker_file))

    if args.produce_to_kafka:
        producer = create_producer()
        rows: list[dict] = []
        candle_rows: list[dict] = []
        async for event in stream_market_events(
            config,
            max_messages=args.max_messages,
            timeout_seconds=args.timeout_seconds,
            include_ohlc=not args.no_ohlcv,
        ):
            if isinstance(event, DNSETradeTick):
                publish_trade_tick(
                    producer,
                    ticker=event.ticker,
                    trade_ts=event.trade_ts,
                    price=event.price,
                    volume=event.volume,
                    topic=args.kafka_topic,
                    data_source="DNSE",
                )
                rows.append(event.to_dict())
            elif isinstance(event, DNSEOhlcCandle):
                publish_ohlcv_candle(
                    producer,
                    ticker=event.ticker,
                    minute_ts=event.minute_ts,
                    open_price=event.open,
                    high_price=event.high,
                    low_price=event.low,
                    close_price=event.close,
                    volume=event.volume,
                    topic=args.ohlcv_kafka_topic,
                    data_source="DNSE",
                )
                candle_rows.append(event.to_dict())
        producer.flush()
        ticks = (
            pl.DataFrame(rows)
            if rows
            else pl.DataFrame(
                schema={
                    "ticker": pl.String,
                    "trade_ts": pl.Datetime,
                    "price": pl.Float64,
                    "volume": pl.Int64,
                    "data_source": pl.String,
                    "raw_json": pl.String,
                }
            )
        )
        print(f"- published_to_kafka: {len(rows)} ticks -> topic '{args.kafka_topic}'")
        print(
            f"- published_ohlcv_to_kafka: {len(candle_rows)} candles "
            f"-> topic '{args.ohlcv_kafka_topic}'"
        )
    else:
        ticks = await collect_trade_ticks(
            config,
            max_messages=args.max_messages,
            timeout_seconds=args.timeout_seconds,
        )
        candle_rows = []

    output_path = bronze_output_path(args.output_dir)
    save_ticks_to_bronze(ticks, output_path)
    save_subscription_metadata(config.symbols, output_path)
    candle_frame = (
        pl.DataFrame(candle_rows)
        if candle_rows
        else pl.DataFrame(
            schema={
                "ticker": pl.String,
                "minute_ts": pl.Datetime,
                "resolution": pl.String,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Int64,
                "is_final": pl.Int8,
                "data_source": pl.String,
                "raw_json": pl.String,
            }
        )
    )
    ohlcv_output_path = bronze_output_path(args.ohlcv_output_dir)
    if not args.no_ohlcv:
        save_ticks_to_bronze(candle_frame, ohlcv_output_path)

    print("DNSE realtime ingest completed")
    print(f"- stream_url: {config.stream_url}")
    print(f"- channel: {config.trade_channel}")
    if not args.no_ohlcv:
        print(f"- ohlcv_channel: {config.ohlc_closed_channel}")
    preview_symbols = ",".join(config.symbols[:10])
    suffix = "..." if len(config.symbols) > 10 else ""
    print(f"- symbols: {len(config.symbols)} ({preview_symbols}{suffix})")
    print(f"- ticks: {ticks.height}")
    print(f"- bronze_file: {output_path}")
    if not args.no_ohlcv:
        print(f"- ohlcv_candles: {candle_frame.height}")
        print(f"- ohlcv_bronze_file: {ohlcv_output_path}")

    # Backup: mirror the local Bronze parquet files to MinIO so the raw
    # realtime source survives even though ClickHouse only retains 30 days
    # (see the TTL clauses on realtime_trade_ticks_raw / fact_intraday_ohlcv /
    # fact_realtime_vwap_1m_state in sql/streaming/realtime_vwap_kafka_engine.sql).
    upload_bronze_backup(output_path, bucket_prefix="dnse/trades")
    if not args.no_ohlcv:
        upload_bronze_backup(ohlcv_output_path, bucket_prefix="dnse/ohlcv_1m")

    if args.load_vwap and not ticks.is_empty():
        client = create_client()
        if not args.append:
            execute(client, "TRUNCATE TABLE IF EXISTS realtime_trade_ticks_raw")
            execute(client, "TRUNCATE TABLE IF EXISTS fact_realtime_vwap_1m_state")
        insert_dataframe(
            client,
            "realtime_trade_ticks_raw",
            ticks.select(["ticker", "trade_ts", "price", "volume", "data_source"]),
        )
        for session_date in ticks["trade_ts"].dt.date().unique().sort().to_list():
            run_backfill(client, session_date.isoformat())
        counts = query_dataframe(
            client,
            "SELECT count() AS row_count, uniqExact(ticker) AS ticker_count FROM fact_realtime_vwap",
        )
        print("- loaded_fact_realtime_vwap: yes (via realtime_trade_ticks_raw backfill)")
        print(counts.write_csv())


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
