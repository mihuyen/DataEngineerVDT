from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, insert_dataframe, query_dataframe
from src.ingestion.vn30_constituents import fetch_vn30_constituents
from src.loaders.load_dimensions import (
    DEFAULT_LOCAL_SILVER_DIR,
    load_dim_date,
    load_dim_index,
    load_dim_sector,
    load_dim_stock,
)
from src.loaders.load_fact_daily_price import (
    build_fact_daily_price,
    load_silver_company_shares,
    load_silver_ohlcv,
)
from src.loaders.load_fact_market_index import (
    build_fact_market_index_from_index,
    build_index_breadth,
    load_silver_market_index,
)
from src.loaders.load_fact_news_sentiment import load_fact_news_sentiment_daily

# Rolling indicators (SMA20/EMA26/RSI14/Bollinger) need this many calendar
# days of trailing Silver history to be correct at the start of the
# reprocessing window, so the window must extend at least this far back from
# the current Gold watermark even though only recent partitions get touched.
INDICATOR_LOOKBACK_DAYS = 35


DIM_TABLES = [
    "dim_date",
    "dim_sector",
    "dim_stock",
    "dim_index",
]

# fact_realtime_vwap and fact_alert_event are owned by the continuous
# realtime-vwap-consumer and alert-engine services respectively, not by this
# batch job. They must never be truncated here: a daily load_gold run would
# otherwise wipe live VWAP/alert history accumulated between DAG runs.
# fact_news_sentiment_daily keeps the previous truncate-and-reload path (news
# processing is out of scope for this change).
BATCH_FACT_PARTITIONS = {
    "fact_daily_price": "trading_date",
    "fact_market_index": "trading_date",
}

TABLES = [*DIM_TABLES, *BATCH_FACT_PARTITIONS, "fact_news_sentiment_daily", "fact_realtime_vwap", "fact_alert_event"]


def verify_counts(client: object) -> pl.DataFrame:
    """Return row counts for Gold tables."""
    queries = [
        f"SELECT '{table_name}' AS table_name, count() AS row_count FROM {table_name}"
        for table_name in TABLES
    ]
    return query_dataframe(client, " UNION ALL ".join(queries))  # type: ignore[arg-type]


def truncate_dim_tables(client: object) -> None:
    """Dimensions are small and fully rebuilt from Silver on every run."""
    for table_name in reversed(DIM_TABLES):
        execute(client, f"TRUNCATE TABLE IF EXISTS {table_name}")  # type: ignore[arg-type]


def truncate_news_sentiment_table(client: object) -> None:
    execute(client, "TRUNCATE TABLE IF EXISTS fact_news_sentiment_daily")  # type: ignore[arg-type]


def drop_partitions_for_dates(client: object, table_name: str, dates: pl.Series) -> None:
    """Drop the monthly (toYYYYMM) partitions touched by `dates`.

    Mirrors the DROP PARTITION + re-insert pattern used by the realtime VWAP
    consumer instead of truncating the whole table: a daily run only ever
    touches the months present in the freshly recomputed Silver data, so
    history outside that range is left untouched.
    """
    if dates.len() == 0:
        return
    partitions = dates.cast(pl.Date).dt.strftime("%Y%m").cast(pl.Int32).unique().to_list()
    for partition_id in partitions:
        execute(client, f"ALTER TABLE {table_name} DROP PARTITION {partition_id}")  # type: ignore[arg-type]


def load_silver_company_profile(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame | None:
    paths = sorted((local_silver_dir / "company_profile").glob("year=*/month=*/data.parquet"))
    if not paths:
        return None
    return pl.concat([pl.read_parquet(path) for path in paths], how="diagonal_relaxed")


def get_watermark(client: object, table_name: str, date_column: str) -> date | None:
    """Latest date already loaded into a Gold fact table, or None if empty."""
    result = client.query(f"SELECT max({date_column}) FROM {table_name}").result_rows[0][0]  # type: ignore[union-attr]
    return result


def filter_to_affected_months(frame: pl.DataFrame, date_column: str, cutoff: date | None) -> pl.DataFrame:
    """Keep every row belonging to a month touched by `cutoff`, not just rows after it.

    DROP PARTITION removes a whole month at a time (partitions are
    toYYYYMM(date)), so re-inserting only the rows after `cutoff` would
    silently lose the rest of that same month: e.g. dropping partition 202605
    and only re-inserting 2026-05-23 onward would erase 2026-05-01..22, which
    were correct and present before this run. Re-supplying the full month for
    every touched partition avoids that partial-month data loss.
    """
    if cutoff is None:
        return frame
    touched_months = (
        frame.filter(pl.col(date_column) >= cutoff)
        .select(pl.col(date_column).dt.strftime("%Y%m"))
        .unique()
        .to_series()
        .to_list()
    )
    return frame.filter(pl.col(date_column).dt.strftime("%Y%m").is_in(touched_months))


def reprocessing_cutoff(watermark: date | None, lookback_days: int = INDICATOR_LOOKBACK_DAYS) -> date | None:
    """First date that needs to be touched this run, or None to process everything.

    On an empty table there is no watermark, so the full Silver history must
    be loaded once. Otherwise only the window from `lookback_days` before the
    watermark onward is recomputed and re-inserted: Silver dates older than
    that are assumed already correct in Gold and are left completely alone,
    which is what makes this incremental rather than a full reload.
    """
    if watermark is None:
        return None
    return watermark - timedelta(days=lookback_days)


def main() -> None:
    """Load Gold Layer dimensions and available batch facts.

    fact_realtime_vwap and fact_alert_event are intentionally never touched
    here: they are owned by the realtime-vwap-consumer and alert-engine
    services, which write to them continuously and independently of this
    daily batch run.
    """
    client = create_client()
    silver_ohlcv = load_silver_ohlcv()
    silver_company_profile = load_silver_company_profile()
    tickers = sorted(silver_ohlcv.get_column("ticker").str.to_uppercase().unique().to_list())

    truncate_dim_tables(client)
    load_dim_date(client)
    load_dim_sector(client, company_frame=silver_company_profile)
    load_dim_stock(client, company_frame=silver_company_profile, tickers=tickers)
    load_dim_index(client)

    # fact_daily_price: rolling indicators need full Silver history to be
    # computed correctly, but only the window since the last watermark (minus
    # a lookback buffer) is actually re-dropped and re-inserted into Gold.
    daily_price_watermark = get_watermark(client, "fact_daily_price", "trading_date")
    daily_price_cutoff = reprocessing_cutoff(daily_price_watermark)
    daily_price_frame = build_fact_daily_price(silver_ohlcv, company_shares=load_silver_company_shares())
    daily_price_frame = filter_to_affected_months(daily_price_frame, "trading_date", daily_price_cutoff)
    drop_partitions_for_dates(client, "fact_daily_price", daily_price_frame.get_column("trading_date"))
    insert_dataframe(client, "fact_daily_price", daily_price_frame)

    # fact_market_index: same incremental window, driven by the same cutoff
    # since breadth/index data shares the OHLCV date range.
    market_index_watermark = get_watermark(client, "fact_market_index", "trading_date")
    market_index_cutoff = reprocessing_cutoff(market_index_watermark)
    vn30_tickers = fetch_vn30_constituents()
    try:
        silver_market_index = load_silver_market_index()
        breadth = build_index_breadth(silver_ohlcv, silver_company_profile, vn30_tickers)
        market_index_frame = build_fact_market_index_from_index(silver_market_index, breadth=breadth)
    except FileNotFoundError:
        market_index_frame = None
    if market_index_frame is not None:
        market_index_frame = filter_to_affected_months(market_index_frame, "trading_date", market_index_cutoff)
        drop_partitions_for_dates(client, "fact_market_index", market_index_frame.get_column("trading_date"))
        insert_dataframe(client, "fact_market_index", market_index_frame)

    try:
        truncate_news_sentiment_table(client)
        load_fact_news_sentiment_daily(client)
    except FileNotFoundError as exc:
        print(f"- skipped fact_news_sentiment_daily: {exc}")

    counts = verify_counts(client)
    print("Gold Layer load completed")
    print(counts.write_csv())


if __name__ == "__main__":
    main()
