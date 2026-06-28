from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.minio_client import create_bucket_if_missing, create_client, upload_file
from src.integrations.nlp_client import NLPArticle, NLPClient, normalized_sentiment_label
from src.transform.news_entity_linking import (
    DEFAULT_LOCAL_GOLD_DIR,
    DEFAULT_LOCAL_SILVER_DIR,
    load_silver_company_profile,
    load_silver_news,
    link_news_to_tickers,
)


OUTPUT_PREFIX = "news_sentiment_detail"


def output_path(base_dir: Path, partition_date: date) -> Path:
    return base_dir / OUTPUT_PREFIX / f"year={partition_date:%Y}" / f"month={partition_date:%m}" / "data.parquet"


def build_inference_articles(news: pl.DataFrame, links: pl.DataFrame) -> tuple[list[NLPArticle], pl.DataFrame]:
    linked_articles = links.select("article_id", "url").unique(subset=["article_id"])
    article_data = linked_articles.join(
        news.select("url", "title", "content", "source").unique(subset=["url"], keep="last"),
        on="url",
        how="left",
    ).with_columns(
        pl.col("title").fill_null(""),
        pl.col("content").fill_null(""),
        pl.col("source").fill_null(""),
    )
    articles = [
        NLPArticle(
            article_id=row["article_id"],
            title=row["title"],
            content=row["content"],
            platform=row["source"],
        )
        for row in article_data.to_dicts()
        if row["title"] or row["content"]
    ]
    return articles, article_data


def flatten_predictions(predictions: list[dict[str, Any]]) -> pl.DataFrame:
    inferred_at = datetime.now(timezone.utc)
    rows = []
    for item in predictions:
        sentiment = item["sentiment"]
        topic = item["topic"]
        score = float(sentiment["sentiment_score"])
        rows.append(
            {
                "article_id": item["article_id"],
                "sentiment_label_raw": sentiment["sentiment_label"],
                "sentiment_label": normalized_sentiment_label(score),
                "sentiment_score": score,
                "confidence_score": float(sentiment["confidence_score"]),
                "is_low_confidence": bool(sentiment["is_low_confidence"]),
                "model_version": sentiment["model_version"],
                "processing_time_ms": float(sentiment["processing_time_ms"]),
                "topics": topic["topics"],
                "topic_distribution": json.dumps(topic["topic_distribution"], ensure_ascii=False),
                "inferred_at": inferred_at,
            }
        )
    return pl.DataFrame(rows)


def save_results(frame: pl.DataFrame, path: Path) -> pl.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        frame = pl.concat([pl.read_parquet(path), frame], how="diagonal_relaxed")
    frame = frame.unique(
        subset=["article_id", "ticker", "model_version"],
        keep="last",
        maintain_order=True,
    ).sort(["published_at", "ticker", "article_id"])
    frame.write_parquet(path)
    return frame


def upload_results(path: Path, partition_date: date) -> str:
    object_name = f"{OUTPUT_PREFIX}/year={partition_date:%Y}/month={partition_date:%m}/data.parquet"
    client = create_client()
    create_bucket_if_missing(client, "gold")
    upload_file(
        client=client,
        bucket_name="gold",
        object_name=object_name,
        file_path=path,
        content_type="application/vnd.apache.parquet",
    )
    return object_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FiNTA NLP inference for linked market news.")
    parser.add_argument("--service-url", default=None)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--no-upload", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    news = load_silver_news(DEFAULT_LOCAL_SILVER_DIR)
    company_profile = load_silver_company_profile(DEFAULT_LOCAL_SILVER_DIR)
    links = link_news_to_tickers(news, company_profile)
    articles, _ = build_inference_articles(news, links)

    client = NLPClient(base_url=args.service_url)
    health = client.health()
    predictions = client.predict_batch(articles, batch_size=args.batch_size)
    prediction_frame = flatten_predictions(predictions)
    enriched = links.join(prediction_frame, on="article_id", how="inner")

    partition_date = date.today()
    path = output_path(DEFAULT_LOCAL_GOLD_DIR, partition_date)
    saved = save_results(enriched, path)
    object_name = None if args.no_upload else upload_results(path, partition_date)

    print("News NLP inference completed")
    print(f"- service_fallback: {health.get('is_fallback')}")
    print(f"- articles_inferred: {len(predictions)}")
    print(f"- linked_rows_saved: {saved.height}")
    print(f"- local_path: {path}")
    if object_name:
        print(f"- minio_path: gold/{object_name}")


if __name__ == "__main__":
    main()
