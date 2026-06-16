from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.company_profile import run
from src.ingestion.vnstock_ohlcv import DEFAULT_EXCHANGES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest company profile data to Bronze MinIO.")
    parser.add_argument(
        "--mode",
        choices=["listing", "profile"],
        default="listing",
        help="listing luu nhanh danh muc 1531 ma; profile goi chi tiet tung ma.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Danh sach ma can ingest. Neu bo trong se lay theo san.",
    )
    parser.add_argument(
        "--ticker-file",
        type=Path,
        help="File CSV co cot symbol hoac ticker.",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        default=list(DEFAULT_EXCHANGES),
        help="Danh sach san can lay ma: HOSE HNX UPCOM.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Gioi han so ma de test nhanh truoc khi ingest toan thi truong.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Dung ngay khi mot ma bi loi.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=5.0,
        help="So giay nghi giua moi ticker khi chay mode profile.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bo qua profile da co file parquet local cho ngay ingest hien tai.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(
        tickers=args.tickers,
        ticker_file=args.ticker_file,
        exchanges=args.exchanges,
        limit=args.limit,
        continue_on_error=not args.fail_fast,
        mode=args.mode,
        request_delay_seconds=args.request_delay_seconds,
        skip_existing=args.skip_existing,
    )

    print("Company profile Bronze ingest completed")
    print(f"- mode: {result['mode']}")
    print(f"- requested: {result['requested']}")
    print(f"- succeeded: {result['succeeded']}")
    print(f"- skipped: {result.get('skipped', '0')}")
    print(f"- failed: {result['failed']}")
    print(f"- local_path: {result['local_path']}")
    print(f"- minio_path: {result['bucket']}/{result['object_name']}")

    if result["errors"]:
        print("Failed symbols:")
        for error in result["errors"]:
            print(f"- {error['symbol']}: {error['error']}")


if __name__ == "__main__":
    main()
