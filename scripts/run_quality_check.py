from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.quality.ohlcv_expectations import (
    DEFAULT_LOCAL_SILVER_DIR,
    DEFAULT_REPORT_DIR,
    load_silver_ohlcv_dataset,
    save_quality_report,
    validate_ohlcv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Silver OHLCV quality rules.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Optional ticker list. If omitted, validate all local Silver OHLCV files.",
    )
    parser.add_argument(
        "--local-silver-dir",
        type=Path,
        default=DEFAULT_LOCAL_SILVER_DIR,
        help="Local Silver root directory.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Directory for quality reports.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 1 if validation fails.",
    )
    return parser.parse_args()


def main() -> None:
    """Run OHLCV quality validation for local Silver data."""
    args = parse_args()
    frame = load_silver_ohlcv_dataset(
        local_silver_dir=args.local_silver_dir,
        tickers=[ticker.upper() for ticker in args.tickers] if args.tickers else None,
    )
    report = validate_ohlcv(frame, source_name="silver_ohlcv")
    report_path = save_quality_report(
        report,
        report_dir=args.report_dir,
        report_name="ohlcv_silver_validation.json",
    )

    print("OHLCV quality check completed")
    print(f"- success: {report.success}")
    print(f"- record_count: {report.record_count}")
    print(f"- error_count: {report.error_count}")
    print(f"- report_path: {report_path}")
    print("Expectations:")
    for expectation in report.expectations:
        status = "PASS" if expectation.success else "FAIL"
        print(f"- {status} {expectation.name}: failed_count={expectation.failed_count}")

    if args.fail_on_error and not report.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
