from pathlib import Path
import subprocess

import yaml

from scripts.setup_superset_day22 import load_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "superset_datasets.yaml"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "setup_superset_day22.py"
DOC_PATH = PROJECT_ROOT / "docs" / "superset_day22.md"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"


def test_day22_superset_config_contains_required_gold_datasets() -> None:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    table_names = {item["table_name"] for item in raw["datasets"]}

    expected_tables = {
        "dim_date",
        "dim_sector",
        "dim_stock",
        "dim_index",
        "fact_daily_price",
        "fact_market_index",
        "fact_news_sentiment_daily",
        "fact_realtime_vwap",
        "fact_alert_event",
    }

    assert raw["database_name"] == "ClickHouse Gold"
    assert expected_tables.issubset(table_names)


def test_day22_load_config_uses_default_clickhouse_uri() -> None:
    config = load_config(CONFIG_PATH)

    assert config.database_name == "ClickHouse Gold"
    assert config.sqlalchemy_uri.startswith("clickhousedb://")
    assert config.schema == "stock_lakehouse"
    assert len(config.datasets) >= 9


def test_day22_setup_script_dry_run_lists_gold_datasets() -> None:
    result = subprocess.run(
        ["python", str(SCRIPT_PATH), "--dry-run"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Superset Day 22 setup" in result.stdout
    assert "- dry_run: yes" in result.stdout
    assert "fact_daily_price" in result.stdout
    assert "fact_realtime_vwap" in result.stdout


def test_day22_superset_container_installs_clickhouse_driver() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "pip install --user clickhouse-connect" in compose
    assert "PYTHONPATH: /app/superset_home/.local/lib/python3.10/site-packages:/app/pythonpath" in compose
    assert "superset db upgrade" in compose


def test_day22_docs_exist_and_explain_setup_flow() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    assert "Ngày 22" in doc
    assert "scripts/setup_superset_day22.py" in doc
    assert "configs/superset_datasets.yaml" in doc
    assert "ClickHouse Gold" in doc
