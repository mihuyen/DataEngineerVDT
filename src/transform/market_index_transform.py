from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from src.common.minio_client import create_bucket_if_missing, create_client, upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
BRONZE_PREFIX = "market_index"
SILVER_PREFIX = "market_index"
SILVER_BUCKET = "silver"


def load_allowed_index_codes(config_path: Path = DEFAULT_CONFIG_PATH) -> set[str]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    for source in config.get("sources", []):
        if source.get("name") == "market_index" or source.get("source_name") == "market_index":
            return {
                str(item["index_code"]).upper()
                for item in source.get("index_codes", [])
                if item.get("index_code")
            }
    raise ValueError("market_index source config is missing")


def discover_bronze_files(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> list[Path]:
    base_dir = local_bronze_dir / BRONZE_PREFIX
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("index_code=*/year=*/month=*/day=*/data.parquet"))


def load_bronze_data(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> pl.DataFrame:
    files = discover_bronze_files(local_bronze_dir)
    if not files:
        raise FileNotFoundError("No Bronze market index parquet files found")
    return pl.concat([pl.read_parquet(file) for file in files], how="diagonal_relaxed")


def transform_market_index(
    frame: pl.DataFrame,
    allowed_index_codes: set[str] | None = None,
) -> pl.DataFrame:
    now = datetime.now(timezone.utc)
    allowed = allowed_index_codes or load_allowed_index_codes()
    rename_map = {
        column: column.strip().lower().replace(" ", "_")
        for column in frame.columns
    }
    frame = frame.rename(rename_map)
    return (
        frame.with_columns(
            pl.col("index_code").cast(pl.Utf8).str.to_uppercase(),
            pl.col("date").cast(pl.Date, strict=False),
            pl.col("open").cast(pl.Float64, strict=False),
            pl.col("high").cast(pl.Float64, strict=False),
            pl.col("low").cast(pl.Float64, strict=False),
            pl.col("close").cast(pl.Float64, strict=False),
            pl.col("volume").cast(pl.Int64, strict=False),
            pl.col("trading_value").cast(pl.Float64, strict=False)
            if "trading_value" in frame.columns
            else pl.lit(None, dtype=pl.Float64).alias("trading_value"),
            pl.lit(now).alias("processed_at"),
            pl.lit("market_index").alias("source_name"),
        )
        .filter(
            pl.col("index_code").is_not_null()
            & pl.col("index_code").is_in(sorted(allowed))
            & pl.col("date").is_not_null()
            & (pl.col("high") >= pl.col("low"))
            & (pl.col("volume") >= 0)
        )
        .unique(subset=["index_code", "date"], keep="last", maintain_order=True)
        .sort(["index_code", "date"])
    )


def build_silver_object_name(
    partition_date: date | None = None,
    filename: str = "data.parquet",
) -> str:
    output_date = partition_date or date.today()
    return f"{SILVER_PREFIX}/year={output_date:%Y}/month={output_date:%m}/{filename}"


def save_to_silver(
    frame: pl.DataFrame,
    output_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    partition_date: date | None = None,
) -> Path:
    object_name = build_silver_object_name(partition_date=partition_date)
    output_path = output_dir / object_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return output_path


def upload_silver_to_minio(local_path: Path, object_name: str, bucket_name: str = SILVER_BUCKET) -> None:
    client = create_client()
    create_bucket_if_missing(client, bucket_name)
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def run(
    local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    upload_to_minio: bool = True,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    bronze = load_bronze_data(local_bronze_dir)
    silver = transform_market_index(
        bronze,
        allowed_index_codes=load_allowed_index_codes(config_path),
    )
    object_name = build_silver_object_name()
    local_path = save_to_silver(silver, output_dir=local_silver_dir)
    if upload_to_minio:
        upload_silver_to_minio(local_path=local_path, object_name=object_name)
    return {
        "dataset": "market_index",
        "record_count": silver.height,
        "local_path": str(local_path),
        "bucket": SILVER_BUCKET,
        "object_name": object_name,
    }
