from datetime import date

import polars as pl

from src.quality.news_expectations import validate_news


def valid_news() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "url": ["https://example.com/a"],
            "title": ["Tin A"],
            "content": ["Nội dung bài viết đủ dài để vượt qua ngưỡng kiểm tra tối thiểu."],
            "source": ["CafeF"],
            "published_at": [date(2026, 6, 14)],
        }
    )


def test_news_quality_passes() -> None:
    report = validate_news(valid_news())

    assert report.success is True
    assert report.error_count == 0


def test_news_quality_fails_invalid_rows() -> None:
    frame = pl.DataFrame(
        {
            "url": ["", "https://example.com/a", "https://example.com/a"],
            "title": ["", "Tin A", "Tin A duplicate"],
            "content": ["short", "short", "Nội dung đủ dài để vượt qua kiểm tra tối thiểu."],
            "source": ["", "CafeF", "CafeF"],
            "published_at": [None, None, date(2026, 6, 14)],
        }
    )

    report = validate_news(frame)
    failed_names = {expectation.name for expectation in report.expectations if not expectation.success}

    assert report.success is False
    assert "expect_url_to_not_be_null" in failed_names
    assert "expect_content_to_be_long_enough" in failed_names
    assert "expect_url_to_be_unique" in failed_names
