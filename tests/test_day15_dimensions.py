from pathlib import Path

import polars as pl

from scripts.load_dimensions import (
    DIMENSION_DDL_FILES,
    DIMENSION_TABLES,
    load_silver_tickers,
)
from src.loaders.load_dimensions import build_dim_index, build_dim_stock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = PROJECT_ROOT / "sql" / "ddl"


def test_day15_dimension_tables_are_explicit() -> None:
    assert DIMENSION_TABLES == ["dim_date", "dim_sector", "dim_stock", "dim_index"]
    assert DIMENSION_DDL_FILES == [
        "dim_date.sql",
        "dim_sector.sql",
        "dim_stock.sql",
        "dim_index.sql",
    ]


def test_day15_dimension_ddl_uses_mergetree_and_order_keys() -> None:
    expected_order_keys = {
        "dim_date.sql": "ORDER BY date_id",
        "dim_sector.sql": "ORDER BY sector_id",
        "dim_stock.sql": "ORDER BY ticker",
        "dim_index.sql": "ORDER BY index_id",
    }

    for ddl_file_name, order_key in expected_order_keys.items():
        ddl = (DDL_DIR / ddl_file_name).read_text(encoding="utf-8")
        assert "ENGINE = MergeTree" in ddl
        assert order_key in ddl


def test_day15_dim_stock_prefers_company_profile_data() -> None:
    company_profile = pl.DataFrame(
        {
            "ticker": ["VCB", "FPT"],
            "company_name": ["Vietcombank", "FPT"],
            "exchange": ["HOSE", "HOSE"],
            "sector_id": ["NGAN_HANG", "CONG_NGHE"],
            "shares_outstanding": [8_355_675_094, 1_703_507_121],
            "market_cap_latest": [0.0, 0.0],
        }
    )

    frame = build_dim_stock(company_frame=company_profile, tickers=["VCB"])

    assert frame.height == 2
    assert set(frame["ticker"].to_list()) == {"VCB", "FPT"}
    assert frame["ticker"].n_unique() == 2


def test_day15_dim_index_contains_vietnam_market_indexes() -> None:
    frame = build_dim_index()

    # HOSE-only scope: HNXINDEX/UPCOMINDEX were dropped once ingestion narrowed to HOSE.
    assert set(frame["index_id"].to_list()) == {"VNINDEX", "VN30"}


def test_day15_load_silver_tickers_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    assert load_silver_tickers(tmp_path) == []
