from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "dags"))

from telegram_notifications import _read_secret, build_message


def test_build_message_success_uses_check_emoji() -> None:
    text = build_message("success", dag_id="stock_lakehouse_daily", run_id="manual__2026-07-06")

    assert "✅" in text
    assert "stock_lakehouse_daily" in text
    assert "manual__2026-07-06" in text
    assert "success" in text


def test_build_message_failure_uses_cross_emoji_and_detail() -> None:
    text = build_message(
        "failed",
        dag_id="stock_lakehouse_daily",
        run_id="scheduled__2026-07-06",
        detail="Task quality_all failed. Log: http://airflow/log",
    )

    assert "❌" in text
    assert "failed" in text
    assert "quality_all" in text
    assert "http://airflow/log" in text


def test_read_secret_prefers_file_over_env(tmp_path, monkeypatch) -> None:
    secret_file = tmp_path / "token.txt"
    secret_file.write_text("FROM_FILE\n", encoding="utf-8")

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN_FILE", str(secret_file))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "FROM_ENV")

    assert _read_secret("TELEGRAM_BOT_TOKEN") == "FROM_FILE"


def test_read_secret_falls_back_to_env(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "FROM_ENV")

    assert _read_secret("TELEGRAM_BOT_TOKEN") == "FROM_ENV"


def test_read_secret_returns_none_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    assert _read_secret("TELEGRAM_BOT_TOKEN") is None
