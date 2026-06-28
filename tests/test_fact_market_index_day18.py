from datetime import date
from pathlib import Path

import polars as pl

from src.loaders.load_fact_market_index import (
    build_fact_market_index_from_index,
    build_index_breadth,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "ddl" / "fact_market_index.sql"


def sample_ohlcv() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["AAA", "AAM", "ACB", "A32", "AAA", "AAM", "ACB", "A32"],
            "date": [
                date(2026, 6, 10),
                date(2026, 6, 10),
                date(2026, 6, 10),
                date(2026, 6, 10),
                date(2026, 6, 11),
                date(2026, 6, 11),
                date(2026, 6, 11),
                date(2026, 6, 11),
            ],
            "open": [10.0, 20.0, 30.0, 40.0, 11.0, 19.0, 31.0, 41.0],
            "high": [12.0, 21.0, 32.0, 42.0, 12.0, 20.0, 33.0, 42.0],
            "low": [9.0, 18.0, 29.0, 39.0, 10.0, 18.0, 30.0, 40.0],
            "close": [11.0, 19.0, 30.0, 40.0, 10.0, 20.0, 32.0, 41.0],
            "volume": [100, 200, 300, 400, 110, 210, 310, 410],
        }
    )


def sample_company_profile() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["AAA", "AAM", "ACB", "A32"],
            "exchange": ["HOSE", "HOSE", "HNX", "UPCOM"],
            "shares_outstanding": [400, 300, 200, 100],
        }
    )


def sample_market_index() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "index_code": ["VNINDEX", "HNXINDEX", "UPCOMINDEX", "VN30"],
            "date": [date(2026, 6, 10)] * 4,
            "open": [1000.0, 200.0, 100.0, 1100.0],
            "high": [1010.0, 210.0, 105.0, 1110.0],
            "low": [990.0, 190.0, 95.0, 1090.0],
            "close": [1005.0, 205.0, 101.0, 1105.0],
            "volume": [1_000, 2_000, 3_000, 4_000],
        }
    )


def test_day18_fact_market_index_ddl_matches_scheme() -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")

    assert "index_id String" in ddl
    assert "advance_count UInt32" in ddl
    assert "decline_count UInt32" in ddl
    assert "unchanged_count UInt32" in ddl
    assert "advance_decline_ratio Float64" in ddl
    assert "PARTITION BY toYYYYMM(trading_date)" in ddl
    assert "ORDER BY (index_id, trading_date)" in ddl


def test_day18_build_index_breadth_by_exchange_and_vn30_demo() -> None:
    # HOSE-only scope: INDEX_EXCHANGE_MAP only maps HOSE -> VNINDEX, so HNX/UPCOM
    # tickers from sample_company_profile() no longer produce breadth rows.
    breadth = build_index_breadth(sample_ohlcv(), sample_company_profile())

    vnindex = breadth.filter(
        (pl.col("index_id") == "VNINDEX") & (pl.col("trading_date") == date(2026, 6, 10))
    ).row(0, named=True)

    assert vnindex["advance_count"] == 1
    assert vnindex["decline_count"] == 1
    assert set(breadth.get_column("index_id").unique().to_list()) == {"VNINDEX", "VN30"}


def test_day18_fact_market_index_joins_breadth_to_index_rows() -> None:
    breadth = build_index_breadth(sample_ohlcv(), sample_company_profile())
    frame = build_fact_market_index_from_index(sample_market_index(), breadth=breadth)

    # HOSE-only scope: build_fact_market_index_from_index keeps only VNINDEX/VN30
    # rows, even though sample_market_index() supplies 4 raw Silver index rows.
    assert frame.height == 2
    assert set(frame.get_column("index_id").to_list()) == {"VNINDEX", "VN30"}
    row = frame.filter(pl.col("index_id") == "VNINDEX").row(0, named=True)
    assert row["advance_count"] == 1
    assert row["decline_count"] == 1
    assert row["advance_decline_ratio"] == 1.0


def test_day18_build_index_breadth_uses_official_vn30_list_when_provided() -> None:
    # Only AAA and ACB are "official" VN30 members here; AAM/A32 must be excluded
    # even though the demo top-30-by-market-cap rule would have included them.
    breadth = build_index_breadth(sample_ohlcv(), sample_company_profile(), vn30_tickers=["AAA", "ACB"])

    vn30 = breadth.filter(pl.col("index_id") == "VN30")
    assert vn30.height == 2  # one row per trading_date
    total_members = vn30["advance_count"] + vn30["decline_count"] + vn30["unchanged_count"]
    assert total_members.to_list() == [2, 2]
