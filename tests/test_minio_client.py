from pathlib import Path
from types import SimpleNamespace

import pytest

from src.common import minio_client


class FakeMinioClient:
    def __init__(self, existing_buckets: set[str] | None = None) -> None:
        self.existing_buckets = existing_buckets or set()
        self.created_buckets: list[str] = []
        self.uploads: list[dict[str, str]] = []

    def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.existing_buckets

    def make_bucket(self, bucket_name: str) -> None:
        self.existing_buckets.add(bucket_name)
        self.created_buckets.append(bucket_name)

    def fput_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str,
    ) -> None:
        self.uploads.append(
            {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "file_path": file_path,
                "content_type": content_type,
            }
        )

    def list_objects(self, bucket_name: str, prefix: str, recursive: bool) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                bucket_name=bucket_name,
                object_name=f"{prefix}data.parquet",
                recursive=recursive,
            )
        ]


def test_create_client_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="Missing MinIO credentials"):
        minio_client.create_client()


def test_create_bucket_if_missing_creates_bucket() -> None:
    client = FakeMinioClient()

    created = minio_client.create_bucket_if_missing(client, "bronze")  # type: ignore[arg-type]

    assert created is True
    assert client.created_buckets == ["bronze"]


def test_upload_file_creates_bucket_and_uploads(tmp_path: Path) -> None:
    local_file = tmp_path / "data.parquet"
    local_file.write_bytes(b"parquet")
    client = FakeMinioClient()

    minio_client.upload_file(
        client=client,  # type: ignore[arg-type]
        bucket_name="bronze",
        object_name="ohlcv/ticker=VCB/year=2026/month=06/day=10/data.parquet",
        file_path=local_file,
        content_type="application/vnd.apache.parquet",
    )

    assert client.created_buckets == ["bronze"]
    assert client.uploads[0]["bucket_name"] == "bronze"
    assert client.uploads[0]["object_name"].startswith("ohlcv/ticker=VCB/")
