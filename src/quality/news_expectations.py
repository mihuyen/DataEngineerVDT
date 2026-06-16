from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import great_expectations as gx
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "quality_reports"
REQUIRED_COLUMNS = ["url", "title", "content", "source", "published_at"]
MIN_CONTENT_LENGTH = 50


@dataclass(frozen=True)
class ExpectationResult:
    name: str
    success: bool
    failed_count: int
    details: str


@dataclass(frozen=True)
class QualityReport:
    generated_at: str
    source_name: str
    record_count: int
    error_count: int
    success: bool
    expectations: list[ExpectationResult]
    gx_version: str


def _failed_count(frame: pl.DataFrame, condition: pl.Expr) -> int:
    if frame.is_empty():
        return 0
    return frame.filter(~condition.fill_null(False)).height


def validate_news(frame: pl.DataFrame) -> QualityReport:
    expectations: list[ExpectationResult] = []
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    expectations.append(
        ExpectationResult(
            name="expect_required_columns_to_exist",
            success=not missing_columns,
            failed_count=len(missing_columns),
            details=", ".join(missing_columns) if missing_columns else "all required columns exist",
        )
    )

    if missing_columns:
        error_count = sum(expectation.failed_count for expectation in expectations)
        return QualityReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_name="silver_news",
            record_count=frame.height,
            error_count=error_count,
            success=False,
            expectations=expectations,
            gx_version=gx.__version__,
        )

    checks = [
        (
            "expect_url_to_not_be_null",
            pl.col("url").is_not_null() & (pl.col("url").cast(pl.Utf8).str.len_chars() > 0),
            "url must not be null or empty",
        ),
        (
            "expect_title_to_not_be_null",
            pl.col("title").is_not_null() & (pl.col("title").cast(pl.Utf8).str.len_chars() > 0),
            "title must not be null or empty",
        ),
        (
            "expect_content_to_be_long_enough",
            pl.col("content").is_not_null()
            & (pl.col("content").cast(pl.Utf8).str.len_chars() >= MIN_CONTENT_LENGTH),
            f"content length >= {MIN_CONTENT_LENGTH}",
        ),
        (
            "expect_source_to_not_be_null",
            pl.col("source").is_not_null() & (pl.col("source").cast(pl.Utf8).str.len_chars() > 0),
            "source must not be null or empty",
        ),
        (
            "expect_published_at_to_not_be_null",
            pl.col("published_at").is_not_null(),
            "published_at must not be null",
        ),
    ]

    for name, condition, details in checks:
        failed = _failed_count(frame, condition)
        expectations.append(ExpectationResult(name, failed == 0, failed, details))

    duplicate_count = (
        frame.group_by("url")
        .len()
        .filter(pl.col("len") > 1)
        .select((pl.col("len") - 1).sum())
        .item()
        or 0
    )
    expectations.append(
        ExpectationResult(
            name="expect_url_to_be_unique",
            success=duplicate_count == 0,
            failed_count=duplicate_count,
            details="url must be unique",
        )
    )

    error_count = sum(expectation.failed_count for expectation in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name="silver_news",
        record_count=frame.height,
        error_count=error_count,
        success=all(expectation.success for expectation in expectations),
        expectations=expectations,
        gx_version=gx.__version__,
    )


def save_quality_report(
    report: QualityReport,
    report_dir: Path = DEFAULT_REPORT_DIR,
    report_name: str = "news_silver_validation.json",
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / report_name
    output_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
