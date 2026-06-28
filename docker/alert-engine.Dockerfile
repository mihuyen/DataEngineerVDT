FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV PYTHONIOENCODING=utf-8

WORKDIR /app
