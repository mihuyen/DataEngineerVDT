"""
data_loader.py — Đọc bài báo thô từ MinIO (các bucket raw-news-*).

Input:  MinIO buckets: raw-news-cafef, raw-news-vietstock, raw-news-vnexpress
        Mỗi object là JSON được tạo bởi historical_crawl.py.
Output: pandas DataFrame chuẩn hóa với các cột:
        article_id, source_url, publisher, title, raw_content,
        publication_timestamp, crawl_timestamp
"""

import os
import json
import logging
import time

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200
MAX_RETRIES = 3

# Bucket thực tế của crawler và tên publisher chuẩn hóa
BUCKET_PUBLISHER_MAP = {
    "raw-news-cafef":     "CafeF",
    "raw-news-vietstock": "VietStock",
    "raw-news-vnexpress": "VNExpress",
}


class BronzeDataLoader:
    """Đọc bài báo từ các bucket MinIO raw-news-* với retry và tiến độ."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        from minio import Minio

        endpoint   = os.environ["MINIO_ENDPOINT"]
        access_key = os.environ["MINIO_ACCESS_KEY"]
        secret_key = os.environ["MINIO_SECRET_KEY"]
        secure     = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self._client = Minio(endpoint, access_key=access_key,
                             secret_key=secret_key, secure=secure)
        return self._client

    def _list_objects_with_retry(self, bucket: str) -> list:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return list(self._get_client().list_objects(bucket, recursive=True))
            except Exception as exc:
                logger.warning("Lần %d/%d liệt kê bucket '%s' thất bại: %s",
                               attempt, MAX_RETRIES, bucket, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _get_object_with_retry(self, bucket: str, name: str) -> dict | None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._get_client().get_object(bucket, name)
                data = json.loads(resp.read())
                resp.close()
                resp.release_conn()
                return data
            except Exception as exc:
                logger.warning("Lần %d/%d tải '%s/%s' thất bại: %s",
                               attempt, MAX_RETRIES, bucket, name, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Bỏ qua '%s/%s'.", bucket, name)
                    return None

    def load(self, target_count: int = 5000) -> pd.DataFrame:
        """
        Đọc bài báo từ tất cả bucket raw-news-*.

        Args:
            target_count: Số bài tối đa cần lấy (chia đều giữa 3 nguồn).

        Returns:
            DataFrame với schema chuẩn hóa.
        """
        per_bucket = target_count // len(BUCKET_PUBLISHER_MAP)
        records    = []
        skipped    = 0

        for bucket, publisher in BUCKET_PUBLISHER_MAP.items():
            logger.info("Đọc bucket '%s' (publisher='%s')...", bucket, publisher)

            try:
                objects = self._list_objects_with_retry(bucket)
            except Exception as exc:
                logger.error("Bỏ qua bucket '%s': %s", bucket, exc)
                continue

            bucket_records = []
            for obj in tqdm(objects, desc=f"  {bucket}", leave=False):
                if len(bucket_records) >= per_bucket:
                    break

                data = self._get_object_with_retry(bucket, obj.object_name)
                if data is None:
                    skipped += 1
                    continue

                # Crawler lưu nội dung vào field "content", chuẩn hóa thành "raw_content"
                raw_content = data.get("content", "")
                if len(raw_content) <= MIN_CONTENT_LENGTH:
                    skipped += 1
                    continue

                bucket_records.append({
                    "article_id":            data.get("article_id"),
                    "source_url":            data.get("url", ""),
                    "publisher":             publisher,
                    "title":                 data.get("title", ""),
                    "raw_content":           raw_content,
                    "publication_timestamp": data.get("published_at"),
                    "crawl_timestamp":       data.get("crawl_timestamp"),
                })

            records.extend(bucket_records)
            logger.info("  → %d bài từ '%s'", len(bucket_records), bucket)

        df = pd.DataFrame(records)
        logger.info("Hoàn tất: %d bài hợp lệ, %d bài bỏ qua.", len(df), skipped)
        return df
