from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from src.alert_engine.notifier import DELIVERY_SENT, send_batch_notification
from src.alert_engine.rules import CROSSING_METRIC_FIELD, AlertRule, evaluate_condition

ALL_TICKERS_WILDCARD = "ALL"
# Scans only the user's own watchlist instead of every HOSE ticker -- the
# recommended default for new rules, since a ticker="ALL" rule matching
# dozens of tickers every cycle is what caused the original notification
# spam (see notifier.py's batching fix). Most rules should not need the
# full market, just the names someone is actually tracking.
WATCHLIST_WILDCARD = "WATCHLIST"


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


def fetch_watchlist_tickers(pg_conn: Any, user_id: str) -> list[str]:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT ticker FROM watchlist WHERE user_id = %s ORDER BY ticker", (user_id,))
        return [row[0] for row in cur.fetchall()]


def expand_wildcard_rules(
    rules: list[AlertRule],
    hose_tickers: list[str],
    watchlist_tickers_by_user: dict[str, list[str]] | None = None,
) -> list[AlertRule]:
    """Turn each ticker='ALL'/'WATCHLIST' rule into one concrete rule per matching ticker."""
    watchlist_tickers_by_user = watchlist_tickers_by_user or {}
    expanded: list[AlertRule] = []
    for rule in rules:
        if rule.ticker == ALL_TICKERS_WILDCARD:
            expanded.extend(replace(rule, ticker=ticker) for ticker in hose_tickers)
        elif rule.ticker == WATCHLIST_WILDCARD:
            expanded.extend(
                replace(rule, ticker=ticker) for ticker in watchlist_tickers_by_user.get(rule.user_id, [])
            )
        else:
            expanded.append(rule)
    return expanded


def fetch_latest_market_data(ch_client: Any, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    tickers_sql = quote_tickers(tickers)
    market: dict[str, dict[str, Any]] = {}

    # Reads rsi_14/bb_upper/bb_lower from fact_daily_price_indicators (dbt),
    # not fact_daily_price's own independently Python-computed columns of
    # the same name -- only the dbt table's values are covered by dbt test's
    # formula checks (RSI range, Bollinger ordering), so alert rules should
    # trigger off those, not the unvalidated Python copy.
    daily = ch_client.query(
        f"""
        SELECT ticker, close, rsi_14, bb_upper, bb_lower
        FROM fact_daily_price_indicators
        WHERE trading_date = (SELECT max(trading_date) FROM fact_daily_price_indicators)
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
          AND data_source = 'DNSE'
          AND toDate(minute_ts) = today()
        GROUP BY ticker
        """
    )
    for ticker, deviation in realtime.result_rows:
        market.setdefault(ticker, {})["price_vs_session_vwap_pct"] = deviation

    # Trailing 20-minute volume average and high/low band, evaluated only at
    # the latest minute per ticker (rn = 1) -- this is what
    # INTRADAY_VOLUME_SPIKE/INTRADAY_BREAKOUT compare the current minute
    # against. The "1 PRECEDING" window deliberately excludes the current
    # minute itself, so a single huge print can't inflate its own baseline
    # and mask the spike it's supposed to trigger.
    intraday = ch_client.query(
        f"""
        WITH agg AS (
            SELECT
              ticker, minute_ts, close, volume,
              avg(volume) OVER (PARTITION BY ticker ORDER BY minute_ts ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS vol_avg_20,
              max(high) OVER (PARTITION BY ticker ORDER BY minute_ts ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS rolling_high_20,
              min(low) OVER (PARTITION BY ticker ORDER BY minute_ts ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS rolling_low_20,
              row_number() OVER (PARTITION BY ticker ORDER BY minute_ts DESC) AS rn
            FROM fact_intraday_ohlcv
            WHERE trading_date = today() AND ticker IN ({tickers_sql})
        )
        SELECT ticker, close, volume, vol_avg_20, rolling_high_20, rolling_low_20
        FROM agg
        WHERE rn = 1
        """
    )
    for ticker, close, volume, vol_avg_20, rolling_high_20, rolling_low_20 in intraday.result_rows:
        entry = market.setdefault(ticker, {})
        # Overrides the EOD close set above with today's latest traded
        # price whenever it exists -- PRICE_ABOVE/BELOW and BB_BREAK were
        # comparing against yesterday's close even during a live session,
        # and INTRADAY_BREAKOUT was comparing yesterday's close against
        # today's 20-minute band, which is not a meaningful comparison at
        # all (two different sessions' price levels).
        entry["close"] = close
        entry["intraday_volume_ratio"] = (volume / vol_avg_20) if vol_avg_20 else None
        entry["intraday_rolling_high_20"] = rolling_high_20
        entry["intraday_rolling_low_20"] = rolling_low_20

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


def fetch_rule_state(ch_client: Any, alert_ids: list[str]) -> dict[tuple[str, str], float]:
    """Latest persisted metric value per (alert_id, ticker), for *_CROSS_* conditions.

    argMax(metric_value, updated_at) rather than relying on ReplacingMergeTree's
    own deduplication: that only happens at merge time, which is not
    immediate, so a plain SELECT could still return a stale duplicate row
    right after an insert.
    """
    if not alert_ids:
        return {}
    alert_ids_sql = ", ".join("'" + alert_id.replace("'", "") + "'" for alert_id in alert_ids)
    result = ch_client.query(
        f"""
        SELECT alert_id, ticker, argMax(metric_value, updated_at) AS value
        FROM fact_alert_rule_state
        WHERE alert_id IN ({alert_ids_sql})
        GROUP BY alert_id, ticker
        """
    )
    return {(alert_id, ticker): value for alert_id, ticker, value in result.result_rows}


def persist_rule_state(ch_client: Any, alert_id: str, ticker: str, metric_value: float) -> None:
    ch_client.insert(
        "fact_alert_rule_state",
        [[alert_id, ticker, float(metric_value), datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)]],
        column_names=["alert_id", "ticker", "metric_value", "updated_at"],
    )


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
    represented by the row that opened the cooldown window. Otherwise it is
    queued for delivery.

    Rules that pass cooldown are NOT notified one-by-one: a wildcard rule
    (ticker = "ALL") can match dozens of tickers in the same cycle, and
    sending one Telegram/email message per ticker floods the channel with
    that many pushes at once. Everything that fires in one cycle for the
    same (user_id, channel) is instead grouped into a single digest message,
    sent once, with the same delivery_status then recorded for every rule in
    that group.
    """
    raw_rules = load_active_rules(pg_conn)
    if any(rule.ticker == ALL_TICKERS_WILDCARD for rule in raw_rules):
        hose_tickers = fetch_hose_tickers(ch_client)
    else:
        hose_tickers = []
    watchlist_users = {rule.user_id for rule in raw_rules if rule.ticker == WATCHLIST_WILDCARD}
    watchlist_tickers_by_user = {user_id: fetch_watchlist_tickers(pg_conn, user_id) for user_id in watchlist_users}
    rules = expand_wildcard_rules(raw_rules, hose_tickers, watchlist_tickers_by_user)
    market = fetch_latest_market_data(ch_client, sorted({rule.ticker for rule in rules}))

    # *_CROSS_* conditions need last cycle's value of whatever metric they
    # track to detect an edge -- fetched once up front for every alert_id
    # that needs it, rather than one query per rule per ticker.
    crossing_alert_ids = sorted({rule.alert_id for rule in rules if rule.condition_type in CROSSING_METRIC_FIELD})
    previous_state = fetch_rule_state(ch_client, crossing_alert_ids)

    results: list[CheckResult] = []
    # Keyed by (user_id, channel): pending (rule, actual_value, result) for
    # everything that fired this cycle and isn't in cooldown, so each group
    # can be sent as one digest and have its single delivery_status written
    # back onto every CheckResult in the group below.
    to_notify: dict[tuple[str, str], list[tuple[AlertRule, float, CheckResult]]] = {}
    for rule in rules:
        data = market.get(rule.ticker)
        if not data:
            results.append(
                CheckResult(rule, triggered=False, skipped_cooldown=False, actual_value=None, delivery_status=None)
            )
            continue

        metric_field = CROSSING_METRIC_FIELD.get(rule.condition_type)
        previous_value = previous_state.get((rule.alert_id, rule.ticker)) if metric_field else None
        actual_value = evaluate_condition(rule, data, previous_value)

        # Persisted every cycle regardless of whether the rule triggers --
        # next cycle's crossing check needs this cycle's value as its
        # "previous", not just the value from the last time it fired.
        if metric_field is not None:
            current_metric = data.get(metric_field)
            if current_metric is not None:
                persist_rule_state(ch_client, rule.alert_id, rule.ticker, current_metric)

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

        result = CheckResult(
            rule, triggered=True, skipped_cooldown=False, actual_value=actual_value, delivery_status=None
        )
        results.append(result)
        to_notify.setdefault((rule.user_id, rule.channel), []).append((rule, actual_value, result))

    for (_user_id, channel), pending in to_notify.items():
        delivery_status = send_batch_notification(channel, [(rule, value) for rule, value, _ in pending])
        for rule, actual_value, result in pending:
            record_alert_event(ch_client, rule, actual_value, delivery_status=delivery_status)
            result.delivery_status = delivery_status

    return results
