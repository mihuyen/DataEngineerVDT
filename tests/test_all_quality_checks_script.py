from pathlib import Path


def test_run_all_quality_checks_references_all_datasets() -> None:
    content = Path("scripts/run_all_quality_checks.py").read_text(encoding="utf-8")

    for script_name in [
        "run_quality_check.py",
        "run_company_profile_quality_check.py",
        "run_market_index_quality_check.py",
        "run_news_quality_check.py",
    ]:
        assert script_name in content


def test_quality_reports_record_great_expectations_version() -> None:
    quality_modules = [
        Path("src/quality/ohlcv_expectations.py"),
        Path("src/quality/company_profile_expectations.py"),
        Path("src/quality/market_index_expectations.py"),
        Path("src/quality/news_expectations.py"),
    ]

    for module_path in quality_modules:
        content = module_path.read_text(encoding="utf-8")
        assert "gx_version" in content
        assert "great_expectations" in content
