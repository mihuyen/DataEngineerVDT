#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

DAG_ID="${DAG_ID:-stock_lakehouse_daily}"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"
NODE_BIN="$PROJECT_ROOT/.node/bin"

mkdir -p "$LOG_DIR" "$PID_DIR"

if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

echo "Starting Docker services..."
docker compose up -d clickhouse minio postgres zookeeper kafka nlp-service alert-engine realtime-vwap-consumer grafana airflow-webserver airflow-scheduler

echo "Waiting for Airflow webserver..."
for _ in $(seq 1 60); do
  if docker exec stock-airflow-webserver airflow dags list >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo "Unpausing Airflow DAG: $DAG_ID"
docker exec stock-airflow-webserver airflow dags unpause "$DAG_ID" >/dev/null || true

if [[ "${TRIGGER_DAG_ON_START:-1}" == "1" ]]; then
  echo "Triggering Airflow DAG now: $DAG_ID"
  docker exec stock-airflow-webserver airflow dags trigger "$DAG_ID" >/dev/null || true
else
  echo "DAG trigger skipped because TRIGGER_DAG_ON_START=0."
fi

echo "Starting dashboard API..."
if [[ -f "$PID_DIR/dashboard_api.pid" ]] && kill -0 "$(cat "$PID_DIR/dashboard_api.pid")" >/dev/null 2>&1; then
  echo "- dashboard API already running with PID $(cat "$PID_DIR/dashboard_api.pid")"
else
  nohup uv run uvicorn src.api.dashboard_api:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/dashboard_api.log" 2>&1 &
  echo $! > "$PID_DIR/dashboard_api.pid"
  echo "- dashboard API PID $(cat "$PID_DIR/dashboard_api.pid")"
fi

echo "Starting frontend dev server..."
if [[ -f "$PID_DIR/frontend.pid" ]] && kill -0 "$(cat "$PID_DIR/frontend.pid")" >/dev/null 2>&1; then
  echo "- frontend already running with PID $(cat "$PID_DIR/frontend.pid")"
else
  (
    cd frontend
    nohup npm run dev -- --host 0.0.0.0 > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
  echo "- frontend PID $(cat "$PID_DIR/frontend.pid")"
fi

echo
echo "Local stack is ready:"
echo "- Frontend: http://localhost:5173"
echo "- API:      http://localhost:8000/api/health"
echo "- NLP API:  http://localhost:8002/health"
echo "- Airflow:  http://localhost:8080  admin/admin"
echo "- MinIO:    http://localhost:9001  minioadmin/minioadmin"
echo
echo "Logs:"
echo "- $LOG_DIR/dashboard_api.log"
echo "- $LOG_DIR/frontend.log"
