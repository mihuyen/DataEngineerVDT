from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from src.alert_engine.notifier import DELIVERY_SENT, send_notification
from src.alert_engine.rules import AlertRule, evaluate_condition

ALL_TICKERS_WILDCARD = "ALL"


def load_active_rules(pg_conn: Any) -> list[AlertRule]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT alert_id, user_id, ticker, condition_type, threshold_value, channel, cooldown_minutes
            FROM user_alerts
            WHERE is_active = true
            """
        )
        rows = cur.fetchall()
    return [
        AlertRule(
            alert_id=str(row[0]),
            user_id=row[1],
            ticker=row[2],
            condition_type=row[3],
            threshold_value=float(row[4]),
            channel=row[5],
            cooldown_minutes=int(row[6]),
        )
        for row in rows
    ]


def quote_tickers(tickers: list[str]) -> str:
    return ", ".join("'" + ticker.replace("'", "") + "'" for ticker in tickers)


def fetch_hose_tickers(ch_client: Any) -> list[str]:
    """All tickers currently in scope (dim_stock exchange = 'HOSE')."""
    result = ch_client.query("SELECT ticker FROM dim_stock WHERE exchange = 'HOSE' ORDER BY ticker")
    return [row[0] for row in result.result_rows]


def expand_wildcard_rules(rules: list[AlertRule], hose_tickers: list[str]) -> list[AlertRule]:
    """Turn each ticker='ALL' rule into one concrete rule per HOSE ticker."""
    expanded: list[AlertRule] = []
    for rule in rules:
        if rule.ticker == ALL_TICKERS_WILDCARD:
            expanded.extend(replace(rule, ticker=ticker) for ticker in hose_tickers)
        else:
            expanded.append(rule)
    return expanded


def fetch_latest_market_data(ch_client: Any, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    tickers_sql = quote_tickers(tickers)
    market: dict[str, dict[str, Any]] = {}

    daily = ch_client.query(
        f"""
        SELECT ticker, close, rsi_14, bb_upper, bb_lower
        FROM fact_daily_price
        WHERE trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND ticker IN ({tickers_sql})
        """
    )
    for ticker, close, rsi_14, bb_upper, bb_lower in daily.result_rows:
        market.setdefault(ticker, {}).update(
            {"close": close, "rsi_14": rsi_14, "bb_upper": bb_upper, "bb_lower": bb_lower}
        )

    realtime = ch_client.query(
        f"""
        SELECT ticker, argMax(price_vs_session_vwap_pct, minute_ts) AS deviation
        FROM fact_realtime_vwap
        WHERE ticker IN ({tickers_sql})
        GROUP BY ticker
        """
    )
    for ticker, deviation in realtime.result_rows:
        market.setdefault(ticker, {})["price_vs_session_vwap_pct"] = deviation

    return market


def is_in_cooldown(ch_client: Any, rule: AlertRule) -> bool:
    # Count any logged event in the window regardless of delivery_status: if
    # the notification channel is unconfigured (delivery never succeeds),
    # filtering on a successful delivery would mean the same condition never
    # enters cooldown and fact_alert_event grows by one row per rule on every
    # check cycle forever.
    result = ch_client.query(
        f"""
        SELECT count() AS cnt
        FROM fact_alert_event
        WHERE user_id = {{user_id:String}}
          AND ticker = {{ticker:String}}
          AND condition_type = {{condition_type:String}}
          AND channel = {{channel:String}}
          AND triggered_at >= now() - INTERVAL {int(rule.cooldown_minutes)} MINUTE
        """,
        parameters={
            "user_id": rule.user_id,
            "ticker": rule.ticker,
            "condition_type": rule.condition_type,
            "channel": rule.channel,
        },
    )
    return result.result_rows[0][0] > 0


def record_alert_event(ch_client: Any, rule: AlertRule, actual_value: float, delivery_status: str) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    date_id = int(now.strftime("%Y%m%d"))
    sent = delivery_status == DELIVERY_SENT
    ch_client.insert(
        "fact_alert_event",
        [
            [
                str(uuid.uuid4()),
                rule.user_id,
                rule.ticker,
                date_id,
                now,
                rule.condition_type,
                float(rule.threshold_value),
                float(actual_value),
                rule.channel,
                delivery_status,
                now if sent else None,
                now,
            ]
        ],
        column_names=[
            "alert_id",
            "user_id",
            "ticker",
            "date_id",
            "triggered_at",
            "condition_type",
            "threshold_value",
            "actual_value",
            "channel",
            "delivery_status",
            "sent_at",
            "created_at",
        ],
    )


@dataclass
class CheckResult:
    rule: AlertRule
    triggered: bool
    skipped_cooldown: bool
    actual_value: float | None
    delivery_status: str | None

    @property
    def sent(self) -> bool:
        return self.delivery_status == DELIVERY_SENT


def run_check_cycle(pg_conn: Any, ch_client: Any) -> list[CheckResult]:
    """Evaluate every active user_alerts rule against the latest Gold data.

    For each rule that triggers: if a matching alert (same user_id + ticker +
    condition_type) was already logged within its cooldown window, the trigger
    is skipped entirely (no notification, no new row) since it is already
    represented by the row that opened the cooldown window. Otherwise the
    notifier is invoked and the event is logged with delivery_status
    reflecting why delivery did or didn't succeed (sent / send_failed /
    channel_not_configured / unknown_channel).
    """
    raw_rules = load_active_rules(pg_conn)
    if any(rule.ticker == ALL_TICKERS_WILDCARD for rule in raw_rules):
        hose_tickers = fetch_hose_tickers(ch_client)
    else:
        hose_tickers = []
    rules = expand_wildcard_rules(raw_rules, hose_tickers)
    market = fetch_latest_market_data(ch_client, sorted({rule.ticker for rule in rules}))

    results: list[CheckResult] = []
    for rule in rules:
        data = market.get(rule.ticker)
        if not data:
            results.append(
                CheckResult(rule, triggered=False, skipped_cooldown=False, actual_value=None, delivery_status=None)
            )
            continue

        actual_value = evaluate_condition(rule, data)
        if actual_value is None:
            results.append(
                CheckResult(rule, triggered=False, skipped_cooldown=False, actual_value=None, delivery_status=None)
            )
            continue

        if is_in_cooldown(ch_client, rule):
            # Do not insert a row here: the condition is still inside the cooldown
            # window opened by a previous trigger, which is already logged. Logging
            # again on every cycle would make fact_alert_event grow unboundedly for
            # any condition that stays true for longer than cooldown_minutes (e.g. a
            # wildcard rule scanning hundreds of tickers every 60s).
            results.append(
                CheckResult(
                    rule, triggered=True, skipped_cooldown=True, actual_value=actual_value, delivery_status=None
                )
            )
            continue

        delivery_status = send_notification(rule, actual_value)
        record_alert_event(ch_client, rule, actual_value, delivery_status=delivery_status)
        results.append(
            CheckResult(
                rule,
                triggered=True,
                skipped_cooldown=False,
                actual_value=actual_value,
                delivery_status=delivery_status,
            )
        )

    return results
