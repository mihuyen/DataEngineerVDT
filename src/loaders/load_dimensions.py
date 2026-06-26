from __future__ import annotations

from datetime import date
from datetime import datetime
from pathlib import Path
from zlib import crc32

import polars as pl

from src.common.clickhouse_client import insert_dataframe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
DEFAULT_SECTOR_MAPPING_PATH = PROJECT_ROOT / "configs" / "sector_mapping.csv"


def make_stock_id(ticker: str) -> int:
    """Create a stable numeric stock id from a ticker."""
    return crc32(ticker.upper().encode("utf-8")) & 0xFFFFFFFF


def make_index_id(index_code: str) -> int:
    """Create a stable numeric index id from an index code."""
    return sum((index + 1) * ord(char) for index, char in enumerate(index_code.upper()))


def load_sector_mapping(mapping_path: Path = DEFAULT_SECTOR_MAPPING_PATH) -> pl.DataFrame:
    """Load curated ticker-to-sector mapping for dashboard-friendly sectors."""
    if not mapping_path.exists():
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "sector_id": pl.Utf8,
                "sector_name": pl.Utf8,
                "industry_group": pl.Utf8,
            }
        )

    return (
        pl.read_csv(mapping_path)
        .with_columns(
            pl.col("ticker").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
            pl.col("sector_id").cast(pl.Utf8).str.strip_chars().str.to_uppercase(),
            pl.col("sector_name").cast(pl.Utf8).str.strip_chars(),
            pl.col("industry_group").cast(pl.Utf8).str.strip_chars(),
        )
        .filter(
            pl.col("ticker").is_not_null()
            & (pl.col("ticker").str.len_chars() > 0)
            & pl.col("sector_id").is_not_null()
            & (pl.col("sector_id").str.len_chars() > 0)
            & pl.col("sector_name").is_not_null()
            & (pl.col("sector_name").str.len_chars() > 0)
        )
        .unique(subset=["ticker"], keep="first", maintain_order=True)
    )


def standardize_coarse_sector_expr(sector_expr: pl.Expr) -> pl.Expr:
    """Map coarse legal company types to dashboard-friendly fallback sectors."""
    return (
        pl.when(sector_expr == "CÔNG_TY_CHỨNG_KHOÁN")
        .then(pl.lit("CHUNG_KHOAN"))
        .when(sector_expr == "CÔNG_TY_BẢO_HIỂM")
        .then(pl.lit("BAO_HIEM"))
        .when(sector_expr == "CÔNG_TY_QUẢN_LÝ_QUỸ")
        .then(pl.lit("TAI_CHINH_KHAC"))
        .when(sector_expr == "CÔNG_TY_CỔ_PHẦN")
        .then(pl.lit("KHAC"))
        .otherwise(sector_expr)
    )


def build_dim_date(start: date = date(2020, 1, 1), end: date = date(2030, 12, 31)) -> pl.DataFrame:
    """Build calendar dimension rows."""
    return (
        pl.date_range(start, end, interval="1d", eager=True)
        .to_frame("date")
        .with_columns(
            (pl.col("date").dt.strftime("%Y%m%d").cast(pl.UInt32)).alias("date_id"),
            pl.col("date").dt.year().cast(pl.UInt16).alias("year"),
            pl.col("date").dt.quarter().cast(pl.UInt8).alias("quarter"),
            pl.col("date").dt.month().cast(pl.UInt8).alias("month"),
            pl.col("date").dt.week().cast(pl.UInt8).alias("week"),
            pl.col("date").dt.strftime("%A").alias("day_of_week"),
            (~pl.col("date").dt.weekday().is_in([6, 7])).cast(pl.UInt8).alias("is_trading_day"),
        )
        .select(
            "date_id",
            "date",
            "year",
            "quarter",
            "month",
            "week",
            "day_of_week",
            "is_trading_day",
        )
    )


def build_dim_sector(company_frame: pl.DataFrame | None = None) -> pl.DataFrame:
    """Build sector dimension from company data or a default unknown sector."""
    sector_mapping = load_sector_mapping()

    if company_frame is None or company_frame.is_empty() or "sector_name" not in company_frame.columns:
        default_frame = pl.DataFrame(
            {
                "sector_id": ["UNKNOWN"],
                "sector_name": ["Unknown"],
                "industry_group": ["Unknown"],
                "description": ["Unknown sector"],
            }
        )
        if sector_mapping.is_empty():
            return default_frame
        mapped_frame = sector_mapping.select("sector_id", "sector_name", "industry_group").unique()
        return (
            pl.concat(
                [
                    default_frame,
                    mapped_frame.with_columns((pl.lit("Nhóm ngành ") + pl.col("sector_name")).alias("description")),
                ],
                how="diagonal_relaxed",
            )
            .unique(subset=["sector_id"], keep="first")
            .sort("sector_id")
        )

    company_sectors = (
        company_frame.select(pl.col("sector_name").fill_null("Unknown").str.strip_chars())
        .unique()
        .with_columns(
            pl.when(pl.col("sector_name") == "")
            .then(pl.lit("Unknown"))
            .otherwise(pl.col("sector_name"))
            .alias("sector_name")
        )
        .with_columns(pl.col("sector_name").str.to_uppercase().str.replace_all(" ", "_").alias("sector_id"))
        .with_columns(
            pl.col("sector_name").alias("industry_group"),
            (pl.lit("Nhóm ngành ") + pl.col("sector_name")).alias("description"),
        )
        .select("sector_id", "sector_name", "industry_group", "description")
        .sort("sector_id")
    )
    if sector_mapping.is_empty():
        return company_sectors

    mapped_sectors = (
        sector_mapping.select("sector_id", "sector_name", "industry_group")
        .unique(subset=["sector_id"], keep="first")
        .with_columns((pl.lit("Nhóm ngành ") + pl.col("sector_name")).alias("description"))
        .select("sector_id", "sector_name", "industry_group", "description")
    )
    return (
        pl.concat([mapped_sectors, company_sectors], how="diagonal_relaxed")
        .unique(subset=["sector_id"], keep="first")
        .sort("sector_id")
    )


def build_dim_stock(company_frame: pl.DataFrame | None = None, tickers: list[str] | None = None) -> pl.DataFrame:
    """Build stock dimension from company profile data or a ticker list."""
    now = datetime.now()
    sector_mapping = load_sector_mapping()
    if company_frame is not None and not company_frame.is_empty():
        frame = company_frame
        if "sector_name" in frame.columns and "sector_id" not in frame.columns:
            frame = frame.with_columns(
                pl.col("sector_name").fill_null("Unknown").str.to_uppercase().str.replace_all(" ", "_").alias(
                    "sector_id"
                )
            )
        if not sector_mapping.is_empty():
            frame = frame.join(
                sector_mapping.select(
                    "ticker",
                    pl.col("sector_id").alias("mapped_sector_id"),
                ),
                on="ticker",
                how="left",
            ).with_columns(
                pl.coalesce(
                    "mapped_sector_id",
                    standardize_coarse_sector_expr(pl.col("sector_id")),
                ).alias("sector_id")
            )
        else:
            frame = frame.with_columns(standardize_coarse_sector_expr(pl.col("sector_id")).alias("sector_id"))
        return (
            frame.with_columns(
                pl.col("ticker").str.to_uppercase(),
                pl.col("company_name").fill_null(pl.col("ticker")).alias("company_name"),
                pl.col("exchange").fill_null("UNKNOWN").alias("exchange"),
                pl.col("sector_id").fill_null("UNKNOWN").alias("sector_id"),
                pl.lit(None, dtype=pl.Date).alias("listed_date"),
                pl.lit("ACTIVE").alias("status"),
                pl.col("shares_outstanding").fill_null(0).cast(pl.UInt64).alias("shares_outstanding"),
                pl.lit(None, dtype=pl.Float64).alias("free_float_rate"),
                pl.col("market_cap_latest").cast(pl.Float64).alias("market_cap_latest"),
                pl.lit(None, dtype=pl.Float64).alias("pe_latest"),
                pl.lit(None, dtype=pl.Float64).alias("eps_latest"),
                pl.lit(None, dtype=pl.Float64).alias("roe_latest"),
                pl.lit(None, dtype=pl.Float64).alias("roa_latest"),
                pl.lit(now, dtype=pl.Datetime).alias("updated_at"),
            )
            .select(
                "ticker",
                "company_name",
                "exchange",
                "sector_id",
                "listed_date",
                "status",
                "shares_outstanding",
                "free_float_rate",
                "market_cap_latest",
                "pe_latest",
                "eps_latest",
                "roe_latest",
                "roa_latest",
                "updated_at",
            )
            .unique(subset=["ticker"], keep="last")
            .sort("ticker")
        )

    values = tickers or ["VCB"]
    frame = pl.DataFrame({"ticker": [ticker.upper() for ticker in values]})
    if not sector_mapping.is_empty():
        frame = frame.join(
            sector_mapping.select("ticker", pl.col("sector_id").alias("mapped_sector_id")),
            on="ticker",
            how="left",
        )
    else:
        frame = frame.with_columns(pl.lit(None, dtype=pl.Utf8).alias("mapped_sector_id"))

    return frame.with_columns(
        pl.col("ticker").alias("company_name"),
        pl.lit("UNKNOWN").alias("exchange"),
        pl.coalesce("mapped_sector_id", pl.lit("UNKNOWN")).alias("sector_id"),
        pl.lit(None, dtype=pl.Date).alias("listed_date"),
        pl.lit("ACTIVE").alias("status"),
        pl.lit(0, dtype=pl.UInt64).alias("shares_outstanding"),
        pl.lit(None, dtype=pl.Float64).alias("free_float_rate"),
        pl.lit(None, dtype=pl.Float64).alias("market_cap_latest"),
        pl.lit(None, dtype=pl.Float64).alias("pe_latest"),
        pl.lit(None, dtype=pl.Float64).alias("eps_latest"),
        pl.lit(None, dtype=pl.Float64).alias("roe_latest"),
        pl.lit(None, dtype=pl.Float64).alias("roa_latest"),
        pl.lit(now, dtype=pl.Datetime).alias("updated_at"),
    ).select(
        "ticker",
        "company_name",
        "exchange",
        "sector_id",
        "listed_date",
        "status",
        "shares_outstanding",
        "free_float_rate",
        "market_cap_latest",
        "pe_latest",
        "eps_latest",
        "roe_latest",
        "roa_latest",
        "updated_at",
    )


def build_dim_index() -> pl.DataFrame:
    """Build static market index dimension."""
    records = [
        {
            "index_id": "VNINDEX",
            "index_name": "VN-Index",
            "exchange": "HOSE",
            "description": "Chỉ số đại diện Sở Giao dịch Chứng khoán TP.HCM",
        },
        {
            "index_id": "VN30",
            "index_name": "VN30",
            "exchange": "HOSE",
            "description": "Chỉ số nhóm 30 cổ phiếu vốn hóa và thanh khoản cao trên HOSE",
        },
    ]
    return pl.DataFrame(records).select("index_id", "index_name", "exchange", "description")


def load_dim_date(client: object) -> pl.DataFrame:
    """Load dim_date into ClickHouse."""
    frame = build_dim_date()
    insert_dataframe(client, "dim_date", frame)  # type: ignore[arg-type]
    return frame


def load_dim_sector(client: object, company_frame: pl.DataFrame | None = None) -> pl.DataFrame:
    """Load dim_sector into ClickHouse."""
    frame = build_dim_sector(company_frame)
    insert_dataframe(client, "dim_sector", frame)  # type: ignore[arg-type]
    return frame


def load_dim_stock(
    client: object,
    company_frame: pl.DataFrame | None = None,
    tickers: list[str] | None = None,
) -> pl.DataFrame:
    """Load dim_stock into ClickHouse."""
    frame = build_dim_stock(company_frame=company_frame, tickers=tickers)
    insert_dataframe(client, "dim_stock", frame)  # type: ignore[arg-type]
    return frame


def load_dim_index(client: object) -> pl.DataFrame:
    """Load dim_index into ClickHouse."""
    frame = build_dim_index()
    insert_dataframe(client, "dim_index", frame)  # type: ignore[arg-type]
    return frame
