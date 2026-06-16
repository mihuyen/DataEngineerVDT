from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"


def test_gold_ddl_files_exist() -> None:
    expected_files = [
        "dim_date.sql",
        "dim_sector.sql",
        "dim_stock.sql",
        "dim_index.sql",
        "fact_daily_price.sql",
        "fact_market_index.sql",
        "fact_realtime_vwap.sql",
        "fact_news_sentiment_daily.sql",
        "fact_alert_event.sql",
    ]

    for file_name in expected_files:
        assert (DDL_DIR / file_name).is_file(), f"Missing DDL file: {file_name}"


def test_fact_daily_price_ddl_has_partition_and_order_key() -> None:
    ddl = (DDL_DIR / "fact_daily_price.sql").read_text(encoding="utf-8")

    assert "ENGINE = MergeTree" in ddl
    assert "PARTITION BY toYYYYMM(trading_date)" in ddl
    assert "ORDER BY (ticker, trading_date)" in ddl


def test_fact_market_index_ddl_has_partition_and_order_key() -> None:
    ddl = (DDL_DIR / "fact_market_index.sql").read_text(encoding="utf-8")

    assert "ENGINE = MergeTree" in ddl
    assert "PARTITION BY toYYYYMM(trading_date)" in ddl
    assert "ORDER BY (index_id, trading_date)" in ddl


def test_scheme_fact_realtime_vwap_ddl_has_daily_partition() -> None:
    ddl = (DDL_DIR / "fact_realtime_vwap.sql").read_text(encoding="utf-8")

    assert "ENGINE = MergeTree" in ddl
    assert "PARTITION BY toYYYYMMDD(trading_date)" in ddl
    assert "ORDER BY (ticker, minute_ts)" in ddl


def test_scheme_news_and_alert_fact_tables_exist() -> None:
    news_ddl = (DDL_DIR / "fact_news_sentiment_daily.sql").read_text(encoding="utf-8")
    alert_ddl = (DDL_DIR / "fact_alert_event.sql").read_text(encoding="utf-8")

    assert "ORDER BY (ticker, news_date)" in news_ddl
    assert "ORDER BY (user_id, triggered_at)" in alert_ddl
