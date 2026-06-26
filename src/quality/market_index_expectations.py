from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import great_expectations as gx
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "quality_reports"
REQUIRED_COLUMNS = ["index_code", "date", "open", "high", "low", "close", "volume"]
EXPECTED_INDEX_CODES = {"VNINDEX", "VN30"}


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


def validate_market_index(frame: pl.DataFrame) -> QualityReport:
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
            source_name="silver_market_index",
            record_count=frame.height,
            error_count=error_count,
            success=False,
            expectations=expectations,
            gx_version=gx.__version__,
        )

    checks = [
        (
            "expect_index_code_to_not_be_null",
            pl.col("index_code").is_not_null() & (pl.col("index_code").cast(pl.Utf8).str.len_chars() > 0),
            "index_code must not be null or empty",
        ),
        (
            "expect_index_code_to_be_expected",
            pl.col("index_code").is_in(sorted(EXPECTED_INDEX_CODES)),
            "index_code must be one of expected market indexes",
        ),
        ("expect_date_to_not_be_null", pl.col("date").is_not_null(), "date must not be null"),
        ("expect_open_to_be_positive", pl.col("open") > 0, "open > 0"),
        ("expect_high_to_be_positive", pl.col("high") > 0, "high > 0"),
        ("expect_low_to_be_positive", pl.col("low") > 0, "low > 0"),
        ("expect_close_to_be_positive", pl.col("close") > 0, "close > 0"),
        ("expect_volume_to_be_non_negative", pl.col("volume") >= 0, "volume >= 0"),
        ("expect_high_to_be_at_least_low", pl.col("high") >= pl.col("low"), "high >= low"),
        ("expect_high_to_be_at_least_open", pl.col("high") >= pl.col("open"), "high >= open"),
        ("expect_high_to_be_at_least_close", pl.col("high") >= pl.col("close"), "high >= close"),
        ("expect_low_to_be_at_most_open", pl.col("low") <= pl.col("open"), "low <= open"),
        ("expect_low_to_be_at_most_close", pl.col("low") <= pl.col("close"), "low <= close"),
    ]

    for name, condition, details in checks:
        failed = _failed_count(frame, condition)
        expectations.append(ExpectationResult(name, failed == 0, failed, details))

    duplicate_count = (
        frame.group_by(["index_code", "date"])
        .len()
        .filter(pl.col("len") > 1)
        .select((pl.col("len") - 1).sum())
        .item()
        or 0
    )
    expectations.append(
        ExpectationResult(
            name="expect_index_code_date_to_be_unique",
            success=duplicate_count == 0,
            failed_count=duplicate_count,
            details="index_code + date must be unique",
        )
    )

    missing_index_count = len(EXPECTED_INDEX_CODES - set(frame.get_column("index_code").unique().to_list()))
    expectations.append(
        ExpectationResult(
            name="expect_expected_index_codes_to_exist",
            success=missing_index_count == 0,
            failed_count=missing_index_count,
            details=", ".join(sorted(EXPECTED_INDEX_CODES)),
        )
    )

    error_count = sum(expectation.failed_count for expectation in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name="silver_market_index",
        record_count=frame.height,
        error_count=error_count,
        success=all(expectation.success for expectation in expectations),
        expectations=expectations,
        gx_version=gx.__version__,
    )


def save_quality_report(
    report: QualityReport,
    report_dir: Path = DEFAULT_REPORT_DIR,
    report_name: str = "market_index_silver_validation.json",
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / report_name
    output_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
