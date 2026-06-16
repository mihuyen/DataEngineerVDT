from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "superset_datasets.yaml"


@dataclass(frozen=True)
class SupersetDataset:
    table_name: str
    description: str


@dataclass(frozen=True)
class SupersetConfig:
    database_name: str
    sqlalchemy_uri: str
    schema: str
    datasets: list[SupersetDataset]


class SupersetClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()

    def login(self) -> None:
        response = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={
                "username": self.username,
                "password": self.password,
                "provider": "db",
                "refresh": True,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        access_token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

        csrf = self.session.get(
            f"{self.base_url}/api/v1/security/csrf_token/",
            timeout=self.timeout,
        )
        csrf.raise_for_status()
        self.session.headers.update({"X-CSRFToken": csrf.json()["result"]})

    def find_database_id(self, database_name: str) -> int | None:
        response = self.session.get(f"{self.base_url}/api/v1/database/", timeout=self.timeout)
        response.raise_for_status()
        for item in response.json().get("result", []):
            if item.get("database_name") == database_name:
                return int(item["id"])
        return None

    def ensure_database(self, database_name: str, sqlalchemy_uri: str) -> int:
        existing_id = self.find_database_id(database_name)
        if existing_id is not None:
            return existing_id

        response = self.session.post(
            f"{self.base_url}/api/v1/database/",
            json={
                "database_name": database_name,
                "sqlalchemy_uri": sqlalchemy_uri,
                "expose_in_sqllab": True,
                "allow_run_async": False,
                "allow_ctas": False,
                "allow_cvas": False,
                "allow_dml": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        database_id = result.get("id") or result.get("database", {}).get("id")
        if database_id is not None:
            return int(database_id)

        created_id = self.find_database_id(database_name)
        if created_id is None:
            raise RuntimeError(f"Superset created database {database_name!r} but did not return an id.")
        return created_id

    def find_dataset_id(self, database_id: int, schema: str, table_name: str) -> int | None:
        response = self.session.get(f"{self.base_url}/api/v1/dataset/", timeout=self.timeout)
        response.raise_for_status()
        for item in response.json().get("result", []):
            if (
                item.get("database", {}).get("id") == database_id
                and item.get("schema") == schema
                and item.get("table_name") == table_name
            ):
                return int(item["id"])
        return None

    def ensure_dataset(self, database_id: int, schema: str, dataset: SupersetDataset) -> str:
        existing_id = self.find_dataset_id(database_id, schema, dataset.table_name)
        payload: dict[str, Any] = {
            "database": database_id,
            "schema": schema,
            "table_name": dataset.table_name,
        }
        if existing_id is not None:
            return "exists"

        response = self.session.post(
            f"{self.base_url}/api/v1/dataset/",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return "created"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SupersetConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sqlalchemy_uri = os.getenv(
        raw["sqlalchemy_uri_env"],
        raw["default_sqlalchemy_uri"],
    )
    schema = os.getenv(raw["schema_env"], raw["default_schema"])
    datasets = [
        SupersetDataset(
            table_name=item["table_name"],
            description=item.get("description", ""),
        )
        for item in raw["datasets"]
    ]
    return SupersetConfig(
        database_name=raw["database_name"],
        sqlalchemy_uri=sqlalchemy_uri,
        schema=schema,
        datasets=datasets,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision Day 22 Superset ClickHouse datasets.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Print planned database and datasets only.")
    parser.add_argument("--url", default=os.getenv("SUPERSET_URL", "http://localhost:8088"))
    parser.add_argument("--username", default=os.getenv("SUPERSET_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("SUPERSET_PASSWORD", "admin"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SUPERSET_TIMEOUT", "30")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    print("Superset Day 22 setup")
    print(f"- database: {config.database_name}")
    print(f"- schema: {config.schema}")
    print(f"- datasets: {len(config.datasets)}")
    for dataset in config.datasets:
        print(f"  - {dataset.table_name}")

    if args.dry_run:
        print("- dry_run: yes")
        return

    client = SupersetClient(
        base_url=args.url,
        username=args.username,
        password=args.password,
        timeout=args.timeout,
    )
    client.login()
    database_id = client.ensure_database(config.database_name, config.sqlalchemy_uri)
    print(f"- database_id: {database_id}")

    for dataset in config.datasets:
        status = client.ensure_dataset(database_id, config.schema, dataset)
        print(f"- {status}: {config.schema}.{dataset.table_name}")

    print("Superset Day 22 setup completed")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"Superset API request failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
