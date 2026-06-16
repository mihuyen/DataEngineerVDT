from pathlib import Path

import yaml


def test_airflow_services_use_uv_image_and_project_mount() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    for service_name in ("airflow-webserver", "airflow-scheduler"):
        service = compose["services"][service_name]

        assert service["build"]["dockerfile"] == "docker/airflow.Dockerfile"
        assert service["image"] == "stock-airflow-uv:local"
        assert ".:/opt/airflow/project" in service["volumes"]


def test_airflow_dockerfile_installs_uv() -> None:
    dockerfile = Path("docker/airflow.Dockerfile").read_text(encoding="utf-8")

    assert "ghcr.io/astral-sh/uv:0.11.19" in dockerfile
    assert "/uv /uvx /bin/" in dockerfile
