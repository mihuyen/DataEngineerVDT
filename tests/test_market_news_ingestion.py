from datetime import date
from pathlib import Path

import polars as pl

from src.ingestion import market_news


VNEXPRESS_HTML = """
<html>
  <head><meta name="pubdate" content="2026-06-14T08:10:00+07:00" /></head>
  <body>
    <h1 class="title-detail">VN-Index tăng mạnh</h1>
    <p class="description">Thị trường chứng khoán hồi phục.</p>
    <article class="fck_detail">
      <p class="Normal">Nhóm ngân hàng dẫn dắt đà tăng.</p>
      <p class="Normal">Thanh khoản cải thiện so với phiên trước.</p>
    </article>
    <div class="tags"><h4 class="item-tag"><a>chứng khoán</a></h4></div>
  </body>
</html>
"""

VIETSTOCK_HTML = """
<html>
  <head><meta property="article:published_time" content="2026-06-14T09:00:00+07:00" /></head>
  <body>
    <h1 class="article-title">Cổ phiếu ngân hàng hút tiền</h1>
    <p class="pHead">Dòng tiền quay lại nhóm vốn hóa lớn.</p>
    <div id="vts-content">
      <p>VCB và CTG tăng tốt.</p>
      <p>Nhà đầu tư theo dõi vùng kháng cự mới.</p>
    </div>
    <div class="box-tags"><a>#ngân hàng</a><a>#VNINDEX</a></div>
  </body>
</html>
"""

CAFEF_HTML = """
<html>
  <body>
    <h1 class="title">Thị trường chứng khoán khởi sắc</h1>
    <h2 class="sapo">Nhiều cổ phiếu bluechip tăng giá.</h2>
    <span class="pdate">14-06-2026 - 10:30 AM</span>
    <div class="detail-content">
      <p>VN30 ghi nhận sắc xanh trên diện rộng.</p>
      <p>Thanh khoản duy trì ở mức cao.</p>
    </div>
    <div class="tags"><a>VN30</a><a>bluechip</a></div>
  </body>
</html>
"""


def test_normalize_date_supports_iso_and_vietnamese_format() -> None:
    assert market_news.normalize_date("2026-06-14T08:10:00+07:00") == "2026-06-14"
    assert market_news.normalize_date("14-06-2026 - 10:30 AM") == "2026-06-14"


def test_extract_vnexpress_article_from_html() -> None:
    article = market_news.extract_vnexpress_article(
        "https://vnexpress.net/test",
        "Chứng khoán",
        html=VNEXPRESS_HTML,
    )

    assert article is not None
    assert article.source == "VnExpress"
    assert article.published_at == "2026-06-14"
    assert "ngân hàng" in article.content


def test_extract_vietstock_article_from_html() -> None:
    article = market_news.extract_vietstock_article(
        "https://vietstock.vn/test.htm",
        "Chứng khoán",
        html=VIETSTOCK_HTML,
    )

    assert article is not None
    assert article.source == "Vietstock"
    assert "VNINDEX" in article.tags


def test_extract_cafef_article_from_html() -> None:
    article = market_news.extract_cafef_article(
        "https://cafef.vn/test.chn",
        "Chứng khoán",
        html=CAFEF_HTML,
    )

    assert article is not None
    assert article.source == "CafeF"
    assert article.published_at == "2026-06-14"
    assert "VN30" in article.tags


def test_build_bronze_object_name() -> None:
    object_name = market_news.build_bronze_object_name(
        ingest_date=date(2026, 6, 14),
        bronze_path="news/",
    )

    assert object_name == "news/source=multi/year=2026/month=06/day=14/data.parquet"


def test_articles_to_frame() -> None:
    article = market_news.extract_cafef_article(
        "https://cafef.vn/test.chn",
        "Chứng khoán",
        html=CAFEF_HTML,
    )

    frame = market_news.articles_to_frame([article] if article else [])

    assert frame.height == 1
    assert frame["source"].to_list() == ["CafeF"]


def test_run_uses_mocked_crawl_and_upload(tmp_path: Path, monkeypatch) -> None:
    article = market_news.extract_vnexpress_article(
        "https://vnexpress.net/test",
        "Chứng khoán",
        html=VNEXPRESS_HTML,
    )
    uploaded: dict[str, str] = {}

    def fake_crawl_articles(config):
        return [article] if article else []

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        uploaded["local_path"] = str(local_path)
        uploaded["object_name"] = object_name
        uploaded["bucket_name"] = bucket_name

    monkeypatch.setattr(market_news, "crawl_articles", fake_crawl_articles)
    monkeypatch.setattr(market_news, "upload_to_minio", fake_upload_to_minio)

    result = market_news.run(local_output_dir=tmp_path)

    assert result["article_count"] == "1"
    assert Path(result["local_path"]).is_file()
    assert uploaded["bucket_name"] == "bronze"
    assert pl.read_parquet(result["local_path"]).height == 1
