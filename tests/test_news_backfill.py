from __future__ import annotations

from src.ingestion.news_backfill import cafef_zone_id, vnexpress_page_url


class FakeResponse:
    text = '<input id="hdZoneId" value="18831" />'

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def get(self, url: str, headers: dict, timeout: int) -> FakeResponse:
        return FakeResponse()


def test_vnexpress_page_url() -> None:
    base = "https://vnexpress.net/kinh-doanh/chung-khoan"

    assert vnexpress_page_url(base, 1) == base
    assert vnexpress_page_url(base, 2) == f"{base}-p2"


def test_cafef_zone_id_from_category_html() -> None:
    assert cafef_zone_id("https://cafef.vn/thi-truong-chung-khoan.chn", FakeSession()) == "18831"
