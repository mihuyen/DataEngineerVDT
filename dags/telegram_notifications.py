from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from typing import Any


def _read_secret(env_name: str) -> str | None:
    """Read a Telegram credential, Docker-secret-file convention first.

    Mirrors src/common/secrets.get_secret's `{NAME}_FILE` convention (Docker
    secret / mounted file takes priority over a plain env var), reimplemented
    with stdlib only: DAG files are parsed inside Airflow's own Python
    environment (see docker/airflow.Dockerfile), not the project's
    .venv-stock, so this avoids depending on python-dotenv or the project
    package being importable there.
    """
    file_path = os.getenv(f"{env_name}_FILE")
    if file_path and os.path.isfile(file_path):
        return open(file_path, encoding="utf-8").read().strip()
    return os.getenv(env_name) or None


def build_message(status: str, dag_id: str, run_id: str, detail: str = "") -> str:
    """Build the Telegram message text for a DAG run outcome."""
    emoji = "✅" if status == "success" else "❌"
    lines = [f"{emoji} {dag_id} — run {run_id} {status}."]
    if detail:
        lines.append(detail)
    return "\n".join(lines)


def _post_to_telegram(text: str) -> None:
    bot_token = _read_secret("TELEGRAM_BOT_TOKEN")
    chat_id = _read_secret("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured; skipping Telegram notification.")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except Exception as exc:  # noqa: BLE001 - notification must never fail the DAG
        print(f"Telegram notification failed: {exc}")


def notify_failure(context: dict[str, Any]) -> None:
    """Airflow on_failure_callback: fires per failed task (after retries)."""
    task_instance = context["task_instance"]
    detail = f"Task {task_instance.task_id} failed. Log: {task_instance.log_url}"
    text = build_message(
        "failed",
        dag_id=context["dag"].dag_id,
        run_id=context["run_id"],
        detail=detail,
    )
    _post_to_telegram(text)


def notify_success(**context: Any) -> None:
    """PythonOperator callable: wired as the final ALL_SUCCESS task in the DAG."""
    text = build_message(
        "success",
        dag_id=context["dag"].dag_id,
        run_id=context["run_id"],
    )
    _post_to_telegram(text)
