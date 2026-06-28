from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.run_realtime_vwap_kafka_consumer import run_cycle
from src.streaming.kafka_producer import trade_tick_to_kafka_message


def test_trade_tick_to_kafka_message_formats_fields() -> None:
    message = trade_tick_to_kafka_message("vcb", datetime(2026, 6, 28, 9, 15, 30), 50000.5, 100)
    assert message == {
        "ticker": "VCB",
        "trade_ts": "2026-06-28 09:15:30",
        "price": 50000.5,
        "volume": 100,
        "data_source": "DNSE",
    }


class FakeQueryResult:
    def __init__(self, result_rows: list[tuple]) -> None:
        self.result_rows = result_rows


class FakeClickHouseClient:
    def __init__(self, raw_ticks: pd.DataFrame, has_existing_partition: bool) -> None:
        self._raw_ticks = raw_ticks
        self._has_existing_partition = has_existing_partition
        self.commands: list[str] = []
        self.inserted: list[tuple[str, pd.DataFrame]] = []

    def query_df(self, sql: str) -> pd.DataFrame:
        return self._raw_ticks

    def query(self, sql: str, parameters: dict | None = None) -> FakeQueryResult:
        return FakeQueryResult([[1 if self._has_existing_partition else 0]])

    def command(self, sql: str) -> None:
        self.commands.append(sql)

    def insert_df(self, table_name: str, frame: pd.DataFrame) -> None:
        self.inserted.append((table_name, frame))


def test_run_cycle_aggregates_ticks_and_drops_existing_partition() -> None:
    today = date.today()
    raw_ticks = pd.DataFrame(
        {
            "ticker": ["VCB", "VCB", "VCB"],
            "trade_ts": [
                datetime.combine(today, datetime.min.time()).replace(hour=9, minute=15, second=0),
                datetime.combine(today, datetime.min.time()).replace(hour=9, minute=15, second=12),
                datetime.combine(today, datetime.min.time()).replace(hour=9, minute=16, second=0),
            ],
            "price": [50000.0, 50010.0, 50020.0],
            "volume": [100, 110, 120],
            "data_source": ["DNSE", "DNSE", "DNSE"],
        }
    )
    client = FakeClickHouseClient(raw_ticks, has_existing_partition=True)

    stats = run_cycle(client)  # type: ignore[arg-type]

    assert stats == {"ticks": 3, "rows": 2}
    assert any("DROP PARTITION" in command for command in client.commands)
    assert len(client.inserted) == 1
    table_name, frame = client.inserted[0]
    assert table_name == "fact_realtime_vwap"
    assert len(frame) == 2


def test_run_cycle_skips_drop_partition_when_none_exists() -> None:
    today = date.today()
    raw_ticks = pd.DataFrame(
        {
            "ticker": ["FPT"],
            "trade_ts": [datetime.combine(today, datetime.min.time()).replace(hour=9, minute=15)],
            "price": [58000.0],
            "volume": [100],
            "data_source": ["DNSE"],
        }
    )
    client = FakeClickHouseClient(raw_ticks, has_existing_partition=False)

    run_cycle(client)  # type: ignore[arg-type]

    assert client.commands == []


def test_run_cycle_returns_zero_for_empty_ticks() -> None:
    client = FakeClickHouseClient(
        pd.DataFrame(columns=["ticker", "trade_ts", "price", "volume", "data_source"]),
        False,
    )

    stats = run_cycle(client)  # type: ignore[arg-type]

    assert stats == {"ticks": 0, "rows": 0}
    assert client.inserted == []
