from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def _read_webhook_url() -> str | None:
    """Read the Slack Incoming Webhook URL.

    Mirrors src/common/secrets.get_secret's `{NAME}_FILE` convention (Docker
    secret / mounted file takes priority over a plain env var), reimplemented
    with stdlib only: DAG files are parsed inside Airflow's own Python
    environment (see docker/airflow.Dockerfile), not the project's
    .venv-stock, so this avoids depending on python-dotenv or the project
    package being importable there.
    """
    file_path = os.getenv("SLACK_WEBHOOK_URL_FILE")
    if file_path and os.path.isfile(file_path):
        return open(file_path, encoding="utf-8").read().strip()
    return os.getenv("SLACK_WEBHOOK_URL") or None


def build_slack_payload(status: str, dag_id: str, run_id: str, detail: str = "") -> dict[str, Any]:
    """Build the Slack Incoming Webhook JSON body for a DAG run outcome."""
    emoji = "✅" if status == "success" else "❌"
    lines = [f"{emoji} *{dag_id}* — run `{run_id}` {status}."]
    if detail:
        lines.append(detail)
    return {"text": "\n".join(lines)}


def _post_to_slack(payload: dict[str, Any]) -> None:
    webhook_url = _read_webhook_url()
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not configured; skipping Slack notification.")
        return
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except Exception as exc:  # noqa: BLE001 - notification must never fail the DAG
        print(f"Slack notification failed: {exc}")


def notify_failure(context: dict[str, Any]) -> None:
    """Airflow on_failure_callback: fires per failed task (after retries)."""
    task_instance = context["task_instance"]
    detail = f"Task `{task_instance.task_id}` failed. Log: {task_instance.log_url}"
    payload = build_slack_payload(
        "failed",
        dag_id=context["dag"].dag_id,
        run_id=context["run_id"],
        detail=detail,
    )
    _post_to_slack(payload)


def notify_success(**context: Any) -> None:
    """PythonOperator callable: wired as the final ALL_SUCCESS task in the DAG."""
    payload = build_slack_payload(
        "success",
        dag_id=context["dag"].dag_id,
        run_id=context["run_id"],
    )
    _post_to_slack(payload)
