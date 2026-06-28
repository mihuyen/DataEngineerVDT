from __future__ import annotations

import pytest

from src.ingestion import vn30_constituents


def test_fetch_vn30_constituents_returns_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingListing:
        def symbols_by_group(self, group: str) -> list[str]:
            raise RuntimeError("network unavailable")

    monkeypatch.setattr("vnstock.Listing", FailingListing)

    assert vn30_constituents.fetch_vn30_constituents() is None


def test_fetch_vn30_constituents_normalizes_tickers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeListing:
        def symbols_by_group(self, group: str) -> list[str]:
            assert group == "VN30"
            return [" vcb ", "fpt", "VCB"]

    monkeypatch.setattr("vnstock.Listing", FakeListing)

    result = vn30_constituents.fetch_vn30_constituents()
    assert result == ["FPT", "VCB"]


def test_fetch_vn30_constituents_returns_none_for_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyListing:
        def symbols_by_group(self, group: str) -> list[str]:
            return []

    monkeypatch.setattr("vnstock.Listing", EmptyListing)

    assert vn30_constituents.fetch_vn30_constituents() is None
