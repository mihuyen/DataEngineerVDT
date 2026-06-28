from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio
from minio.datatypes import Object
from minio.error import S3Error

load_dotenv()


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def create_client() -> Minio:
    endpoint = _env_first("MINIO_ENDPOINT") or "localhost:9000"
    access_key = _env_first("MINIO_ACCESS_KEY", "MINIO_ROOT_USER")
    secret_key = _env_first("MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    if not access_key or not secret_key:
        raise ValueError(
            "Missing MinIO credentials. Set MINIO_ACCESS_KEY/MINIO_SECRET_KEY "
            "or MINIO_ROOT_USER/MINIO_ROOT_PASSWORD."
        )

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def bucket_exists(client: Minio, bucket_name: str) -> bool:
    return client.bucket_exists(bucket_name)


def create_bucket_if_missing(client: Minio, bucket_name: str) -> bool:
    if bucket_exists(client, bucket_name):
        return False
    client.make_bucket(bucket_name)
    return True


def upload_file(
    client: Minio,
    bucket_name: str,
    object_name: str,
    file_path: Path,
    content_type: str = "application/octet-stream",
) -> None:
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        create_bucket_if_missing(client, bucket_name)
        client.fput_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=str(file_path),
            content_type=content_type,
        )
    except S3Error as exc:
        raise RuntimeError(f"Failed to upload {file_path} to {bucket_name}/{object_name}") from exc


def list_objects(client: Minio, bucket_name: str, prefix: str = "") -> Iterable[Object]:
    return client.list_objects(bucket_name, prefix=prefix, recursive=True)
