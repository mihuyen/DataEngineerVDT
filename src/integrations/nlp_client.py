from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


DEFAULT_NLP_SERVICE_URL = "http://localhost:8002"


@dataclass(frozen=True)
class NLPArticle:
    article_id: str
    content: str
    title: str = ""
    source_type: str = "article"
    platform: str = ""

    def as_payload(self) -> dict[str, str]:
        return {
            "article_id": self.article_id,
            "content": self.content,
            "title": self.title,
            "source_type": self.source_type,
            "platform": self.platform,
        }


def normalized_sentiment_label(score: float) -> str:
    if score > 0.05:
        return "positive"
    if score < -0.05:
        return "negative"
    return "neutral"


class NLPClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 120,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("NLP_SERVICE_URL") or DEFAULT_NLP_SERVICE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}/health", timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def predict_batch(self, articles: list[NLPArticle], batch_size: int = 32) -> list[dict[str, Any]]:
        if not articles:
            return []
        if not 1 <= batch_size <= 32:
            raise ValueError("batch_size must be between 1 and 32")

        predictions: list[dict[str, Any]] = []
        for start in range(0, len(articles), batch_size):
            batch = articles[start : start + batch_size]
            response = self.session.post(
                f"{self.base_url}/predict/batch",
                json={
                    "articles": [article.as_payload() for article in batch],
                    "max_batch_size": batch_size,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or len(payload) != len(batch):
                raise ValueError("NLP service returned an invalid batch response")
            predictions.extend(payload)
        return predictions
