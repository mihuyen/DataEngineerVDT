from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from src.quality.ohlcv_expectations import DEFAULT_REPORT_DIR, ExpectationResult, QualityReport, save_quality_report

# HOSE trading hours, Vietnam time -- a candle/tick timestamped outside these
# windows on a trading day is evidence of a timezone bug somewhere in the
# DNSE/Vnstock ingestion path, not real market activity.
MARKET_OPEN = (9, 0)
MORNING_CLOSE = (11, 30)
AFTERNOON_OPEN = (13, 0)
MARKET_CLOSE = (15, 0)

# fact_intraday_ohlcv is fed by two continuous services (DNSE WS + the daily
# Vnstock backfill); a 10-minute-old "latest candle" during a live session
# means one of them has stalled, well before it'd be obvious from the chart.
MAX_INTRADAY_STALENESS_MINUTES = 10

# Below this, "realtime data" is technically present but covers too few
# names to be useful for cross-market scans (technical signals, alerts) --
# worth flagging even though it's not an outright failure.
MIN_HOSE_COVERAGE_RATIO = 0.5

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _within_market_hours(hour: int, minute: int) -> bool:
    minutes_of_day = hour * 60 + minute
    open_m = MARKET_OPEN[0] * 60 + MARKET_OPEN[1]
    morning_close_m = MORNING_CLOSE[0] * 60 + MORNING_CLOSE[1]
    afternoon_open_m = AFTERNOON_OPEN[0] * 60 + AFTERNOON_OPEN[1]
    close_m = MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]
    return open_m <= minutes_of_day <= morning_close_m or afternoon_open_m <= minutes_of_day <= close_m


def expect_no_duplicate_keys(name: str, total_rows: int, distinct_keys: int) -> ExpectationResult:
    duplicate_count = total_rows - distinct_keys
    return ExpectationResult(
        name=name,
        success=duplicate_count == 0,
        failed_count=max(0, duplicate_count),
        details=f"total_rows={total_rows}, distinct_keys={distinct_keys}, duplicate_rows={duplicate_count}",
    )


def expect_candles_within_market_hours(name: str, out_of_hours_count: int) -> ExpectationResult:
    return ExpectationResult(
        name=name,
        success=out_of_hours_count == 0,
        failed_count=out_of_hours_count,
        details=f"out_of_hours_candles={out_of_hours_count}",
    )


def expect_ohlc_valid(name: str, invalid_count: int) -> ExpectationResult:
    return ExpectationResult(
        name=name,
        success=invalid_count == 0,
        failed_count=invalid_count,
        details=f"invalid_ohlc_rows={invalid_count}",
    )


def expect_freshness(name: str, latest_minute: datetime | None, is_market_live: bool, now: datetime) -> ExpectationResult:
    if not is_market_live:
        return ExpectationResult(name=name, success=True, failed_count=0, details="market closed, freshness not applicable")
    if latest_minute is None:
        return ExpectationResult(name=name, success=False, failed_count=1, details="no intraday rows today during a live session")
    staleness_minutes = max(0.0, (now - latest_minute).total_seconds() / 60)
    success = staleness_minutes <= MAX_INTRADAY_STALENESS_MINUTES
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=0 if success else 1,
        details=f"staleness_minutes={staleness_minutes:.1f}, max_allowed={MAX_INTRADAY_STALENESS_MINUTES}",
    )


def expect_hose_coverage_ratio(name: str, tickers_with_data: int, total_hose_tickers: int) -> ExpectationResult:
    if total_hose_tickers == 0:
        return ExpectationResult(name=name, success=False, failed_count=1, details="dim_stock has no HOSE tickers")
    ratio = tickers_with_data / total_hose_tickers
    success = ratio >= MIN_HOSE_COVERAGE_RATIO
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=0 if success else total_hose_tickers - tickers_with_data,
        details=(
            f"tickers_with_data={tickers_with_data}/{total_hose_tickers} "
            f"({ratio:.1%}), min_allowed={MIN_HOSE_COVERAGE_RATIO:.0%}"
        ),
    )


def expect_vwap_volume_matches_intraday_volume(
    name: str, vwap_total_volume: int, intraday_total_volume: int, max_drop_ratio: float = 0.15
) -> ExpectationResult:
    """fact_realtime_vwap (raw ticks) and fact_intraday_ohlcv (DNSE 1m bars)
    are two independently-subscribed DNSE WebSocket connections -- the
    dnse-producer (tick channel) and dnse-ohlc-consumer (ohlc_closed.1
    channel) each resolve "ALL HOSE tickers" from dim_stock at their own
    startup, so their actual subscribed ticker sets are not guaranteed
    identical. Comparing whole-market volume totals would then be comparing
    different ticker universes, not a real data-quality signal -- so the
    caller must already restrict both totals to the *intersection* of
    tickers present in both sources today before calling this.
    """
    if vwap_total_volume == 0 and intraday_total_volume == 0:
        return ExpectationResult(name=name, success=True, failed_count=0, details="no realtime volume from either source yet")
    larger = max(vwap_total_volume, intraday_total_volume, 1)
    diff_ratio = abs(vwap_total_volume - intraday_total_volume) / larger
    success = diff_ratio <= max_drop_ratio
    return ExpectationResult(
        name=name,
        success=success,
        failed_count=0 if success else 1,
        details=(
            f"vwap_volume={vwap_total_volume}, intraday_volume={intraday_total_volume}, "
            f"diff_ratio={diff_ratio:.3f}, max_allowed={max_drop_ratio:.3f}"
        ),
    )


def build_realtime_quality_report(ch_client: Any, today: date | None = None, now: datetime | None = None) -> QualityReport:
    """Quality checks for the two realtime pipelines (DNSE 1m candles,
    raw-tick VWAP) that the daily Bronze/Silver/Gold reconciliation in
    reconciliation.py never covers -- that one only looks at the once-a-day
    batch tables.
    """
    today = today or datetime.now(timezone.utc).date()
    # Naive UTC, to match clickhouse-connect's naive DateTime values (the
    # ClickHouse server here runs in UTC) -- comparing a tz-aware `now`
    # against those would raise on subtraction.
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)

    intraday_rows = ch_client.query(
        "SELECT ticker, minute_ts, open, high, low, close, volume "
        "FROM fact_intraday_ohlcv WHERE trading_date = today()"
    ).result_rows

    total_rows = len(intraday_rows)
    distinct_keys = len({(ticker, minute_ts) for ticker, minute_ts, *_ in intraday_rows})
    out_of_hours = sum(
        1 for _, minute_ts, *_ in intraday_rows if not _within_market_hours(minute_ts.hour, minute_ts.minute)
    )
    invalid_ohlc = sum(
        1
        for _, _, open_, high, low, close, volume in intraday_rows
        if not (low <= open_ <= high and low <= close <= high and volume >= 0)
    )
    latest_minute = max((minute_ts for _, minute_ts, *_ in intraday_rows), default=None)
    tickers_with_data = len({ticker for ticker, *_ in intraday_rows})

    intraday_volume_by_ticker: dict[str, int] = {}
    for ticker, *_, volume in intraday_rows:
        intraday_volume_by_ticker[ticker] = intraday_volume_by_ticker.get(ticker, 0) + volume

    total_hose_tickers = int(
        ch_client.query("SELECT count() FROM dim_stock WHERE exchange = 'HOSE'").result_rows[0][0]
    )

    vwap_volume_by_ticker = {
        ticker: int(volume)
        for ticker, volume in ch_client.query(
            "SELECT ticker, argMax(session_volume, minute_ts) AS session_volume"
            " FROM fact_realtime_vwap WHERE toDate(minute_ts) = today() GROUP BY ticker"
        ).result_rows
    }

    # Each DNSE WebSocket connection (dnse-producer for ticks,
    # dnse-ohlc-consumer for 1m candles) resolves "ALL HOSE tickers" from
    # dim_stock independently at its own startup, so their actual subscribed
    # sets are not guaranteed identical -- comparing whole-market totals
    # would just be comparing different universes. Restricting to tickers
    # both sources actually have data for today is what makes this a real
    # same-activity comparison.
    shared_tickers = set(intraday_volume_by_ticker) & set(vwap_volume_by_ticker)
    intraday_total_volume = sum(intraday_volume_by_ticker[t] for t in shared_tickers)
    vwap_total_volume = sum(vwap_volume_by_ticker[t] for t in shared_tickers)

    vwap_rows = ch_client.query(
        "SELECT count(), uniqExact(ticker, minute_ts, data_source) FROM fact_realtime_vwap WHERE toDate(minute_ts) = today()"
    ).result_rows[0]

    # Market hours are Vietnam local time, not whatever timezone `now` is in
    # (UTC here) -- comparing UTC hour/minute directly against 9:00-15:00
    # would mark the market "closed" for most of the actual trading day.
    local_now = now.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ)
    current_minutes = local_now.hour * 60 + local_now.minute
    is_market_live = local_now.weekday() < 5 and (
        MARKET_OPEN[0] * 60 + MARKET_OPEN[1] <= current_minutes <= MORNING_CLOSE[0] * 60 + MORNING_CLOSE[1]
        or AFTERNOON_OPEN[0] * 60 + AFTERNOON_OPEN[1] <= current_minutes <= MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]
    )

    expectations = [
        expect_no_duplicate_keys("expect_fact_intraday_ohlcv_no_duplicate_keys", total_rows, distinct_keys),
        expect_candles_within_market_hours("expect_intraday_candles_within_market_hours", out_of_hours),
        expect_ohlc_valid("expect_intraday_ohlc_valid", invalid_ohlc),
        expect_freshness("expect_intraday_freshness_within_sla", latest_minute, is_market_live, now),
        expect_hose_coverage_ratio("expect_hose_coverage_ratio", tickers_with_data, total_hose_tickers),
        expect_no_duplicate_keys("expect_fact_realtime_vwap_no_duplicate_keys", vwap_rows[0], vwap_rows[1]),
        expect_vwap_volume_matches_intraday_volume(
            "expect_vwap_volume_matches_intraday_volume", vwap_total_volume, intraday_total_volume
        ),
    ]

    error_count = sum(e.failed_count for e in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name="realtime_quality",
        record_count=total_rows,
        error_count=error_count,
        success=all(e.success for e in expectations),
        expectations=expectations,
        gx_version="n/a",
    )


def save_realtime_quality_report(report: QualityReport, report_dir=DEFAULT_REPORT_DIR):
    return save_quality_report(report, report_dir, report_name="realtime_quality_validation.json")
