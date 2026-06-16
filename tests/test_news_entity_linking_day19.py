from datetime import date

import polars as pl

from src.ingestion.market_news import save_parquet
from src.transform.news_entity_linking import (
    build_company_dictionary,
    link_news_to_tickers,
    make_article_id,
)


def sample_company_profile() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ticker": ["VCB", "FPT", "HPG"],
            "company_name": [
                "Ngân hàng TMCP Ngoại thương Việt Nam",
                "CTCP FPT",
                "CTCP Tập đoàn Hòa Phát",
            ],
            "company_name_en": ["Vietcombank", "FPT Corporation", "Hoa Phat Group"],
        }
    )


def test_day19_build_company_dictionary_contains_ticker_and_aliases() -> None:
    dictionary = build_company_dictionary(sample_company_profile())
    aliases = {(item["ticker"], item["alias"]) for item in dictionary}

    assert ("VCB", "VCB") in aliases
    assert ("FPT", "FPT") in aliases
    assert ("HPG", "Hoa Phat Group") in aliases


def test_day19_link_news_to_tickers_by_ticker_and_company_name() -> None:
    news = pl.DataFrame(
        {
            "url": ["https://example.com/1", "https://example.com/2"],
            "title": ["VCB tăng mạnh sau tin lợi nhuận", "FPT mở rộng mảng AI"],
            "description": ["Vietcombank được nhà đầu tư chú ý", ""],
            "content": [
                "Ngân hàng TMCP Ngoại thương Việt Nam ghi nhận kết quả tích cực.",
                "CTCP FPT công bố chiến lược mới.",
            ],
            "tags": [["VCB"], ["FPT"]],
            "published_at": [date(2026, 6, 16), date(2026, 6, 16)],
            "source": ["CafeF", "VnExpress"],
            "category": ["Chứng khoán", "Doanh nghiệp"],
        }
    )

    linked = link_news_to_tickers(news, sample_company_profile())

    assert set(linked.get_column("ticker").to_list()) == {"VCB", "FPT"}
    assert make_article_id("https://example.com/1") in linked.get_column("article_id").to_list()


def test_day19_save_parquet_appends_and_deduplicates_urls(tmp_path) -> None:
    output_path = tmp_path / "news" / "data.parquet"
    first = pl.DataFrame({"url": ["a", "b"], "title": ["old a", "old b"]})
    second = pl.DataFrame({"url": ["b", "c"], "title": ["new b", "new c"]})

    save_parquet(first, output_path)
    save_parquet(second, output_path)
    result = pl.read_parquet(output_path).sort("url")

    assert result.height == 3
    assert result.filter(pl.col("url") == "b").item(0, "title") == "new b"
