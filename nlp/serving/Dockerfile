FROM python:3.10-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/

COPY nlp/pyproject.toml nlp/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy toàn bộ nlp package để import nlp.serving.* hoạt động
COPY nlp /app/nlp

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# workers=1 vì PhoBERT dùng nhiều RAM (4-6GB), nhiều workers sẽ OOM trên Oracle VM 24GB
# Chạy từ /app để Python có thể resolve import nlp.serving.main
CMD ["uvicorn", "nlp.serving.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "30"]
