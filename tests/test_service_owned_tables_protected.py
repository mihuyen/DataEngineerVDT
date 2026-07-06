from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import load_gold, migrate_gold_schema

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# fact_alert_event is written continuously by the alert-engine service. No
# batch script may ever TRUNCATE or DROP it: load_gold.py and
# migrate_gold_schema.py both did exactly that in the past, wiping out
# hours/days of live history each time the daily DAG ran. This test exists so
# a future change to either script's table lists fails CI immediately instead
# of silently reintroducing the bug.
#
# fact_realtime_vwap is checked separately below: it is now a plain VIEW (see
# sql/streaming/realtime_vwap_kafka_engine.sql), not a DDL-managed table, so
# it can never appear in load_gold.py's/migrate_gold_schema.py's table lists
# at all -- there is nothing there to drop. Its underlying physical state,
# fact_realtime_vwap_1m_state, is what the static TRUNCATE/DROP scan guards.
PROTECTED_TABLES = ("fact_alert_event",)
PROTECTED_VIEWS_OR_STATE_TABLES = ("fact_realtime_vwap", "fact_realtime_vwap_1m_state")

# Scripts allowed to truncate realtime state: both are manual, opt-in CLI
# tools (truncate is gated behind an explicit `--append` flag a human must
# pass to skip it) that exist only for local demo/manual testing. Neither is
# invoked by the DAG, docker-compose, or start_local_stack.sh -- the danger
# this test guards against is automated/unattended wipes, not a developer
# deliberately resetting their own demo data by hand. Any new entry here
# should be reviewed for the same property before being added.
ALLOWED_SCRIPTS: tuple[str, ...] = (
    "load_realtime_vwap_demo.py",
    "run_dnse_realtime_ingest.py",
)


def test_load_gold_never_truncates_protected_tables():
    for table in (*PROTECTED_TABLES, *PROTECTED_VIEWS_OR_STATE_TABLES):
        assert table not in load_gold.DIM_TABLES
        assert table not in load_gold.BATCH_FACT_PARTITIONS


def test_migrate_gold_schema_never_drops_protected_tables():
    for table in PROTECTED_TABLES:
        assert table not in migrate_gold_schema.GOLD_TABLES
        assert table in migrate_gold_schema.NO_DROP_TABLES
    for table in PROTECTED_VIEWS_OR_STATE_TABLES:
        assert table not in migrate_gold_schema.GOLD_TABLES
        assert table not in migrate_gold_schema.NO_DROP_TABLES


def _iter_python_files():
    for directory in ("scripts", "src"):
        yield from (PROJECT_ROOT / directory).rglob("*.py")


@pytest.mark.parametrize("table", (*PROTECTED_TABLES, "fact_realtime_vwap_1m_state"))
def test_no_truncate_or_drop_table_statement_targets_protected_tables(table):
    """Static scan: catch a literal TRUNCATE/DROP TABLE on these tables anywhere.

    This is a second, independent line of defense on top of the list-based
    checks above: it would also catch a brand new script that hardcodes a
    destructive statement instead of going through load_gold.py's table
    lists at all.
    """
    pattern = re.compile(
        rf"(TRUNCATE\s+TABLE|DROP\s+TABLE)(\s+IF\s+EXISTS)?\s+['\"`]?{re.escape(table)}\b",
        re.IGNORECASE,
    )
    offenders = []
    for path in _iter_python_files():
        if path.name in ALLOWED_SCRIPTS:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert not offenders, (
        f"Found a literal TRUNCATE/DROP TABLE statement targeting '{table}' in: {offenders}. "
        f"{table} is owned by a continuous background service and must never be truncated "
        f"or dropped by a batch script."
    )
