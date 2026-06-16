from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = PROJECT_ROOT / "dbt"


def test_day17_dbt_project_files_exist() -> None:
    expected_files = [
        "dbt_project.yml",
        "profiles.yml",
        "models/sources.yml",
        "models/staging/stg_fact_daily_price.sql",
        "models/marts/fact_daily_price_indicators.sql",
        "models/marts/schema.yml",
        "tests/assert_fact_daily_price_indicators_unique_key.sql",
        "tests/assert_fact_daily_price_indicators_market_cap.sql",
        "tests/assert_fact_daily_price_indicators_macd.sql",
    ]

    for relative_path in expected_files:
        assert (DBT_DIR / relative_path).is_file(), f"Missing dbt file: {relative_path}"


def test_day17_dbt_indicator_model_contains_required_metrics() -> None:
    model_sql = (DBT_DIR / "models" / "marts" / "fact_daily_price_indicators.sql").read_text(
        encoding="utf-8"
    )

    expected_terms = [
        "market_cap",
        "sma_20",
        "ema_12",
        "ema_26",
        "macd",
        "rsi_14",
        "bb_upper",
        "bb_middle",
        "bb_lower",
    ]

    for term in expected_terms:
        assert term in model_sql


def test_day17_dbt_tests_cover_key_business_rules() -> None:
    unique_test = (DBT_DIR / "tests" / "assert_fact_daily_price_indicators_unique_key.sql").read_text(
        encoding="utf-8"
    )
    market_cap_test = (
        DBT_DIR / "tests" / "assert_fact_daily_price_indicators_market_cap.sql"
    ).read_text(encoding="utf-8")
    macd_test = (DBT_DIR / "tests" / "assert_fact_daily_price_indicators_macd.sql").read_text(
        encoding="utf-8"
    )

    assert "group by ticker, trading_date" in unique_test
    assert "market_cap - (close * shares_outstanding)" in market_cap_test
    assert "macd - (ema_12 - ema_26)" in macd_test
