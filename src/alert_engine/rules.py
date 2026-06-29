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
    "STOP_LOSS",
    "TAKE_PROFIT",
    "VWAP_CROSS_UP",
    "VWAP_CROSS_DOWN",
    "RSI_CROSS_UP",
    "RSI_CROSS_DOWN",
)

# Crossing conditions need the *previous* cycle's metric value to detect an
# edge (e.g. RSI just moved from 28 to 32, crossing up through 30) -- unlike
# every other condition type here, which only looks at the current value.
# This maps each one to which market field it tracks, so the engine knows
# what to persist into fact_alert_rule_state every cycle (not just when the
# rule actually fires) regardless of trigger.
CROSSING_METRIC_FIELD = {
    "VWAP_CROSS_UP": "price_vs_session_vwap_pct",
    "VWAP_CROSS_DOWN": "price_vs_session_vwap_pct",
    "RSI_CROSS_UP": "rsi_14",
    "RSI_CROSS_DOWN": "rsi_14",
}


@dataclass(frozen=True)
class AlertRule:
    alert_id: str
    user_id: str
    ticker: str
    condition_type: str
    threshold_value: float
    channel: str
    cooldown_minutes: int


def evaluate_condition(
    rule: AlertRule, market: dict[str, Any], previous_value: float | None = None
) -> float | None:
    """Return the actual value that triggered the rule, or None if the condition is not met.

    `market` holds the latest known indicator values for `rule.ticker`:
    close, rsi_14, bb_upper, bb_lower (from fact_daily_price) and
    price_vs_session_vwap_pct (from fact_realtime_vwap).

    `previous_value` is only used by the *_CROSS_* condition types (see
    CROSSING_METRIC_FIELD) -- the prior cycle's value of whichever metric
    that condition tracks, fetched by the engine from fact_alert_rule_state.
    It is None on every other condition type, and also on a crossing
    condition's very first evaluation for a given (alert, ticker) before any
    state has been recorded yet -- both cases correctly evaluate to "no
    trigger" below, since a crossing can't be detected without a prior
    value to compare against.
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

    if condition == "STOP_LOSS":
        # Same comparison as PRICE_BELOW, but named for what it's actually
        # used for -- threshold is the stop price the user picked themself
        # (no cost-basis/holdings data exists in this app to derive it).
        price = market.get("close")
        return price if price is not None and price <= threshold else None

    if condition == "TAKE_PROFIT":
        price = market.get("close")
        return price if price is not None and price >= threshold else None

    if condition == "VWAP_CROSS_UP":
        # threshold is unused -- a cross is a discrete event (was at/below
        # VWAP, now above it), not a magnitude to compare against.
        deviation = market.get("price_vs_session_vwap_pct")
        if deviation is None or previous_value is None:
            return None
        return deviation if previous_value <= 0 and deviation > 0 else None

    if condition == "VWAP_CROSS_DOWN":
        deviation = market.get("price_vs_session_vwap_pct")
        if deviation is None or previous_value is None:
            return None
        return deviation if previous_value >= 0 and deviation < 0 else None

    if condition == "RSI_CROSS_UP":
        # threshold is the level being crossed (typically 30, recovering out
        # of oversold) -- unlike RSI_ABOVE/BELOW, this only fires once at the
        # moment of crossing, not on every cycle RSI happens to still be on
        # the same side of it.
        rsi = market.get("rsi_14")
        if rsi is None or previous_value is None:
            return None
        return rsi if previous_value <= threshold and rsi > threshold else None

    if condition == "RSI_CROSS_DOWN":
        rsi = market.get("rsi_14")
        if rsi is None or previous_value is None:
            return None
        return rsi if previous_value >= threshold and rsi < threshold else None

    raise ValueError(f"Unknown condition_type: {condition}")
