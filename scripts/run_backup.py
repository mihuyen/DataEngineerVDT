from __future__ import annotations

import argparse
import gzip
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client
from src.common.minio_client import create_client as create_minio_client, upload_file

BACKUP_BUCKET = "backups"

# Postgres holds operational state (user_alerts, alert config) that nothing
# else can rebuild -- ClickHouse Gold tables, by contrast, can be fully
# regenerated from Bronze/Silver via the daily DAG. Backing both up anyway
# protects against the time-to-rebuild cost (ClickHouse) and total data loss
# (Postgres) in one pass.
CLICKHOUSE_TABLES = [
    "dim_stock",
    "dim_sector",
    "dim_index",
    "dim_date",
    "fact_daily_price",
    "fact_market_index",
    "fact_news_sentiment_daily",
    "fact_alert_event",
    "fact_realtime_vwap",
]

RETENTION_DAYS = 14


def backup_postgres(work_dir: Path, run_id: str) -> Path:
    dump_path = work_dir / f"postgres_{run_id}.dump"
    subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--file",
            str(dump_path),
            f"--host={_env('POSTGRES_HOST', 'localhost')}",
            f"--port={_env('POSTGRES_PORT', '5432')}",
            f"--username={_env('POSTGRES_USER', 'stock_user')}",
            _env("POSTGRES_DB", "stock_lakehouse"),
        ],
        check=True,
        env=_pg_env(),
    )
    return dump_path


def backup_clickhouse(work_dir: Path, run_id: str) -> list[Path]:
    client = create_client()
    paths = []
    for table in CLICKHOUSE_TABLES:
        raw = client.raw_query(f"SELECT * FROM {table} FORMAT Native")
        out_path = work_dir / f"{table}_{run_id}.native.gz"
        with gzip.open(out_path, "wb") as fh:
            fh.write(raw)
        paths.append(out_path)
    return paths


def _env(name: str, default: str) -> str:
    import os

    return os.getenv(name) or default


def _pg_env() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["PGPASSWORD"] = _env("POSTGRES_PASSWORD", "stock_password")
    return env


def upload_backups(paths: list[Path], run_id: str) -> None:
    minio_client = create_minio_client()
    for path in paths:
        upload_file(minio_client, BACKUP_BUCKET, f"{run_id}/{path.name}", path)
        print(f"- uploaded: {run_id}/{path.name}")


def prune_old_backups() -> None:
    minio_client = create_minio_client()
    if not minio_client.bucket_exists(BACKUP_BUCKET):
        return
    cutoff = datetime.now(timezone.utc).timestamp() - RETENTION_DAYS * 86400
    for obj in minio_client.list_objects(BACKUP_BUCKET, recursive=True):
        if obj.last_modified and obj.last_modified.timestamp() < cutoff:
            minio_client.remove_object(BACKUP_BUCKET, obj.object_name)
            print(f"- pruned (older than {RETENTION_DAYS}d): {obj.object_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup Postgres + ClickHouse Gold tables to MinIO.")
    parser.add_argument("--skip-postgres", action="store_true")
    parser.add_argument("--skip-clickhouse", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    with tempfile.TemporaryDirectory(prefix="stock_backup_") as tmp:
        work_dir = Path(tmp)
        paths: list[Path] = []

        if not args.skip_postgres:
            paths.append(backup_postgres(work_dir, run_id))
            print("- postgres dump created")

        if not args.skip_clickhouse:
            paths.extend(backup_clickhouse(work_dir, run_id))
            print(f"- clickhouse export created ({len(CLICKHOUSE_TABLES)} tables)")

        upload_backups(paths, run_id)

    prune_old_backups()
    print(f"Backup run {run_id} completed")


if __name__ == "__main__":
    main()
