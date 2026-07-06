from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_realtime_vwap_kafka_consumer import BACKFILL_INSERT_SQL, run_backfill
from src.streaming.kafka_producer import ohlcv_candle_to_kafka_message, trade_tick_to_kafka_message


def test_trade_tick_to_kafka_message_formats_fields() -> None:
    message = trade_tick_to_kafka_message("vcb", datetime(2026, 6, 28, 9, 15, 30), 50000.5, 100)
    assert message == {
        "ticker": "VCB",
        "trade_ts": "2026-06-28 09:15:30",
        "price": 50000.5,
        "volume": 100,
        "data_source": "DNSE",
    }


def test_ohlcv_candle_to_kafka_message_formats_fields() -> None:
    message = ohlcv_candle_to_kafka_message(
        "fpt",
        datetime(2026, 6, 29, 9, 15),
        70.1,
        70.4,
        70.0,
        70.3,
        12500,
    )

    assert message == {
        "ticker": "FPT",
        "minute_ts": "2026-06-29 09:15:00",
        "resolution": "1m",
        "open": 70.1,
        "high": 70.4,
        "low": 70.0,
        "close": 70.3,
        "volume": 12500,
        "is_final": 1,
        "data_source": "DNSE",
    }


class FakeClickHouseClient:
    """fact_realtime_vwap_1m_state is now populated by a ClickHouse Materialized
    View (mv_fact_realtime_vwap_1m_state); this backfill script only reruns
    the same aggregation as a single INSERT ... SELECT statement, so the fake
    client just needs to record the executed SQL."""

    def __init__(self) -> None:
        self.commands: list[str] = []

    def command(self, sql: str) -> None:
        self.commands.append(sql)


def test_run_backfill_executes_insert_select_for_session_date() -> None:
    client = FakeClickHouseClient()

    run_backfill(client, "2026-06-28")  # type: ignore[arg-type]

    assert len(client.commands) == 1
    executed_sql = client.commands[0]
    assert "INSERT INTO fact_realtime_vwap_1m_state" in executed_sql
    assert "FROM realtime_trade_ticks_raw" in executed_sql
    assert "toDate('2026-06-28')" in executed_sql
    assert "argMinState(price, trade_ts)" in executed_sql
    assert "sumState(volume)" in executed_sql


def test_run_backfill_rejects_invalid_date() -> None:
    client = FakeClickHouseClient()

    try:
        run_backfill(client, "not-a-date")  # type: ignore[arg-type]
        raised = False
    except ValueError:
        raised = True

    assert raised
    assert client.commands == []


def test_backfill_sql_template_has_placeholder() -> None:
    assert "{session_date}" in BACKFILL_INSERT_SQL
