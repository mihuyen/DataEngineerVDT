from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from src.common.minio_client import create_bucket_if_missing, create_client, upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
BRONZE_PREFIX = "news"
SILVER_PREFIX = "news"
SILVER_BUCKET = "silver"


def discover_bronze_files(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> list[Path]:
    base_dir = local_bronze_dir / BRONZE_PREFIX
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("**/data.parquet"))


def load_bronze_data(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> pl.DataFrame:
    files = discover_bronze_files(local_bronze_dir)
    if not files:
        raise FileNotFoundError("No Bronze news parquet files found")
    return pl.concat([pl.read_parquet(file) for file in files], how="diagonal_relaxed")


def normalize_columns(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.rename(
        {
            column: column.strip().lower().replace(" ", "_")
            for column in frame.columns
        }
    )


def transform_news(frame: pl.DataFrame) -> pl.DataFrame:
    now = datetime.now(timezone.utc)
    frame = normalize_columns(frame)

    required = {"url", "title", "content", "source"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"News Silver data is missing required columns: {', '.join(sorted(missing))}")

    if "published_at" not in frame.columns:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Utf8).alias("published_at"))
    if "category" not in frame.columns:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Utf8).alias("category"))
    if "description" not in frame.columns:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Utf8).alias("description"))

    return (
        frame.with_columns(
            pl.col("url").cast(pl.Utf8).str.strip_chars(),
            pl.col("title").cast(pl.Utf8).str.replace_all(r"\s+", " ").str.strip_chars(),
            pl.col("description").cast(pl.Utf8).str.replace_all(r"\s+", " ").str.strip_chars(),
            pl.col("content").cast(pl.Utf8).str.replace_all(r"\s+", " ").str.strip_chars(),
            pl.col("source").cast(pl.Utf8).str.strip_chars(),
            pl.col("category").cast(pl.Utf8).str.strip_chars(),
            pl.col("published_at").cast(pl.Date, strict=False),
            pl.lit(now).alias("processed_at"),
            pl.lit("market_news").alias("source_name"),
        )
        .filter(
            pl.col("url").is_not_null()
            & (pl.col("url").str.len_chars() > 0)
            & pl.col("title").is_not_null()
            & (pl.col("title").str.len_chars() > 0)
            & pl.col("content").is_not_null()
            & (pl.col("content").str.len_chars() >= 50)
        )
        .unique(subset=["url"], keep="last", maintain_order=True)
        .sort(["source", "published_at", "title"])
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
) -> dict[str, Any]:
    bronze = load_bronze_data(local_bronze_dir)
    silver = transform_news(bronze)
    object_name = build_silver_object_name()
    local_path = save_to_silver(silver, output_dir=local_silver_dir)
    if upload_to_minio:
        upload_silver_to_minio(local_path=local_path, object_name=object_name)
    return {
        "dataset": "news",
        "record_count": silver.height,
        "local_path": str(local_path),
        "bucket": SILVER_BUCKET,
        "object_name": object_name,
    }
