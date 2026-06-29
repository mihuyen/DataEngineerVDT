from __future__ import annotations

from datetime import datetime

from src.quality.realtime_expectations import (
    expect_candles_within_market_hours,
    expect_freshness,
    expect_hose_coverage_ratio,
    expect_no_duplicate_keys,
    expect_ohlc_valid,
    expect_vwap_volume_matches_intraday_volume,
)


def test_expect_no_duplicate_keys_passes_when_counts_match() -> None:
    result = expect_no_duplicate_keys("name", total_rows=100, distinct_keys=100)
    assert result.success is True
    assert result.failed_count == 0


def test_expect_no_duplicate_keys_fails_when_rows_exceed_distinct_keys() -> None:
    result = expect_no_duplicate_keys("name", total_rows=105, distinct_keys=100)
    assert result.success is False
    assert result.failed_count == 5


def test_expect_candles_within_market_hours_fails_on_any_out_of_hours_candle() -> None:
    assert expect_candles_within_market_hours("name", 0).success is True
    result = expect_candles_within_market_hours("name", 3)
    assert result.success is False
    assert result.failed_count == 3


def test_expect_ohlc_valid_fails_on_any_invalid_row() -> None:
    assert expect_ohlc_valid("name", 0).success is True
    assert expect_ohlc_valid("name", 2).success is False


def test_expect_freshness_not_applicable_when_market_closed() -> None:
    result = expect_freshness("name", latest_minute=None, is_market_live=False, now=datetime(2026, 6, 29, 20, 0))
    assert result.success is True


def test_expect_freshness_fails_when_no_data_during_live_session() -> None:
    result = expect_freshness("name", latest_minute=None, is_market_live=True, now=datetime(2026, 6, 29, 10, 0))
    assert result.success is False


def test_expect_freshness_fails_when_stale_during_live_session() -> None:
    result = expect_freshness(
        "name",
        latest_minute=datetime(2026, 6, 29, 9, 40),
        is_market_live=True,
        now=datetime(2026, 6, 29, 10, 0),
    )
    assert result.success is False
    assert "staleness_minutes=20.0" in result.details


def test_expect_freshness_passes_when_recent_during_live_session() -> None:
    result = expect_freshness(
        "name",
        latest_minute=datetime(2026, 6, 29, 9, 58),
        is_market_live=True,
        now=datetime(2026, 6, 29, 10, 0),
    )
    assert result.success is True


def test_expect_hose_coverage_ratio_fails_below_minimum() -> None:
    result = expect_hose_coverage_ratio("name", tickers_with_data=100, total_hose_tickers=403)
    assert result.success is False


def test_expect_hose_coverage_ratio_passes_above_minimum() -> None:
    result = expect_hose_coverage_ratio("name", tickers_with_data=300, total_hose_tickers=403)
    assert result.success is True


def test_expect_vwap_volume_matches_intraday_volume_passes_when_close() -> None:
    result = expect_vwap_volume_matches_intraday_volume("name", vwap_total_volume=1000, intraday_total_volume=1050)
    assert result.success is True


def test_expect_vwap_volume_matches_intraday_volume_fails_when_far_apart() -> None:
    result = expect_vwap_volume_matches_intraday_volume("name", vwap_total_volume=157_230, intraday_total_volume=1_215_400)
    assert result.success is False


def test_expect_vwap_volume_matches_intraday_volume_passes_with_no_data_from_either() -> None:
    result = expect_vwap_volume_matches_intraday_volume("name", vwap_total_volume=0, intraday_total_volume=0)
    assert result.success is True
