FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Minimal dependency set for alert-engine / realtime-vwap-consumer only
# (psycopg, clickhouse-connect, polars, requests, dotenv) -- resolved and
# installed at build time, not the full repo's ~25-package set (dbt,
# great-expectations, vnstock, pyarrow, fastapi...) that those services
# never import. See services/alert-engine/pyproject.toml.
COPY services/alert-engine/pyproject.toml services/alert-engine/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Only the source these two services actually import -- not the whole repo,
# so this image can't accidentally start depending on something from
# ingestion/transform/api code that isn't in the dependency set above.
COPY src/common ./src/common
COPY src/alert_engine ./src/alert_engine
COPY src/loaders/__init__.py ./src/loaders/__init__.py
COPY src/loaders/load_fact_realtime_vwap.py ./src/loaders/load_fact_realtime_vwap.py
COPY scripts/run_alert_engine.py scripts/init_user_alerts.py ./scripts/
COPY scripts/run_realtime_vwap_kafka_consumer.py scripts/init_realtime_streaming.py ./scripts/
COPY sql/ddl_postgres ./sql/ddl_postgres
COPY sql/streaming ./sql/streaming

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
