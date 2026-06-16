from __future__ import annotations

from pathlib import Path
from datetime import datetime

import polars as pl

from src.common.clickhouse_client import insert_dataframe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
INDEX_EXCHANGE_MAP = {
    "HOSE": "VNINDEX",
    "HNX": "HNXINDEX",
    "UPCOM": "UPCOMINDEX",
}
MARKET_INDEX_COLUMNS = [
    "index_id",
    "date_id",
    "trading_date",
    "open_point",
    "high_point",
    "low_point",
    "close_point",
    "point_change",
    "pct_change",
    "total_volume",
    "total_value",
    "advance_count",
    "decline_count",
    "unchanged_count",
    "advance_decline_ratio",
    "sma_20",
    "rsi_14",
    "created_at",
]


def load_silver_market_index(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame:
    """Load local Silver market index parquet files."""
    files = sorted((local_silver_dir / "market_index").glob("year=*/month=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"No Silver market index parquet files found under {local_silver_dir}")
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def load_silver_company_profile(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame | None:
    """Load Silver company profile data for index breadth mapping."""
    files = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not files:
        return None
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def _with_index_rsi(frame: pl.DataFrame) -> pl.DataFrame:
    """Add a simple RSI14 over index close points."""
    return (
        frame.sort(["index_id", "trading_date"])
        .with_columns(pl.col("close_point").diff().over("index_id").alias("point_delta"))
        .with_columns(
            pl.when(pl.col("point_delta") > 0).then(pl.col("point_delta")).otherwise(0.0).alias("rsi_gain"),
            pl.when(pl.col("point_delta") < 0).then(-pl.col("point_delta")).otherwise(0.0).alias("rsi_loss"),
        )
        .with_columns(
            pl.col("rsi_gain").rolling_mean(window_size=14).over("index_id").alias("avg_gain14"),
            pl.col("rsi_loss").rolling_mean(window_size=14).over("index_id").alias("avg_loss14"),
        )
        .with_columns(
            pl.when(pl.col("avg_loss14") == 0)
            .then(100.0)
            .otherwise(100 - (100 / (1 + (pl.col("avg_gain14") / pl.col("avg_loss14")))))
            .alias("rsi_14")
        )
        .drop("point_delta", "rsi_gain", "rsi_loss", "avg_gain14", "avg_loss14")
    )


def build_index_breadth(
    silver_ohlcv: pl.DataFrame,
    company_profile: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build advance/decline breadth by market index from stock-level OHLCV."""
    if company_profile is None or company_profile.is_empty():
        return pl.DataFrame(
            schema={
                "index_id": pl.Utf8,
                "trading_date": pl.Date,
                "advance_count": pl.UInt32,
                "decline_count": pl.UInt32,
                "unchanged_count": pl.UInt32,
                "advance_decline_ratio": pl.Float64,
            }
        )

    company = company_profile.select(
        pl.col("ticker").str.to_uppercase(),
        pl.col("exchange").str.to_uppercase(),
        pl.col("shares_outstanding").fill_null(0).cast(pl.UInt64),
    ).unique(subset=["ticker"], keep="last")

    exchange_members = (
        silver_ohlcv.with_columns(pl.col("ticker").str.to_uppercase())
        .join(company.select("ticker", "exchange"), on="ticker", how="left")
        .with_columns(pl.col("exchange").replace_strict(INDEX_EXCHANGE_MAP, default=None).alias("index_id"))
        .filter(pl.col("index_id").is_not_null())
    )

    vn30_tickers = (
        company.filter(pl.col("exchange") == "HOSE")
        .sort("shares_outstanding", descending=True)
        .head(30)
        .select("ticker")
    )
    vn30_members = (
        silver_ohlcv.with_columns(pl.col("ticker").str.to_uppercase())
        .join(vn30_tickers, on="ticker", how="inner")
        .with_columns(pl.lit("VN30").alias("index_id"))
    )

    members = pl.concat([exchange_members, vn30_members], how="diagonal_relaxed")
    if members.is_empty():
        return pl.DataFrame(
            schema={
                "index_id": pl.Utf8,
                "trading_date": pl.Date,
                "advance_count": pl.UInt32,
                "decline_count": pl.UInt32,
                "unchanged_count": pl.UInt32,
                "advance_decline_ratio": pl.Float64,
            }
        )

    return (
        members.with_columns(
            pl.col("date").alias("trading_date"),
            (pl.col("close") > pl.col("open")).cast(pl.UInt8).alias("is_advancing"),
            (pl.col("close") < pl.col("open")).cast(pl.UInt8).alias("is_declining"),
            (pl.col("close") == pl.col("open")).cast(pl.UInt8).alias("is_unchanged"),
        )
        .group_by(["index_id", "trading_date"])
        .agg(
            pl.sum("is_advancing").cast(pl.UInt32).alias("advance_count"),
            pl.sum("is_declining").cast(pl.UInt32).alias("decline_count"),
            pl.sum("is_unchanged").cast(pl.UInt32).alias("unchanged_count"),
        )
        .with_columns(
            pl.when(pl.col("decline_count") == 0)
            .then(pl.col("advance_count").cast(pl.Float64))
            .otherwise(pl.col("advance_count") / pl.col("decline_count"))
            .alias("advance_decline_ratio")
        )
        .sort(["index_id", "trading_date"])
    )


def build_fact_market_index_from_index(
    silver_market_index: pl.DataFrame,
    breadth: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build fact_market_index from Silver market index OHLCV data."""
    now = datetime.now()
    frame = (
        silver_market_index.sort(["index_code", "date"])
        .with_columns(
            pl.col("index_code").str.to_uppercase().alias("index_id"),
            pl.col("date").alias("trading_date"),
            pl.col("date").dt.strftime("%Y%m%d").cast(pl.UInt32).alias("date_id"),
            pl.col("open").cast(pl.Float64).alias("open_point"),
            pl.col("high").cast(pl.Float64).alias("high_point"),
            pl.col("low").cast(pl.Float64).alias("low_point"),
            pl.col("close").cast(pl.Float64).alias("close_point"),
            pl.col("volume").cast(pl.UInt64).alias("total_volume"),
            ((pl.col("open") + pl.col("high") + pl.col("low") + pl.col("close")) / 4 * pl.col("volume")).alias(
                "total_value"
            ),
            pl.col("close").rolling_mean(window_size=20).over("index_code").alias("sma_20"),
            pl.col("close").diff().over("index_code").fill_null(0).alias("point_change"),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
        )
        .with_columns(
            (
                pl.col("point_change")
                / (pl.col("close_point") - pl.col("point_change"))
                * 100
            )
            .fill_nan(0)
            .fill_null(0)
            .alias("pct_change"),
        )
    )
    frame = _with_index_rsi(frame)

    if breadth is not None and not breadth.is_empty():
        frame = frame.join(breadth, on=["index_id", "trading_date"], how="left")
    else:
        frame = frame.with_columns(
            pl.lit(0, dtype=pl.UInt32).alias("advance_count"),
            pl.lit(0, dtype=pl.UInt32).alias("decline_count"),
            pl.lit(0, dtype=pl.UInt32).alias("unchanged_count"),
            pl.lit(0.0).alias("advance_decline_ratio"),
        )

    return (
        frame.with_columns(
            pl.col("advance_count").fill_null(0).cast(pl.UInt32),
            pl.col("decline_count").fill_null(0).cast(pl.UInt32),
            pl.col("unchanged_count").fill_null(0).cast(pl.UInt32),
            pl.col("advance_decline_ratio").fill_null(0).cast(pl.Float64),
        )
        .select(
            MARKET_INDEX_COLUMNS,
        )
        .unique(subset=["index_id", "date_id"], keep="last")
        .sort(["index_id", "date_id"])
    )


def build_fact_market_index(silver_ohlcv: pl.DataFrame, index_code: str = "VNINDEX") -> pl.DataFrame:
    """Build a v1 market index fact from stock-level Silver OHLCV data."""
    now = datetime.now()
    index_id = index_code.upper()
    return (
        silver_ohlcv.with_columns(
            pl.col("date").alias("trading_date"),
            (pl.col("close") > pl.col("open")).cast(pl.UInt8).alias("is_advancing"),
            (pl.col("close") < pl.col("open")).cast(pl.UInt8).alias("is_declining"),
            (pl.col("close") == pl.col("open")).cast(pl.UInt8).alias("is_unchanged"),
        )
        .group_by("trading_date")
        .agg(
            pl.mean("open").alias("open_point"),
            pl.max("high").alias("high_point"),
            pl.min("low").alias("low_point"),
            pl.mean("close").alias("close_point"),
            pl.sum("volume").cast(pl.UInt64).alias("total_volume"),
            ((pl.col("close") * pl.col("volume")).sum()).alias("total_value"),
            pl.sum("is_advancing").cast(pl.UInt32).alias("advance_count"),
            pl.sum("is_declining").cast(pl.UInt32).alias("decline_count"),
            pl.sum("is_unchanged").cast(pl.UInt32).alias("unchanged_count"),
        )
        .with_columns(
            pl.col("trading_date").dt.strftime("%Y%m%d").cast(pl.UInt32).alias("date_id"),
            pl.lit(index_id).alias("index_id"),
            pl.col("close_point").diff().fill_null(0).alias("point_change"),
            pl.col("close_point").rolling_mean(window_size=20).alias("sma_20"),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
        )
        .with_columns(
            (
                pl.col("point_change")
                / (pl.col("close_point") - pl.col("point_change"))
                * 100
            )
            .fill_nan(0)
            .fill_null(0)
            .alias("pct_change"),
            pl.when(pl.col("decline_count") == 0)
            .then(pl.col("advance_count").cast(pl.Float64))
            .otherwise(pl.col("advance_count") / pl.col("decline_count"))
            .alias("advance_decline_ratio"),
        )
        .pipe(_with_index_rsi)
        .select(MARKET_INDEX_COLUMNS)
        .sort(["index_id", "date_id"])
    )


def load_fact_market_index(
    client: object,
    silver_ohlcv: pl.DataFrame | None = None,
    silver_market_index: pl.DataFrame | None = None,
    company_profile: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Load fact_market_index into ClickHouse."""
    if silver_market_index is not None:
        breadth = build_index_breadth(silver_ohlcv, company_profile) if silver_ohlcv is not None else None
        frame = build_fact_market_index_from_index(silver_market_index, breadth=breadth)
    else:
        try:
            market_index = load_silver_market_index()
            profile = company_profile if company_profile is not None else load_silver_company_profile()
            breadth = build_index_breadth(silver_ohlcv, profile) if silver_ohlcv is not None else None
            frame = build_fact_market_index_from_index(market_index, breadth=breadth)
        except FileNotFoundError:
            if silver_ohlcv is None:
                raise
            frame = build_fact_market_index(silver_ohlcv)
    insert_dataframe(client, "fact_market_index", frame)  # type: ignore[arg-type]
    return frame
