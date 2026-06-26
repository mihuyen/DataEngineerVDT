from __future__ import annotations

from pathlib import Path
from datetime import datetime

import polars as pl

from src.common.clickhouse_client import insert_dataframe


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"


def load_silver_ohlcv(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame:
    """Load local Silver OHLCV parquet files."""
    files = sorted((local_silver_dir / "ohlcv").glob("ticker=*/year=*/month=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"No Silver OHLCV parquet files found under {local_silver_dir}")
    frame = pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")

    company_profile_files = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not company_profile_files:
        return frame

    company_profile = pl.concat(
        [pl.read_parquet(file_path) for file_path in company_profile_files],
        how="diagonal_relaxed",
    )
    if not {"ticker", "exchange"}.issubset(company_profile.columns):
        return frame

    hose_tickers = (
        company_profile.select(
            pl.col("ticker").cast(pl.Utf8).str.to_uppercase(),
            pl.col("exchange").cast(pl.Utf8).str.to_uppercase(),
        )
        .filter(pl.col("exchange") == "HOSE")
        .get_column("ticker")
        .unique()
        .to_list()
    )
    if not hose_tickers:
        return frame

    return frame.with_columns(pl.col("ticker").str.to_uppercase()).filter(pl.col("ticker").is_in(hose_tickers))


def add_technical_indicators(frame: pl.DataFrame) -> pl.DataFrame:
    """Add common technical indicators using Polars."""
    return (
        frame.sort(["ticker", "date"])
        .with_columns(
            pl.col("close").rolling_mean(window_size=20).over("ticker").alias("sma_20"),
            pl.col("close").ewm_mean(span=12, adjust=False).over("ticker").alias("ema_12"),
            pl.col("close").ewm_mean(span=26, adjust=False).over("ticker").alias("ema_26"),
            pl.col("volume").rolling_mean(window_size=20).over("ticker").alias("volume_sma_20"),
            pl.col("close").rolling_std(window_size=20).over("ticker").alias("bb_std20"),
            pl.col("close").diff().over("ticker").alias("price_delta"),
        )
        .with_columns(
            (pl.col("ema_12") - pl.col("ema_26")).alias("macd"),
            pl.col("sma_20").alias("bb_middle"),
            (pl.col("sma_20") + (pl.col("bb_std20") * 2)).alias("bb_upper"),
            (pl.col("sma_20") - (pl.col("bb_std20") * 2)).alias("bb_lower"),
            pl.when(pl.col("price_delta") > 0)
            .then(pl.col("price_delta"))
            .otherwise(0.0)
            .alias("rsi_gain"),
            pl.when(pl.col("price_delta") < 0)
            .then(-pl.col("price_delta"))
            .otherwise(0.0)
            .alias("rsi_loss"),
        )
        .with_columns(
            pl.col("macd").ewm_mean(span=9, adjust=False).over("ticker").alias("macd_signal"),
            pl.col("rsi_gain").rolling_mean(window_size=14).over("ticker").alias("avg_gain14"),
            pl.col("rsi_loss").rolling_mean(window_size=14).over("ticker").alias("avg_loss14"),
        )
        .with_columns(
            pl.when(pl.col("avg_loss14") == 0)
            .then(100.0)
            .otherwise(100 - (100 / (1 + (pl.col("avg_gain14") / pl.col("avg_loss14")))))
            .alias("rsi_14")
        )
        .drop("bb_std20", "price_delta", "rsi_gain", "rsi_loss", "avg_gain14", "avg_loss14")
    )


def load_silver_company_shares(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame | None:
    """Load ticker and shares_outstanding from Silver company profile if available."""
    files = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not files:
        return None
    frame = pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")
    if not {"ticker", "shares_outstanding"}.issubset(frame.columns):
        return None
    return frame.select(
        pl.col("ticker").str.to_uppercase(),
        pl.col("shares_outstanding").fill_null(0).cast(pl.UInt64),
    ).unique(subset=["ticker"], keep="last")


def build_fact_daily_price(
    silver_ohlcv: pl.DataFrame,
    company_shares: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build fact_daily_price from Silver OHLCV data."""
    now = datetime.now()
    frame = add_technical_indicators(silver_ohlcv).with_columns(pl.col("ticker").str.to_uppercase())
    if company_shares is not None and not company_shares.is_empty():
        frame = frame.join(company_shares, on="ticker", how="left")
    else:
        frame = frame.with_columns(pl.lit(0, dtype=pl.UInt64).alias("shares_outstanding"))

    return (
        frame
        .with_columns(
            pl.col("date").alias("trading_date"),
            pl.col("date").dt.strftime("%Y%m%d").cast(pl.UInt32).alias("date_id"),
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64),
            pl.col("volume").cast(pl.UInt64),
            pl.col("shares_outstanding").fill_null(0).cast(pl.UInt64),
            ((pl.col("open") + pl.col("high") + pl.col("low") + pl.col("close")) / 4 * pl.col("volume")).alias(
                "value"
            ),
            (pl.col("close") * pl.col("shares_outstanding").fill_null(0)).alias("market_cap"),
            pl.col("close").diff().over("ticker").fill_null(0).alias("price_change"),
            (
                (pl.col("close") - pl.col("close").shift(1).over("ticker"))
                / pl.col("close").shift(1).over("ticker")
                * 100
            )
            .fill_null(0)
            .alias("pct_change"),
            (pl.col("rsi_14") > 70).fill_null(False).cast(pl.UInt8).alias("overbought_flag"),
            (pl.col("rsi_14") < 30).fill_null(False).cast(pl.UInt8).alias("oversold_flag"),
            (pl.col("close") > pl.col("bb_upper")).fill_null(False).cast(pl.UInt8).alias("breakout_flag"),
            (pl.col("close") < pl.col("bb_lower")).fill_null(False).cast(pl.UInt8).alias("breakdown_flag"),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
            pl.lit(now, dtype=pl.Datetime).alias("updated_at"),
        )
        .select(
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
        )
        .sort(["ticker", "trading_date"])
    )


def load_fact_daily_price(
    client: object,
    silver_ohlcv: pl.DataFrame | None = None,
    company_shares: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Load fact_daily_price into ClickHouse."""
    source = silver_ohlcv if silver_ohlcv is not None else load_silver_ohlcv()
    shares = company_shares if company_shares is not None else load_silver_company_shares()
    frame = build_fact_daily_price(source, company_shares=shares)
    insert_dataframe(client, "fact_daily_price", frame)  # type: ignore[arg-type]
    return frame
