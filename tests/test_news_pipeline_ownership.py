from pathlib import Path


def test_news_five_minute_cycle_owns_quality_inference_and_gold_load() -> None:
    content = Path("scripts/run_news_crawl_loop.py").read_text(encoding="utf-8")

    ordered_commands = [
        "scripts/run_news_ingest.py",
        "scripts/run_news_silver.py",
        "scripts/run_news_quality_check.py",
        "scripts/run_news_entity_linking.py",
        "scripts/run_news_nlp_inference.py",
        "scripts/run_news_sentiment_quality.py",
        "scripts/load_news_sentiment_gold.py",
    ]
    positions = [content.index(command) for command in ordered_commands]
    assert positions == sorted(positions)


def test_daily_dag_does_not_own_news_processing() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "run_news_ingest.py" not in content
    assert "run_news_silver.py" not in content
    assert "run_news_nlp_inference.py" not in content
    assert "--exclude-news" in content
    assert "--skip-news" in content
