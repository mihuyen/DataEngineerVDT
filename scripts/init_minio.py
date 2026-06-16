from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.minio_client import create_bucket_if_missing, create_client


BUCKETS = ("bronze", "silver", "gold")


def main() -> None:
    client = create_client()

    for bucket_name in BUCKETS:
        created = create_bucket_if_missing(client, bucket_name)
        status = "CREATED" if created else "EXISTS"
        print(f"- {bucket_name}: {status}")


if __name__ == "__main__":
    main()
