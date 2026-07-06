from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import polars as pl

from src.common.minio_client import create_client, create_bucket_if_missing, list_objects, upload_file
from src.quality.ohlcv_expectations import save_quality_report, validate_ohlcv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"
BRONZE_PREFIX = "ohlcv"
SILVER_PREFIX = "ohlcv"


def build_silver_object_name(
    partition_date: date | None = None,
    filename: str = "data.parquet",
) -> str:
    """Build the Silver OHLCV object name partitioned by year and month (all tickers combined)."""
    output_date = partition_date or date.today()
    return (
        f"{SILVER_PREFIX}/"
        f"year={output_date:%Y}/"
        f"month={output_date:%m}/"
        f"{filename}"
    )


def _read_bronze_from_local(local_bronze_dir: Path) -> pl.DataFrame | None:
    """Read local Bronze parquet files (year/month/day partition, all tickers combined)."""
    base_dir = local_bronze_dir / BRONZE_PREFIX
    files = sorted(base_dir.glob("year=*/month=*/day=*/data.parquet"))
    if not files:
        return None
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def _read_bronze_from_minio() -> pl.DataFrame:
    """Read Bronze parquet files from MinIO."""
    client = create_client()
    prefix = f"{BRONZE_PREFIX}/"
    frames: list[pl.DataFrame] = []

    for item in list_objects(client, BRONZE_BUCKET, prefix=prefix):
        object_name = item.object_name or ""
        if not object_name.endswith(".parquet"):
            continue
        response = client.get_object(BRONZE_BUCKET, object_name)
        try:
            frames.append(pl.read_parquet(BytesIO(response.read())))
        finally:
            response.close()
            response.release_conn()

    if not frames:
        raise FileNotFoundError("No Bronze OHLCV parquet files found")
    return pl.concat(frames, how="diagonal_relaxed")


def discover_local_bronze_tickers(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> list[str]:
    """Discover tickers present in the combined local Bronze OHLCV parquet files."""
    frame = _read_bronze_from_local(local_bronze_dir)
    if frame is None:
        return []
    frame = normalize_columns(frame)
    if "ticker" not in frame.columns:
        return []
    return sorted(
        frame.get_column("ticker")
        .drop_nulls()
        .cast(pl.Utf8)
        .str.to_uppercase()
        .unique()
        .to_list()
    )


def load_bronze_data(
    start_date: str | None = None,
    end_date: str | None = None,
    local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    prefer_local: bool = True,
) -> pl.DataFrame:
    """Load all Bronze OHLCV data from local cache or MinIO and filter by date range."""
    frame = _read_bronze_from_local(local_bronze_dir) if prefer_local else None
    if frame is None:
        frame = _read_bronze_from_minio()

    frame = normalize_columns(frame)
    if "date" in frame.columns:
        frame = frame.with_columns(pl.col("date").cast(pl.Date, strict=False))
    if start_date:
        frame = frame.filter(pl.col("date") >= pl.lit(start_date).cast(pl.Date))
    if end_date:
        frame = frame.filter(pl.col("date") <= pl.lit(end_date).cast(pl.Date))
    return frame


def normalize_columns(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize column names to lowercase snake_case."""
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
        "vol": "volume",
    }
    for old_name, new_name in aliases.items():
        if old_name in frame.columns and new_name not in frame.columns:
            frame = frame.rename({old_name: new_name})
    return frame


def cast_schema(frame: pl.DataFrame) -> pl.DataFrame:
    """Cast OHLCV columns to the Silver schema."""
    return frame.with_columns(
        pl.col("date").cast(pl.Date, strict=False),
        pl.col("open").cast(pl.Float64, strict=False),
        pl.col("high").cast(pl.Float64, strict=False),
        pl.col("low").cast(pl.Float64, strict=False),
        pl.col("close").cast(pl.Float64, strict=False),
        pl.col("volume").cast(pl.Int64, strict=False),
    )


def remove_duplicates(frame: pl.DataFrame) -> pl.DataFrame:
    """Remove duplicate OHLCV rows by ticker and date."""
    return frame.unique(subset=["ticker", "date"], keep="last", maintain_order=True)


def remove_invalid_records(frame: pl.DataFrame) -> pl.DataFrame:
    """Remove invalid OHLCV rows before writing Silver data."""
    return frame.filter(
        (pl.col("volume") >= 0)
        & (pl.col("open") > 0)
        & (pl.col("high") > 0)
        & (pl.col("low") > 0)
        & (pl.col("close") > 0)
        & (pl.col("high") >= pl.col("low"))
    )


def add_metadata_columns(
    frame: pl.DataFrame,
    source_name: str = "vnstock_ohlcv",
) -> pl.DataFrame:
    """Add metadata columns required by the Silver Layer."""
    now = datetime.now(timezone.utc)
    return frame.with_columns(
        pl.col("ticker").cast(pl.Utf8).str.to_uppercase().alias("ticker"),
        pl.lit(now).alias("ingested_at"),
        pl.lit(now).alias("processed_at"),
        pl.lit(source_name).alias("source_name"),
    )


def transform_ohlcv(
    frame: pl.DataFrame,
    source_name: str = "vnstock_ohlcv",
) -> pl.DataFrame:
    """Run all OHLCV Silver transformations for the combined multi-ticker frame."""
    return (
        frame.pipe(normalize_columns)
        .pipe(cast_schema)
        .pipe(add_metadata_columns, source_name=source_name)
        .pipe(remove_invalid_records)
        .pipe(remove_duplicates)
        .sort(["ticker", "date"])
    )


def save_to_silver(
    frame: pl.DataFrame,
    output_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    partition_date: date | None = None,
) -> Path:
    """Write Silver OHLCV parquet to a local path matching the MinIO object layout."""
    object_name = build_silver_object_name(partition_date=partition_date)
    output_path = output_dir / object_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return output_path


def upload_silver_to_minio(local_path: Path, object_name: str, bucket_name: str = SILVER_BUCKET) -> None:
    """Upload a local Silver parquet file to MinIO."""
    client = create_client()
    create_bucket_if_missing(client, bucket_name)
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def run_many(
    tickers: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    upload_to_minio: bool = True,
    continue_on_error: bool = True,
    skip_existing: bool = False,
) -> dict[str, Any]:
    """Run Bronze-to-Silver OHLCV transform for all tickers at once.

    Writes ONE Silver file per month: ohlcv/year=YYYY/month=MM/data.parquet
    (all tickers combined — mirrors the Bronze year/month/day layout).
    """
    object_name = build_silver_object_name()
    local_path = local_silver_dir / object_name
    if skip_existing and local_path.is_file():
        existing = pl.read_parquet(local_path)
        return {
            "requested": "0",
            "succeeded": "0",
            "skipped": "1",
            "failed": "0",
            "record_count": existing.height,
            "quality_success": True,
            "quality_report": "",
            "local_path": str(local_path),
            "bucket": SILVER_BUCKET,
            "object_name": object_name,
            "results": [],
            "errors": [],
        }

    bronze = load_bronze_data(
        start_date=start_date,
        end_date=end_date,
        local_bronze_dir=local_bronze_dir,
    )
    if tickers:
        wanted = [ticker.strip().upper() for ticker in tickers if ticker.strip()]
        bronze = bronze.filter(pl.col("ticker").cast(pl.Utf8).str.to_uppercase().is_in(wanted))

    silver = transform_ohlcv(bronze)
    report = validate_ohlcv(silver)
    report_path = save_quality_report(report)
    local_path = save_to_silver(silver, output_dir=local_silver_dir)
    if upload_to_minio:
        upload_silver_to_minio(local_path=local_path, object_name=object_name)

    ticker_count = silver.get_column("ticker").n_unique() if silver.height else 0
    return {
        "requested": str(ticker_count),
        "succeeded": str(ticker_count),
        "skipped": "0",
        "failed": "0",
        "record_count": silver.height,
        "quality_success": report.success,
        "quality_report": str(report_path),
        "local_path": str(local_path),
        "bucket": SILVER_BUCKET,
        "object_name": object_name,
        "results": [],
        "errors": [],
    }
