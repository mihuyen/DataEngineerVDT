from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from time import sleep
from typing import Any

import pandas as pd
import polars as pl
import yaml

from src.common.minio_client import create_client, upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}
DEFAULT_EXCHANGES = ("HOSE",)


def load_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_name: str = "vnstock_ohlcv",
) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == source_name or source.get("source_name") == source_name:
            return source

    raise ValueError(f"Source config not found: {source_name}")


def _normalise_ohlcv_frame(data: pd.DataFrame | pl.DataFrame) -> pl.DataFrame:
    frame = pl.from_pandas(data) if isinstance(data, pd.DataFrame) else data
    rename_map = {
        column: column.strip().lower().replace(" ", "_")
        for column in frame.columns
    }
    frame = frame.rename(rename_map)

    aliases = {
        "time": "date",
        "trading_date": "date",
        "tradingdate": "date",
        "match_volume": "volume",
    }
    for old_name, new_name in aliases.items():
        if old_name in frame.columns and new_name not in frame.columns:
            frame = frame.rename({old_name: new_name})

    if "date" in frame.columns:
        frame = frame.with_columns(pl.col("date").cast(pl.Date, strict=False))

    return frame


def fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pl.DataFrame:
    from vnstock.api.quote import Quote

    raw_data = Quote(symbol=ticker.upper(), source="VCI").history(
        start=start_date,
        end=end_date,
        interval="1D",
    )

    frame = _normalise_ohlcv_frame(raw_data)
    validate_schema(frame)
    return frame


def fetch_ticker_universe(
    exchanges: Sequence[str] = DEFAULT_EXCHANGES,
    source: str = "kbs",
) -> pl.DataFrame:
    """Fetch listed stock symbols by exchange from vnstock."""
    from vnstock.api.listing import Listing

    listing = Listing(source=source)
    raw_data = listing.symbols_by_exchange()
    frame = _normalise_listing_frame(raw_data)
    allowed_exchanges = {exchange.upper() for exchange in exchanges}

    if "symbol" not in frame.columns or "exchange" not in frame.columns:
        raise ValueError("Ticker universe is missing required columns: symbol, exchange")

    frame = frame.with_columns(
        pl.col("symbol").cast(pl.Utf8).str.to_uppercase(),
        pl.col("exchange").cast(pl.Utf8).str.to_uppercase(),
    )

    if "type" in frame.columns:
        frame = frame.with_columns(pl.col("type").cast(pl.Utf8).str.to_uppercase())
        frame = frame.filter(pl.col("type") == "STOCK")

    return (
        frame.filter(
            pl.col("exchange").is_in(sorted(allowed_exchanges))
            & pl.col("symbol").is_not_null()
            & (pl.col("symbol").str.len_chars() > 0)
        )
        .unique(subset=["symbol"])
        .sort("symbol")
    )


def _normalise_listing_frame(data: pd.DataFrame | pl.DataFrame) -> pl.DataFrame:
    frame = pl.from_pandas(data) if isinstance(data, pd.DataFrame) else data
    rename_map = {
        column: column.strip().lower().replace(" ", "_")
        for column in frame.columns
    }
    frame = frame.rename(rename_map)

    aliases = {
        "ticker": "symbol",
        "code": "symbol",
        "board": "exchange",
        "floor": "exchange",
    }
    for old_name, new_name in aliases.items():
        if old_name in frame.columns and new_name not in frame.columns:
            frame = frame.rename({old_name: new_name})

    return frame


def read_tickers_from_file(file_path: Path) -> list[str]:
    frame = pl.read_csv(file_path)
    columns = {column.lower(): column for column in frame.columns}
    symbol_column = columns.get("symbol") or columns.get("ticker")

    if symbol_column is None:
        raise ValueError("Ticker file must contain a symbol or ticker column")

    return (
        frame.select(pl.col(symbol_column).cast(pl.Utf8).str.to_uppercase().alias("symbol"))
        .drop_nulls()
        .unique()
        .sort("symbol")
        .get_column("symbol")
        .to_list()
    )


def validate_schema(frame: pl.DataFrame) -> None:
    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"OHLCV schema is missing required columns: {missing}")


def build_bronze_object_name(
    ticker: str,
    ingest_date: date | None = None,
    bronze_path: str = "ohlcv/",
    filename: str = "data.parquet",
) -> str:
    partition_date = ingest_date or date.today()
    cleaned_prefix = bronze_path.strip("/")
    return (
        f"{cleaned_prefix}/"
        f"ticker={ticker.upper()}/"
        f"year={partition_date:%Y}/"
        f"month={partition_date:%m}/"
        f"day={partition_date:%d}/"
        f"{filename}"
    )


def save_parquet(frame: pl.DataFrame, output_path: Path) -> Path:
    validate_schema(frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return output_path


def upload_to_minio(
    local_path: Path,
    object_name: str,
    bucket_name: str = "bronze",
) -> None:
    client = create_client()
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def run(
    ticker: str = "VCB",
    start_date: str | None = None,
    end_date: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    skip_existing: bool = False,
) -> dict[str, str]:
    today = date.today()
    resolved_end_date = end_date or today.isoformat()
    resolved_start_date = start_date or (today - timedelta(days=30)).isoformat()
    source_config = load_config(config_path)
    bronze_path = str(source_config.get("bronze_path", "ohlcv/"))
    bucket_name = str(source_config.get("bronze_bucket", "bronze"))
    object_name = build_bronze_object_name(ticker=ticker, bronze_path=bronze_path)
    local_path = local_output_dir / object_name

    if skip_existing and local_path.is_file():
        return {
            "ticker": ticker.upper(),
            "status": "SKIPPED",
            "start_date": resolved_start_date,
            "end_date": resolved_end_date,
            "local_path": str(local_path),
            "bucket": bucket_name,
            "object_name": object_name,
        }

    frame = fetch_ohlcv(ticker=ticker, start_date=resolved_start_date, end_date=resolved_end_date)
    save_parquet(frame, local_path)
    upload_to_minio(local_path=local_path, object_name=object_name, bucket_name=bucket_name)

    return {
        "ticker": ticker.upper(),
        "status": "SUCCESS",
        "start_date": resolved_start_date,
        "end_date": resolved_end_date,
        "local_path": str(local_path),
        "bucket": bucket_name,
        "object_name": object_name,
    }


def run_many(
    tickers: Sequence[str],
    start_date: str | None = None,
    end_date: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    continue_on_error: bool = True,
    request_delay_seconds: float = 0.0,
    skip_existing: bool = False,
) -> dict[str, Any]:
    results: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for ticker in tickers:
        cleaned_ticker = ticker.strip().upper()
        if not cleaned_ticker:
            continue

        try:
            results.append(
                run(
                    ticker=cleaned_ticker,
                    start_date=start_date,
                    end_date=end_date,
                    config_path=config_path,
                    local_output_dir=local_output_dir,
                    skip_existing=skip_existing,
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            errors.append({"ticker": cleaned_ticker, "error": str(exc)})

        if request_delay_seconds > 0:
            sleep(request_delay_seconds)

    skipped = sum(1 for result in results if result.get("status") == "SKIPPED")
    succeeded = sum(1 for result in results if result.get("status") == "SUCCESS")

    return {
        "requested": str(len(tickers)),
        "succeeded": str(succeeded),
        "skipped": str(skipped),
        "failed": str(len(errors)),
        "results": results,
        "errors": errors,
    }
