from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import feedparser
import polars as pl
import requests
import yaml
from bs4 import BeautifulSoup

from src.common.minio_client import create_client, upload_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "sources.yaml"
DEFAULT_LOCAL_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://google.com/",
}


@dataclass(frozen=True)
class NewsArticle:
    """Raw normalized news article for Bronze storage."""

    url: str
    title: str
    published_at: str
    description: str
    content: str
    tags: list[str]
    source: str
    category: str
    crawl_at: str


def load_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    source_name: str = "market_news",
) -> dict[str, Any]:
    """Load market news source config from YAML."""
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    for source in config.get("sources", []):
        if source.get("name") == source_name or source.get("source_name") == source_name:
            return source

    raise ValueError(f"Source config not found: {source_name}")


def clean_text(value: str | None) -> str:
    """Collapse whitespace in crawled text."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_date(value: str | None) -> str:
    """Normalize common article date strings to YYYY-MM-DD when possible."""
    if not value:
        return ""
    match_iso = re.search(r"(\d{4}-\d{2}-\d{2})", value)
    match_vn = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", value)
    if match_iso:
        return match_iso.group(1)
    if match_vn:
        return f"{match_vn.group(3)}-{match_vn.group(2)}-{match_vn.group(1)}"
    return value[:10].strip()


def is_recent_article(published_at: str, max_age_days: int, today: date | None = None) -> bool:
    """Return whether the article is recent enough for Bronze ingest."""
    if not published_at:
        return True
    try:
        article_date = datetime.strptime(published_at, "%Y-%m-%d").date()
    except ValueError:
        return True
    reference_date = today or date.today()
    return (reference_date - article_date).days <= max_age_days


def make_article(
    url: str,
    source: str,
    category: str,
    title: str,
    description: str,
    content: str,
    tags: list[str] | None,
    published_at: str,
) -> NewsArticle | None:
    """Create a normalized article if title/content are usable."""
    normalized_title = clean_text(title)
    normalized_content = clean_text(content)
    if not normalized_title or not normalized_content:
        return None

    return NewsArticle(
        url=url,
        title=normalized_title,
        published_at=normalize_date(published_at),
        description=clean_text(description),
        content=normalized_content,
        tags=tags or [],
        source=source,
        category=category,
        crawl_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def fetch_html(url: str, session: requests.Session | None = None, timeout: int = 25) -> str:
    """Fetch HTML using a browser-like header."""
    client = session or requests.Session()
    response = client.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_vnexpress_article(url: str, category: str, html: str | None = None) -> NewsArticle | None:
    """Extract a VnExpress article."""
    soup = BeautifulSoup(html if html is not None else fetch_html(url), "html.parser")
    title = clean_text(soup.select_one("h1.title-detail").get_text(" ")) if soup.select_one("h1.title-detail") else ""
    desc = clean_text(soup.select_one("p.description").get_text(" ")) if soup.select_one("p.description") else ""
    content_div = soup.select_one("article.fck_detail")
    content = ""
    if content_div:
        for related in content_div.select("div.box-tinlienquanv2"):
            related.decompose()
        content = "\n".join(clean_text(p.get_text(" ")) for p in content_div.select("p.Normal"))
    tags = [clean_text(tag.get_text(" ")) for tag in soup.select("div.tags a, div.tags-news a")]
    if not tags:
        meta_tag = soup.select_one('meta[name="keywords"]')
        tags = [item.strip() for item in meta_tag.get("content", "").split(",") if item.strip()] if meta_tag else []
    date_meta = soup.select_one('meta[name="pubdate"]')
    date_span = soup.select_one("span.date")
    published_at = date_meta.get("content", "") if date_meta else date_span.get_text(" ") if date_span else ""
    return make_article(url, "VnExpress", category, title, desc, content, tags, published_at)


def extract_vietstock_article(url: str, category: str, html: str | None = None) -> NewsArticle | None:
    """Extract a Vietstock article."""
    soup = BeautifulSoup(html if html is not None else fetch_html(url), "html.parser")
    title_tag = soup.select_one("h1.article-title, h1.title, h1")
    desc_tag = soup.select_one("p.pHead, .pHead, p.p-head, h2.sapo, p.sapo, div.sapo, .article-sapo")
    content_div = soup.select_one("div#vts-content, div.p-body, div.article-content")
    content = ""
    if content_div:
        for junk in content_div.select("script, style, div.box-related, div.relate-news"):
            junk.decompose()
        content = "\n".join(clean_text(p.get_text(" ")) for p in content_div.find_all("p"))
    tags = [clean_text(tag.get_text(" ")).strip(" ,#") for tag in soup.select("div.box-tags a, div.tags a, .post-tags a")]
    if not tags:
        meta_tag = soup.select_one('meta[name="keywords"]')
        tags = [item.strip() for item in meta_tag.get("content", "").split(",") if item.strip()] if meta_tag else []
    date_tag = soup.select_one('meta[property="article:published_time"], span.date, div.date')
    published_at = date_tag.get("content", "") if date_tag and date_tag.name == "meta" else date_tag.get_text(" ") if date_tag else ""
    return make_article(
        url,
        "Vietstock",
        category,
        title_tag.get_text(" ") if title_tag else "",
        desc_tag.get_text(" ") if desc_tag else "",
        content,
        tags,
        published_at,
    )


def extract_cafef_article(url: str, category: str, html: str | None = None) -> NewsArticle | None:
    """Extract a CafeF article."""
    soup = BeautifulSoup(html if html is not None else fetch_html(url), "html.parser")
    if soup.select_one(".vcdetail-content, .sp-detail-content, .emagazine-sapo, h1.emagazine-title"):
        return None
    title_tag = soup.select_one("h1.title")
    desc_tag = soup.select_one("h2.sapo")
    content_div = soup.select_one(".cafef_detail_tag, div.detail-content")
    content = ""
    if content_div:
        for junk in content_div.select("script, style, div.VCSortableInPreviewMode, div.tinlienquan, div.link-content-footer"):
            junk.decompose()
        content = "\n".join(clean_text(p.get_text(" ")) for p in content_div.find_all("p"))
    tag_wrapper = (
        soup.find("div", attrs={"data-marked-zoneid": "cafef_detail_tag"})
        or soup.find("div", class_="row2")
        or soup.find("div", class_="tags")
        or soup.find("div", class_="tag-detail")
        or soup.find("div", class_="row-tags")
    )
    tags = []
    if tag_wrapper:
        tags = [clean_text(tag.get_text(" ")).strip(" ,") for tag in tag_wrapper.find_all("a")]
        tags = [tag for tag in tags if tag and tag.lower() not in {"tags", "tags:", "từ khóa", "tag"}]
    date_tag = soup.select_one("span.pdate, div.date-and-time")
    return make_article(
        url,
        "CafeF",
        category,
        title_tag.get_text(" ") if title_tag else "",
        desc_tag.get_text(" ") if desc_tag else "",
        content,
        tags,
        date_tag.get_text(" ") if date_tag else "",
    )


def discover_vnexpress_links(category_url: str, session: requests.Session | None = None) -> list[str]:
    """Discover VnExpress article links from a category page."""
    soup = BeautifulSoup(fetch_html(category_url, session=session), "html.parser")
    links = []
    for title_tag in soup.find_all(["h2", "h3"], class_="title-news"):
        anchor = title_tag.find("a", href=True)
        if anchor:
            links.append(str(anchor["href"]))
    return links


def discover_vietstock_links(channel_id: str | int, session: requests.Session | None = None) -> list[str]:
    """Discover Vietstock article links from its channel API."""
    client = session or requests.Session()
    response = client.post(
        "https://vietstock.vn/StartPage/ChannelContentPage",
        headers=HEADERS,
        data={"channelID": channel_id, "page": 1, "pageSize": 15},
        timeout=25,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        id_part = href.split("-")[-1].replace(".htm", "")
        if href.endswith(".htm") and "-" in href and id_part.isdigit() and "fili.vn" not in href:
            links.append(urljoin("https://vietstock.vn", href))
    return links


def discover_cafef_links(category_url: str, session: requests.Session | None = None) -> list[str]:
    """Discover CafeF article links from a category page."""
    blacklist = ["video", "tac-gia", "/tag/", "emagazine", "longform", "mega-story", "infographic", "photo"]
    soup = BeautifulSoup(fetch_html(category_url, session=session), "html.parser")
    links = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).lower()
        id_part = href.split("-")[-1].replace(".chn", "")
        if href.endswith(".chn") and "-" in href and id_part.isdigit() and all(item not in href for item in blacklist):
            links.append(urljoin("https://cafef.vn", href))
    return links


def discover_rss_links(feed_url: str) -> list[str]:
    """Discover article links from an RSS feed."""
    feed = feedparser.parse(feed_url)
    return [str(entry.link) for entry in feed.entries if getattr(entry, "link", None)]


def crawl_articles(config: dict[str, Any] | None = None) -> list[NewsArticle]:
    """Crawl all configured market news sources."""
    source_config = config or load_config()
    max_age_days = int(source_config.get("max_age_days", 2))
    max_articles_per_source = int(source_config.get("max_articles_per_source", 20))
    seen_urls: set[str] = set()
    articles: list[NewsArticle] = []

    def source_count(source_name: str) -> int:
        return len([item for item in articles if item.source == source_name])

    def safe_extract(extractor, link: str, category: str) -> NewsArticle | None:
        try:
            return extractor(link, category)
        except requests.RequestException as exc:
            print(f"Skip article due to request error: {link} ({exc})")
            return None
        except Exception as exc:
            print(f"Skip article due to parse error: {link} ({exc})")
            return None

    for source in source_config.get("sources", []):
        source_name = source.get("source")
        session = requests.Session()
        if source_name == "VnExpress":
            for category, category_url in source.get("categories", {}).items():
                if source_count(source_name) >= max_articles_per_source:
                    break
                try:
                    links = discover_vnexpress_links(category_url, session=session)
                except requests.RequestException as exc:
                    print(f"Skip VnExpress category due to request error: {category_url} ({exc})")
                    continue
                for link in links:
                    if source_count(source_name) >= max_articles_per_source:
                        break
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    article = safe_extract(extract_vnexpress_article, link, category)
                    if article and is_recent_article(article.published_at, max_age_days):
                        articles.append(article)
        elif source_name == "Vietstock":
            for channel_id, category in source.get("channels", {}).items():
                if source_count(source_name) >= max_articles_per_source:
                    break
                try:
                    links = discover_vietstock_links(channel_id, session=session)
                except requests.RequestException as exc:
                    print(f"Skip Vietstock channel due to request error: {channel_id} ({exc})")
                    continue
                for link in links:
                    if source_count(source_name) >= max_articles_per_source:
                        break
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    article = safe_extract(extract_vietstock_article, link, category)
                    if article and is_recent_article(article.published_at, max_age_days):
                        articles.append(article)
        elif source_name == "CafeF":
            for category, category_url in source.get("categories", {}).items():
                if source_count(source_name) >= max_articles_per_source:
                    break
                try:
                    links = discover_cafef_links(category_url, session=session)
                except requests.RequestException as exc:
                    print(f"Skip CafeF category due to request error: {category_url} ({exc})")
                    continue
                for link in links:
                    if source_count(source_name) >= max_articles_per_source:
                        break
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    article = safe_extract(extract_cafef_article, link, category)
                    if article and is_recent_article(article.published_at, max_age_days):
                        articles.append(article)

    return articles


def articles_to_frame(articles: list[NewsArticle]) -> pl.DataFrame:
    """Convert normalized articles to a Polars DataFrame."""
    if not articles:
        return pl.DataFrame(
            schema={
                "url": pl.Utf8,
                "title": pl.Utf8,
                "published_at": pl.Utf8,
                "description": pl.Utf8,
                "content": pl.Utf8,
                "tags": pl.List(pl.Utf8),
                "source": pl.Utf8,
                "category": pl.Utf8,
                "crawl_at": pl.Utf8,
            }
        )
    return pl.DataFrame([asdict(article) for article in articles])


def build_bronze_object_name(
    ingest_date: date | None = None,
    bronze_path: str = "news/",
    filename: str = "data.parquet",
) -> str:
    """Build Bronze object name for raw market news."""
    partition_date = ingest_date or date.today()
    cleaned_prefix = bronze_path.strip("/")
    return (
        f"{cleaned_prefix}/"
        f"source=multi/"
        f"year={partition_date:%Y}/"
        f"month={partition_date:%m}/"
        f"day={partition_date:%d}/"
        f"{filename}"
    )


def save_parquet(frame: pl.DataFrame, output_path: Path, append_existing: bool = True) -> Path:
    """Save raw market news as parquet, preserving previous same-day articles."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if append_existing and output_path.exists():
        existing = pl.read_parquet(output_path)
        frame = pl.concat([existing, frame], how="diagonal_relaxed").unique(
            subset=["url"],
            keep="last",
            maintain_order=True,
        )
    frame.write_parquet(output_path)
    return output_path


def upload_to_minio(local_path: Path, object_name: str, bucket_name: str = "bronze") -> None:
    """Upload raw market news parquet to MinIO."""
    client = create_client()
    upload_file(
        client=client,
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=local_path,
        content_type="application/vnd.apache.parquet",
    )


def run(
    config_path: Path = DEFAULT_CONFIG_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    upload: bool = True,
) -> dict[str, str]:
    """Run market news Bronze ingest."""
    source_config = load_config(config_path)
    articles = crawl_articles(source_config)
    frame = articles_to_frame(articles)
    bronze_path = str(source_config.get("bronze_path", "news/"))
    bucket_name = str(source_config.get("bronze_bucket", "bronze"))
    object_name = build_bronze_object_name(bronze_path=bronze_path)
    local_path = local_output_dir / object_name
    save_parquet(frame, local_path)
    if upload:
        upload_to_minio(local_path=local_path, object_name=object_name, bucket_name=bucket_name)
    return {
        "article_count": str(frame.height),
        "local_path": str(local_path),
        "bucket": bucket_name,
        "object_name": object_name,
    }
