from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import great_expectations as gx
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "quality_reports"
REQUIRED_COLUMNS = [
    "ticker",
    "company_name",
    "exchange",
    "sector_id",
    "sector_name",
    "shares_outstanding",
]
VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM", "UNKNOWN"}


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


def validate_company_profile(frame: pl.DataFrame) -> QualityReport:
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
            source_name="silver_company_profile",
            record_count=frame.height,
            error_count=error_count,
            success=False,
            expectations=expectations,
            gx_version=gx.__version__,
        )

    checks = [
        (
            "expect_ticker_to_not_be_null",
            pl.col("ticker").is_not_null() & (pl.col("ticker").cast(pl.Utf8).str.len_chars() > 0),
            "ticker must not be null or empty",
        ),
        (
            "expect_company_name_to_not_be_null",
            pl.col("company_name").is_not_null()
            & (pl.col("company_name").cast(pl.Utf8).str.len_chars() > 0),
            "company_name must not be null or empty",
        ),
        (
            "expect_exchange_to_be_valid",
            pl.col("exchange").is_in(sorted(VALID_EXCHANGES)),
            "exchange must be HOSE, HNX, UPCOM, or UNKNOWN",
        ),
        (
            "expect_sector_id_to_not_be_null",
            pl.col("sector_id").is_not_null() & (pl.col("sector_id").cast(pl.Utf8).str.len_chars() > 0),
            "sector_id must not be null or empty",
        ),
        (
            "expect_shares_outstanding_to_be_non_negative",
            pl.col("shares_outstanding") >= 0,
            "shares_outstanding >= 0",
        ),
    ]

    for name, condition, details in checks:
        failed = _failed_count(frame, condition)
        expectations.append(
            ExpectationResult(
                name=name,
                success=failed == 0,
                failed_count=failed,
                details=details,
            )
        )

    duplicate_count = (
        frame.group_by("ticker")
        .len()
        .filter(pl.col("len") > 1)
        .select((pl.col("len") - 1).sum())
        .item()
        or 0
    )
    expectations.append(
        ExpectationResult(
            name="expect_ticker_to_be_unique",
            success=duplicate_count == 0,
            failed_count=duplicate_count,
            details="ticker must be unique",
        )
    )

    error_count = sum(expectation.failed_count for expectation in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name="silver_company_profile",
        record_count=frame.height,
        error_count=error_count,
        success=all(expectation.success for expectation in expectations),
        expectations=expectations,
        gx_version=gx.__version__,
    )


def save_quality_report(
    report: QualityReport,
    report_dir: Path = DEFAULT_REPORT_DIR,
    report_date: date | None = None,
    report_name: str | None = None,
) -> Path:
    output_date = report_date or date.today()
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / (report_name or f"{output_date:%Y-%m-%d}_company_profile.json")
    output_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
