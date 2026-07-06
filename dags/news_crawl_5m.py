from __future__ import annotations

from datetime import datetime, timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from slack_notifications import notify_failure, notify_success


PROJECT_DIR = "/opt/airflow/project"
LOCAL_TZ = pendulum.timezone("Asia/Ho_Chi_Minh")
COMMON_ENV = (
    "export PYTHONIOENCODING=utf-8 && "
    "export UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock && "
    "export MINIO_ENDPOINT=${MINIO_ENDPOINT:-minio:9000} && "
    "export MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin} && "
    "export MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin} && "
    "export MINIO_SECURE=${MINIO_SECURE:-false} && "
    "export CLICKHOUSE_HOST=${CLICKHOUSE_HOST:-clickhouse} && "
    "export CLICKHOUSE_PORT=${CLICKHOUSE_PORT:-8123} && "
    "export CLICKHOUSE_USER=${CLICKHOUSE_USER:-default} && "
    "export CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-clickhouse} && "
    "export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092} && "
    "export POSTGRES_HOST=${POSTGRES_HOST:-postgres} && "
    "export POSTGRES_PORT=${POSTGRES_PORT:-5432} && "
    "export POSTGRES_USER=${POSTGRES_USER:-stock_user} && "
    "export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-stock_password} && "
    "export POSTGRES_DB=${POSTGRES_DB:-stock_lakehouse} && "
    "export NLP_SERVICE_URL=${NLP_SERVICE_URL:-http://nlp-service:8000} && "
    "cd " + PROJECT_DIR
)


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": notify_failure,
}


with DAG(
    dag_id="news_crawl_5m",
    description="News crawl, entity linking and sentiment refresh every 5 minutes",
    default_args=default_args,
    start_date=datetime(2026, 6, 14, tzinfo=LOCAL_TZ),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["news", "crawl", "nlp", "sentiment"],
) as dag:
    run_news_cycle = BashOperator(
        task_id="run_news_cycle",
        bash_command=(
            f"{COMMON_ENV} && uv run python scripts/run_news_crawl_loop.py "
            "--run-once --load-gold"
        ),
    )

    notify_dag_success = PythonOperator(
        task_id="notify_dag_success",
        python_callable=notify_success,
    )

    run_news_cycle >> notify_dag_success