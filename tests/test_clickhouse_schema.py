from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"
STREAMING_SQL_PATH = PROJECT_ROOT / "sql" / "streaming" / "realtime_vwap_kafka_engine.sql"


def test_gold_ddl_files_exist() -> None:
    # fact_realtime_vwap is not here: it's a VIEW defined in
    # sql/streaming/realtime_vwap_kafka_engine.sql on top of the
    # AggregatingMergeTree state table fact_realtime_vwap_1m_state, applied by
    # scripts/init_realtime_streaming.py rather than migrate_gold_schema.py.
    expected_files = [
        "dim_date.sql",
        "dim_sector.sql",
        "dim_stock.sql",
        "dim_index.sql",
        "fact_daily_price.sql",
        "fact_market_index.sql",
        "fact_intraday_ohlcv.sql",
        "fact_news_sentiment_daily.sql",
        "fact_news_sentiment_detail.sql",
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


def test_scheme_fact_realtime_vwap_state_has_daily_partition() -> None:
    sql = STREAMING_SQL_PATH.read_text(encoding="utf-8")

    assert "ENGINE = AggregatingMergeTree" in sql
    assert "PARTITION BY toYYYYMMDD(trading_date)" in sql
    assert "ORDER BY (data_source, ticker, minute_ts)" in sql
    assert "CREATE VIEW fact_realtime_vwap AS" in sql


def test_fact_intraday_ohlcv_ddl_has_daily_partition() -> None:
    ddl = (DDL_DIR / "fact_intraday_ohlcv.sql").read_text(encoding="utf-8")

    assert "ENGINE = ReplacingMergeTree(ingested_at)" in ddl
    assert "PARTITION BY toYYYYMMDD(trading_date)" in ddl
    assert "ORDER BY (ticker, resolution, minute_ts)" in ddl


def test_scheme_news_and_alert_fact_tables_exist() -> None:
    news_ddl = (DDL_DIR / "fact_news_sentiment_daily.sql").read_text(encoding="utf-8")
    alert_ddl = (DDL_DIR / "fact_alert_event.sql").read_text(encoding="utf-8")

    assert "ORDER BY (ticker, news_date)" in news_ddl
    detail_ddl = (DDL_DIR / "fact_news_sentiment_detail.sql").read_text(encoding="utf-8")
    assert "ReplacingMergeTree(inferred_at)" in detail_ddl
    assert "ORDER BY (ticker, published_at, article_id)" in detail_ddl
    assert "ORDER BY (user_id, triggered_at)" in alert_ddl
