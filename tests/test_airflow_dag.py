from pathlib import Path


def test_stock_lakehouse_daily_dag_contains_core_tasks() -> None:
    dag_path = Path("dags/stock_lakehouse_daily.py")
    content = dag_path.read_text(encoding="utf-8")

    expected_tasks = [
        "init_minio_buckets",
        "bronze_ohlcv",
        "bronze_company_profile_listing",
        "bronze_market_index",
        "bronze_market_news",
        "silver_ohlcv",
        "silver_company_profile",
        "silver_market_index",
        "silver_news",
        "news_nlp_inference",
        "news_sentiment_quality",
        "quality_all",
        "migrate_gold_schema",
        "load_gold",
    ]

    for task_id in expected_tasks:
        assert task_id in content


def test_stock_lakehouse_daily_dag_uses_resume_for_long_ohlcv_ingest() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "--skip-existing" in content
    assert "--request-delay-seconds 5" in content
    assert "UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock" in content


def test_stock_lakehouse_daily_dag_has_quality_gate_before_gold() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "scripts/run_all_quality_checks.py" in content
    assert "quality_all >> [migrate_gold, news_nlp_inference]" in content
    assert "news_nlp_inference >> news_sentiment_quality" in content
    assert "[migrate_gold, news_sentiment_quality] >> load_gold" in content


def test_stock_lakehouse_daily_dag_uses_vietnam_timezone_and_weekday_schedule() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "Asia/Ho_Chi_Minh" in content
    assert 'schedule="0 18 * * 1-5"' in content
