from pathlib import Path


def test_airflow_day14_runbook_exists() -> None:
    content = Path("docs/airflow_day14.md").read_text(encoding="utf-8")

    assert "stock_lakehouse_daily" in content
    assert "quality_all" in content
    assert "Bronze" in content
    assert "Silver" in content
    assert "Gold" in content


def test_airflow_day14_check_script_exists() -> None:
    content = Path("scripts/airflow_day14_check.sh").read_text(encoding="utf-8")

    assert "airflow dags list-import-errors" in content
    assert "airflow tasks list" in content
    assert "scripts/run_all_quality_checks.py" in content
