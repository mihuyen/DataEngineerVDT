from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from src.ingestion.news_url_registry import NewsURLRegistry, normalize_url


def test_normalize_url_removes_fragment_and_tracking_parameters() -> None:
    assert normalize_url("HTTPS://Example.com/news?a=1&utm_source=x#top") == "https://example.com/news?a=1"


def test_successful_url_is_not_crawled_again(tmp_path: Path) -> None:
    registry = NewsURLRegistry(tmp_path / "registry.sqlite3")
    url = "https://example.com/article"

    registry.register_discovered(url, "VnExpress", "Chứng khoán")
    assert registry.should_crawl(url)

    registry.mark_success(url, "VnExpress", "Chứng khoán")

    assert not registry.should_crawl(url)
    assert registry.status_counts() == {"success": 1}


def test_failed_url_respects_retry_limit_and_delay(tmp_path: Path) -> None:
    registry = NewsURLRegistry(tmp_path / "registry.sqlite3")
    url = "https://example.com/broken"
    registry.register_discovered(url, "CafeF", "Doanh nghiệp")
    registry.mark_failure(url, "CafeF", "Doanh nghiệp", "timeout")

    assert not registry.should_crawl(url, retry_after=timedelta(minutes=30))
    assert registry.should_crawl(url, retry_after=timedelta(seconds=0))

    registry.mark_failure(url, "CafeF", "Doanh nghiệp", "timeout")
    registry.mark_failure(url, "CafeF", "Doanh nghiệp", "timeout")
    assert not registry.should_crawl(url, max_attempts=3, retry_after=timedelta(seconds=0))


def test_backfill_can_retry_a_skipped_historical_url(tmp_path: Path) -> None:
    registry = NewsURLRegistry(tmp_path / "registry.sqlite3")
    url = "https://example.com/historical"
    registry.register_discovered(url, "VnExpress", "Chứng khoán")
    registry.mark_skipped(url, "VnExpress", "Chứng khoán", "article is older than max_age_days")

    assert not registry.should_crawl(url)
    assert registry.should_crawl(url, retry_skipped=True)


def test_seed_success_only_inserts_new_urls(tmp_path: Path) -> None:
    registry = NewsURLRegistry(tmp_path / "registry.sqlite3")
    rows = [
        {"url": "https://example.com/a", "source": "Vietstock", "category": "Tài chính"},
        {"url": "https://example.com/a", "source": "Vietstock", "category": "Tài chính"},
    ]

    assert registry.seed_success(rows) == 1
    assert registry.seed_success(rows) == 0
    assert registry.count() == 1
