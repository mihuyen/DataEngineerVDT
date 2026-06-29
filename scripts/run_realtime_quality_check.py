from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client
from src.quality.realtime_expectations import build_realtime_quality_report, save_realtime_quality_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quality checks for the realtime pipelines (DNSE 1m candles, raw-tick VWAP)."
    )
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = create_client()
    report = build_realtime_quality_report(client)
    report_path = save_realtime_quality_report(report)

    print("Realtime quality check completed")
    print(f"- success: {report.success}")
    print(f"- error_count: {report.error_count}")
    print(f"- report_path: {report_path}")
    print("Expectations:")
    for expectation in report.expectations:
        status = "PASS" if expectation.success else "FAIL"
        print(f"- {status} {expectation.name}: {expectation.details}")

    if args.fail_on_error and not report.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
