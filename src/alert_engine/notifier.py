from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

from src.alert_engine.rules import AlertRule
from src.common.secrets import get_secret

load_dotenv()

logger = logging.getLogger(__name__)

CONDITION_LABELS = {
    "PRICE_ABOVE": "Giá vượt ngưỡng",
    "PRICE_BELOW": "Giá dưới ngưỡng",
    "RSI_ABOVE": "RSI quá mua",
    "RSI_BELOW": "RSI quá bán",
    "BB_BREAK": "Vượt Bollinger Band",
    "VWAP_DEVIATION": "Lệch VWAP",
    "INTRADAY_VOLUME_SPIKE": "Khối lượng đột biến",
    "INTRADAY_BREAKOUT": "Breakout trong phiên",
}


def format_alert_message(rule: AlertRule, actual_value: float) -> str:
    label = CONDITION_LABELS.get(rule.condition_type, rule.condition_type)
    return (
        f"[Alert] {rule.ticker} - {label}\n"
        f"Threshold: {rule.threshold_value}\n"
        f"Actual: {actual_value:.2f}"
    )


# Hard cap on how many ticker lines a single digest message lists, so a
# wildcard rule (ticker = "ALL") matching e.g. 80 tickers in one check cycle
# still produces one short, readable message instead of one that's
# borderline too long to read (Telegram's actual limit is 4096 characters --
# this cap exists for readability, not to avoid hitting it).
MAX_BATCH_LINES_PER_CONDITION = 25


def format_batch_message(triggers: list[tuple[AlertRule, float]]) -> str:
    """One digest message for every rule that fired in a single check cycle.

    Sending one Telegram/email message per ticker (the original behavior)
    means a wildcard rule matching dozens of tickers in the same cycle
    floods the channel with that many separate notifications at once.
    Grouping everything from one cycle into a single message turns that into
    one push per condition type per cycle.
    """
    by_condition: dict[str, list[tuple[AlertRule, float]]] = {}
    for rule, actual_value in triggers:
        by_condition.setdefault(rule.condition_type, []).append((rule, actual_value))

    sections = []
    for condition_type, rows in sorted(by_condition.items()):
        label = CONDITION_LABELS.get(condition_type, condition_type)
        lines = [f"{rule.ticker}: {actual_value:.2f} (ngưỡng {rule.threshold_value})" for rule, actual_value in rows]
        shown = lines[:MAX_BATCH_LINES_PER_CONDITION]
        remaining = len(lines) - len(shown)
        body = "\n".join(shown)
        if remaining > 0:
            body += f"\n... và {remaining} mã khác"
        sections.append(f"[{label}] ({len(rows)} mã)\n{body}")

    return f"[Stock Alert] {len(triggers)} điều kiện kích hoạt:\n\n" + "\n\n".join(sections)


def send_batch_notification(channel: str, triggers: list[tuple[AlertRule, float]]) -> str:
    """Send one digest covering every rule that fired for `channel` this cycle."""
    if not triggers:
        return DELIVERY_SENT
    message = format_batch_message(triggers)
    if channel == "TELEGRAM":
        return send_telegram(message)
    if channel == "EMAIL":
        return send_email(message)
    logger.warning("Unknown channel %s, batch alert not sent: %s", channel, message)
    return DELIVERY_UNKNOWN_CHANNEL


DELIVERY_SENT = "sent"
DELIVERY_SEND_FAILED = "send_failed"
DELIVERY_CHANNEL_NOT_CONFIGURED = "channel_not_configured"
DELIVERY_UNKNOWN_CHANNEL = "unknown_channel"


def send_telegram(message: str) -> str:
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.info("Telegram credentials missing, alert not sent: %s", message)
        return DELIVERY_CHANNEL_NOT_CONFIGURED
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        return DELIVERY_SENT if response.ok else DELIVERY_SEND_FAILED
    except requests.RequestException:
        logger.exception("Failed to send Telegram alert")
        return DELIVERY_SEND_FAILED


def send_email(message: str) -> str:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = get_secret("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or username
    recipients = [
        recipient.strip()
        for recipient in os.getenv("SMTP_TO", "").split(",")
        if recipient.strip()
    ]
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    if not host or not username or not password or not sender or not recipients:
        logger.info("SMTP not configured, alert not sent: %s", message)
        return DELIVERY_CHANNEL_NOT_CONFIGURED

    mail = EmailMessage()
    mail["Subject"] = os.getenv("SMTP_SUBJECT", "Stocky - Stock Alert")
    mail["From"] = sender
    mail["To"] = ", ".join(recipients)
    mail.set_content(message)

    context = ssl.create_default_context()
    try:
        if use_ssl:
            smtp_client = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        else:
            smtp_client = smtplib.SMTP(host, port, timeout=15)
        with smtp_client as smtp:
            if use_tls and not use_ssl:
                smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(mail)
        return DELIVERY_SENT
    except (OSError, smtplib.SMTPException, ValueError):
        logger.exception("Failed to send email alert")
        return DELIVERY_SEND_FAILED


def send_notification(rule: AlertRule, actual_value: float) -> str:
    """Attempt delivery and return one of the DELIVERY_* status constants."""
    message = format_alert_message(rule, actual_value)
    if rule.channel == "TELEGRAM":
        return send_telegram(message)
    if rule.channel == "EMAIL":
        return send_email(message)
    logger.warning("Unknown channel %s, alert not sent: %s", rule.channel, message)
    return DELIVERY_UNKNOWN_CHANNEL
