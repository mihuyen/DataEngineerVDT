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


def test_quality_reports_have_a_gx_version_field_without_depending_on_great_expectations() -> None:
    """These validators are plain Python, not real GE checkpoints/suites --
    great_expectations was only ever imported here to read __version__ for
    this report field, so it should not appear as an import anymore.
    """
    quality_modules = [
        Path("src/quality/ohlcv_expectations.py"),
        Path("src/quality/company_profile_expectations.py"),
        Path("src/quality/market_index_expectations.py"),
        Path("src/quality/news_expectations.py"),
    ]

    for module_path in quality_modules:
        content = module_path.read_text(encoding="utf-8")
        assert "gx_version" in content
        assert "great_expectations" not in content
