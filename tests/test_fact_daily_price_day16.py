from datetime import date
from pathlib import Path

import polars as pl

from src.loaders.load_fact_daily_price import build_fact_daily_price


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "fact_daily_price.sql"

EXPECTED_FACT_DAILY_PRICE_COLUMNS = [
    "ticker",
    "date_id",
    "trading_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "value",
    "shares_outstanding",
    "market_cap",
    "price_change",
    "pct_change",
    "sma_20",
    "ema_12",
    "ema_26",
    "macd",
    "macd_signal",
    "rsi_14",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "volume_sma_20",
    "overbought_flag",
    "oversold_flag",
    "breakout_flag",
    "breakdown_flag",
    "created_at",
    "updated_at",
]


def sample_ohlcv() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "VCB", "FPT"],
            "date": [date(2026, 6, 10), date(2026, 6, 11), date(2026, 6, 10)],
            "open": [100.0, 102.0, 90.0],
            "high": [105.0, 106.0, 95.0],
            "low": [99.0, 101.0, 88.0],
            "close": [102.0, 104.0, 89.0],
            "volume": [1_000_000, 1_200_000, 900_000],
        }
    )


def test_day16_fact_daily_price_ddl_matches_scheme() -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")

    assert "ticker String" in ddl
    assert "trading_date Date" in ddl
    assert "market_cap Float64" in ddl
    assert "sma_20 Nullable(Float64)" in ddl
    assert "rsi_14 Nullable(Float64)" in ddl
    assert "PARTITION BY toYYYYMM(trading_date)" in ddl
    assert "ORDER BY (ticker, trading_date)" in ddl


def test_day16_build_fact_daily_price_outputs_scheme_columns() -> None:
    shares = pl.DataFrame(
        {
            "ticker": ["VCB", "FPT"],
            "shares_outstanding": [8_355_675_094, 1_703_507_121],
        }
    )

    frame = build_fact_daily_price(sample_ohlcv(), company_shares=shares)

    assert frame.columns == EXPECTED_FACT_DAILY_PRICE_COLUMNS
    assert frame.height == 3
    assert frame.select(["ticker", "trading_date"]).is_unique().all()


def test_day16_fact_daily_price_calculates_market_cap_and_change() -> None:
    shares = pl.DataFrame({"ticker": ["VCB"], "shares_outstanding": [10]})

    frame = build_fact_daily_price(sample_ohlcv().filter(pl.col("ticker") == "VCB"), company_shares=shares)
    rows = frame.sort("trading_date").to_dicts()

    assert rows[0]["market_cap"] == 1020.0
    assert rows[1]["market_cap"] == 1040.0
    assert rows[0]["price_change"] == 0.0
    assert rows[1]["price_change"] == 2.0
