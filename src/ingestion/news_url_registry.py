from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "state" / "news_urls.sqlite3"
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_KEYS
            and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
        ]
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


class NewsURLRegistry:
    def __init__(self, path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS news_url_registry (
                    url TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_attempt_at TEXT,
                    crawled_at TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_url_status ON news_url_registry(status)"
            )

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT count(*) AS count FROM news_url_registry").fetchone()
        return int(row["count"] if row else 0)

    def register_discovered(self, url: str, source: str, category: str) -> None:
        normalized_url = normalize_url(url)
        timestamp = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO news_url_registry (
                    url, source, category, status, first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, 'discovered', ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    source = excluded.source,
                    category = excluded.category,
                    last_seen_at = excluded.last_seen_at
                """,
                (normalized_url, source, category, timestamp, timestamp),
            )

    def should_crawl(
        self,
        url: str,
        max_attempts: int = 3,
        retry_after: timedelta = timedelta(minutes=30),
    ) -> bool:
        normalized_url = normalize_url(url)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, attempt_count, last_attempt_at FROM news_url_registry WHERE url = ?",
                (normalized_url,),
            ).fetchone()
        if row is None or row["status"] == "discovered":
            return True
        if row["status"] in {"success", "skipped"}:
            return False
        if int(row["attempt_count"]) >= max_attempts:
            return False
        if not row["last_attempt_at"]:
            return True
        last_attempt = datetime.fromisoformat(str(row["last_attempt_at"]))
        return utc_now() - last_attempt >= retry_after

    def mark_success(self, url: str, source: str, category: str) -> None:
        self._mark(url, source, category, status="success", error=None, crawled=True)

    def mark_skipped(self, url: str, source: str, category: str, reason: str) -> None:
        self._mark(url, source, category, status="skipped", error=reason, crawled=True)

    def mark_failure(self, url: str, source: str, category: str, error: str) -> None:
        self._mark(url, source, category, status="failed", error=error, crawled=False)

    def _mark(
        self,
        url: str,
        source: str,
        category: str,
        status: str,
        error: str | None,
        crawled: bool,
    ) -> None:
        normalized_url = normalize_url(url)
        timestamp = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO news_url_registry (
                    url, source, category, status, first_seen_at, last_seen_at,
                    last_attempt_at, crawled_at, attempt_count, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(url) DO UPDATE SET
                    source = excluded.source,
                    category = excluded.category,
                    status = excluded.status,
                    last_seen_at = excluded.last_seen_at,
                    last_attempt_at = excluded.last_attempt_at,
                    crawled_at = excluded.crawled_at,
                    attempt_count = news_url_registry.attempt_count + 1,
                    last_error = excluded.last_error
                """,
                (
                    normalized_url,
                    source,
                    category,
                    status,
                    timestamp,
                    timestamp,
                    timestamp,
                    timestamp if crawled else None,
                    error,
                ),
            )

    def seed_success(self, rows: list[dict[str, str]]) -> int:
        if not rows:
            return 0
        timestamp = utc_now().isoformat()
        values = [
            (
                normalize_url(row["url"]),
                row.get("source", "unknown"),
                row.get("category", ""),
                timestamp,
                timestamp,
                timestamp,
                timestamp,
            )
            for row in rows
            if row.get("url")
        ]
        with self._connect() as connection:
            before = connection.total_changes
            connection.executemany(
                """
                INSERT OR IGNORE INTO news_url_registry (
                    url, source, category, status, first_seen_at, last_seen_at,
                    last_attempt_at, crawled_at, attempt_count
                ) VALUES (?, ?, ?, 'success', ?, ?, ?, ?, 1)
                """,
                values,
            )
            inserted = connection.total_changes - before
        return inserted

    def status_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, count(*) AS count FROM news_url_registry GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}
