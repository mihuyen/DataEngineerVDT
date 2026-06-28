from __future__ import annotations

import logging
import os

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


def send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.info("Telegram credentials missing, alert not sent: %s", message)
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        return response.ok
    except requests.RequestException:
        logger.exception("Failed to send Telegram alert")
        return False


def send_email(message: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        logger.info("SMTP not configured, alert not sent: %s", message)
        return False
    logger.info("SMTP sending not implemented yet, alert logged only: %s", message)
    return False


def send_notification(rule: AlertRule, actual_value: float) -> bool:
    message = format_alert_message(rule, actual_value)
    if rule.channel == "TELEGRAM":
        return send_telegram(message)
    if rule.channel == "EMAIL":
        return send_email(message)
    logger.warning("Unknown channel %s, alert not sent: %s", rule.channel, message)
    return False
