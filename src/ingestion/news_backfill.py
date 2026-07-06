"""Historical, resumable crawler for the configured market-news sources."""

from __future__ import annotations

import math
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import polars as pl
import requests
from bs4 import BeautifulSoup

from src.ingestion.market_news import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOCAL_BRONZE_DIR,
    HEADERS,
    NewsArticle,
    articles_to_frame,
    build_bronze_object_name,
    discover_cafef_links,
    discover_vnexpress_links,
    extract_cafef_article,
    extract_vietstock_article,
    extract_vnexpress_article,
    fetch_html,
    load_config,
    save_parquet,
    upload_to_minio,
)
from src.ingestion.news_url_registry import (
    DEFAULT_REGISTRY_PATH,
    NewsURLRegistry,
    normalize_url,
)


SOURCE_NAMES = ("VnExpress", "Vietstock", "CafeF")


def vnexpress_page_url(category_url: str, page: int) -> str:
    return category_url if page <= 1 else f"{category_url.rstrip('/')}-p{page}"


def discover_vietstock_page(
    channel_id: str | int,
    page: int,
    session: requests.Session,
    page_size: int = 15,
) -> list[str]:
    response = session.post(
        "https://vietstock.vn/StartPage/ChannelContentPage",
        headers=HEADERS,
        data={"channelID": channel_id, "page": page, "pageSize": page_size},
        timeout=25,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        article_id = href.split("-")[-1].removesuffix(".htm")
        if href.endswith(".htm") and article_id.isdigit() and "fili.vn" not in href:
            links.append(urljoin("https://vietstock.vn", href))
    return list(dict.fromkeys(links))


def cafef_zone_id(category_url: str, session: requests.Session) -> str:
    response = session.get(category_url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    element = soup.select_one("#hdZoneId")
    zone_id = str(element.get("value", "")).strip() if element else ""
    if not zone_id.isdigit():
        raise ValueError(f"CafeF zone id not found: {category_url}")
    return zone_id


def discover_cafef_page(zone_id: str, page: int, session: requests.Session) -> list[str]:
    return discover_cafef_links(
        f"https://cafef.vn/timelinelist/{zone_id}/{page}.chn",
        session=session,
    )


def load_existing_counts(
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
) -> tuple[set[str], Counter[str]]:
    urls: set[str] = set()
    counts: Counter[str] = Counter()
    for path in sorted((local_output_dir / "news").glob("**/data.parquet")):
        frame = pl.read_parquet(path)
        if not {"url", "source"}.issubset(frame.columns):
            continue
        for row in frame.select("url", "source").drop_nulls("url").to_dicts():
            normalized = normalize_url(str(row["url"]))
            if normalized in urls:
                continue
            urls.add(normalized)
            counts[str(row.get("source") or "unknown")] += 1
    return urls, counts


class BackfillCrawler:
    def __init__(
        self,
        config: dict[str, Any],
        target_total: int,
        max_pages: int,
        request_delay_seconds: float,
        checkpoint_size: int,
        registry: NewsURLRegistry,
        local_output_dir: Path,
        upload: bool,
    ) -> None:
        self.config = config
        self.target_total = target_total
        self.max_pages = max_pages
        self.request_delay_seconds = request_delay_seconds
        self.checkpoint_size = checkpoint_size
        self.registry = registry
        self.local_output_dir = local_output_dir
        self.upload = upload
        self.seen_urls, self.counts = load_existing_counts(local_output_dir)
        per_source = math.ceil(target_total / len(SOURCE_NAMES))
        self.targets = {source: per_source for source in SOURCE_NAMES}
        self.targets[SOURCE_NAMES[-1]] -= per_source * len(SOURCE_NAMES) - target_total
        self.pending: list[NewsArticle] = []
        self.stats: Counter[str] = Counter()
        self.output_path = local_output_dir / build_bronze_object_name()

    def target_reached(self) -> bool:
        return sum(self.counts[source] for source in SOURCE_NAMES) >= self.target_total

    def source_target_reached(self, source: str) -> bool:
        return self.counts[source] >= self.targets[source]

    def flush(self) -> None:
        if not self.pending:
            return
        batch = list(self.pending)
        save_parquet(articles_to_frame(batch), self.output_path)
        for article in batch:
            self.registry.mark_success(article.url, article.source, article.category)
        self.pending.clear()
        self.stats["checkpoints"] += 1
        print(
            f"Checkpoint saved: total={sum(self.counts.values())} "
            f"sources={dict(self.counts)}",
            flush=True,
        )

    def process_links(
        self,
        links: list[str],
        source: str,
        category: str,
        session: requests.Session,
        extractor: Callable[[str, str, str | None], NewsArticle | None],
    ) -> None:
        for raw_url in links:
            if self.target_reached() or self.source_target_reached(source):
                break
            url = normalize_url(raw_url)
            if url in self.seen_urls:
                self.stats["existing_or_seen"] += 1
                continue
            self.registry.register_discovered(url, source, category)
            if not self.registry.should_crawl(
                url,
                max_attempts=3,
                retry_skipped=True,
            ):
                self.stats["registry_skipped"] += 1
                continue
            try:
                html = fetch_html(url, session=session)
                article = extractor(url, category, html)
            except Exception as exc:
                self.registry.mark_failure(url, source, category, str(exc))
                self.stats["failed"] += 1
                continue
            time.sleep(self.request_delay_seconds)
            if article is None or len(article.content) < 200:
                self.registry.mark_failure(url, source, category, "empty or short article")
                self.stats["failed"] += 1
                continue
            self.seen_urls.add(url)
            self.counts[source] += 1
            self.pending.append(article)
            self.stats["crawled"] += 1
            if len(self.pending) >= self.checkpoint_size:
                self.flush()

    def run(self) -> dict[str, Any]:
        sessions = {source: requests.Session() for source in SOURCE_NAMES}
        source_configs = {
            str(item.get("source")): item for item in self.config.get("sources", [])
        }
        cafef_config = source_configs.get("CafeF", {})
        cafef_zones: dict[str, str] = {}
        for category, url in cafef_config.get("categories", {}).items():
            try:
                cafef_zones[category] = cafef_zone_id(url, sessions["CafeF"])
            except Exception as exc:
                print(f"Skip CafeF category {category}: {exc}", flush=True)

        try:
            for page in range(1, self.max_pages + 1):
                if self.target_reached():
                    break
                print(f"Backfill page {page}/{self.max_pages}", flush=True)

                vne_config = source_configs.get("VnExpress", {})
                if not self.source_target_reached("VnExpress"):
                    for category, url in vne_config.get("categories", {}).items():
                        try:
                            links = discover_vnexpress_links(
                                vnexpress_page_url(url, page), sessions["VnExpress"]
                            )
                            self.process_links(
                                links,
                                "VnExpress",
                                category,
                                sessions["VnExpress"],
                                extract_vnexpress_article,
                            )
                        except Exception as exc:
                            print(f"VnExpress discovery failed page={page}: {exc}", flush=True)

                vietstock_config = source_configs.get("Vietstock", {})
                if not self.source_target_reached("Vietstock"):
                    for channel_id, category in vietstock_config.get("channels", {}).items():
                        try:
                            links = discover_vietstock_page(
                                channel_id, page, sessions["Vietstock"]
                            )
                            self.process_links(
                                links,
                                "Vietstock",
                                category,
                                sessions["Vietstock"],
                                extract_vietstock_article,
                            )
                        except Exception as exc:
                            print(f"Vietstock discovery failed page={page}: {exc}", flush=True)

                if not self.source_target_reached("CafeF"):
                    for category, zone_id in cafef_zones.items():
                        try:
                            links = discover_cafef_page(zone_id, page, sessions["CafeF"])
                            self.process_links(
                                links,
                                "CafeF",
                                category,
                                sessions["CafeF"],
                                extract_cafef_article,
                            )
                        except Exception as exc:
                            print(f"CafeF discovery failed page={page}: {exc}", flush=True)
        finally:
            self.flush()

        if self.upload and self.output_path.exists():
            object_name = build_bronze_object_name()
            upload_to_minio(self.output_path, object_name, self.config.get("bronze_bucket", "bronze"))

        return {
            "target_total": self.target_total,
            "record_count": sum(self.counts[source] for source in SOURCE_NAMES),
            "source_counts": dict(self.counts),
            "source_targets": self.targets,
            "stats": dict(self.stats),
            "target_reached": self.target_reached(),
            "local_path": str(self.output_path),
        }


def run(
    target_total: int = 3000,
    max_pages: int = 40,
    request_delay_seconds: float = 0.35,
    checkpoint_size: int = 25,
    config_path: Path = DEFAULT_CONFIG_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    local_output_dir: Path = DEFAULT_LOCAL_BRONZE_DIR,
    upload: bool = True,
) -> dict[str, Any]:
    crawler = BackfillCrawler(
        config=load_config(config_path),
        target_total=target_total,
        max_pages=max_pages,
        request_delay_seconds=request_delay_seconds,
        checkpoint_size=checkpoint_size,
        registry=NewsURLRegistry(registry_path),
        local_output_dir=local_output_dir,
        upload=upload,
    )
    return crawler.run()
