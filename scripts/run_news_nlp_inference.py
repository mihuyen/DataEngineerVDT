from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.minio_client import create_bucket_if_missing, create_client, upload_file
from src.integrations.nlp_client import NLPArticle, NLPClient
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
        score = float(item["sentiment_score"])
        rows.append(
            {
                "article_id": item["article_id"],
                "sentiment_label": item["sentiment_label"],
                "sentiment_score": score,
                "confidence_score": float(item["confidence_score"]),
                "is_low_confidence": bool(item["is_low_confidence"]),
                "model_version": item["model_version"],
                "processing_time_ms": float(item["processing_time_ms"]),
                "inferred_at": inferred_at,
            }
        )
    return pl.DataFrame(rows)


def load_processed_article_ids(base_dir: Path, model_version: str) -> set[str]:
    files = sorted((base_dir / OUTPUT_PREFIX).glob("year=*/month=*/data.parquet"))
    if not files:
        return set()
    existing = pl.concat(
        [pl.read_parquet(path, columns=["article_id", "model_version"]) for path in files],
        how="diagonal_relaxed",
    )
    return set(
        existing.filter(pl.col("model_version") == model_version)
        .get_column("article_id")
        .to_list()
    )


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
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-run articles already inferred by this model version.")
    parser.add_argument("--no-upload", action="store_true")
    return parser.parse_args()


def predict_parallel(articles: list[NLPArticle], base_url: str, workers: int) -> list[dict | None]:
    """Gọi /predict/sentiment song song bằng thread pool.

    A single article that fails after retries is logged and skipped (result
    stays None) rather than raising out of the whole batch -- this script's
    caller only writes output once, at the very end, so an unretried
    transient failure (e.g. the NLP service reloading its model right after a
    restart) used to throw away every successful prediction collected in the
    same run, sometimes 20+ minutes of work.
    """
    import time

    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed

    session = requests.Session()
    url = base_url.rstrip("/") + "/predict/sentiment"
    max_attempts = 3

    def call_one(article: NLPArticle) -> dict | None:
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = session.post(url, json=article.as_payload(), timeout=60)
                resp.raise_for_status()
                result = resp.json()
                result["article_id"] = article.article_id
                return result
            except Exception as exc:  # noqa: BLE001 - retry any transient failure
                last_exc = exc
                if attempt < max_attempts:
                    time.sleep(2**attempt)
        print(f"  inference_failed: article_id={article.article_id} after {max_attempts} attempts ({last_exc})", flush=True)
        return None

    results: list[dict | None] = [None] * len(articles)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {pool.submit(call_one, a): i for i, a in enumerate(articles)}
        done = 0
        failed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            if results[idx] is None:
                failed += 1
            done += 1
            if done % 50 == 0:
                print(f"  inference: {done}/{len(articles)} (failed={failed})", flush=True)
    return results


def main() -> None:
    args = parse_args()
    news = load_silver_news(DEFAULT_LOCAL_SILVER_DIR)
    company_profile = load_silver_company_profile(DEFAULT_LOCAL_SILVER_DIR)
    links = link_news_to_tickers(news, company_profile)
    articles, _ = build_inference_articles(news, links)

    client = NLPClient(base_url=args.service_url)
    health = client.health()
    if health.get("is_fallback") and not args.allow_fallback:
        raise RuntimeError("NLP service is using rule-based fallback; refusing to publish model sentiment.")

    model_version = str(health.get("model_version") or "unknown")
    if not args.force:
        processed = load_processed_article_ids(DEFAULT_LOCAL_GOLD_DIR, model_version)
        articles = [article for article in articles if article.article_id not in processed]

    base_url = client.base_url
    if not articles:
        print(f"No new linked articles for model_version={model_version}")
        return
    print(f"Running inference on {len(articles)} articles with {args.workers} workers...")
    raw_predictions = predict_parallel(articles, base_url, workers=args.workers)
    predictions = [item for item in raw_predictions if item is not None]
    failed_count = len(raw_predictions) - len(predictions)
    if failed_count:
        print(f"- failed_after_retries: {failed_count} (will be retried on next run)")
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
