from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.transform.news_transform import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform Bronze news to Silver.")
    parser.add_argument("--no-upload", action="store_true", help="Chi ghi local, khong upload MinIO.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(upload_to_minio=not args.no_upload)
    print("News Silver transform completed")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
