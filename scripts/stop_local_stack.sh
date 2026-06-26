#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"

stop_pid_file() {
  local name="$1"
  local file="$PID_DIR/$name.pid"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Stopping $name PID $pid"
      kill "$pid" || true
    fi
    rm -f "$file"
  fi
}

stop_pid_file "frontend"
stop_pid_file "dashboard_api"

if [[ "${STOP_DOCKER:-0}" == "1" ]]; then
  cd "$PROJECT_ROOT"
  docker compose stop
else
  echo "Docker services left running. Set STOP_DOCKER=1 to stop containers too."
fi
