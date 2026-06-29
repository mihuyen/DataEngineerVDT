from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONDITION_TYPES = (
    "PRICE_ABOVE",
    "PRICE_BELOW",
    "RSI_ABOVE",
    "RSI_BELOW",
    "BB_BREAK",
    "VWAP_DEVIATION",
    "INTRADAY_VOLUME_SPIKE",
    "INTRADAY_BREAKOUT",
)


@dataclass(frozen=True)
class AlertRule:
    alert_id: str
    user_id: str
    ticker: str
    condition_type: str
    threshold_value: float
    channel: str
    cooldown_minutes: int


def evaluate_condition(rule: AlertRule, market: dict[str, Any]) -> float | None:
    """Return the actual value that triggered the rule, or None if the condition is not met.

    `market` holds the latest known indicator values for `rule.ticker`:
    close, rsi_14, bb_upper, bb_lower (from fact_daily_price) and
    price_vs_session_vwap_pct (from fact_realtime_vwap).
    """
    condition = rule.condition_type
    threshold = rule.threshold_value

    if condition == "PRICE_ABOVE":
        price = market.get("close")
        return price if price is not None and price > threshold else None

    if condition == "PRICE_BELOW":
        price = market.get("close")
        return price if price is not None and price < threshold else None

    if condition == "RSI_ABOVE":
        rsi = market.get("rsi_14")
        return rsi if rsi is not None and rsi > threshold else None

    if condition == "RSI_BELOW":
        rsi = market.get("rsi_14")
        return rsi if rsi is not None and rsi < threshold else None

    if condition == "BB_BREAK":
        close = market.get("close")
        if close is None:
            return None
        bb_upper = market.get("bb_upper")
        bb_lower = market.get("bb_lower")
        if bb_upper is not None and close > bb_upper:
            return close
        if bb_lower is not None and close < bb_lower:
            return close
        return None

    if condition == "VWAP_DEVIATION":
        deviation = market.get("price_vs_session_vwap_pct")
        return deviation if deviation is not None and abs(deviation) > threshold else None

    if condition == "INTRADAY_VOLUME_SPIKE":
        # threshold is a multiple of the trailing 20-minute average volume
        # (e.g. 2.0 = latest minute's volume is at least 2x that average).
        ratio = market.get("intraday_volume_ratio")
        return ratio if ratio is not None and ratio > threshold else None

    if condition == "INTRADAY_BREAKOUT":
        # threshold is a % buffer past the trailing 20-minute high/low (0 =
        # break the level exactly; a small positive value damps noise from
        # prices hovering right at the band).
        close = market.get("close")
        rolling_high = market.get("intraday_rolling_high_20")
        rolling_low = market.get("intraday_rolling_low_20")
        if close is None:
            return None
        if rolling_high is not None and close > rolling_high * (1 + threshold / 100):
            return close
        if rolling_low is not None and close < rolling_low * (1 - threshold / 100):
            return close
        return None

    raise ValueError(f"Unknown condition_type: {condition}")
