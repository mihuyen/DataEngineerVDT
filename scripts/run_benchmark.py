from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "quality_reports" / "benchmark_report.json"

# Each stage runs the exact same command the Airflow DAG runs (see
# dags/stock_lakehouse_daily.py) -- timing the real entrypoint instead of
# calling internal functions means the number reported here is what a DAG
# run actually pays, not an optimistic in-process approximation.
STAGES = [
    ("migrate_gold_schema", ["uv", "run", "python", "scripts/migrate_gold_schema.py"]),
    ("load_gold", ["uv", "run", "python", "scripts/load_gold.py"]),
    ("reconcile_gold", ["uv", "run", "python", "scripts/run_reconciliation_check.py"]),
    ("dbt_run", ["uv", "run", "dbt", "run", "--project-dir", "dbt", "--profiles-dir", "dbt"]),
    ("export_frontend_data", ["uv", "run", "python", "scripts/export_frontend_data.py"]),
]

ROW_COUNT_QUERIES = {
    "fact_daily_price": "SELECT count() FROM fact_daily_price",
    "fact_daily_price_indicators": "SELECT count() FROM fact_daily_price_indicators",
    "fact_market_index": "SELECT count() FROM fact_market_index",
}


def time_stage(name: str, command: list[str]) -> dict:
    start = time.monotonic()
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True)
    duration_seconds = time.monotonic() - start
    return {
        "stage": name,
        "duration_seconds": round(duration_seconds, 3),
        "success": result.returncode == 0,
        "stderr_tail": result.stderr[-500:] if result.returncode != 0 else "",
    }


def row_counts(client: object) -> dict[str, int]:
    counts = {}
    for table, sql in ROW_COUNT_QUERIES.items():
        try:
            counts[table] = int(client.query(sql).result_rows[0][0])
        except Exception:
            counts[table] = -1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Time each stage of the daily pipeline against the current local stack."
    )
    parser.add_argument(
        "--stages",
        nargs="*",
        choices=[name for name, _ in STAGES],
        help="Subset of stages to run (default: all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stages_to_run = [(name, cmd) for name, cmd in STAGES if not args.stages or name in args.stages]

    client = create_client()
    before_counts = row_counts(client)

    results = []
    for name, command in stages_to_run:
        print(f"- running {name} ...")
        outcome = time_stage(name, command)
        results.append(outcome)
        status = "ok" if outcome["success"] else "FAILED"
        print(f"  {status} in {outcome['duration_seconds']}s")
        if not outcome["success"]:
            print(f"  stderr: {outcome['stderr_tail']}")

    after_counts = row_counts(client)
    report = {
        "stages": results,
        "total_duration_seconds": round(sum(r["duration_seconds"] for r in results), 3),
        "row_counts_before": before_counts,
        "row_counts_after": after_counts,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nSummary:")
    for outcome in results:
        print(f"- {outcome['stage']}: {outcome['duration_seconds']}s")
    print(f"- total: {report['total_duration_seconds']}s")
    print(f"Report written to {REPORT_PATH}")

    if not all(r["success"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
