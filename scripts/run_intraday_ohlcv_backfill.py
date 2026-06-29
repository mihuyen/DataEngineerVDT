from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, insert_dataframe


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "fact_intraday_ohlcv.sql"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local" / "intraday_ohlcv_1m"
SILVER_DIR = PROJECT_ROOT / "data" / "silver_local" / "intraday_ohlcv_1m"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill one-minute HOSE candles from Vnstock.")
    parser.add_argument(
        "--tickers", nargs="+", help="Ticker list; defaults to ClickHouse HOSE universe."
    )
    parser.add_argument(
        "--date", help="Trading date YYYY-MM-DD; defaults to latest daily Gold date."
    )
    parser.add_argument("--source", default="kbs", choices=["kbs", "vci"])
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--request-delay-seconds", type=float, default=1.0)
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def normalize_intraday_frame(data: pd.DataFrame | pl.DataFrame, ticker: str) -> pl.DataFrame:
    frame = pl.from_pandas(data) if isinstance(data, pd.DataFrame) else data
    rename_map = {column: column.strip().lower().replace(" ", "_") for column in frame.columns}
    frame = frame.rename(rename_map)
    if "time" not in frame.columns and "datetime" in frame.columns:
        frame = frame.rename({"datetime": "time"})
    required = {"time", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Intraday schema missing columns: {', '.join(sorted(missing))}")

    return (
        frame.select(
            pl.lit(ticker.upper()).alias("ticker"),
            pl.col("time").cast(pl.Datetime, strict=False).alias("minute_ts"),
            pl.lit("1m").alias("resolution"),
            pl.col("open").cast(pl.Float64, strict=False),
            pl.col("high").cast(pl.Float64, strict=False),
            pl.col("low").cast(pl.Float64, strict=False),
            pl.col("close").cast(pl.Float64, strict=False),
            pl.col("volume").cast(pl.UInt64, strict=False),
        )
        .drop_nulls(["minute_ts", "open", "high", "low", "close", "volume"])
        .filter(
            (pl.col("open") > 0)
            & (pl.col("high") >= pl.col("low"))
            & (pl.col("low") > 0)
            & (pl.col("close") > 0)
        )
        .unique(subset=["ticker", "minute_ts", "resolution"], keep="last")
        .sort("minute_ts")
    )


def storage_path(base_dir: Path, source: str, ticker: str, trading_date: date) -> Path:
    return (
        base_dir
        / f"source={source.lower()}"
        / f"ticker={ticker.upper()}"
        / f"year={trading_date:%Y}"
        / f"month={trading_date:%m}"
        / f"day={trading_date:%d}"
        / "data.parquet"
    )


def load_tickers(client: object) -> list[str]:
    result = client.query("SELECT ticker FROM dim_stock WHERE exchange = 'HOSE' ORDER BY ticker")
    return [str(row[0]).upper() for row in result.result_rows]


def resolve_trading_date(client: object, value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    result = client.query("SELECT max(trading_date) FROM fact_daily_price").result_rows
    if not result or result[0][0] is None:
        raise ValueError("Cannot resolve latest trading date from fact_daily_price")
    return result[0][0]


def main() -> None:
    from vnstock.ui import Market

    args = parse_args()
    client = create_client()
    execute(client, DDL_PATH.read_text(encoding="utf-8"))
    trading_date = resolve_trading_date(client, args.date)
    tickers = [ticker.upper() for ticker in args.tickers] if args.tickers else load_tickers(client)
    if args.limit:
        tickers = tickers[: args.limit]

    market = Market()
    succeeded = 0
    failed = 0
    inserted = 0
    for ticker in tickers:
        try:
            raw = market.equity(ticker).ohlcv(
                count=args.count,
                resolution="1m",
                source=args.source,
            )
            normalized = normalize_intraday_frame(raw, ticker).filter(
                pl.col("minute_ts").dt.date() == trading_date
            )
            if normalized.is_empty():
                print(f"- {ticker}: EMPTY", flush=True)
                continue

            raw_frame = pl.from_pandas(raw) if isinstance(raw, pd.DataFrame) else raw
            bronze_path = storage_path(BRONZE_DIR, args.source, ticker, trading_date)
            bronze_path.parent.mkdir(parents=True, exist_ok=True)
            raw_frame.write_parquet(bronze_path)

            now = datetime.now()
            silver = normalized.with_columns(
                pl.lit(trading_date).cast(pl.Date).alias("trading_date"),
                pl.lit(1, dtype=pl.UInt8).alias("is_final"),
                pl.lit(f"VNSTOCK_{args.source.upper()}").alias("data_source"),
                pl.lit(now).alias("ingested_at"),
            ).select(
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
            )
            silver_path = storage_path(SILVER_DIR, args.source, ticker, trading_date)
            silver_path.parent.mkdir(parents=True, exist_ok=True)
            silver.write_parquet(silver_path)
            insert_dataframe(client, "fact_intraday_ohlcv", silver)
            succeeded += 1
            inserted += silver.height
            print(f"- {ticker}: {silver.height} candles", flush=True)
        except Exception as exc:
            failed += 1
            print(f"- {ticker}: FAILED ({exc})", flush=True)
            if args.fail_fast:
                raise
        if args.request_delay_seconds > 0:
            time.sleep(args.request_delay_seconds)

    print(
        f"Intraday backfill completed: requested={len(tickers)} "
        f"succeeded={succeeded} failed={failed} inserted={inserted} date={trading_date}"
    )


if __name__ == "__main__":
    main()
