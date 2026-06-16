from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.quality.market_index_expectations import save_quality_report, validate_market_index
from src.transform.market_index_transform import DEFAULT_LOCAL_SILVER_DIR, build_silver_object_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Silver market index quality rules.")
    parser.add_argument("--local-silver-dir", type=Path, default=DEFAULT_LOCAL_SILVER_DIR)
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pl.read_parquet(args.local_silver_dir / build_silver_object_name())
    report = validate_market_index(frame)
    report_path = save_quality_report(report)

    print("Market index quality check completed")
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
