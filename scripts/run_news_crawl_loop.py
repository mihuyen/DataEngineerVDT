from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl news every N seconds.")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--skip-silver", action="store_true")
    parser.add_argument("--skip-linking", action="store_true")
    parser.add_argument("--load-gold", action="store_true")
    return parser.parse_args()


def run_command(command: list[str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def run_cycle(args: argparse.Namespace) -> None:
    ingest_cmd = [sys.executable, "scripts/run_news_ingest.py"]
    if args.no_upload:
        ingest_cmd.append("--no-upload")
    run_command(ingest_cmd)
    if not args.skip_silver:
        silver_cmd = [sys.executable, "scripts/run_news_silver.py"]
        if args.no_upload:
            silver_cmd.append("--no-upload")
        run_command(silver_cmd)
        run_command([sys.executable, "scripts/run_news_quality_check.py", "--fail-on-error"])
    if not args.skip_linking:
        run_command([sys.executable, "scripts/run_news_entity_linking.py"])
    if args.load_gold:
        run_command([sys.executable, "scripts/run_news_nlp_inference.py"])
        run_command([sys.executable, "scripts/run_news_sentiment_quality.py"])
        run_command([sys.executable, "scripts/load_news_sentiment_gold.py"])


def main() -> None:
    args = parse_args()
    while True:
        started_at = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"News crawl cycle started at {started_at}", flush=True)
        run_cycle(args)
        if args.run_once:
            break
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
