from datetime import date, datetime

import polars as pl

from src.quality.news_sentiment_expectations import validate_news_sentiment_detail


def test_news_sentiment_detail_quality_passes_valid_hose_rows() -> None:
    detail = pl.DataFrame(
        {
            "article_id": ["a1"],
            "ticker": ["VCB"],
            "published_at": [date(2026, 7, 6)],
            "sentiment_label": ["positive"],
            "sentiment_score": [0.8],
            "confidence_score": [0.9],
            "model_version": ["v1"],
            "inferred_at": [datetime(2026, 7, 6, 10, 0)],
        }
    )
    companies = pl.DataFrame({"ticker": ["VCB"], "exchange": ["HOSE"]})

    assert validate_news_sentiment_detail(detail, companies)["status"] == "PASS"


def test_news_sentiment_detail_quality_rejects_invalid_label_and_ticker() -> None:
    detail = pl.DataFrame(
        {
            "article_id": ["a1"],
            "ticker": ["SHB"],
            "published_at": [date(2026, 7, 6)],
            "sentiment_label": ["bullish"],
            "sentiment_score": [2.0],
            "confidence_score": [1.2],
            "model_version": ["v1"],
            "inferred_at": [datetime(2026, 7, 6, 10, 0)],
        }
    )
    companies = pl.DataFrame({"ticker": ["VCB"], "exchange": ["HOSE"]})

    report = validate_news_sentiment_detail(detail, companies)
    assert report["status"] == "FAIL"
    assert report["checks"]["invalid_tickers"] == 1
