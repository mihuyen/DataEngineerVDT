from __future__ import annotations

from typing import Any

import pytest

from src.integrations.nlp_client import NLPArticle, NLPClient, normalized_sentiment_label


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []

    def get(self, url: str, timeout: float) -> FakeResponse:
        return FakeResponse({"status": "ok", "is_fallback": False})

    def post(self, url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        self.posts.append(json)
        return FakeResponse([{"article_id": item["article_id"]} for item in json["articles"]])


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0.75, "positive"), (-0.75, "negative"), (0.0, "neutral")],
)
def test_normalized_sentiment_label(score: float, expected: str) -> None:
    assert normalized_sentiment_label(score) == expected


def test_nlp_client_splits_batches() -> None:
    session = FakeSession()
    client = NLPClient(base_url="http://nlp", session=session)  # type: ignore[arg-type]
    articles = [NLPArticle(article_id=str(i), content="content") for i in range(35)]

    predictions = client.predict_batch(articles, batch_size=16)

    assert len(predictions) == 35
    assert [len(request["articles"]) for request in session.posts] == [16, 16, 3]
