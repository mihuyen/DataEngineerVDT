from __future__ import annotations

from datetime import date, datetime, time, timedelta

import polars as pl

from src.common.clickhouse_client import insert_dataframe


REALTIME_VWAP_COLUMNS = [
    "ticker",
    "minute_ts",
    "trading_date",
    "data_source",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "vwap_1m",
    "session_vwap",
    "total_volume",
    "total_value",
    "session_volume",
    "session_value",
    "avg_price",
    "trade_count",
    "price_vs_vwap_pct",
    "price_vs_session_vwap_pct",
    "created_at",
]


def generate_demo_trade_ticks(
    tickers: list[str] | None = None,
    trading_date: date | None = None,
    minutes: int = 10,
    trades_per_minute: int = 4,
) -> pl.DataFrame:
    """Generate deterministic intraday trade ticks for a realtime VWAP demo."""
    selected_tickers = tickers or ["VCB", "FPT", "HPG"]
    session_date = trading_date or date.today()
    session_start = datetime.combine(session_date, time(hour=9, minute=15))

    rows = []
    for ticker_index, ticker in enumerate(selected_tickers):
        base_price = 50_000 + ticker_index * 8_000
        for minute_offset in range(minutes):
            for trade_index in range(trades_per_minute):
                trade_ts = session_start + timedelta(
                    minutes=minute_offset, seconds=trade_index * 12
                )
                price = base_price + minute_offset * 120 + trade_index * 15 + ticker_index * 10
                volume = 100 + ticker_index * 25 + minute_offset * 5 + trade_index * 10
                rows.append(
                    {
                        "ticker": ticker.upper(),
                        "trade_ts": trade_ts,
                        "price": float(price),
                        "volume": int(volume),
                        "data_source": "DEMO",
                    }
                )

    return pl.DataFrame(rows)


def build_fact_realtime_vwap(trade_ticks: pl.DataFrame) -> pl.DataFrame:
    """Aggregate trade ticks into minute-level realtime VWAP rows."""
    required = {"ticker", "trade_ts", "price", "volume"}
    missing = required.difference(trade_ticks.columns)
    if missing:
        raise ValueError(f"Realtime ticks missing columns: {', '.join(sorted(missing))}")

    now = datetime.now()
    if "data_source" not in trade_ticks.columns:
        trade_ticks = trade_ticks.with_columns(pl.lit("UNKNOWN").alias("data_source"))
    minute_bars = (
        trade_ticks.sort(["data_source", "ticker", "trade_ts"])
        .with_columns(
            pl.col("ticker").str.to_uppercase(),
            pl.col("data_source").cast(pl.String).str.to_uppercase(),
            pl.col("trade_ts").dt.truncate("1m").alias("minute_ts"),
            pl.col("trade_ts").dt.date().alias("trading_date"),
            (pl.col("price") * pl.col("volume")).alias("trade_value"),
        )
        .group_by(["data_source", "ticker", "trading_date", "minute_ts"], maintain_order=True)
        .agg(
            pl.col("price").first().alias("open_price"),
            pl.col("price").max().alias("high_price"),
            pl.col("price").min().alias("low_price"),
            pl.col("price").last().alias("close_price"),
            pl.sum("volume").cast(pl.UInt64).alias("total_volume"),
            pl.sum("trade_value").alias("total_value"),
            pl.mean("price").alias("avg_price"),
            pl.len().cast(pl.UInt32).alias("trade_count"),
        )
        .with_columns((pl.col("total_value") / pl.col("total_volume")).alias("vwap_1m"))
        .sort(["data_source", "ticker", "trading_date", "minute_ts"])
        .with_columns(
            pl.col("total_volume")
            .cum_sum()
            .over(["data_source", "ticker", "trading_date"])
            .alias("session_volume"),
            pl.col("total_value")
            .cum_sum()
            .over(["data_source", "ticker", "trading_date"])
            .alias("session_value"),
        )
        .with_columns((pl.col("session_value") / pl.col("session_volume")).alias("session_vwap"))
        .with_columns(
            ((pl.col("close_price") - pl.col("vwap_1m")) / pl.col("vwap_1m") * 100).alias(
                "price_vs_vwap_pct"
            ),
            ((pl.col("close_price") - pl.col("session_vwap")) / pl.col("session_vwap") * 100).alias(
                "price_vs_session_vwap_pct"
            ),
            pl.lit(now, dtype=pl.Datetime).alias("created_at"),
        )
        .select(REALTIME_VWAP_COLUMNS)
    )
    return minute_bars


def load_fact_realtime_vwap(
    client: object,
    trade_ticks: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Load demo realtime VWAP rows into ClickHouse."""
    source = trade_ticks if trade_ticks is not None else generate_demo_trade_ticks()
    frame = build_fact_realtime_vwap(source)
    insert_dataframe(client, "fact_realtime_vwap", frame)  # type: ignore[arg-type]
    return frame
