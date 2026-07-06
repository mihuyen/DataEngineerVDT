from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute

# Mirrors the SELECT in mv_fact_realtime_vwap_1m_state (sql/streaming/
# realtime_vwap_kafka_engine.sql), but reads from realtime_trade_ticks_raw
# instead of the ephemeral Kafka engine table, so it can replay a specific
# time range on demand.
BACKFILL_INSERT_SQL = """
INSERT INTO fact_realtime_vwap_1m_state
SELECT
    data_source,
    ticker,
    toDate(trade_ts) AS trading_date,
    toStartOfMinute(trade_ts) AS minute_ts,
    argMinState(price, trade_ts) AS open_state,
    argMaxState(price, trade_ts) AS close_state,
    maxState(price) AS high_price,
    minState(price) AS low_price,
    sumState(volume) AS total_volume,
    sumState(price * volume) AS total_value,
    countState() AS trade_count
FROM realtime_trade_ticks_raw
WHERE toDate(trade_ts) = toDate('{session_date}')
GROUP BY data_source, ticker, trading_date, minute_ts
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual backfill for fact_realtime_vwap_1m_state. Not part of the "
            "live path: fact_realtime_vwap is a VIEW computed continuously by "
            "ClickHouse via mv_fact_realtime_vwap_1m_state (see "
            "sql/streaming/realtime_vwap_kafka_engine.sql), which consumes "
            "directly from the Kafka Engine table. Use this only to replay a "
            "session's ticks from realtime_trade_ticks_raw after the Kafka MV "
            "was down for a stretch -- running it twice for the same date "
            "double-counts, since AggregatingMergeTree states are additive."
        )
    )
    parser.add_argument(
        "--session-date",
        default=date.today().isoformat(),
        help="Trading date (YYYY-MM-DD) to replay from realtime_trade_ticks_raw.",
    )
    return parser.parse_args()


def run_backfill(client: object, session_date: str) -> None:
    # date.fromisoformat rejects anything that isn't a real calendar date
    # before it reaches string formatting, so this stays safe from injection.
    validated = date.fromisoformat(session_date)
    execute(client, BACKFILL_INSERT_SQL.format(session_date=validated.isoformat()))


def main() -> None:
    args = parse_args()
    client = create_client()
    run_backfill(client, args.session_date)
    print(f"Backfilled fact_realtime_vwap_1m_state for {args.session_date}")


if __name__ == "__main__":
    main()
