from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.transform.ohlcv_transform import run_many

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"


def load_allowed_exchanges(config_path: Path = DEFAULT_CONFIG_PATH) -> set[str]:
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == "vnstock_ohlcv" or source.get("source_name") == "vnstock_ohlcv":
            exchanges = source.get("default_exchanges") or ["HOSE"]
            return {str(exchange).upper() for exchange in exchanges}
    return {"HOSE"}


def discover_configured_tickers(
    local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    allowed_exchanges: set[str] | None = None,
) -> list[str]:
    exchanges = allowed_exchanges or load_allowed_exchanges()
    paths = sorted((local_bronze_dir / "company_profile" / "dataset=listing").glob("year=*/month=*/day=*/data.parquet"))
    if not paths:
        return []

    frame = pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")
    symbol_column = "symbol" if "symbol" in frame.columns else "ticker"
    if symbol_column not in frame.columns or "exchange" not in frame.columns:
        return []

    return (
        frame.with_columns(
            pl.col(symbol_column).cast(pl.Utf8).str.to_uppercase().alias("ticker"),
            pl.col("exchange").cast(pl.Utf8).str.to_uppercase(),
        )
        .filter(pl.col("exchange").is_in(sorted(exchanges)))
        .select("ticker")
        .unique()
        .sort("ticker")
        .get_column("ticker")
        .to_list()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform Bronze OHLCV to Silver.")
    parser.add_argument("--tickers", nargs="+", help="Danh sach ticker can transform.")
    parser.add_argument("--start-date", help="Loc tu ngay YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Loc den ngay YYYY-MM-DD.")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Chi ghi local, khong upload MinIO.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bo qua Silver parquet da ton tai.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Dung ngay khi mot ticker loi.",
    )
    return parser.parse_args()


def main() -> None:
    """Run Bronze-to-Silver OHLCV transform for one or many tickers."""
    args = parse_args()
    tickers = [ticker.upper() for ticker in args.tickers] if args.tickers else discover_configured_tickers()
    if not tickers:
        tickers = None
    result = run_many(
        tickers=tickers,
        start_date=args.start_date,
        end_date=args.end_date,
        upload_to_minio=not args.no_upload,
        continue_on_error=not args.fail_fast,
        skip_existing=args.skip_existing,
    )
    print("OHLCV Silver transform completed")
    print(f"- requested: {result['requested']}")
    print(f"- succeeded: {result['succeeded']}")
    print(f"- skipped: {result['skipped']}")
    print(f"- failed: {result['failed']}")

    if result["errors"]:
        print("Failed tickers:")
        for error in result["errors"]:
            print(f"- {error['ticker']}: {error['error']}")


if __name__ == "__main__":
    main()
