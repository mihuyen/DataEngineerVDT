FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Minimal dependency set for the alert engine only -- requests,
# clickhouse-connect, psycopg, dotenv. It never builds or reads a Polars
# DataFrame (only ch_client.query()/insert() with plain rows), so it does
# not need polars/pandas/pyarrow at all -- those live in
# docker/vwap-consumer.Dockerfile instead. See services/alert-engine/pyproject.toml.
COPY services/alert-engine/pyproject.toml services/alert-engine/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Only the source this service actually imports.
COPY src/common ./src/common
COPY src/alert_engine ./src/alert_engine
COPY scripts/run_alert_engine.py scripts/init_user_alerts.py ./scripts/
COPY sql/ddl_postgres ./sql/ddl_postgres

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
