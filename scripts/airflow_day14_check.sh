#!/usr/bin/env bash
set -euo pipefail

DAG_ID="${DAG_ID:-stock_lakehouse_daily}"
AIRFLOW_CONTAINER="${AIRFLOW_CONTAINER:-stock-airflow-webserver}"
PROJECT_DIR="${PROJECT_DIR:-/opt/airflow/project}"

echo "Checking Airflow container: ${AIRFLOW_CONTAINER}"
docker exec "${AIRFLOW_CONTAINER}" airflow dags list | grep "${DAG_ID}"

echo "Checking DAG import errors"
docker exec "${AIRFLOW_CONTAINER}" airflow dags list-import-errors

echo "Checking DAG task graph"
docker exec "${AIRFLOW_CONTAINER}" airflow tasks list "${DAG_ID}" --tree

echo "Checking project uv environment inside Airflow container"
docker exec "${AIRFLOW_CONTAINER}" bash -lc \
  "cd ${PROJECT_DIR} && export UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock && uv run python scripts/run_all_quality_checks.py"

echo "Checking DAG paused state"
docker exec "${AIRFLOW_CONTAINER}" airflow dags list | grep "${DAG_ID}"

echo "Airflow Day 14 check completed"
