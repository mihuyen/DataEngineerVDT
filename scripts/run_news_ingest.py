from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.market_news import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run market news Bronze ingest.")
    parser.add_argument("--no-upload", action="store_true", help="Chi ghi local, khong upload MinIO.")
    return parser.parse_args()


def main() -> None:
    """Run market news Bronze ingest from VnExpress, Vietstock and CafeF."""
    args = parse_args()
    result = run(upload=not args.no_upload)
    print("Market news Bronze ingest completed")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
