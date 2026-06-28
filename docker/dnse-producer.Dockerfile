FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Minimal dependency set for the DNSE realtime tick producer only -- not the
# full repo's dependency set (this never touches dbt, vnstock's quality-check
# fallback path is a lazy import it doesn't trigger here, etc).
COPY services/dnse-producer/pyproject.toml services/dnse-producer/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/common ./src/common
COPY src/loaders/__init__.py ./src/loaders/__init__.py
COPY src/loaders/load_fact_realtime_vwap.py ./src/loaders/load_fact_realtime_vwap.py
COPY src/streaming ./src/streaming
COPY scripts/run_dnse_realtime_ingest.py ./scripts/run_dnse_realtime_ingest.py

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
