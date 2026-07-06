from __future__ import annotations

import re
import os
from datetime import datetime
from pathlib import Path

import polars as pl

from src.common.clickhouse_client import insert_dataframe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_GOLD_DIR = PROJECT_ROOT / "data" / "gold_local"
NEWS_ENTITY_LINKS_PREFIX = "news_entity_links"

POSITIVE_TERMS = {
    "bứt phá",
    "cao kỷ lục",
    "cải thiện",
    "chia cổ tức",
    "đạt đỉnh",
    "đột biến",
    "hồi phục",
    "khởi sắc",
    "lãi",
    "lợi nhuận",
    "mở rộng",
    "phục hồi",
    "tăng",
    "tăng mạnh",
    "tăng trưởng",
    "tích cực",
    "trúng thầu",
    "vượt kế hoạch",
}

NEGATIVE_TERMS = {
    "bắt tạm giam",
    "cảnh báo",
    "đình chỉ",
    "giảm",
    "giảm mạnh",
    "khởi tố",
    "lỗ",
    "lao dốc",
    "nợ xấu",
    "phạt",
    "rủi ro",
    "sụt giảm",
    "tiêu cực",
    "thua lỗ",
    "truy tố",
}


def load_news_entity_links(local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR) -> pl.DataFrame:
    """Load local news entity links produced by Day 19."""
    files = sorted((local_gold_dir / NEWS_ENTITY_LINKS_PREFIX).glob("year=*/month=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"No news entity link parquet files found under {local_gold_dir}")
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def sentiment_score(text: str | None) -> float:
    """Return a simple lexicon-based sentiment score from -1 to 1."""
    normalized = normalize_text(text)
    positive_count = sum(1 for term in POSITIVE_TERMS if term in normalized)
    negative_count = sum(1 for term in NEGATIVE_TERMS if term in normalized)
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (positive_count - negative_count) / total))


def sentiment_label(score: float) -> str:
    if score > 0.05:
        return "positive"
    if score < -0.05:
        return "negative"
    return "neutral"


def add_demo_sentiment(linked_news: pl.DataFrame) -> pl.DataFrame:
    """Attach demo sentiment score and label to linked news rows."""
    if linked_news.is_empty():
        return linked_news.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("sentiment_score"),
            pl.lit(None, dtype=pl.Utf8).alias("sentiment_label"),
        )

    return linked_news.with_columns(
        pl.col("title").map_elements(sentiment_score, return_dtype=pl.Float64).alias("sentiment_score")
    ).with_columns(
        pl.col("sentiment_score").map_elements(sentiment_label, return_dtype=pl.Utf8).alias("sentiment_label")
    )


def build_fact_news_sentiment_daily(linked_news: pl.DataFrame) -> pl.DataFrame:
    """Build daily ticker-level news sentiment fact rows."""
    now = datetime.now()
    if linked_news.is_empty():
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "date_id": pl.UInt32,
                "news_date": pl.Date,
                "news_count": pl.UInt32,
                "source_count": pl.UInt8,
                "positive_count": pl.UInt32,
                "negative_count": pl.UInt32,
                "neutral_count": pl.UInt32,
                "avg_sentiment_score": pl.Float64,
                "top_headline": pl.Utf8,
                "created_at": pl.Datetime,
            }
        )

    enriched = (
        add_demo_sentiment(linked_news)
        .with_columns(
            pl.col("ticker").str.to_uppercase(),
            pl.col("published_at").alias("news_date"),
            (pl.col("sentiment_label") == "positive").cast(pl.UInt8).alias("is_positive"),
            (pl.col("sentiment_label") == "negative").cast(pl.UInt8).alias("is_negative"),
            (pl.col("sentiment_label") == "neutral").cast(pl.UInt8).alias("is_neutral"),
        )
        .filter(pl.col("news_date").is_not_null())
        .unique(subset=["article_id", "ticker"], keep="last", maintain_order=True)
    )

    return (
        enriched.group_by(["ticker", "news_date"])
        .agg(
            pl.col("article_id").n_unique().cast(pl.UInt32).alias("news_count"),
            pl.col("source").n_unique().cast(pl.UInt8).alias("source_count"),
            pl.sum("is_positive").cast(pl.UInt32).alias("positive_count"),
            pl.sum("is_negative").cast(pl.UInt32).alias("negative_count"),
            pl.sum("is_neutral").cast(pl.UInt32).alias("neutral_count"),
            pl.mean("sentiment_score").alias("avg_sentiment_score"),
            pl.col("title").sort_by("match_score", descending=True).first().alias("top_headline"),
        )
        .with_columns(
            pl.col("news_date").dt.strftime("%Y%m%d").cast(pl.UInt32).alias("date_id"),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
        )
        .select(
            "ticker",
            "date_id",
            "news_date",
            "news_count",
            "source_count",
            "positive_count",
            "negative_count",
            "neutral_count",
            "avg_sentiment_score",
            "top_headline",
            "created_at",
        )
        .sort(["ticker", "news_date"])
    )


NLP_SENTIMENT_DETAIL_PREFIX = "news_sentiment_detail"


def load_nlp_sentiment_detail(local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR) -> pl.DataFrame | None:
    """Load NLP inference output from run_news_nlp_inference.py, or None if not available."""
    files = sorted((local_gold_dir / NLP_SENTIMENT_DETAIL_PREFIX).glob("year=*/month=*/data.parquet"))
    if not files:
        return None
    return pl.concat([pl.read_parquet(f) for f in files], how="diagonal_relaxed")


def build_fact_news_sentiment_daily_from_nlp(nlp_detail: pl.DataFrame) -> pl.DataFrame:
    """Build fact_news_sentiment_daily from NLP model inference output."""
    now = datetime.now()
    detail = select_active_model_version(nlp_detail)
    return (
        detail
        .with_columns(
            pl.col("ticker").str.to_uppercase(),
            pl.col("published_at").cast(pl.Date).alias("news_date"),
            (pl.col("sentiment_label") == "positive").cast(pl.UInt8).alias("is_positive"),
            (pl.col("sentiment_label") == "negative").cast(pl.UInt8).alias("is_negative"),
            (pl.col("sentiment_label") == "neutral").cast(pl.UInt8).alias("is_neutral"),
        )
        .filter(pl.col("news_date").is_not_null())
        .unique(subset=["article_id", "ticker"], keep="last", maintain_order=True)
        .group_by(["ticker", "news_date"])
        .agg(
            pl.col("article_id").n_unique().cast(pl.UInt32).alias("news_count"),
            pl.col("source").n_unique().cast(pl.UInt8).alias("source_count"),
            pl.sum("is_positive").cast(pl.UInt32).alias("positive_count"),
            pl.sum("is_negative").cast(pl.UInt32).alias("negative_count"),
            pl.sum("is_neutral").cast(pl.UInt32).alias("neutral_count"),
            pl.mean("sentiment_score").alias("avg_sentiment_score"),
            pl.col("title").sort_by("match_score", descending=True).first().alias("top_headline"),
        )
        .with_columns(
            pl.col("news_date").dt.strftime("%Y%m%d").cast(pl.UInt32).alias("date_id"),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
        )
        .select(
            "ticker", "date_id", "news_date", "news_count", "source_count",
            "positive_count", "negative_count", "neutral_count",
            "avg_sentiment_score", "top_headline", "created_at",
        )
        .sort(["ticker", "news_date"])
    )


def select_active_model_version(nlp_detail: pl.DataFrame) -> pl.DataFrame:
    """Keep one reproducible model version and the latest prediction per article/ticker."""
    configured = os.getenv("MODEL_VERSION")
    versions = nlp_detail.get_column("model_version").drop_nulls().unique().to_list()
    if configured and configured in versions:
        active = configured
    else:
        active = (
            nlp_detail.group_by("model_version")
            .agg(pl.max("inferred_at").alias("latest"))
            .sort("latest", descending=True)
            .item(0, "model_version")
        )
    return (
        nlp_detail.filter(pl.col("model_version") == active)
        .unique(subset=["article_id", "ticker"], keep="last", maintain_order=True)
    )


def build_fact_news_sentiment_detail(nlp_detail: pl.DataFrame) -> pl.DataFrame:
    detail = select_active_model_version(nlp_detail)
    return (
        detail.with_columns(
            pl.col("published_at").cast(pl.Date),
            pl.col("match_score").cast(pl.UInt8),
            pl.col("is_low_confidence").cast(pl.UInt8),
            pl.col("inferred_at").dt.replace_time_zone(None),
        )
        .select(
            "article_id",
            "ticker",
            "url",
            "title",
            "source",
            "published_at",
            "sentiment_label",
            "sentiment_score",
            "confidence_score",
            "is_low_confidence",
            "model_version",
            "match_method",
            "match_score",
            "inferred_at",
        )
        .sort(["ticker", "published_at", "article_id"])
    )


def load_fact_news_sentiment_daily(
    client: object,
    linked_news: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Load fact_news_sentiment_daily into ClickHouse.

    Requires versioned NLP model output. Lexicon helpers remain available for
    tests and exploration but are never published as production sentiment.
    """
    nlp_detail = load_nlp_sentiment_detail()
    if nlp_detail is None or nlp_detail.is_empty():
        raise FileNotFoundError(
            "No versioned NLP inference output found; refusing to publish lexicon demo sentiment."
        )
    detail = build_fact_news_sentiment_detail(nlp_detail)
    frame = build_fact_news_sentiment_daily_from_nlp(nlp_detail)
    insert_dataframe(client, "fact_news_sentiment_detail", detail)  # type: ignore[arg-type]
    insert_dataframe(client, "fact_news_sentiment_daily", frame)  # type: ignore[arg-type]
    return frame
