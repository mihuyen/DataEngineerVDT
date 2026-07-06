from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_COMMANDS = [
    ("ohlcv", [sys.executable, "scripts/run_quality_check.py", "--fail-on-error"]),
    (
        "company_profile",
        [sys.executable, "scripts/run_company_profile_quality_check.py", "--fail-on-error"],
    ),
    ("market_index", [sys.executable, "scripts/run_market_index_quality_check.py", "--fail-on-error"]),
    ("news", [sys.executable, "scripts/run_news_quality_check.py", "--fail-on-error"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all Silver data quality checks.")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Run all checks even if one pipeline fails.",
    )
    parser.add_argument(
        "--exclude-news",
        action="store_true",
        help="Skip Silver news checks when news is owned by the 5-minute DAG.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    failures: list[str] = []

    commands = [item for item in QUALITY_COMMANDS if not (args.exclude_news and item[0] == "news")]
    for dataset_name, command in commands:
        print(f"Running quality check: {dataset_name}")
        completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
        if completed.returncode != 0:
            failures.append(dataset_name)
            print(f"- {dataset_name}: FAILED")
            if not args.continue_on_error:
                break
        else:
            print(f"- {dataset_name}: PASSED")

    print("All quality checks completed")
    print(f"- passed: {len(commands) - len(failures)}")
    print(f"- failed: {len(failures)}")
    if failures:
        print("- failed_datasets: " + ", ".join(failures))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
