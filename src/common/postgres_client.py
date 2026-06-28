from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv

from src.common.secrets import get_secret

load_dotenv()


def create_connection() -> psycopg.Connection:
    """Create a PostgreSQL connection from environment variables."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST") or "localhost",
        port=int(os.getenv("POSTGRES_PORT") or "5432"),
        user=os.getenv("POSTGRES_USER", "stock_user"),
        password=get_secret("POSTGRES_PASSWORD", required=True),
        dbname=os.getenv("POSTGRES_DB", "stock_lakehouse"),
        autocommit=True,
    )
