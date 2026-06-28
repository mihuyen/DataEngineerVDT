from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
from minio.deleteobjects import DeleteObject

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_silver_transform import discover_configured_tickers
from src.common.minio_client import create_client, upload_file
from src.transform.market_index_transform import load_allowed_index_codes


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
TICKER_PATTERN = re.compile(r"(?:^|/)ticker=([^/]+)(?:/|$)")
INDEX_PATTERN = re.compile(r"(?:^|/)index_code=([^/]+)(?:/|$)")


def ticker_from_path(value: str) -> str | None:
    match = TICKER_PATTERN.search(value)
    return match.group(1).upper() if match else None


def index_from_path(value: str) -> str | None:
    match = INDEX_PATTERN.search(value)
    return match.group(1).upper() if match else None


def discover_local_scope(
    allowed_tickers: set[str],
    allowed_indexes: set[str],
) -> tuple[list[Path], list[Path]]:
    directories: list[Path] = []
    for base in [
        DATA_DIR / "bronze_local" / "ohlcv",
        DATA_DIR / "silver_local" / "ohlcv",
        DATA_DIR / "bronze_local" / "company_profile" / "dataset=profile",
    ]:
        if not base.exists():
            continue
        directories.extend(
            path
            for path in base.glob("ticker=*")
            if path.is_dir() and (ticker_from_path(str(path)) not in allowed_tickers)
        )

    index_base = DATA_DIR / "bronze_local" / "market_index"
    if index_base.exists():
        directories.extend(
            path
            for path in index_base.glob("index_code=*")
            if path.is_dir() and (index_from_path(str(path)) not in allowed_indexes)
        )

    combined_files: list[Path] = []
    for root in [
        DATA_DIR / "bronze_local" / "company_profile",
        DATA_DIR / "silver_local" / "market_index",
    ]:
        if root.exists():
            combined_files.extend(
                path for path in root.glob("**/*.parquet") if ticker_from_path(str(path)) is None
            )
    return sorted(set(directories)), sorted(set(combined_files))


def filtered_frame(
    path: Path,
    allowed_tickers: set[str],
    allowed_indexes: set[str],
) -> pl.DataFrame | None:
    frame = pl.read_parquet(path)
    if "index_code" in frame.columns:
        return frame.with_columns(pl.col("index_code").cast(pl.Utf8).str.to_uppercase()).filter(
            pl.col("index_code").is_in(sorted(allowed_indexes))
        )
    if "exchange" in frame.columns:
        return frame.with_columns(pl.col("exchange").cast(pl.Utf8).str.to_uppercase()).filter(
            pl.col("exchange") == "HOSE"
        )
    if "ticker" in frame.columns and "company_profile" in path.parts:
        return frame.with_columns(pl.col("ticker").cast(pl.Utf8).str.to_uppercase()).filter(
            pl.col("ticker").is_in(sorted(allowed_tickers))
        )
    return None


def minio_objects_outside_scope(
    allowed_tickers: set[str],
    allowed_indexes: set[str],
) -> dict[str, list[str]]:
    client = create_client()
    result: dict[str, list[str]] = {"bronze": [], "silver": []}
    prefixes = {
        "bronze": ["ohlcv/", "company_profile/dataset=profile/", "market_index/"],
        "silver": ["ohlcv/"],
    }
    for bucket, bucket_prefixes in prefixes.items():
        for prefix in bucket_prefixes:
            for item in client.list_objects(bucket, prefix=prefix, recursive=True):
                object_name = item.object_name or ""
                ticker = ticker_from_path(object_name)
                index_code = index_from_path(object_name)
                if ticker and ticker not in allowed_tickers:
                    result[bucket].append(object_name)
                elif index_code and index_code not in allowed_indexes:
                    result[bucket].append(object_name)
    return {bucket: sorted(set(values)) for bucket, values in result.items()}


def archive_local_path(path: Path, archive_root: Path) -> Path:
    relative = path.relative_to(PROJECT_ROOT)
    destination = archive_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Archive destination already exists: {destination}")
    shutil.move(str(path), destination)
    return destination


def apply_cleanup(
    directories: list[Path],
    combined_files: list[Path],
    minio_objects: dict[str, list[str]],
    allowed_tickers: set[str],
    allowed_indexes: set[str],
    archive_root: Path,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "allowed_ticker_count": len(allowed_tickers),
        "allowed_indexes": sorted(allowed_indexes),
        "archived_directories": [],
        "rewritten_files": [],
        "removed_minio_objects": {"bronze": [], "silver": []},
    }

    for path in directories:
        destination = archive_local_path(path, archive_root)
        manifest["archived_directories"].append(
            {"source": str(path), "archive": str(destination)}
        )

    rewritten: list[tuple[Path, pl.DataFrame]] = []
    for path in combined_files:
        frame = filtered_frame(path, allowed_tickers, allowed_indexes)
        if frame is None:
            continue
        original_rows = pl.scan_parquet(path).select(pl.len()).collect().item()
        if frame.height == original_rows:
            continue
        destination = archive_root / path.relative_to(PROJECT_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        frame.write_parquet(path)
        rewritten.append((path, frame))
        manifest["rewritten_files"].append(
            {
                "path": str(path),
                "archive": str(destination),
                "rows_before": original_rows,
                "rows_after": frame.height,
            }
        )

    client = create_client()
    for bucket, object_names in minio_objects.items():
        if not object_names:
            continue
        errors = list(client.remove_objects(bucket, [DeleteObject(name) for name in object_names]))
        if errors:
            raise RuntimeError(f"Failed to remove {len(errors)} objects from {bucket}: {errors[:3]}")
        manifest["removed_minio_objects"][bucket] = object_names

    for path, _ in rewritten:
        if "bronze_local" in path.parts:
            bucket = "bronze"
            object_name = str(path.relative_to(DATA_DIR / "bronze_local"))
        elif "silver_local" in path.parts:
            bucket = "silver"
            object_name = str(path.relative_to(DATA_DIR / "silver_local"))
        else:
            continue
        upload_file(client, bucket, object_name, path, "application/vnd.apache.parquet")

    archive_root.mkdir(parents=True, exist_ok=True)
    manifest_path = archive_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive non-HOSE data from active Bronze and Silver layers.")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup. Default is dry-run.")
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=DATA_DIR / "archive" / datetime.now().strftime("hose_scope_%Y%m%d_%H%M%S"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    allowed_tickers = set(discover_configured_tickers())
    allowed_indexes = load_allowed_index_codes()
    if not allowed_tickers:
        raise RuntimeError("No configured HOSE tickers were discovered; cleanup aborted")

    directories, combined_files = discover_local_scope(allowed_tickers, allowed_indexes)
    minio_objects = minio_objects_outside_scope(allowed_tickers, allowed_indexes)
    preview = {
        "allowed_tickers": len(allowed_tickers),
        "allowed_indexes": sorted(allowed_indexes),
        "local_directories_to_archive": len(directories),
        "combined_files_to_check": len(combined_files),
        "minio_objects_to_remove": {
            bucket: len(values) for bucket, values in minio_objects.items()
        },
        "archive_root": str(args.archive_root),
    }
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    if not args.apply:
        print("Dry-run only. Re-run with --apply to archive and clean active layers.")
        return

    manifest = apply_cleanup(
        directories,
        combined_files,
        minio_objects,
        allowed_tickers,
        allowed_indexes,
        args.archive_root,
    )
    print("HOSE scope cleanup completed")
    print(f"- manifest: {manifest['manifest_path']}")
    print(f"- archived_directories: {len(manifest['archived_directories'])}")
    print(f"- rewritten_files: {len(manifest['rewritten_files'])}")


if __name__ == "__main__":
    main()
