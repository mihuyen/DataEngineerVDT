from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import polars as pl

from src.quality.ohlcv_expectations import (
    DEFAULT_LOCAL_SILVER_DIR,
    DEFAULT_REPORT_DIR,
    ExpectationResult,
    QualityReport,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"

# Bronze/Silver are compared on distinct (ticker, date) keys, so the only
# legitimate drop is Silver's invalid-row filtering (price <= 0, high < low,
# etc.), which is normally a tiny fraction of rows. Anything beyond this
# signals a likely ingestion/transform bug rather than normal cleaning.
MAX_BRONZE_TO_SILVER_DROP_RATIO = 0.05

# Gold is built straight from Silver with no additional row filtering, so its
# count should not drop versus Silver at all (a drop means the Gold load
# silently lost data, e.g. a partial/failed insert).
MAX_SILVER_TO_GOLD_DROP_RATIO = 0.0

# fact_daily_price/fact_market_index are refreshed by the 18:00 Mon-Fri batch
# DAG, which only ever produces new trading-session rows, never weekend ones.
# Measuring staleness in business days (Mon-Fri) rather than calendar days
# means a Monday run is judged against Friday's data fairly, instead of a
# fixed calendar-day SLA having to be loose enough to tolerate weekends and
# therefore also being slow to catch a pipeline stall on a weekday.
MAX_STALENESS_BUSINESS_DAYS = 2


def count_parquet_rows(root: Path, glob_pattern: str) -> int:
    files = sorted(root.glob(glob_pattern))
    if not files:
        return 0
    return sum(pl.scan_parquet(file_path).select(pl.len()).collect().item() for file_path in files)


def count_distinct_bronze_ticker_dates(root: Path, glob_pattern: str, ticker_part_index: int) -> int:
    """Count distinct (ticker, trading date) pairs across Bronze OHLCV/index files.

    Bronze intentionally re-fetches overlapping historical windows on every
    ingest run (each run lands in its own ticker/year/month/day partition, by
    ingest date, not trading date), so raw row counts can be several times
    larger than Silver's deduplicated row count even with zero real data
    loss. Counting distinct (ticker, date) keys instead of raw rows is what
    actually reflects whether Silver/Gold cover everything Bronze has seen.
    `ticker_part_index` is the negative index of the `ticker=...`/`index_code=...`
    path segment within each file's `Path.parts`.
    """
    files = sorted(root.glob(glob_pattern))
    if not files:
        return 0
    frames = []
    for file_path in files:
        ticker = file_path.parts[ticker_part_index].split("=", 1)[1]
        frames.append(pl.read_parquet(file_path).select("date").with_columns(pl.lit(ticker).alias("key")))
    frame = pl.concat(frames, how="diagonal_relaxed")
    return frame.unique(["key", "date"]).height


def count_distinct_bronze_keys(root: Path, glob_pattern: str, key_column: str) -> int:
    """Count distinct (key, trading date) pairs when the key lives in a column.

    Used for the combined year/month/day Bronze layout where all tickers share
    one file per ingest day, so the ticker is a data column instead of a path
    segment.
    """
    files = sorted(root.glob(glob_pattern))
    if not files:
        return 0
    frame = pl.concat(
        (pl.read_parquet(file_path).select(key_column, "date") for file_path in files),
        how="diagonal_relaxed",
    )
    return frame.unique([key_column, "date"]).height


def _ratio_check(
    name: str,
    upstream_count: int,
    downstream_count: int,
    max_drop_ratio: float,
) -> ExpectationResult:
    if upstream_count == 0:
        return ExpectationResult(
            name=name,
            success=downstream_count == 0,
            failed_count=0 if downstream_count == 0 else downstream_count,
            details=f"upstream_count=0, downstream_count={downstream_count}",
        )
    drop_ratio = max(0.0, (upstream_count - downstream_count) / upstream_count)
    success = drop_ratio <= max_drop_ratio
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=0 if success else upstream_count - downstream_count,
        details=(
            f"upstream={upstream_count}, downstream={downstream_count}, "
            f"drop_ratio={drop_ratio:.3f}, max_allowed={max_drop_ratio:.3f}"
        ),
    )


def _exact_match_check(name: str, upstream_count: int, downstream_count: int) -> ExpectationResult:
    """Fail on any mismatch in either direction.

    Unlike `_ratio_check`, this also fails when downstream has *more* rows
    than upstream (e.g. duplicate inserts from a partial/re-run Gold load),
    not just fewer. Silver and Gold are expected to carry the exact same set
    of (ticker, date) keys with no additional filtering in between.
    """
    success = upstream_count == downstream_count
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=abs(upstream_count - downstream_count),
        details=f"upstream={upstream_count}, downstream={downstream_count}",
    )


def read_silver_keys(root: Path, glob_pattern: str, ticker_column: str = "ticker") -> set[tuple]:
    """Distinct (ticker, date) keys actually present in Silver parquet files."""
    files = sorted(root.glob(glob_pattern))
    if not files:
        return set()
    frame = pl.concat(
        (pl.read_parquet(file_path).select(ticker_column, "date") for file_path in files),
        how="diagonal_relaxed",
    )
    return {(row[0], row[1]) for row in frame.unique().iter_rows()}


def read_gold_keys(ch_client: Any, table: str, ticker_column: str, date_column: str) -> set[tuple]:
    """Distinct (ticker, date) keys actually present in a Gold ClickHouse table."""
    result = ch_client.query(f"SELECT DISTINCT {ticker_column}, {date_column} FROM {table}")
    return {(row[0], row[1]) for row in result.result_rows}


def _anti_join_check(
    name: str,
    silver_keys: set[tuple],
    gold_keys: set[tuple],
    max_examples: int = 10,
) -> ExpectationResult:
    """Identify exactly which (ticker, date) keys are missing or extra.

    `_exact_match_check` can pass on a count that happens to match while
    Gold actually holds a different set of keys than Silver (e.g. one
    ticker's rows silently swapped for another's) -- it only sees totals.
    This compares the actual key sets so a mismatch names the specific rows
    affected instead of just the size of the discrepancy.
    """
    missing_in_gold = silver_keys - gold_keys
    extra_in_gold = gold_keys - silver_keys
    success = not missing_in_gold and not extra_in_gold
    details_parts = [f"missing_in_gold_count={len(missing_in_gold)}", f"extra_in_gold_count={len(extra_in_gold)}"]
    if missing_in_gold:
        details_parts.append(f"missing_in_gold_sample={sorted(missing_in_gold)[:max_examples]}")
    if extra_in_gold:
        details_parts.append(f"extra_in_gold_sample={sorted(extra_in_gold)[:max_examples]}")
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=len(missing_in_gold) + len(extra_in_gold),
        details=", ".join(details_parts),
    )


def _duplicate_key_check(ch_client: Any, name: str, table: str, key_columns: list[str]) -> ExpectationResult:
    """Fail if a Gold table has more rows than distinct business keys.

    A row-count-only reconciliation can pass even when Gold has duplicate
    (ticker, date) rows that happen to offset a real loss elsewhere, so
    duplicates are checked directly via count() vs uniqExact(...).
    """
    keys_sql = ", ".join(key_columns)
    row = ch_client.query(f"SELECT count() AS total, uniqExact({keys_sql}) AS distinct_keys FROM {table}").result_rows[
        0
    ]
    total, distinct_keys = int(row[0]), int(row[1])
    duplicate_count = total - distinct_keys
    return ExpectationResult(
        name=name,
        success=duplicate_count == 0,
        failed_count=max(0, duplicate_count),
        details=f"total_rows={total}, distinct_keys={distinct_keys}, duplicate_rows={duplicate_count}",
    )


def _count_business_days(start: date, end: date) -> int:
    """Number of Mon-Fri calendar days strictly between `start` and `end`."""
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return days


def _freshness_check(
    name: str, latest_date: Any, max_staleness_business_days: int, today: date
) -> ExpectationResult:
    if latest_date is None:
        return ExpectationResult(
            name=name,
            success=False,
            failed_count=1,
            details="no rows found in Gold table",
        )
    if isinstance(latest_date, datetime):
        latest_date = latest_date.date()
    staleness_business_days = _count_business_days(latest_date, today)
    success = staleness_business_days <= max_staleness_business_days
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=0 if success else 1,
        details=(
            f"latest_date={latest_date}, staleness_business_days={staleness_business_days}, "
            f"max_allowed={max_staleness_business_days}"
        ),
    )


def build_reconciliation_report(
    ch_client: Any,
    local_bronze_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    today: date | None = None,
) -> QualityReport:
    """Cross-layer reconciliation: row-count drop and Gold freshness checks.

    Closes the gap the rest of the quality suite leaves open: each layer's
    own validators check that rows look correct in isolation, but nothing
    previously confirmed that rows from Bronze actually survived into Silver
    and Gold, or that Gold is still being refreshed on schedule.
    """
    today = today or datetime.now(timezone.utc).date()

    bronze_ohlcv = count_distinct_bronze_keys(
        local_bronze_dir, "ohlcv/year=*/month=*/day=*/data.parquet", "ticker"
    )
    silver_ohlcv = len(read_silver_keys(local_silver_dir, "ohlcv/year=*/month=*/data.parquet", "ticker"))
    gold_daily_price = int(ch_client.query("SELECT count() FROM fact_daily_price").result_rows[0][0])

    bronze_market_index = count_distinct_bronze_ticker_dates(
        local_bronze_dir, "market_index/index_code=*/year=*/month=*/day=*/data.parquet", ticker_part_index=-5
    )
    silver_market_index = len(read_silver_keys(local_silver_dir, "market_index/year=*/month=*/data.parquet", "index_code"))
    gold_market_index = int(ch_client.query("SELECT count() FROM fact_market_index").result_rows[0][0])

    silver_ohlcv_keys = read_silver_keys(local_silver_dir, "ohlcv/year=*/month=*/data.parquet", "ticker")
    gold_ohlcv_keys = read_gold_keys(ch_client, "fact_daily_price", "ticker", "trading_date")

    silver_market_index_keys = read_silver_keys(
        local_silver_dir, "market_index/year=*/month=*/data.parquet", "index_code"
    )
    gold_market_index_keys = read_gold_keys(ch_client, "fact_market_index", "index_id", "trading_date")

    latest_daily_price = ch_client.query("SELECT max(trading_date) FROM fact_daily_price").result_rows[0][0]
    latest_market_index = ch_client.query("SELECT max(trading_date) FROM fact_market_index").result_rows[0][0]

    expectations = [
        _ratio_check(
            "expect_ohlcv_bronze_to_silver_drop_within_threshold",
            bronze_ohlcv,
            silver_ohlcv,
            MAX_BRONZE_TO_SILVER_DROP_RATIO,
        ),
        _exact_match_check("expect_ohlcv_silver_to_gold_exact_match", silver_ohlcv, gold_daily_price),
        _anti_join_check("expect_ohlcv_silver_to_gold_same_keys", silver_ohlcv_keys, gold_ohlcv_keys),
        _duplicate_key_check(
            ch_client, "expect_fact_daily_price_no_duplicate_keys", "fact_daily_price", ["ticker", "trading_date"]
        ),
        _ratio_check(
            "expect_market_index_bronze_to_silver_drop_within_threshold",
            bronze_market_index,
            silver_market_index,
            MAX_BRONZE_TO_SILVER_DROP_RATIO,
        ),
        _exact_match_check("expect_market_index_silver_to_gold_exact_match", silver_market_index, gold_market_index),
        _anti_join_check(
            "expect_market_index_silver_to_gold_same_keys", silver_market_index_keys, gold_market_index_keys
        ),
        _duplicate_key_check(
            ch_client,
            "expect_fact_market_index_no_duplicate_keys",
            "fact_market_index",
            ["index_id", "trading_date"],
        ),
        _freshness_check(
            "expect_fact_daily_price_fresh_within_sla",
            latest_daily_price,
            MAX_STALENESS_BUSINESS_DAYS,
            today,
        ),
        _freshness_check(
            "expect_fact_market_index_fresh_within_sla",
            latest_market_index,
            MAX_STALENESS_BUSINESS_DAYS,
            today,
        ),
    ]

    error_count = sum(expectation.failed_count for expectation in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name="reconciliation",
        record_count=gold_daily_price,
        error_count=error_count,
        success=all(expectation.success for expectation in expectations),
        expectations=expectations,
        gx_version="n/a",
    )


def save_reconciliation_report(report: QualityReport, report_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / "reconciliation_validation.json"
    import json

    output_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
