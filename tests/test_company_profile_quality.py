import polars as pl

from src.quality.company_profile_expectations import validate_company_profile


def valid_company_profile() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "FPT"],
            "company_name": ["Vietcombank", "FPT"],
            "exchange": ["HOSE", "HOSE"],
            "sector_id": ["NGAN_HANG", "CONG_NGHE"],
            "sector_name": ["Ngân hàng", "Công nghệ"],
            "shares_outstanding": [1000, 2000],
        }
    )


def test_company_profile_quality_passes() -> None:
    report = validate_company_profile(valid_company_profile())

    assert report.success is True
    assert report.error_count == 0


def test_company_profile_quality_fails_invalid_rows() -> None:
    frame = pl.DataFrame(
        {
            "ticker": ["VCB", "VCB"],
            "company_name": ["", "Vietcombank"],
            "exchange": ["BAD", "HOSE"],
            "sector_id": ["", "NGAN_HANG"],
            "sector_name": ["", "Ngân hàng"],
            "shares_outstanding": [-1, 1000],
        }
    )

    report = validate_company_profile(frame)
    failed_names = {expectation.name for expectation in report.expectations if not expectation.success}

    assert report.success is False
    assert "expect_ticker_to_be_unique" in failed_names
    assert "expect_exchange_to_be_valid" in failed_names
    assert "expect_shares_outstanding_to_be_non_negative" in failed_names
