from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl
import yaml

from src.common.minio_client import create_client, upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
DEFAULT_INDEX_CODES = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"]
DEFAULT_PROVIDER_SYMBOLS = {
    "VNINDEX": "VNINDEX",
    "VN30": "VN30",
    "HNXINDEX": "HNXINDEX",
    "UPCOMINDEX": "UPCOMINDEX",
}
DEFAULT_PROVIDER_SOURCE = "vci"
REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def load_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_name: str = "market_index",
) -> dict[str, Any]:
    """Load market index source configuration from YAML."""
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == source_name or source.get("source_name") == source_name:
            return source

    raise ValueError(f"Source config not found: {source_name}")


def _normalise_index_frame(data: pd.DataFrame | pl.DataFrame, index_code: str) -> pl.DataFrame:
    """Normalize provider output to a consistent raw market index schema."""
    frame = pl.from_pandas(data) if isinstance(data, pd.DataFrame) else data
    frame = frame.rename(
        {
            column: column.strip().lower().replace(" ", "_")
            for column in frame.columns
        }
    )

    aliases = {
        "time": "date",
        "trading_date": "date",
        "tradingdate": "date",
        "value": "trading_value",
        "match_value": "trading_value",
        "match_volume": "volume",
    }
    for old_name, new_name in aliases.items():
        if old_name in frame.columns and new_name not in frame.columns:
            frame = frame.rename({old_name: new_name})

    if "date" in frame.columns:
        frame = frame.with_columns(pl.col("date").cast(pl.Date, strict=False))
    if "trading_value" not in frame.columns:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Float64).alias("trading_value"))

    return frame.with_columns(pl.lit(index_code.upper()).alias("index_code"))


def fetch_index_ohlcv(
    index_code: str,
    start_date: str,
    end_date: str,
    provider_symbol: str | None = None,
    provider_source: str = DEFAULT_PROVIDER_SOURCE,
) -> pl.DataFrame:
    """Fetch market index OHLCV from vnstock."""
    from vnstock.api.quote import Quote

    resolved_symbol = provider_symbol or DEFAULT_PROVIDER_SYMBOLS.get(index_code.upper(), index_code.upper())
    raw_data = Quote(source=provider_source, symbol=resolved_symbol).history(
        start=start_date,
        end=end_date,
        interval="1D",
    )
    frame = _normalise_index_frame(raw_data, index_code=index_code)
    validate_schema(frame)
    return frame


def validate_schema(frame: pl.DataFrame) -> None:
    """Validate required raw market index columns."""
    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Market index schema is missing required columns: {missing}")


def build_bronze_object_name(
    index_code: str,
    ingest_date: date | None = None,
    bronze_path: str = "market_index/",
    filename: str = "data.parquet",
) -> str:
    """Build Bronze object path for a market index parquet file."""
    partition_date = ingest_date or date.today()
    cleaned_prefix = bronze_path.strip("/")
    return (
        f"{cleaned_prefix}/"
        f"index_code={index_code.upper()}/"
        f"year={partition_date:%Y}/"
        f"month={partition_date:%m}/"
        f"day={partition_date:%d}/"
        f"{filename}"
    )


def save_parquet(frame: pl.DataFrame, output_path: Path) -> Path:
    """Save raw market index data as local parquet."""
    validate_schema(frame)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return output_path


def upload_to_minio(local_path: Path, object_name: str, bucket_name: str = "bronze") -> None:
    """Upload a local parquet file to MinIO Bronze."""
    client = create_client()
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def run(
    index_codes: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    continue_on_error: bool = True,
) -> list[dict[str, str]]:
    """Run Bronze ingest for configured market indices."""
    today = date.today()
    resolved_end_date = end_date or today.isoformat()
    resolved_start_date = start_date or (today - timedelta(days=30)).isoformat()
    source_config = load_config(config_path)

    configured_codes = source_config.get("index_codes") or DEFAULT_INDEX_CODES
    if index_codes:
        resolved_specs = [
            {
                "index_code": code,
                "provider_symbol": DEFAULT_PROVIDER_SYMBOLS.get(code.upper(), code.upper()),
            }
            for code in index_codes
        ]
    else:
        resolved_specs = [
            spec if isinstance(spec, dict) else {"index_code": str(spec), "provider_symbol": str(spec)}
            for spec in configured_codes
        ]
    bronze_path = str(source_config.get("bronze_path", "market_index/"))
    bucket_name = str(source_config.get("bronze_bucket", "bronze"))
    provider_source = str(source_config.get("provider_source", DEFAULT_PROVIDER_SOURCE))
    results: list[dict[str, str]] = []

    for spec in resolved_specs:
        index_code = str(spec["index_code"]).upper()
        provider_symbol = str(spec.get("provider_symbol") or index_code)
        try:
            frame = fetch_index_ohlcv(
                index_code=index_code,
                start_date=resolved_start_date,
                end_date=resolved_end_date,
                provider_symbol=provider_symbol,
                provider_source=provider_source,
            )
            object_name = build_bronze_object_name(index_code=index_code, bronze_path=bronze_path)
            local_path = local_output_dir / object_name
            save_parquet(frame, local_path)
            upload_to_minio(local_path=local_path, object_name=object_name, bucket_name=bucket_name)
            results.append(
                {
                    "index_code": index_code,
                    "provider_symbol": provider_symbol,
                    "provider_source": provider_source,
                    "status": "SUCCESS",
                    "start_date": resolved_start_date,
                    "end_date": resolved_end_date,
                    "local_path": str(local_path),
                    "bucket": bucket_name,
                    "object_name": object_name,
                }
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            results.append(
                {
                    "index_code": index_code,
                    "provider_symbol": provider_symbol,
                    "provider_source": provider_source,
                    "status": "FAILED",
                    "start_date": resolved_start_date,
                    "end_date": resolved_end_date,
                    "error": str(exc),
                }
            )

    return results
