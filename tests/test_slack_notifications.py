from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "dags"))

from slack_notifications import _read_webhook_url, build_slack_payload


def test_build_slack_payload_success_uses_check_emoji() -> None:
    payload = build_slack_payload("success", dag_id="stock_lakehouse_daily", run_id="manual__2026-07-06")

    assert "✅" in payload["text"]
    assert "stock_lakehouse_daily" in payload["text"]
    assert "manual__2026-07-06" in payload["text"]
    assert "success" in payload["text"]


def test_build_slack_payload_failure_uses_cross_emoji_and_detail() -> None:
    payload = build_slack_payload(
        "failed",
        dag_id="stock_lakehouse_daily",
        run_id="scheduled__2026-07-06",
        detail="Task `quality_all` failed. Log: http://airflow/log",
    )

    assert "❌" in payload["text"]
    assert "failed" in payload["text"]
    assert "quality_all" in payload["text"]
    assert "http://airflow/log" in payload["text"]


def test_read_webhook_url_prefers_file_over_env(tmp_path, monkeypatch) -> None:
    secret_file = tmp_path / "webhook.txt"
    secret_file.write_text("https://hooks.slack.com/services/FROM_FILE\n", encoding="utf-8")

    monkeypatch.setenv("SLACK_WEBHOOK_URL_FILE", str(secret_file))
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/FROM_ENV")

    assert _read_webhook_url() == "https://hooks.slack.com/services/FROM_FILE"


def test_read_webhook_url_falls_back_to_env(monkeypatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL_FILE", raising=False)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/FROM_ENV")

    assert _read_webhook_url() == "https://hooks.slack.com/services/FROM_ENV"


def test_read_webhook_url_returns_none_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL_FILE", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    assert _read_webhook_url() is None
