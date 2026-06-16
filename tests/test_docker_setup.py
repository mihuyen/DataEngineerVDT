from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_docker_day_2_files_exist() -> None:
    expected_files = [
        "docker-compose.yml",
        "docs/docker_setup.md",
        "scripts/check_services.py",
    ]

    for relative_path in expected_files:
        assert (PROJECT_ROOT / relative_path).is_file(), f"Missing file: {relative_path}"


def test_docker_compose_services_exist() -> None:
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    compose_config = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    expected_services = {
        "minio",
        "clickhouse",
        "postgres",
        "zookeeper",
        "kafka",
        "airflow-webserver",
        "airflow-scheduler",
        "superset",
        "grafana",
    }

    assert expected_services.issubset(compose_config["services"].keys())
