from __future__ import annotations

import smtplib

from src.alert_engine import notifier


SMTP_ENV_KEYS = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_TO",
    "SMTP_USE_TLS",
    "SMTP_USE_SSL",
)


def configure_smtp(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    monkeypatch.setenv("SMTP_TO", "one@example.com,two@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_USE_SSL", "false")


def test_send_email_reports_missing_configuration(monkeypatch) -> None:
    for key in SMTP_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    assert notifier.send_email("test") == notifier.DELIVERY_CHANNEL_NOT_CONFIGURED


def test_send_email_uses_starttls_and_multiple_recipients(monkeypatch) -> None:
    configure_smtp(monkeypatch)
    calls: list[object] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def starttls(self, context) -> None:
            calls.append(("starttls", context is not None))

        def login(self, username: str, password: str) -> None:
            calls.append(("login", username, password))

        def send_message(self, message) -> None:
            calls.append(("send", message["From"], message["To"], message.get_content().strip()))

    monkeypatch.setattr(notifier.smtplib, "SMTP", FakeSMTP)

    assert notifier.send_email("Stock alert") == notifier.DELIVERY_SENT
    assert ("connect", "smtp.example.com", 587, 15) in calls
    assert ("starttls", True) in calls
    assert ("login", "sender@example.com", "app-password") in calls
    assert ("send", "sender@example.com", "one@example.com, two@example.com", "Stock alert") in calls


def test_send_email_reports_smtp_failure(monkeypatch) -> None:
    configure_smtp(monkeypatch)

    class FailingSMTP:
        def __init__(self, *_args, **_kwargs) -> None:
            raise smtplib.SMTPException("connection failed")

    monkeypatch.setattr(notifier.smtplib, "SMTP", FailingSMTP)

    assert notifier.send_email("test") == notifier.DELIVERY_SEND_FAILED
