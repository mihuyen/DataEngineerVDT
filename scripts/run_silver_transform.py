from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.transform.ohlcv_transform import run_many


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
    result = run_many(
        tickers=[ticker.upper() for ticker in args.tickers] if args.tickers else None,
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
