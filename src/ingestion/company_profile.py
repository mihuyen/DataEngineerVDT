from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from time import sleep
from typing import Any

import pandas as pd
import polars as pl
import yaml

from src.common.minio_client import create_client, upload_file
from src.ingestion.vnstock_ohlcv import DEFAULT_EXCHANGES, fetch_ticker_universe, read_tickers_from_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
REQUIRED_COLUMNS = {"symbol"}


def load_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_name: str = "company_profile",
) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == source_name or source.get("source_name") == source_name:
            return source

    raise ValueError(f"Source config not found: {source_name}")


def _normalise_profile_frame(
    data: pd.DataFrame | pl.DataFrame,
    ticker: str,
    exchange: str | None = None,
    source: str = "kbs",
) -> pl.DataFrame:
    frame = pl.from_pandas(data) if isinstance(data, pd.DataFrame) else data
    frame = frame.rename(
        {
            column: column.strip().lower().replace(" ", "_")
            for column in frame.columns
        }
    )

    if "symbol" not in frame.columns:
        frame = frame.with_columns(pl.lit(ticker.upper()).alias("symbol"))

    if "exchange" not in frame.columns:
        frame = frame.with_columns(pl.lit(exchange).alias("exchange"))

    return frame.with_columns(
        pl.col("symbol").cast(pl.Utf8).str.to_uppercase(),
        pl.col("exchange").cast(pl.Utf8).str.to_uppercase(),
        pl.lit(source.upper()).alias("source"),
        pl.lit(datetime.now().isoformat(timespec="seconds")).alias("ingested_at"),
    )


def fetch_company_profile(
    ticker: str,
    exchange: str | None = None,
    source: str = "kbs",
) -> pl.DataFrame:
    from vnstock.api.company import Company

    company = Company(source=source, symbol=ticker.upper())
    raw_data = company.overview()
    frame = _normalise_profile_frame(raw_data, ticker=ticker, exchange=exchange, source=source)
    validate_schema(frame)
    return frame


def validate_schema(frame: pl.DataFrame) -> None:
    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Company profile schema is missing required columns: {missing}")


def build_bronze_object_name(
    ingest_date: date | None = None,
    bronze_path: str = "company_profile/",
    filename: str = "data.parquet",
) -> str:
    partition_date = ingest_date or date.today()
    cleaned_prefix = bronze_path.strip("/")
    return (
        f"{cleaned_prefix}/"
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


def upload_to_minio(local_path: Path, object_name: str, bucket_name: str = "bronze") -> None:
    client = create_client()
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def resolve_ticker_universe(
    tickers: Sequence[str] | None = None,
    ticker_file: Path | None = None,
    exchanges: Sequence[str] = DEFAULT_EXCHANGES,
    listing_source: str = "kbs",
) -> pl.DataFrame:
    if tickers:
        return pl.DataFrame(
            {
                "symbol": [ticker.strip().upper() for ticker in tickers if ticker.strip()],
                "exchange": [None for ticker in tickers if ticker.strip()],
            }
        )

    if ticker_file:
        resolved_tickers = read_tickers_from_file(ticker_file)
        return pl.DataFrame(
            {
                "symbol": resolved_tickers,
                "exchange": [None for _ in resolved_tickers],
            }
        )

    universe = fetch_ticker_universe(exchanges=exchanges, source=listing_source)
    return universe.select(["symbol", "exchange"])


def fetch_company_listing(
    exchanges: Sequence[str] = DEFAULT_EXCHANGES,
    listing_source: str = "kbs",
) -> pl.DataFrame:
    frame = fetch_ticker_universe(exchanges=exchanges, source=listing_source)
    return frame.with_columns(
        pl.lit(listing_source.upper()).alias("source"),
        pl.lit(datetime.now().isoformat(timespec="seconds")).alias("ingested_at"),
    )


def run(
    tickers: Sequence[str] | None = None,
    ticker_file: Path | None = None,
    exchanges: Sequence[str] | None = None,
    limit: int | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    continue_on_error: bool = True,
    mode: str = "listing",
    request_delay_seconds: float = 0.0,
    skip_existing: bool = False,
) -> dict[str, Any]:
    source_config = load_config(config_path)
    configured_exchanges = source_config.get("default_exchanges") or DEFAULT_EXCHANGES
    resolved_exchanges = exchanges or configured_exchanges
    profile_source = str(source_config.get("profile_source", "kbs"))
    listing_source = str(source_config.get("listing_source", "kbs"))
    bronze_path = str(source_config.get("bronze_path", "company_profile/"))
    mode_bronze_path = f"{bronze_path.strip('/')}/dataset={mode}/"
    bucket_name = str(source_config.get("bronze_bucket", "bronze"))

    if mode not in {"listing", "profile"}:
        raise ValueError("mode must be 'listing' or 'profile'")

    if mode == "listing" and not tickers and not ticker_file:
        result_frame = fetch_company_listing(
            exchanges=resolved_exchanges,
            listing_source=listing_source,
        )
        if limit:
            result_frame = result_frame.head(limit)
        object_name = build_bronze_object_name(bronze_path=mode_bronze_path)
        local_path = local_output_dir / object_name
        save_parquet(result_frame, local_path)
        upload_to_minio(local_path=local_path, object_name=object_name, bucket_name=bucket_name)
        return {
            "mode": mode,
            "requested": str(len(result_frame)),
            "succeeded": str(len(result_frame)),
            "failed": "0",
            "local_path": str(local_path),
            "bucket": bucket_name,
            "object_name": object_name,
            "errors": [],
        }

    universe = resolve_ticker_universe(
        tickers=tickers,
        ticker_file=ticker_file,
        exchanges=resolved_exchanges,
        listing_source=listing_source,
    )
    if limit:
        universe = universe.head(limit)

    results: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    skipped = 0

    for row in universe.iter_rows(named=True):
        ticker = str(row["symbol"]).upper()
        exchange = row.get("exchange")
        ticker_bronze_path = f"{mode_bronze_path.strip('/')}/ticker={ticker}/"
        object_name = build_bronze_object_name(bronze_path=ticker_bronze_path)
        local_path = local_output_dir / object_name

        if skip_existing and local_path.is_file():
            skipped += 1
            results.append(
                {
                    "symbol": ticker,
                    "status": "SKIPPED",
                    "local_path": str(local_path),
                    "bucket": bucket_name,
                    "object_name": object_name,
                }
            )
            continue

        try:
            frame = fetch_company_profile(ticker=ticker, exchange=exchange, source=profile_source)
            save_parquet(frame, local_path)
            upload_to_minio(local_path=local_path, object_name=object_name, bucket_name=bucket_name)
            results.append(
                {
                    "symbol": ticker,
                    "status": "SUCCESS",
                    "local_path": str(local_path),
                    "bucket": bucket_name,
                    "object_name": object_name,
                }
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            errors.append({"symbol": ticker, "error": str(exc)})

        if request_delay_seconds > 0:
            sleep(request_delay_seconds)

    succeeded = sum(1 for result in results if result["status"] == "SUCCESS")
    if not results and errors:
        raise ValueError("No company profile data was fetched successfully")

    return {
        "mode": "profile",
        "requested": str(len(universe)),
        "succeeded": str(succeeded),
        "skipped": str(skipped),
        "failed": str(len(errors)),
        "local_path": str(local_output_dir / mode_bronze_path),
        "bucket": bucket_name,
        "object_name": mode_bronze_path.strip("/"),
        "results": results,
        "errors": errors,
    }
