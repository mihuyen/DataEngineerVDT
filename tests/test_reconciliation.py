from __future__ import annotations

from src.quality.reconciliation import _anti_join_check, _no_orphan_check


def test_anti_join_check_passes_on_identical_key_sets() -> None:
    keys = {("AAA", "2026-01-01"), ("BBB", "2026-01-01")}
    result = _anti_join_check("name", keys, keys)
    assert result.success is True
    assert result.failed_count == 0


def test_anti_join_check_reports_missing_in_gold() -> None:
    silver = {("AAA", "2026-01-01"), ("BBB", "2026-01-01")}
    gold = {("AAA", "2026-01-01")}
    result = _anti_join_check("name", silver, gold)
    assert result.success is False
    assert result.failed_count == 1
    assert "missing_in_gold_count=1" in result.details
    assert "('BBB', '2026-01-01')" in result.details


def test_anti_join_check_reports_extra_in_gold() -> None:
    silver = {("AAA", "2026-01-01")}
    gold = {("AAA", "2026-01-01"), ("CCC", "2026-01-01")}
    result = _anti_join_check("name", silver, gold)
    assert result.success is False
    assert result.failed_count == 1
    assert "extra_in_gold_count=1" in result.details


def test_anti_join_check_catches_swapped_keys_that_exact_count_match_would_miss() -> None:
    """A row-count check sees equal totals here; only the key-set diff catches the swap."""
    silver = {("AAA", "2026-01-01"), ("BBB", "2026-01-01")}
    gold = {("AAA", "2026-01-01"), ("ZZZ", "2026-01-01")}
    result = _anti_join_check("name", silver, gold)
    assert result.success is False
    assert result.failed_count == 2


def test_no_orphan_check_passes_when_gold_is_a_subset_of_silver() -> None:
    """News Gold is expected to drop Silver rows that Entity Linking couldn't match to a ticker."""
    silver = {"https://a", "https://b", "https://c"}
    gold = {"https://a"}
    result = _no_orphan_check("name", silver, gold)
    assert result.success is True
    assert result.failed_count == 0


def test_no_orphan_check_fails_when_gold_has_a_key_absent_from_silver() -> None:
    silver = {"https://a"}
    gold = {"https://a", "https://z"}
    result = _no_orphan_check("name", silver, gold)
    assert result.success is False
    assert result.failed_count == 1
    assert "extra_in_gold_count=1" in result.details
    assert "https://z" in result.details
