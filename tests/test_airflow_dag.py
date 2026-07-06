from pathlib import Path


def test_stock_lakehouse_daily_dag_contains_core_tasks() -> None:
    dag_path = Path("dags/stock_lakehouse_daily.py")
    content = dag_path.read_text(encoding="utf-8")

    expected_tasks = [
        "init_minio_buckets",
        "bronze_ohlcv",
        "bronze_company_profile_listing",
        "bronze_market_index",
        "silver_ohlcv",
        "silver_company_profile",
        "silver_market_index",
        "quality_all",
        "migrate_gold_schema",
        "load_gold",
    ]

    for task_id in expected_tasks:
        assert task_id in content

    for news_task in ["bronze_market_news", "silver_news", "news_nlp_inference", "news_sentiment_quality"]:
        assert news_task not in content


def test_stock_lakehouse_daily_dag_uses_resume_for_long_ohlcv_ingest() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "--skip-existing" in content
    assert "--request-delay-seconds 5" in content
    assert "UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock" in content


def test_stock_lakehouse_daily_dag_has_quality_gate_before_gold() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "scripts/run_all_quality_checks.py --exclude-news" in content
    assert "scripts/migrate_gold_schema.py --skip-news" in content
    assert "scripts/load_gold.py --skip-news" in content
    assert "quality_all >> migrate_gold >> load_gold" in content


def test_stock_lakehouse_daily_dag_uses_vietnam_timezone_and_weekday_schedule() -> None:
    content = Path("dags/stock_lakehouse_daily.py").read_text(encoding="utf-8")

    assert "Asia/Ho_Chi_Minh" in content
    assert 'schedule="0 18 * * 1-5"' in content


def test_news_crawl_5m_dag_runs_every_five_minutes() -> None:
    content = Path("dags/news_crawl_5m.py").read_text(encoding="utf-8")

    assert "news_crawl_5m" in content
    assert 'schedule="*/5 * * * *"' in content
    assert "scripts/run_news_crawl_loop.py" in content
    assert "--run-once --load-gold" in content
    assert "notify_success" not in content
