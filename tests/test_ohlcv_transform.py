from datetime import date
from pathlib import Path

import polars as pl

from src.transform import ohlcv_transform


def raw_sample_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "Date": ["2026-06-10", "2026-06-10", "2026-06-11", "2026-06-12"],
            "Open": ["100", "100", "101", "102"],
            "High": ["105", "105", "99", "106"],
            "Low": ["99", "99", "100", "101"],
            "Close": ["102", "102", "98", "103"],
            "Volume": ["1000000", "1000000", "-1", "1200000"],
        }
    )


def test_cast_schema_uses_expected_dtypes() -> None:
    frame = ohlcv_transform.normalize_columns(raw_sample_frame())
    casted = ohlcv_transform.cast_schema(frame)

    assert casted.schema["date"] == pl.Date
    assert casted.schema["open"] == pl.Float64
    assert casted.schema["high"] == pl.Float64
    assert casted.schema["low"] == pl.Float64
    assert casted.schema["close"] == pl.Float64
    assert casted.schema["volume"] == pl.Int64


def test_transform_removes_duplicates_and_invalid_records() -> None:
    transformed = ohlcv_transform.transform_ohlcv(raw_sample_frame(), ticker="VCB")

    assert transformed.height == 2
    assert transformed["date"].to_list() == [date(2026, 6, 10), date(2026, 6, 12)]
    assert transformed["ticker"].to_list() == ["VCB", "VCB"]


def test_build_silver_object_name() -> None:
    object_name = ohlcv_transform.build_silver_object_name(
        ticker="vcb",
        partition_date=date(2026, 6, 10),
    )

    assert object_name == "ohlcv/ticker=VCB/year=2026/month=06/data.parquet"


def test_save_to_silver_writes_parquet(tmp_path: Path) -> None:
    transformed = ohlcv_transform.transform_ohlcv(raw_sample_frame(), ticker="VCB")

    output_path = ohlcv_transform.save_to_silver(
        transformed,
        ticker="VCB",
        output_dir=tmp_path,
        partition_date=date(2026, 6, 10),
    )

    assert output_path.is_file()
    assert output_path.relative_to(tmp_path).as_posix() == (
        "ohlcv/ticker=VCB/year=2026/month=06/data.parquet"
    )
    assert pl.read_parquet(output_path).height == 2


def test_sample_parquet_can_drive_transform() -> None:
    sample_path = Path("tests/data/sample_ohlcv.parquet")

    transformed = ohlcv_transform.transform_ohlcv(pl.read_parquet(sample_path), ticker="VCB")

    assert transformed.height == 2
    assert transformed["ticker"].to_list() == ["VCB", "VCB"]


def test_discover_local_bronze_tickers(tmp_path: Path) -> None:
    bronze_file = tmp_path / "ohlcv" / "ticker=VCB" / "year=2026" / "month=06" / "day=14" / "data.parquet"
    bronze_file.parent.mkdir(parents=True)
    raw_sample_frame().write_parquet(bronze_file)

    tickers = ohlcv_transform.discover_local_bronze_tickers(tmp_path)

    assert tickers == ["VCB"]


def test_run_many_transforms_discovered_tickers(tmp_path: Path) -> None:
    bronze_file = tmp_path / "bronze" / "ohlcv" / "ticker=VCB" / "year=2026" / "month=06" / "day=14" / "data.parquet"
    bronze_file.parent.mkdir(parents=True)
    raw_sample_frame().write_parquet(bronze_file)

    result = ohlcv_transform.run_many(
        local_bronze_dir=tmp_path / "bronze",
        local_silver_dir=tmp_path / "silver",
        upload_to_minio=False,
    )

    assert result["requested"] == "1"
    assert result["succeeded"] == "1"
    assert result["failed"] == "0"
    assert Path(result["results"][0]["local_path"]).is_file()
