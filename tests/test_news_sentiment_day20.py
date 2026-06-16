from datetime import date
from pathlib import Path

import polars as pl

from src.loaders.load_fact_news_sentiment import (
    build_fact_news_sentiment_daily,
    sentiment_label,
    sentiment_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "fact_news_sentiment_daily.sql"


def sample_linked_news() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "article_id": ["a1", "a2", "a3", "a4"],
            "url": ["u1", "u2", "u3", "u4"],
            "title": [
                "VCB lợi nhuận tăng mạnh",
                "VCB bị cảnh báo rủi ro nợ xấu",
                "FPT mở rộng mảng AI",
                "FPT họp đại hội cổ đông",
            ],
            "published_at": [
                date(2026, 6, 16),
                date(2026, 6, 16),
                date(2026, 6, 16),
                date(2026, 6, 16),
            ],
            "source": ["CafeF", "Vietstock", "CafeF", "VnExpress"],
            "category": ["Chứng khoán", "Chứng khoán", "Doanh nghiệp", "Doanh nghiệp"],
            "ticker": ["VCB", "VCB", "FPT", "FPT"],
            "matched_alias": ["VCB", "VCB", "FPT", "FPT"],
            "match_method": ["ticker_regex"] * 4,
            "match_score": [2, 2, 2, 2],
        }
    )


def test_day20_fact_news_sentiment_ddl_matches_scheme() -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")

    assert "ticker String" in ddl
    assert "news_count UInt32" in ddl
    assert "source_count UInt8" in ddl
    assert "avg_sentiment_score Float64" in ddl
    assert "PARTITION BY toYYYYMM(news_date)" in ddl
    assert "ORDER BY (ticker, news_date)" in ddl


def test_day20_demo_sentiment_score_and_label() -> None:
    assert sentiment_score("lợi nhuận tăng mạnh") > 0
    assert sentiment_score("bị khởi tố và cảnh báo rủi ro") < 0
    assert sentiment_score("họp đại hội cổ đông") == 0
    assert sentiment_label(0.5) == "positive"
    assert sentiment_label(-0.5) == "negative"
    assert sentiment_label(0.0) == "neutral"


def test_day20_build_fact_news_sentiment_daily_aggregates_by_ticker_date() -> None:
    frame = build_fact_news_sentiment_daily(sample_linked_news())

    assert frame.height == 2
    vcb = frame.filter(pl.col("ticker") == "VCB").row(0, named=True)
    fpt = frame.filter(pl.col("ticker") == "FPT").row(0, named=True)

    assert vcb["news_count"] == 2
    assert vcb["source_count"] == 2
    assert vcb["positive_count"] == 1
    assert vcb["negative_count"] == 1
    assert fpt["news_count"] == 2
    assert fpt["positive_count"] == 1
    assert fpt["neutral_count"] == 1
