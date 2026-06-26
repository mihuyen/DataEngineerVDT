from datetime import date

import polars as pl

from src.loaders.load_dimensions import (
    build_dim_date,
    build_dim_index,
    build_dim_sector,
    build_dim_stock,
    make_stock_id,
)
from src.loaders.load_fact_daily_price import build_fact_daily_price
from src.loaders.load_fact_market_index import build_fact_market_index, build_fact_market_index_from_index


def sample_silver_ohlcv() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "VCB", "VCB", "FPT"],
            "date": [date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 10), date(2026, 6, 10)],
            "open": [100.0, 101.0, 102.0, 90.0],
            "high": [105.0, 106.0, 107.0, 95.0],
            "low": [99.0, 100.0, 101.0, 88.0],
            "close": [102.0, 103.0, 104.0, 89.0],
            "volume": [1_000_000, 1_100_000, 1_200_000, 900_000],
        }
    )


def test_build_dim_date_generates_calendar_rows() -> None:
    frame = build_dim_date(start=date(2026, 6, 10), end=date(2026, 6, 12))

    assert frame.height == 3
    assert frame["date_id"].to_list() == [20260610, 20260611, 20260612]


def test_build_dim_sector_from_company_data() -> None:
    company = pl.DataFrame({"sector_name": ["Banking", "Technology", "Banking"]})

    frame = build_dim_sector(company)

    assert {"BANKING", "TECHNOLOGY"}.issubset(set(frame["sector_id"].to_list()))
    assert {"industry_group", "description"}.issubset(frame.columns)


def test_build_dim_stock_from_tickers() -> None:
    frame = build_dim_stock(tickers=["VCB", "FPT"])

    assert frame.height == 2
    assert set(frame["ticker"].to_list()) == {"VCB", "FPT"}
    assert {"listed_date", "status", "free_float_rate", "updated_at"}.issubset(frame.columns)


def test_make_stock_id_has_no_collision_for_common_ticker_shape() -> None:
    tickers = ["A32", "AAA", "AAH", "VCB", "VIC", "VND", "YBM", "YEG", "YTC"]
    stock_ids = [make_stock_id(ticker) for ticker in tickers]

    assert len(stock_ids) == len(set(stock_ids))


def test_build_dim_index_static_values() -> None:
    frame = build_dim_index()

    assert frame.height == 2
    assert set(frame["index_id"].to_list()) == {"VNINDEX", "VN30"}
    assert set(frame["exchange"].to_list()) == {"HOSE"}
    assert {"index_name", "exchange", "description"}.issubset(frame.columns)


def test_build_fact_daily_price_maps_keys_and_indicators() -> None:
    frame = build_fact_daily_price(sample_silver_ohlcv())

    assert frame.height == 4
    assert {
        "date_id",
        "ticker",
        "trading_date",
        "value",
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
    }.issubset(frame.columns)
    assert frame.filter(pl.col("ticker") == "VCB").height == 3


def test_build_fact_market_index_aggregates_counts() -> None:
    frame = build_fact_market_index(sample_silver_ohlcv())

    assert frame.height == 3
    row = frame.filter(pl.col("date_id") == 20260610).row(0, named=True)
    assert row["advance_count"] == 1
    assert row["decline_count"] == 1


def test_build_fact_market_index_from_actual_index_data() -> None:
    market_index = pl.DataFrame(
        {
            "index_code": ["VNINDEX", "UPCOMINDEX"],
            "date": [date(2026, 6, 10), date(2026, 6, 10)],
            "open": [1000.0, 100.0],
            "high": [1010.0, 101.0],
            "low": [990.0, 99.0],
            "close": [1005.0, 100.5],
            "volume": [1_000_000, 200_000],
        }
    )

    frame = build_fact_market_index_from_index(market_index)

    assert frame.height == 1
    assert frame["index_id"].to_list() == ["VNINDEX"]
    assert {"open_point", "close_point", "advance_decline_ratio", "created_at"}.issubset(frame.columns)
