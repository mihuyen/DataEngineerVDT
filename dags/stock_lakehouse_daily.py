from __future__ import annotations

from datetime import datetime, timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule


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
    "cd " + PROJECT_DIR
)


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="stock_lakehouse_daily",
    description="Daily Bronze -> Silver -> Gold pipeline for Vietnam stock lakehouse",
    default_args=default_args,
    start_date=datetime(2026, 6, 14, tzinfo=LOCAL_TZ),
    schedule="0 18 * * 1-5",
    catchup=False,
    max_active_runs=1,
    tags=["stock", "lakehouse", "bronze", "silver", "gold"],
) as dag:
    init_minio = BashOperator(
        task_id="init_minio_buckets",
        bash_command=f"{COMMON_ENV} && uv run python scripts/init_minio.py",
    )

    ingest_market_index = BashOperator(
        task_id="bronze_market_index",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_market_index_ingest.py",
    )

    ingest_news = BashOperator(
        task_id="bronze_market_news",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_news_ingest.py",
    )

    ingest_company_profile = BashOperator(
        task_id="bronze_company_profile_listing",
        bash_command=(
            f"{COMMON_ENV} && "
            "uv run python scripts/run_company_profile_ingest.py "
            "--mode listing "
            "--exchanges HOSE"
        ),
    )

    ingest_ohlcv = BashOperator(
        task_id="bronze_ohlcv",
        bash_command=(
            f"{COMMON_ENV} && "
            "uv run python scripts/run_ohlcv_ingest.py "
            "--exchanges HOSE "
            "--request-delay-seconds 5 "
            "--skip-existing"
        ),
        execution_timeout=timedelta(hours=4),
    )

    silver_ohlcv = BashOperator(
        task_id="silver_ohlcv",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_silver_transform.py",
    )

    silver_company_profile = BashOperator(
        task_id="silver_company_profile",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_company_profile_silver.py",
    )

    silver_market_index = BashOperator(
        task_id="silver_market_index",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_market_index_silver.py",
    )

    silver_news = BashOperator(
        task_id="silver_news",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_news_silver.py",
    )

    quality_all = BashOperator(
        task_id="quality_all",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_all_quality_checks.py",
    )

    migrate_gold = BashOperator(
        task_id="migrate_gold_schema",
        bash_command=f"{COMMON_ENV} && uv run python scripts/migrate_gold_schema.py",
    )

    load_gold = BashOperator(
        task_id="load_gold",
        bash_command=f"{COMMON_ENV} && uv run python scripts/load_gold.py",
    )

    reconcile_gold = BashOperator(
        task_id="reconcile_gold",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_reconciliation_check.py --fail-on-error",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{COMMON_ENV}/dbt && uv run dbt run --project-dir . --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{COMMON_ENV}/dbt && uv run dbt test --project-dir . --profiles-dir .",
    )

    export_gold_to_minio = BashOperator(
        task_id="export_gold_to_minio",
        bash_command=f"{COMMON_ENV} && uv run python scripts/export_gold_to_minio.py",
    )

    export_frontend_data = BashOperator(
        task_id="export_frontend_data",
        bash_command=f"{COMMON_ENV} && uv run python scripts/export_frontend_data.py",
    )

    init_user_alerts = BashOperator(
        task_id="init_user_alerts",
        bash_command=f"{COMMON_ENV} && uv run python scripts/init_user_alerts.py",
    )

    check_alerts = BashOperator(
        task_id="check_alerts",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_alert_engine.py --run-once",
    )

    backup_lakehouse = BashOperator(
        task_id="backup_lakehouse",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_backup.py",
    )

    # Run after the close with the same conservative pacing as daily OHLCV.
    # Processing the complete HOSE universe is slower, but avoids leaving a
    # permanently partial intraday session in the investor-facing chart.
    intraday_ohlcv_backfill = BashOperator(
        task_id="intraday_ohlcv_backfill",
        bash_command=(
            f"{COMMON_ENV} && uv run python scripts/run_intraday_ohlcv_backfill.py "
            "--request-delay-seconds 3.5"
        ),
        execution_timeout=timedelta(hours=2),
    )

    # Does not gate anything downstream: a quality finding here (e.g. the
    # two DNSE WebSocket pipelines disagreeing on session volume because one
    # missed ticks during a reconnect) should not block the daily batch from
    # publishing, it's diagnostic for the realtime services specifically.
    realtime_quality_check = BashOperator(
        task_id="realtime_quality_check",
        bash_command=f"{COMMON_ENV} && uv run python scripts/run_realtime_quality_check.py",
        # Vnstock's rate limit makes intraday_ohlcv_backfill fail often for
        # reasons unrelated to data quality -- this should still report on
        # whatever intraday data exists rather than being skipped right
        # along with it (the default trigger_rule, all_success, would do
        # that).
        trigger_rule=TriggerRule.ALL_DONE,
    )

    init_minio >> [ingest_market_index, ingest_news, ingest_ohlcv, ingest_company_profile]
    ingest_ohlcv >> silver_ohlcv
    ingest_market_index >> silver_market_index
    ingest_news >> silver_news
    ingest_company_profile >> silver_company_profile
    [silver_ohlcv, silver_company_profile, silver_market_index, silver_news] >> quality_all
    quality_all >> migrate_gold >> load_gold >> reconcile_gold
    reconcile_gold >> init_user_alerts >> check_alerts
    reconcile_gold >> dbt_run >> dbt_test
    # Backup and the intraday backfill do not gate export_gold_to_minio or
    # export_frontend_data: backfill specifically calls an external API
    # (Vnstock) with a hard rate limit, so it fails often and for reasons
    # that have nothing to do with whether the rest of Gold is fine -- a
    # rate-limit error here must not block the dashboard from getting fresh
    # daily-batch data. Both run as side branches off reconcile_gold instead
    # of joining the export fan-in below.
    reconcile_gold >> backup_lakehouse
    reconcile_gold >> intraday_ohlcv_backfill >> realtime_quality_check
    reconcile_gold >> export_gold_to_minio
    [export_gold_to_minio, check_alerts, dbt_test] >> export_frontend_data
