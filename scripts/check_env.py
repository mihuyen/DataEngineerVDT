from __future__ import annotations

import os
import platform
from pathlib import Path

from dotenv import load_dotenv


SECRET_KEYS = {
    "MINIO_ROOT_PASSWORD",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "CLICKHOUSE_PASSWORD",
    "POSTGRES_PASSWORD",
    "FINNHUB_API_KEY",
    "DNSE_PASSWORD",
    "AIRFLOW_WEBSERVER_SECRET_KEY",
    "SUPERSET_SECRET_KEY",
    "GF_SECURITY_ADMIN_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
}

ENV_KEYS = [
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "CLICKHOUSE_DB",
    "CLICKHOUSE_HOST",
    "CLICKHOUSE_PORT",
    "CLICKHOUSE_USER",
    "CLICKHOUSE_PASSWORD",
    "CLICKHOUSE_DATABASE",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_DATABASE",
    "KAFKA_BOOTSTRAP_SERVERS",
    "AIRFLOW_UID",
    "AIRFLOW_PROJ_DIR",
    "AIRFLOW_WEBSERVER_SECRET_KEY",
    "SUPERSET_SECRET_KEY",
    "GF_SECURITY_ADMIN_USER",
    "GF_SECURITY_ADMIN_PASSWORD",
    "FINNHUB_API_KEY",
    "DNSE_USERNAME",
    "DNSE_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def mask_value(key: str, value: str | None) -> str:
    if not value:
        return "missing"
    if key in SECRET_KEYS:
        return "set (hidden)"
    return "set"


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    load_dotenv(env_path)

    print(f"Python version: {platform.python_version()}")
    print(f"Project root: {project_root}")
    print(f".env loaded: {env_path.exists()}")
    print("Environment variables:")

    for key in ENV_KEYS:
        print(f"- {key}: {mask_value(key, os.getenv(key))}")


if __name__ == "__main__":
    main()
