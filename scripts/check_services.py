from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceCheck:
    name: str
    host: str
    port: int
    note: str


SERVICES = [
    ServiceCheck("MinIO console", "localhost", 9001, "http://localhost:9001"),
    ServiceCheck("ClickHouse HTTP", "localhost", 8123, "http://localhost:8123"),
    ServiceCheck("PostgreSQL", "localhost", 5432, "postgres://localhost:5432"),
    ServiceCheck("Kafka", "localhost", 9092, "localhost:9092"),
    ServiceCheck("Airflow", "localhost", 8080, "http://localhost:8080"),
    ServiceCheck("Superset", "localhost", 8088, "http://localhost:8088"),
    ServiceCheck("Grafana", "localhost", 3000, "http://localhost:3000"),
]


def check_port(host: str, port: int, timeout_seconds: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def main() -> None:
    print("Local service readiness check")
    print("No API, database query, or authenticated request is executed.")

    for service in SERVICES:
        status = "OK" if check_port(service.host, service.port) else "NOT READY"
        print(f"- {service.name}: {status} ({service.note})")

    print("SKIPPED: deep health checks, credentials, Kafka topics, and database queries.")


if __name__ == "__main__":
    main()
