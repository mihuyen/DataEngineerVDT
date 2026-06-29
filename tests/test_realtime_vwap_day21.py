from datetime import datetime
from pathlib import Path

import polars as pl

from src.loaders.load_fact_realtime_vwap import (
    build_fact_realtime_vwap,
    generate_demo_trade_ticks,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "fact_realtime_vwap.sql"
STREAMING_SQL_PATH = PROJECT_ROOT / "sql" / "streaming" / "realtime_vwap_kafka_engine.sql"


def test_day21_fact_realtime_vwap_ddl_matches_scheme() -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")

    assert "ticker String" in ddl
    assert "data_source LowCardinality(String)" in ddl
    assert "minute_ts DateTime" in ddl
    assert "vwap_1m Float64" in ddl
    assert "session_vwap Float64" in ddl
    assert "PARTITION BY toYYYYMMDD(trading_date)" in ddl
    assert "ORDER BY (ticker, minute_ts)" in ddl


def test_day21_generate_demo_trade_ticks_is_deterministic() -> None:
    ticks = generate_demo_trade_ticks(tickers=["VCB", "FPT"], minutes=2, trades_per_minute=3)

    assert ticks.height == 12
    assert set(ticks.get_column("ticker").to_list()) == {"VCB", "FPT"}
    assert set(ticks.get_column("data_source").to_list()) == {"DEMO"}


def test_day21_build_fact_realtime_vwap_aggregates_minute_bars() -> None:
    ticks = pl.DataFrame(
        {
            "ticker": ["VCB", "VCB", "VCB"],
            "trade_ts": [
                datetime(2026, 6, 16, 9, 15, 1),
                datetime(2026, 6, 16, 9, 15, 20),
                datetime(2026, 6, 16, 9, 16, 1),
            ],
            "price": [100.0, 110.0, 120.0],
            "volume": [10, 30, 60],
            "data_source": ["DNSE", "DNSE", "DNSE"],
        }
    )

    frame = build_fact_realtime_vwap(ticks)
    first = frame.sort("minute_ts").row(0, named=True)
    second = frame.sort("minute_ts").row(1, named=True)

    assert frame.height == 2
    assert first["open_price"] == 100.0
    assert first["close_price"] == 110.0
    assert first["total_volume"] == 40
    assert first["vwap_1m"] == 107.5
    assert second["session_volume"] == 100
    assert second["session_vwap"] == 115.0


def test_day21_streaming_sql_contains_kafka_engine_and_materialized_view() -> None:
    sql = STREAMING_SQL_PATH.read_text(encoding="utf-8")

    assert "ENGINE = Kafka" in sql
    assert "dnse-trades-raw" in sql
    assert "CREATE MATERIALIZED VIEW" in sql
    assert "data_source LowCardinality(String)" in sql
    # The MV lands raw ticks into a staging table; a Python consumer
    # (scripts/run_realtime_vwap_kafka_consumer.py) computes the correct
    # cumulative session VWAP and loads fact_realtime_vwap from there.
    assert "TO realtime_trade_ticks_raw" in sql
    assert "dnse-ohlcv-1m" in sql
    assert "TO fact_intraday_ohlcv" in sql
