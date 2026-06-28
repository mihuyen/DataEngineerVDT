from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Literal

from clickhouse_connect.driver.client import Client
from minio import Minio
import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client as create_clickhouse_client
from src.common.clickhouse_client import query_dataframe
from src.common.minio_client import create_client as create_minio_client
from src.common.minio_client import upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_GOLD_DIR = PROJECT_ROOT / "data" / "gold_local"
GOLD_BUCKET = "gold"

GOLD_TABLES = [
    "dim_date",
    "dim_sector",
    "dim_stock",
    "dim_index",
    "fact_daily_price",
    "fact_market_index",
    "fact_news_sentiment_daily",
    "fact_realtime_vwap",
    "fact_alert_event",
]

DIMENSION_TABLES = {"dim_date", "dim_sector", "dim_stock", "dim_index"}
FACT_PARTITIONS: dict[str, tuple[str, Literal["month", "day"]]] = {
    "fact_daily_price": ("trading_date", "month"),
    "fact_market_index": ("trading_date", "month"),
    "fact_news_sentiment_daily": ("news_date", "month"),
    "fact_realtime_vwap": ("trading_date", "day"),
    "fact_alert_event": ("triggered_at", "month"),
}


def build_snapshot_local_path(table_name: str, snapshot_date: date, base_dir: Path = DEFAULT_LOCAL_GOLD_DIR) -> Path:
    return base_dir / table_name / f"snapshot_date={snapshot_date.isoformat()}" / "data.parquet"


def build_snapshot_object_name(table_name: str, snapshot_date: date) -> str:
    return f"{table_name}/snapshot_date={snapshot_date.isoformat()}/data.parquet"


def build_monthly_local_path(
    table_name: str,
    partition_date: date,
    base_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> Path:
    return base_dir / table_name / f"year={partition_date:%Y}" / f"month={partition_date:%m}" / "data.parquet"


def build_monthly_object_name(table_name: str, partition_date: date) -> str:
    return f"{table_name}/year={partition_date:%Y}/month={partition_date:%m}/data.parquet"


def build_daily_local_path(
    table_name: str,
    partition_date: date,
    base_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> Path:
    return base_dir / table_name / f"trading_date={partition_date.isoformat()}" / "data.parquet"


def build_daily_object_name(table_name: str, partition_date: date) -> str:
    return f"{table_name}/trading_date={partition_date.isoformat()}/data.parquet"


def upload_frame(
    minio: Minio,
    frame: pl.DataFrame,
    local_path: Path,
    object_name: str,
) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(local_path)
    upload_file(
        client=minio,
        bucket_name=GOLD_BUCKET,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def export_snapshot_table(
    clickhouse: Client,
    minio: Minio,
    table_name: str,
    snapshot_date: date,
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> list[dict[str, object]]:
    frame = query_dataframe(clickhouse, f"SELECT * FROM {table_name}")
    local_path = build_snapshot_local_path(table_name, snapshot_date, local_gold_dir)
    object_name = build_snapshot_object_name(table_name, snapshot_date)
    upload_frame(minio=minio, frame=frame, local_path=local_path, object_name=object_name)

    return [{
        "table": table_name,
        "rows": frame.height,
        "local_path": str(local_path),
        "minio_path": f"{GOLD_BUCKET}/{object_name}",
        "partition": f"snapshot_date={snapshot_date.isoformat()}",
    }]


def export_partitioned_fact_table(
    clickhouse: Client,
    minio: Minio,
    table_name: str,
    snapshot_date: date,
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> list[dict[str, object]]:
    date_column, granularity = FACT_PARTITIONS[table_name]
    frame = query_dataframe(clickhouse, f"SELECT * FROM {table_name}")
    if frame.is_empty():
        return export_snapshot_table(
            clickhouse=clickhouse,
            minio=minio,
            table_name=table_name,
            snapshot_date=snapshot_date,
            local_gold_dir=local_gold_dir,
        )

    if frame.schema[date_column] == pl.Datetime:
        frame = frame.with_columns(pl.col(date_column).dt.date().alias("_partition_date"))
    else:
        frame = frame.with_columns(pl.col(date_column).cast(pl.Date).alias("_partition_date"))
    results: list[dict[str, object]] = []

    if granularity == "month":
        frame = frame.with_columns(
            pl.col("_partition_date").dt.year().alias("_partition_year"),
            pl.col("_partition_date").dt.month().alias("_partition_month"),
        )
        grouped = frame.partition_by(["_partition_year", "_partition_month"], as_dict=True)
    else:
        grouped = frame.partition_by("_partition_date", as_dict=True)

    for key, partition_frame in grouped.items():
        cleaned_frame = partition_frame.drop(
            [column for column in ["_partition_date", "_partition_year", "_partition_month"] if column in partition_frame.columns]
        )
        if granularity == "month":
            year, month = key if isinstance(key, tuple) else (key[0], key[1])
            partition_date = date(int(year), int(month), 1)
            local_path = build_monthly_local_path(table_name, partition_date, local_gold_dir)
            object_name = build_monthly_object_name(table_name, partition_date)
            partition_label = f"year={partition_date:%Y}/month={partition_date:%m}"
        else:
            partition_date = key[0] if isinstance(key, tuple) else key
            local_path = build_daily_local_path(table_name, partition_date, local_gold_dir)
            object_name = build_daily_object_name(table_name, partition_date)
            partition_label = f"trading_date={partition_date.isoformat()}"

        upload_frame(minio=minio, frame=cleaned_frame, local_path=local_path, object_name=object_name)
        results.append(
            {
                "table": table_name,
                "rows": cleaned_frame.height,
                "local_path": str(local_path),
                "minio_path": f"{GOLD_BUCKET}/{object_name}",
                "partition": partition_label,
            }
        )

    return results


def export_table(
    clickhouse: Client,
    minio: Minio,
    table_name: str,
    snapshot_date: date,
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> list[dict[str, object]]:
    if table_name in DIMENSION_TABLES:
        return export_snapshot_table(clickhouse, minio, table_name, snapshot_date, local_gold_dir)
    if table_name in FACT_PARTITIONS:
        return export_partitioned_fact_table(clickhouse, minio, table_name, snapshot_date, local_gold_dir)
    return export_snapshot_table(clickhouse, minio, table_name, snapshot_date, local_gold_dir)


def export_gold_tables(
    table_names: list[str] | None = None,
    snapshot_date: date | None = None,
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
    cleanup_legacy_fact_snapshots: bool = True,
) -> list[dict[str, object]]:
    resolved_snapshot_date = snapshot_date or date.today()
    resolved_tables = table_names or GOLD_TABLES
    clickhouse = create_clickhouse_client()
    minio = create_minio_client()

    results: list[dict[str, object]] = []
    for table_name in resolved_tables:
        results.extend(export_table(
            clickhouse=clickhouse,
            minio=minio,
            table_name=table_name,
            snapshot_date=resolved_snapshot_date,
            local_gold_dir=local_gold_dir,
        ))
    if cleanup_legacy_fact_snapshots:
        partitioned_fact_tables = sorted(
            {
                str(result["table"])
                for result in results
                if result["table"] in FACT_PARTITIONS and not str(result["partition"]).startswith("snapshot_date=")
            }
        )
        cleanup_legacy_snapshots(
            minio=minio,
            table_names=partitioned_fact_tables,
            local_gold_dir=local_gold_dir,
        )
    return results


def cleanup_legacy_snapshots(
    minio: Minio,
    table_names: list[str],
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> None:
    for table_name in table_names:
        prefix = f"{table_name}/snapshot_date="
        for item in minio.list_objects(GOLD_BUCKET, prefix=prefix, recursive=True):
            if item.object_name:
                minio.remove_object(GOLD_BUCKET, item.object_name)

        table_dir = local_gold_dir / table_name
        if not table_dir.exists():
            continue
        for path in table_dir.glob("snapshot_date=*"):
            if path.is_dir():
                shutil.rmtree(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export ClickHouse Gold tables to parquet files in MinIO.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=None,
        help="Gold table names to export. Defaults to all Gold tables.",
    )
    parser.add_argument(
        "--snapshot-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Snapshot partition date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--local-gold-dir",
        type=Path,
        default=DEFAULT_LOCAL_GOLD_DIR,
        help="Local directory used before uploading parquet files to MinIO.",
    )
    parser.add_argument(
        "--keep-legacy-fact-snapshots",
        action="store_true",
        help="Khong xoa cac file fact/*/snapshot_date cu sau khi export layout partition moi.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = export_gold_tables(
        table_names=args.tables,
        snapshot_date=args.snapshot_date,
        local_gold_dir=args.local_gold_dir,
        cleanup_legacy_fact_snapshots=not args.keep_legacy_fact_snapshots,
    )

    print("Gold parquet export completed")
    for result in results:
        print(f"- {result['table']} [{result['partition']}]: {result['rows']} rows -> {result['minio_path']}")


if __name__ == "__main__":
    main()
