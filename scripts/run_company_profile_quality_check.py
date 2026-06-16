from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.quality.company_profile_expectations import save_quality_report, validate_company_profile
from src.transform.company_profile_transform import DEFAULT_LOCAL_SILVER_DIR, build_silver_object_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Silver company profile quality rules.")
    parser.add_argument(
        "--local-silver-dir",
        type=Path,
        default=DEFAULT_LOCAL_SILVER_DIR,
        help="Local Silver root directory.",
    )
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    silver_path = args.local_silver_dir / build_silver_object_name()
    frame = pl.read_parquet(silver_path)
    report = validate_company_profile(frame)
    report_path = save_quality_report(report, report_name="company_profile_silver_validation.json")

    print("Company profile quality check completed")
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
