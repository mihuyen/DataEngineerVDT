from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

from src.alert_engine.rules import AlertRule

load_dotenv()

logger = logging.getLogger(__name__)

CONDITION_LABELS = {
    "PRICE_ABOVE": "Giá vượt ngưỡng",
    "PRICE_BELOW": "Giá dưới ngưỡng",
    "RSI_ABOVE": "RSI quá mua",
    "RSI_BELOW": "RSI quá bán",
    "BB_BREAK": "Vượt Bollinger Band",
    "VWAP_DEVIATION": "Lệch VWAP",
}


def format_alert_message(rule: AlertRule, actual_value: float) -> str:
    label = CONDITION_LABELS.get(rule.condition_type, rule.condition_type)
    return (
        f"[Alert] {rule.ticker} - {label}\n"
        f"Threshold: {rule.threshold_value}\n"
        f"Actual: {actual_value:.2f}"
    )


DELIVERY_SENT = "sent"
DELIVERY_SEND_FAILED = "send_failed"
DELIVERY_CHANNEL_NOT_CONFIGURED = "channel_not_configured"
DELIVERY_UNKNOWN_CHANNEL = "unknown_channel"


def send_telegram(message: str) -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
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
    password = os.getenv("SMTP_PASSWORD")
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
