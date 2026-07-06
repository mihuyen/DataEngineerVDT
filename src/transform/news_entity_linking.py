from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
DEFAULT_LOCAL_GOLD_DIR = PROJECT_ROOT / "data" / "gold_local"
NEWS_PREFIX = "news"
COMPANY_PROFILE_PREFIX = "company_profile"
NEWS_ENTITY_LINKS_PREFIX = "news_entity_links"
GENERIC_ALIASES = {
    "an",
    "anh",
    "can",
    "ceo",
    "co",
    "con",
    "dau",
    "gia",
    "hcm",
    "hợp nhất",
    "nam",
    "sai gon",
    "sài gòn",
    "thang",
    "thu",
    "tin",
    "trang",
    "usd",
    "viet nam",
    "việt nam",
}


def load_silver_news(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame:
    files = sorted((local_silver_dir / NEWS_PREFIX).glob("year=*/month=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"No Silver news parquet files found under {local_silver_dir}")
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def load_silver_company_profile(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> pl.DataFrame:
    files = sorted((local_silver_dir / COMPANY_PROFILE_PREFIX).glob("year=*/month=*/data.parquet"))
    if not files:
        raise FileNotFoundError(f"No Silver company profile parquet files found under {local_silver_dir}")
    return pl.concat([pl.read_parquet(file_path) for file_path in files], how="diagonal_relaxed")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def make_article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def build_company_dictionary(company_profile: pl.DataFrame) -> list[dict[str, str]]:
    required = {"ticker", "company_name"}
    missing = required.difference(company_profile.columns)
    if missing:
        raise ValueError(f"Company profile is missing required columns: {', '.join(sorted(missing))}")

    if "exchange" in company_profile.columns:
        company_profile = company_profile.filter(pl.col("exchange").str.to_uppercase() == "HOSE")
    if "processed_at" in company_profile.columns:
        company_profile = company_profile.sort("processed_at").unique(subset=["ticker"], keep="last")
    else:
        company_profile = company_profile.unique(subset=["ticker"], keep="last")

    optional_name_col = "company_name_en" if "company_name_en" in company_profile.columns else None
    records: list[dict[str, str]] = []
    for row in company_profile.to_dicts():
        ticker = normalize_text(str(row.get("ticker", ""))).upper()
        company_name = normalize_text(str(row.get("company_name", "")))
        company_name_en = normalize_text(str(row.get(optional_name_col, ""))) if optional_name_col else ""
        if not ticker:
            continue
        aliases = {ticker}
        for name in [company_name, company_name_en]:
            if name and name.lower() != "none":
                aliases.add(name)
                simplified = re.sub(
                    r"\b(CTCP|Công ty cổ phần|Ngân hàng TMCP|Tổng Công ty|Tập đoàn)\b",
                    "",
                    name,
                    flags=re.IGNORECASE,
                )
                simplified = normalize_text(simplified)
                if len(simplified) >= 4:
                    aliases.add(simplified)
        for alias in aliases:
            normalized_alias = alias.casefold()
            is_ticker = alias == ticker
            is_useful_company_alias = len(alias) >= 8 and normalized_alias not in GENERIC_ALIASES
            if is_ticker or is_useful_company_alias:
                records.append({"ticker": ticker, "alias": alias})

    unique = {(record["ticker"], record["alias"].casefold()): record for record in records}
    return sorted(unique.values(), key=lambda item: (item["ticker"], item["alias"]))


@lru_cache(maxsize=4096)
def alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    if alias.isascii() and alias.replace(".", "").isalnum() and len(alias) <= 5:
        return re.compile(rf"(?<![A-Z0-9]){escaped}(?![A-Z0-9])")
    return re.compile(escaped, flags=re.IGNORECASE)


@lru_cache(maxsize=1024)
def ticker_context_pattern(ticker: str) -> re.Pattern[str]:
    escaped = re.escape(ticker)
    return re.compile(
        rf"(?:cổ phiếu|mã|HOSE|HSX|chứng khoán|sàn)\s{{0,20}}{escaped}"
        rf"|{escaped}\s{{0,20}}(?:cổ phiếu|HOSE|HSX|chứng khoán)",
        flags=re.IGNORECASE,
    )


def link_article_to_tickers(
    article: dict[str, Any],
    company_dictionary: list[dict[str, str]],
) -> list[dict[str, Any]]:
    title = normalize_text(str(article.get("title", "")))
    body = " ".join(
        normalize_text(str(article.get(column, "")))
        for column in ["description", "content"]
    )
    tags = article.get("tags") or []
    tag_values = {normalize_text(str(tag)).upper() for tag in tags} if isinstance(tags, list) else set()
    text = f"{title} {body}"
    text_casefold = text.casefold()
    ticker_set = {record["ticker"] for record in company_dictionary}
    title_tickers = {
        match.group(0)
        for match in re.finditer(r"(?<![A-Z0-9])[A-Z][A-Z0-9.]{1,4}(?![A-Z0-9])", title)
        if match.group(0) in ticker_set
    }
    context_tickers: set[str] = set()
    for pattern in [
        r"(?:cổ phiếu|mã|HOSE|HSX|chứng khoán|sàn)\s{0,20}([A-Z][A-Z0-9.]{1,4})(?![A-Z0-9])",
        r"(?<![A-Z0-9])([A-Z][A-Z0-9.]{1,4})\s{0,20}(?:cổ phiếu|HOSE|HSX|chứng khoán)",
    ]:
        context_tickers.update(
            match.group(1)
            for match in re.finditer(pattern, body, flags=re.IGNORECASE)
            if match.group(1).upper() in ticker_set
        )
    context_tickers = {ticker.upper() for ticker in context_tickers}

    matches: dict[str, dict[str, Any]] = {}
    for record in company_dictionary:
        alias = record["alias"]
        ticker = record["ticker"]
        is_ticker = alias == ticker
        method = ""
        score = 0
        if is_ticker and ticker in tag_values:
            method, score = "tag_exact", 3
        elif is_ticker and ticker in title_tickers:
            method, score = "ticker_title_regex", 3
        elif not is_ticker and alias.casefold() in text_casefold:
            method, score = "company_alias_regex", 2
        elif is_ticker and ticker in context_tickers:
            method, score = "ticker_context_regex", 2

        if score:
            current = matches.get(ticker)
            if current is None or score > current["match_score"]:
                matches[ticker] = {
                    "ticker": ticker,
                    "matched_alias": alias,
                    "match_score": score,
                    "match_method": method,
                }

    article_id = make_article_id(str(article.get("url", "")))
    linked_at = datetime.now(timezone.utc)
    output = []
    for match in sorted(matches.values(), key=lambda item: item["ticker"]):
        output.append(
            {
                "article_id": article_id,
                "url": article.get("url"),
                "title": article.get("title"),
                "published_at": article.get("published_at"),
                "source": article.get("source"),
                "category": article.get("category"),
                "ticker": match["ticker"],
                "matched_alias": match["matched_alias"],
                "match_method": match["match_method"],
                "match_score": match["match_score"],
                "linked_at": linked_at,
            }
        )
    return output


def link_news_to_tickers(news: pl.DataFrame, company_profile: pl.DataFrame) -> pl.DataFrame:
    dictionary = build_company_dictionary(company_profile)
    rows: list[dict[str, Any]] = []
    for article in news.to_dicts():
        rows.extend(link_article_to_tickers(article, dictionary))

    schema = {
        "article_id": pl.Utf8,
        "url": pl.Utf8,
        "title": pl.Utf8,
        "published_at": pl.Date,
        "source": pl.Utf8,
        "category": pl.Utf8,
        "ticker": pl.Utf8,
        "matched_alias": pl.Utf8,
        "match_method": pl.Utf8,
        "match_score": pl.Int64,
        "linked_at": pl.Datetime(time_zone="UTC"),
    }
    if not rows:
        return pl.DataFrame(schema=schema)
    return (
        pl.DataFrame(rows, schema=schema)
        .unique(subset=["article_id", "ticker"], keep="last", maintain_order=True)
        .sort(["published_at", "ticker", "source"])
    )


def build_output_path(
    output_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
    partition_date: date | None = None,
) -> Path:
    output_date = partition_date or date.today()
    return output_dir / NEWS_ENTITY_LINKS_PREFIX / f"year={output_date:%Y}" / f"month={output_date:%m}" / "data.parquet"


def save_links(frame: pl.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(output_path)
    return output_path


def run(
    local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    local_gold_dir: Path = DEFAULT_LOCAL_GOLD_DIR,
) -> dict[str, Any]:
    news = load_silver_news(local_silver_dir)
    company_profile = load_silver_company_profile(local_silver_dir)
    linked = link_news_to_tickers(news, company_profile)
    output_path = build_output_path(local_gold_dir)
    save_links(linked, output_path)
    return {
        "dataset": NEWS_ENTITY_LINKS_PREFIX,
        "article_count": news.height,
        "linked_row_count": linked.height,
        "linked_article_count": linked.get_column("article_id").n_unique() if linked.height else 0,
        "linked_ticker_count": linked.get_column("ticker").n_unique() if linked.height else 0,
        "local_path": str(output_path),
    }
