from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.news_backfill import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical market news.")
    parser.add_argument("--target-total", type=int, default=3000)
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--request-delay-seconds", type=float, default=0.35)
    parser.add_argument("--checkpoint-size", type=int, default=25)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    result = run(
        target_total=args.target_total,
        max_pages=args.max_pages,
        request_delay_seconds=args.request_delay_seconds,
        checkpoint_size=args.checkpoint_size,
        upload=not args.no_upload,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["target_reached"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
