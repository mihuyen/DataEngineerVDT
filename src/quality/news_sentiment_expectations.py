from __future__ import annotations

import polars as pl


VALID_LABELS = {"positive", "neutral", "negative"}


def validate_news_sentiment_detail(
    detail: pl.DataFrame,
    company_profile: pl.DataFrame,
) -> dict[str, object]:
    required = {
        "article_id",
        "ticker",
        "published_at",
        "sentiment_label",
        "sentiment_score",
        "confidence_score",
        "model_version",
    }
    missing = sorted(required.difference(detail.columns))
    errors: list[str] = []
    if missing:
        return {"status": "FAIL", "errors": [f"missing columns: {', '.join(missing)}"]}

    hose_tickers = set(
        company_profile.filter(pl.col("exchange").str.to_uppercase() == "HOSE")
        .get_column("ticker")
        .str.to_uppercase()
        .unique()
        .to_list()
    )
    invalid_labels = detail.filter(~pl.col("sentiment_label").is_in(sorted(VALID_LABELS))).height
    invalid_scores = detail.filter(~pl.col("sentiment_score").is_between(-1.0, 1.0)).height
    invalid_confidence = detail.filter(~pl.col("confidence_score").is_between(0.0, 1.0)).height
    invalid_tickers = detail.filter(~pl.col("ticker").is_in(sorted(hose_tickers))).height
    duplicate_rows = detail.group_by(["article_id", "ticker", "model_version"]).len().filter(pl.col("len") > 1).height

    checks = {
        "rows": detail.height,
        "articles": detail.get_column("article_id").n_unique(),
        "tickers": detail.get_column("ticker").n_unique(),
        "invalid_labels": invalid_labels,
        "invalid_scores": invalid_scores,
        "invalid_confidence": invalid_confidence,
        "invalid_tickers": invalid_tickers,
        "duplicate_business_keys": duplicate_rows,
    }
    for name in [
        "invalid_labels",
        "invalid_scores",
        "invalid_confidence",
        "invalid_tickers",
        "duplicate_business_keys",
    ]:
        if checks[name]:
            errors.append(f"{name}: {checks[name]}")
    if detail.is_empty():
        errors.append("no sentiment detail rows")
    return {"status": "PASS" if not errors else "FAIL", "checks": checks, "errors": errors}
