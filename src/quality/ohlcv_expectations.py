from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "quality_reports"
DEFAULT_LOCAL_SILVER_DIR = PROJECT_ROOT / "data" / "silver_local"
REQUIRED_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class ExpectationResult:
    """Result for one OHLCV quality expectation."""

    name: str
    success: bool
    failed_count: int
    details: str


@dataclass(frozen=True)
class QualityReport:
    """Serializable quality report for OHLCV Silver validation."""

    generated_at: str
    source_name: str
    record_count: int
    error_count: int
    success: bool
    expectations: list[ExpectationResult]
    gx_version: str


def _failed_count(frame: pl.DataFrame, condition: pl.Expr) -> int:
    """Count rows that do not satisfy a Polars boolean condition."""
    if frame.is_empty():
        return 0
    return frame.filter(~condition.fill_null(False)).height


def validate_ohlcv(frame: pl.DataFrame, source_name: str = "vnstock_ohlcv") -> QualityReport:
    """Validate OHLCV data using Great Expectations-style rules.

    The project keeps the checks in Polars so validation can run without creating a
    persistent Great Expectations context. The module still depends on
    Great Expectations and records its version for reproducibility.
    """
    expectations: list[ExpectationResult] = []
    columns = set(frame.columns)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
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
            source_name=source_name,
            record_count=frame.height,
            error_count=error_count,
            success=False,
            expectations=expectations,
            gx_version="n/a",
        )

    checks = [
        (
            "expect_ticker_to_not_be_null",
            pl.col("ticker").is_not_null() & (pl.col("ticker").cast(pl.Utf8).str.len_chars() > 0),
            "ticker must not be null or empty",
        ),
        (
            "expect_date_to_not_be_null",
            pl.col("date").is_not_null(),
            "date must not be null",
        ),
        (
            "expect_close_to_not_be_null",
            pl.col("close").is_not_null(),
            "close must not be null",
        ),
        (
            "expect_volume_to_not_be_null",
            pl.col("volume").is_not_null(),
            "volume must not be null",
        ),
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
        expectations.append(
            ExpectationResult(
                name=name,
                success=failed == 0,
                failed_count=failed,
                details=details,
            )
        )

    duplicate_count = (
        frame.group_by(["ticker", "date"])
        .len()
        .filter(pl.col("len") > 1)
        .select((pl.col("len") - 1).sum())
        .item()
        or 0
    )
    expectations.append(
        ExpectationResult(
            name="expect_ticker_date_to_be_unique",
            success=duplicate_count == 0,
            failed_count=duplicate_count,
            details="ticker + date must be unique",
        )
    )

    error_count = sum(expectation.failed_count for expectation in expectations)
    return QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_name=source_name,
        record_count=frame.height,
        error_count=error_count,
        success=all(expectation.success for expectation in expectations),
        expectations=expectations,
        gx_version="n/a",
    )


def discover_silver_ohlcv_files(local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR) -> list[Path]:
    """Discover local Silver OHLCV parquet files."""
    base_dir = local_silver_dir / "ohlcv"
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("ticker=*/year=*/month=*/data.parquet"))


def load_silver_ohlcv_dataset(
    local_silver_dir: Path = DEFAULT_LOCAL_SILVER_DIR,
    tickers: list[str] | None = None,
) -> pl.DataFrame:
    """Load local Silver OHLCV data for quality validation."""
    allowed_tickers = {ticker.upper() for ticker in tickers} if tickers else None
    frames: list[pl.DataFrame] = []

    for file_path in discover_silver_ohlcv_files(local_silver_dir):
        ticker = file_path.parts[-4].replace("ticker=", "").upper()
        if allowed_tickers is not None and ticker not in allowed_tickers:
            continue
        frames.append(pl.read_parquet(file_path))

    if not frames:
        raise FileNotFoundError("No Silver OHLCV parquet files found for quality validation")

    return pl.concat(frames, how="diagonal_relaxed")


def save_quality_report(
    report: QualityReport,
    report_dir: Path = DEFAULT_REPORT_DIR,
    report_date: date | None = None,
    report_name: str | None = None,
) -> Path:
    """Save a quality report as JSON."""
    output_date = report_date or date.today()
    report_dir.mkdir(parents=True, exist_ok=True)
    output_name = report_name or f"{output_date:%Y-%m-%d}_validation.json"
    output_path = report_dir / output_name
    payload = asdict(report)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
