from __future__ import annotations

import pytest

from src.alert_engine import engine
from src.alert_engine.rules import AlertRule, evaluate_condition


def make_rule(
    condition_type: str,
    threshold: float,
    ticker: str = "VCB",
    cooldown_minutes: int = 30,
) -> AlertRule:
    return AlertRule(
        alert_id="alert-1",
        user_id="demo_user",
        ticker=ticker,
        condition_type=condition_type,
        threshold_value=threshold,
        channel="TELEGRAM",
        cooldown_minutes=cooldown_minutes,
    )


def test_rsi_above_triggers_when_exceeded() -> None:
    rule = make_rule("RSI_ABOVE", 70)
    assert evaluate_condition(rule, {"rsi_14": 72}) == 72


def test_rsi_above_does_not_trigger_when_below_threshold() -> None:
    rule = make_rule("RSI_ABOVE", 70)
    assert evaluate_condition(rule, {"rsi_14": 65}) is None


def test_rsi_below_triggers() -> None:
    rule = make_rule("RSI_BELOW", 30)
    assert evaluate_condition(rule, {"rsi_14": 25}) == 25


def test_price_above_triggers() -> None:
    rule = make_rule("PRICE_ABOVE", 90)
    assert evaluate_condition(rule, {"close": 95}) == 95


def test_price_below_triggers() -> None:
    rule = make_rule("PRICE_BELOW", 90)
    assert evaluate_condition(rule, {"close": 85}) == 85


def test_bb_break_triggers_above_upper_band() -> None:
    rule = make_rule("BB_BREAK", 0)
    assert evaluate_condition(rule, {"close": 105, "bb_upper": 100, "bb_lower": 80}) == 105


def test_bb_break_triggers_below_lower_band() -> None:
    rule = make_rule("BB_BREAK", 0)
    assert evaluate_condition(rule, {"close": 75, "bb_upper": 100, "bb_lower": 80}) == 75


def test_bb_break_no_trigger_inside_band() -> None:
    rule = make_rule("BB_BREAK", 0)
    assert evaluate_condition(rule, {"close": 90, "bb_upper": 100, "bb_lower": 80}) is None


def test_vwap_deviation_triggers_on_absolute_value() -> None:
    rule = make_rule("VWAP_DEVIATION", 2.0)
    assert evaluate_condition(rule, {"price_vs_session_vwap_pct": -3.5}) == -3.5


def test_vwap_deviation_no_trigger_within_band() -> None:
    rule = make_rule("VWAP_DEVIATION", 2.0)
    assert evaluate_condition(rule, {"price_vs_session_vwap_pct": 1.0}) is None


def test_intraday_volume_spike_triggers_above_threshold() -> None:
    rule = make_rule("INTRADAY_VOLUME_SPIKE", 2.0)
    assert evaluate_condition(rule, {"intraday_volume_ratio": 3.2}) == 3.2


def test_intraday_volume_spike_no_trigger_below_threshold() -> None:
    rule = make_rule("INTRADAY_VOLUME_SPIKE", 2.0)
    assert evaluate_condition(rule, {"intraday_volume_ratio": 1.1}) is None


def test_intraday_breakout_triggers_above_rolling_high() -> None:
    rule = make_rule("INTRADAY_BREAKOUT", 0.0)
    assert evaluate_condition(rule, {"close": 105, "intraday_rolling_high_20": 100, "intraday_rolling_low_20": 80}) == 105


def test_intraday_breakout_triggers_below_rolling_low() -> None:
    rule = make_rule("INTRADAY_BREAKOUT", 0.0)
    assert evaluate_condition(rule, {"close": 75, "intraday_rolling_high_20": 100, "intraday_rolling_low_20": 80}) == 75


def test_intraday_breakout_no_trigger_inside_band() -> None:
    rule = make_rule("INTRADAY_BREAKOUT", 0.0)
    assert evaluate_condition(rule, {"close": 90, "intraday_rolling_high_20": 100, "intraday_rolling_low_20": 80}) is None


def test_intraday_breakout_threshold_buffer_damps_noise() -> None:
    rule = make_rule("INTRADAY_BREAKOUT", 5.0)
    # 1% past the rolling high is inside a 5% buffer, so no trigger yet.
    assert evaluate_condition(rule, {"close": 101, "intraday_rolling_high_20": 100, "intraday_rolling_low_20": 80}) is None


def test_missing_market_field_returns_none() -> None:
    rule = make_rule("RSI_ABOVE", 70)
    assert evaluate_condition(rule, {}) is None


def test_unknown_condition_type_raises() -> None:
    rule = make_rule("UNKNOWN", 1)
    with pytest.raises(ValueError):
        evaluate_condition(rule, {"close": 1})


class FakeCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def execute(self, sql: str, params: tuple | None = None) -> None:
        pass

    def fetchall(self) -> list[tuple]:
        return self._rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class FakePgConnection:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._rows)


class FakeQueryResult:
    def __init__(self, result_rows: list[tuple]) -> None:
        self.result_rows = result_rows


class FakeClickHouseClient:
    def __init__(
        self,
        daily_rows: list[tuple],
        realtime_rows: list[tuple],
        cooldown_hits: set[tuple],
        hose_tickers: list[str] | None = None,
    ) -> None:
        self._daily_rows = daily_rows
        self._realtime_rows = realtime_rows
        self._cooldown_hits = cooldown_hits
        self._hose_tickers = hose_tickers or []
        self.inserted: list[tuple] = []

    def query(self, sql: str, parameters: dict | None = None) -> FakeQueryResult:
        if "fact_alert_event" in sql:
            assert parameters is not None
            key = (
                parameters["user_id"],
                parameters["ticker"],
                parameters["condition_type"],
                parameters["channel"],
            )
            return FakeQueryResult([[1 if key in self._cooldown_hits else 0]])
        if "dim_stock" in sql:
            return FakeQueryResult([[ticker] for ticker in self._hose_tickers])
        if "fact_realtime_vwap" in sql:
            return FakeQueryResult(self._realtime_rows)
        return FakeQueryResult(self._daily_rows)

    def insert(self, table: str, rows: list[list], column_names: list[str]) -> None:
        self.inserted.append((table, rows, column_names))


def test_run_check_cycle_triggers_and_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "send_batch_notification", lambda channel, triggers: "sent")

    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "VCB", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[("VCB", 95.0, 72.0, 100.0, 80.0)],
        realtime_rows=[],
        cooldown_hits=set(),
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert len(results) == 1
    assert results[0].triggered is True
    assert results[0].skipped_cooldown is False
    assert results[0].sent is True
    assert results[0].delivery_status == "sent"
    assert results[0].actual_value == 72.0
    assert len(ch_client.inserted) == 1
    _, rows, columns = ch_client.inserted[0]
    assert rows[0][columns.index("delivery_status")] == "sent"


def test_run_check_cycle_records_channel_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "send_batch_notification", lambda channel, triggers: "channel_not_configured")

    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "VCB", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[("VCB", 95.0, 72.0, 100.0, 80.0)],
        realtime_rows=[],
        cooldown_hits=set(),
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert results[0].sent is False
    assert results[0].delivery_status == "channel_not_configured"
    _, rows, columns = ch_client.inserted[0]
    assert rows[0][columns.index("delivery_status")] == "channel_not_configured"
    assert rows[0][columns.index("sent_at")] is None


def test_run_check_cycle_does_not_trigger_when_condition_not_met() -> None:
    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "VCB", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[("VCB", 95.0, 50.0, 100.0, 80.0)],
        realtime_rows=[],
        cooldown_hits=set(),
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert results[0].triggered is False
    assert ch_client.inserted == []


def test_run_check_cycle_skips_when_in_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    send_calls = []
    monkeypatch.setattr(engine, "send_batch_notification", lambda channel, triggers: send_calls.append(triggers) or "sent")

    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "VCB", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[("VCB", 95.0, 72.0, 100.0, 80.0)],
        realtime_rows=[],
        cooldown_hits={("demo_user", "VCB", "RSI_ABOVE", "TELEGRAM")},
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert results[0].triggered is True
    assert results[0].skipped_cooldown is True
    assert results[0].sent is False
    assert send_calls == []
    assert len(ch_client.inserted) == 0


def test_cooldown_is_scoped_to_notification_channel() -> None:
    ch_client = FakeClickHouseClient(
        daily_rows=[],
        realtime_rows=[],
        cooldown_hits={("demo_user", "VCB", "RSI_ABOVE", "TELEGRAM")},
    )
    email_rule = AlertRule(
        alert_id="alert-email",
        user_id="demo_user",
        ticker="VCB",
        condition_type="RSI_ABOVE",
        threshold_value=70.0,
        channel="EMAIL",
        cooldown_minutes=30,
    )

    assert engine.is_in_cooldown(ch_client, email_rule) is False


def test_run_check_cycle_skips_ticker_with_no_market_data() -> None:
    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "ZZZ", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(daily_rows=[], realtime_rows=[], cooldown_hits=set())

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert results[0].triggered is False


def test_wildcard_rule_expands_to_every_hose_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "send_batch_notification", lambda channel, triggers: "sent")

    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "ALL", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[
            ("AAA", 10.0, 80.0, 11.0, 9.0),
            ("BBB", 20.0, 50.0, 21.0, 19.0),
            ("CCC", 30.0, 90.0, 31.0, 29.0),
        ],
        realtime_rows=[],
        cooldown_hits=set(),
        hose_tickers=["AAA", "BBB", "CCC"],
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert len(results) == 3
    triggered_tickers = {r.rule.ticker for r in results if r.triggered}
    assert triggered_tickers == {"AAA", "CCC"}
    assert len(ch_client.inserted) == 2


def test_wildcard_rule_sends_one_batched_notification_not_one_per_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wildcard rule matching many tickers in one cycle must send one digest,
    not one notification per ticker -- the original per-ticker behavior is
    what caused real Telegram/email spam once a real channel was wired up.
    """
    batch_calls = []
    monkeypatch.setattr(
        engine,
        "send_batch_notification",
        lambda channel, triggers: batch_calls.append((channel, triggers)) or "sent",
    )

    pg_conn = FakePgConnection(
        [("alert-1", "demo_user", "ALL", "RSI_ABOVE", 70.0, "TELEGRAM", 30)]
    )
    ch_client = FakeClickHouseClient(
        daily_rows=[
            ("AAA", 10.0, 80.0, 11.0, 9.0),
            ("BBB", 20.0, 50.0, 21.0, 19.0),
            ("CCC", 30.0, 90.0, 31.0, 29.0),
        ],
        realtime_rows=[],
        cooldown_hits=set(),
        hose_tickers=["AAA", "BBB", "CCC"],
    )

    results = engine.run_check_cycle(pg_conn, ch_client)

    assert len(batch_calls) == 1
    channel, triggers = batch_calls[0]
    assert channel == "TELEGRAM"
    assert {rule.ticker for rule, _ in triggers} == {"AAA", "CCC"}
    triggered_results = [r for r in results if r.triggered and not r.skipped_cooldown]
    assert all(r.delivery_status == "sent" for r in triggered_results)
    assert len(ch_client.inserted) == 2
