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
SILVER_BUCKET = "silver"
BRONZE_PREFIX = "company_profile"
SILVER_PREFIX = "company_profile"
TEXT_COLUMNS = [
    "symbol",
    "organ_name",
    "organ_name_en",
    "exchange",
    "company_type",
    "business_model",
    "address",
    "website",
    "source",
]
NUMERIC_COLUMNS = [
    "charter_capital",
    "listed_volume",
    "outstanding_shares",
    "free_float",
    "free_float_percentage",
]


def load_allowed_exchanges(config_path: Path = DEFAULT_CONFIG_PATH) -> set[str]:
    if not config_path.exists():
        return {"HOSE"}
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == "company_profile" or source.get("source_name") == "company_profile":
            exchanges = source.get("default_exchanges") or ["HOSE"]
            return {str(exchange).upper() for exchange in exchanges}
    return {"HOSE"}


def discover_bronze_files(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> list[Path]:
    base_dir = local_bronze_dir / BRONZE_PREFIX
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("**/data.parquet"))


def load_bronze_data(local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR) -> pl.DataFrame:
    files = discover_bronze_files(local_bronze_dir)
    if not files:
        raise FileNotFoundError("No Bronze company profile parquet files found")
    return pl.concat([pl.read_parquet(file) for file in files], how="diagonal_relaxed")


def normalize_columns(frame: pl.DataFrame) -> pl.DataFrame:
    rename_map = {
        column: column.strip().lower().replace(" ", "_")
        for column in frame.columns
    }
    frame = frame.rename(rename_map)

    aliases = {
        "ticker": "symbol",
        "organ_short_name": "short_name",
        "vi_organ_name": "organ_name",
        "en_organ_name": "organ_name_en",
        "industry": "company_type",
        "sector": "company_type",
        "sector_name": "company_type",
        "shares_outstanding": "outstanding_shares",
    }
    for old_name, new_name in aliases.items():
        if old_name in frame.columns and new_name not in frame.columns:
            frame = frame.rename({old_name: new_name})

    return frame


def _ensure_columns(frame: pl.DataFrame, columns: list[str], dtype: pl.DataType) -> pl.DataFrame:
    missing = [column for column in columns if column not in frame.columns]
    if not missing:
        return frame
    return frame.with_columns([pl.lit(None, dtype=dtype).alias(column) for column in missing])


def _clean_text(column: str) -> pl.Expr:
    return (
        pl.col(column)
        .cast(pl.Utf8, strict=False)
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )


def _clean_numeric(column: str) -> pl.Expr:
    return pl.col(column).cast(pl.Float64, strict=False)


def _sector_id_expr() -> pl.Expr:
    return (
        pl.col("sector_name")
        .fill_null("Unknown")
        .str.strip_chars()
        .str.to_uppercase()
        .str.replace_all(r"[\s\-/.,;:]+", "_")
        .str.strip_chars("_")
        .alias("sector_id")
    )


def transform_company_profile(frame: pl.DataFrame, allowed_exchanges: set[str] | None = None) -> pl.DataFrame:
    now = datetime.now(timezone.utc)
    frame = normalize_columns(frame)
    exchanges = allowed_exchanges or load_allowed_exchanges()

    if "symbol" not in frame.columns:
        raise ValueError("Company profile Silver data requires symbol column")

    frame = _ensure_columns(frame, TEXT_COLUMNS, pl.Utf8)
    frame = _ensure_columns(frame, NUMERIC_COLUMNS, pl.Float64)

    cleaned = frame.with_columns(
        _clean_text("symbol").str.to_uppercase().alias("symbol"),
        _clean_text("organ_name").alias("organ_name"),
        _clean_text("organ_name_en").alias("organ_name_en"),
        _clean_text("exchange").str.to_uppercase().alias("exchange"),
        _clean_text("company_type").alias("company_type"),
        _clean_text("business_model").alias("business_model"),
        _clean_text("address").alias("address"),
        _clean_text("website").alias("website"),
        _clean_text("source").alias("source"),
        *[_clean_numeric(column).alias(column) for column in NUMERIC_COLUMNS],
    ).filter(
        pl.col("symbol").is_not_null()
        & (pl.col("symbol").str.len_chars() > 0)
        & pl.col("exchange").is_in(sorted(exchanges))
    )

    aggregated = cleaned.group_by("symbol").agg(
        [
            pl.col(column).drop_nulls().first().alias(column)
            for column in cleaned.columns
            if column != "symbol"
        ]
    )

    return (
        aggregated.with_columns(
            pl.col("symbol").alias("ticker"),
            pl.col("organ_name").fill_null(pl.col("symbol")).alias("company_name"),
            pl.col("organ_name_en").alias("company_name_en"),
            pl.col("company_type").fill_null("Unknown").alias("sector_name"),
            pl.col("outstanding_shares")
            .fill_null(pl.col("listed_volume"))
            .fill_null(0)
            .round(0)
            .cast(pl.UInt64)
            .alias("shares_outstanding"),
            pl.lit(0.0, dtype=pl.Float64).alias("market_cap_latest"),
            pl.lit(1, dtype=pl.UInt8).alias("is_active"),
            pl.lit(now).alias("processed_at"),
            pl.lit("company_profile").alias("source_name"),
        )
        .with_columns(_sector_id_expr())
        .with_columns(
            pl.when(pl.col("sector_id") == "")
            .then(pl.lit("UNKNOWN"))
            .otherwise(pl.col("sector_id"))
            .alias("sector_id"),
            pl.col("exchange").fill_null("UNKNOWN").alias("exchange"),
        )
        .select(
            "ticker",
            "company_name",
            "company_name_en",
            "exchange",
            "sector_id",
            "sector_name",
            "shares_outstanding",
            "market_cap_latest",
            "is_active",
            "charter_capital",
            "listed_volume",
            "free_float",
            "free_float_percentage",
            "business_model",
            "address",
            "website",
            "processed_at",
            "source_name",
        )
        .unique(subset=["ticker"], keep="last", maintain_order=True)
        .sort("ticker")
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
    silver = transform_company_profile(bronze)
    object_name = build_silver_object_name()
    local_path = save_to_silver(silver, output_dir=local_silver_dir)
    if upload_to_minio:
        upload_silver_to_minio(local_path=local_path, object_name=object_name)
    return {
        "dataset": "company_profile",
        "record_count": silver.height,
        "local_path": str(local_path),
        "bucket": SILVER_BUCKET,
        "object_name": object_name,
    }
