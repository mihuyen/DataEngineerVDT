from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from src.alert_engine.notifier import send_notification
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
    result = ch_client.query(
        f"""
        SELECT count() AS cnt
        FROM fact_alert_event
        WHERE user_id = {{user_id:String}}
          AND ticker = {{ticker:String}}
          AND condition_type = {{condition_type:String}}
          AND is_sent = 1
          AND triggered_at >= now() - INTERVAL {int(rule.cooldown_minutes)} MINUTE
        """,
        parameters={
            "user_id": rule.user_id,
            "ticker": rule.ticker,
            "condition_type": rule.condition_type,
        },
    )
    return result.result_rows[0][0] > 0


def record_alert_event(ch_client: Any, rule: AlertRule, actual_value: float, is_sent: bool) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    date_id = int(now.strftime("%Y%m%d"))
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
                1 if is_sent else 0,
                now if is_sent else None,
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
            "is_sent",
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
    sent: bool


def run_check_cycle(pg_conn: Any, ch_client: Any) -> list[CheckResult]:
    """Evaluate every active user_alerts rule against the latest Gold data.

    For each rule that triggers: if a matching alert (same user_id + ticker +
    condition_type) was already sent within its cooldown window, the event is
    still logged to fact_alert_event with is_sent=0 (audit trail) but no
    notification goes out. Otherwise the notifier is invoked and the event is
    logged with is_sent reflecting whether delivery succeeded.
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
                CheckResult(rule, triggered=False, skipped_cooldown=False, actual_value=None, sent=False)
            )
            continue

        actual_value = evaluate_condition(rule, data)
        if actual_value is None:
            results.append(
                CheckResult(rule, triggered=False, skipped_cooldown=False, actual_value=None, sent=False)
            )
            continue

        if is_in_cooldown(ch_client, rule):
            record_alert_event(ch_client, rule, actual_value, is_sent=False)
            results.append(
                CheckResult(rule, triggered=True, skipped_cooldown=True, actual_value=actual_value, sent=False)
            )
            continue

        sent = send_notification(rule, actual_value)
        record_alert_event(ch_client, rule, actual_value, is_sent=sent)
        results.append(
            CheckResult(rule, triggered=True, skipped_cooldown=False, actual_value=actual_value, sent=sent)
        )

    return results
