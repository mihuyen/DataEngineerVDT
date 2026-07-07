from __future__ import annotations

from src.api import dashboard_api


def test_news_sentiment_query_avoids_nested_source_aggregate(monkeypatch) -> None:
    queries: list[str] = []

    def capture_rows(sql: str) -> list[dict[str, object]]:
        queries.append(sql)
        return []

    monkeypatch.setattr(dashboard_api, "rows", capture_rows)

    result = dashboard_api.get_news_sentiment(days=7)

    assert result == {
        "count": 0,
        "data": [],
        "byDate": [],
        "articles": [],
        "modelVersions": [],
    }
    assert "argMax(source, inferred_at) AS latestSource" in queries[0]
    assert "any(d.latestSource) AS source" in queries[0]
