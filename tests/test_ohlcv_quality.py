from datetime import date
from pathlib import Path

import polars as pl

from src.quality.ohlcv_expectations import (
    load_silver_ohlcv_dataset,
    save_quality_report,
    validate_ohlcv,
)


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "VCB"],
            "date": [date(2026, 6, 10), date(2026, 6, 11)],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [102.0, 103.0],
            "volume": [1_000_000, 1_200_000],
        }
    )


def invalid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "VCB"],
            "date": [date(2026, 6, 10), date(2026, 6, 10)],
            "open": [100.0, -1.0],
            "high": [98.0, 90.0],
            "low": [99.0, 91.0],
            "close": [102.0, None],
            "volume": [1_000_000, -10],
        }
    )


def test_quality_expectations_pass() -> None:
    report = validate_ohlcv(valid_frame())

    assert report.success is True
    assert report.error_count == 0
    assert {expectation.name for expectation in report.expectations}


def test_quality_expectations_fail() -> None:
    report = validate_ohlcv(invalid_frame())

    assert report.success is False
    assert report.error_count > 0
    failed_names = {
        expectation.name for expectation in report.expectations if not expectation.success
    }
    assert "expect_ticker_date_to_be_unique" in failed_names
    assert "expect_close_to_not_be_null" in failed_names
    assert "expect_volume_to_not_be_null" not in failed_names
    assert "expect_volume_to_be_non_negative" in failed_names


def test_save_quality_report_writes_json(tmp_path: Path) -> None:
    report = validate_ohlcv(valid_frame())

    output_path = save_quality_report(report, report_dir=tmp_path, report_date=date(2026, 6, 10))

    assert output_path.is_file()
    assert output_path.name == "2026-06-10_validation.json"
    assert '"success": true' in output_path.read_text(encoding="utf-8")


def test_save_quality_report_supports_custom_name(tmp_path: Path) -> None:
    report = validate_ohlcv(valid_frame())

    output_path = save_quality_report(report, report_dir=tmp_path, report_name="custom.json")

    assert output_path.is_file()
    assert output_path.name == "custom.json"


def test_load_silver_ohlcv_dataset_reads_selected_tickers(tmp_path: Path) -> None:
    silver_path = tmp_path / "ohlcv" / "year=2026" / "month=06" / "data.parquet"
    silver_path.parent.mkdir(parents=True)
    pl.concat(
        [valid_frame(), valid_frame().with_columns(pl.lit("ACB").alias("ticker"))],
        how="diagonal_relaxed",
    ).write_parquet(silver_path)

    frame = load_silver_ohlcv_dataset(local_silver_dir=tmp_path, tickers=["ACB"])

    assert frame.height == 2
    assert frame.get_column("ticker").unique().to_list() == ["ACB"]
