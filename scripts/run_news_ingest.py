from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.market_news import run
from src.ingestion.news_url_registry import DEFAULT_REGISTRY_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run market news Bronze ingest.")
    parser.add_argument("--no-upload", action="store_true", help="Chi ghi local, khong upload MinIO.")
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument(
        "--reset-registry",
        action="store_true",
        help="Xoa URL registry. Chi dung khi can crawl lai toan bo lich su.",
    )
    return parser.parse_args()


def main() -> None:
    """Run market news Bronze ingest from VnExpress, Vietstock and CafeF."""
    args = parse_args()
    if args.reset_registry:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(args.registry_path) + suffix)
            if path.exists():
                path.unlink()
    result = run(
        upload=not args.no_upload,
        registry_path=args.registry_path,
        seed_existing_bronze=not args.reset_registry,
    )
    print("Market news Bronze ingest completed")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
