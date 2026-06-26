from datetime import date

import polars as pl

from src.quality.market_index_expectations import validate_market_index


def valid_market_index() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "index_code": ["VNINDEX", "VN30"],
            "date": [date(2026, 6, 10)] * 2,
            "open": [100.0, 100.0],
            "high": [110.0, 110.0],
            "low": [90.0, 90.0],
            "close": [105.0, 105.0],
            "volume": [1, 1],
        }
    )


def test_market_index_quality_passes() -> None:
    report = validate_market_index(valid_market_index())

    assert report.success is True
    assert report.error_count == 0


def test_market_index_quality_fails_invalid_rows() -> None:
    frame = valid_market_index().vstack(
        pl.DataFrame(
            {
                "index_code": ["BAD"],
                "date": [date(2026, 6, 10)],
                "open": [-1.0],
                "high": [80.0],
                "low": [90.0],
                "close": [85.0],
                "volume": [-1],
            }
        )
    )
    report = validate_market_index(frame)
    failed_names = {expectation.name for expectation in report.expectations if not expectation.success}

    assert report.success is False
    assert "expect_index_code_to_be_expected" in failed_names
    assert "expect_open_to_be_positive" in failed_names
    assert "expect_volume_to_be_non_negative" in failed_names
