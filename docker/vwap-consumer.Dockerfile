FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Minimal dependency set for the realtime VWAP consumer only -- this one
# round-trips DataFrames through ClickHouse (query_dataframe/insert_dataframe),
# which is the only reason polars/pandas/pyarrow are needed; the alert engine
# (docker/alert-engine.Dockerfile) does not pull these. See
# services/vwap-consumer/pyproject.toml.
COPY services/vwap-consumer/pyproject.toml services/vwap-consumer/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/common ./src/common
COPY src/loaders/__init__.py ./src/loaders/__init__.py
COPY src/loaders/load_fact_realtime_vwap.py ./src/loaders/load_fact_realtime_vwap.py
COPY scripts/run_realtime_vwap_kafka_consumer.py scripts/init_realtime_streaming.py ./scripts/
COPY sql/streaming ./sql/streaming

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
