from datetime import date
from pathlib import Path

import polars as pl
import pytest

from src.ingestion import vnstock_ohlcv


def sample_ohlcv_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2026, 6, 10)],
            "open": [100.0],
            "high": [105.0],
            "low": [99.0],
            "close": [102.0],
            "volume": [1_000_000],
        }
    )


def test_load_config_reads_vnstock_source() -> None:
    config = vnstock_ohlcv.load_config()

    assert config["name"] == "vnstock_ohlcv"
    assert config["source_type"] == "ohlcv"
    assert config["bronze_bucket"] == "bronze"
    assert config["bronze_path"] == "ohlcv/"


def test_validate_schema_accepts_required_columns() -> None:
    vnstock_ohlcv.validate_schema(sample_ohlcv_frame())


def test_validate_schema_rejects_missing_column() -> None:
    frame = sample_ohlcv_frame().drop("volume")

    with pytest.raises(ValueError, match="volume"):
        vnstock_ohlcv.validate_schema(frame)


def test_build_bronze_object_name_partitions_by_ingest_date() -> None:
    object_name = vnstock_ohlcv.build_bronze_object_name(
        ingest_date=date(2026, 6, 10),
        bronze_path="ohlcv/",
    )

    assert object_name == "ohlcv/year=2026/month=06/day=10/data.parquet"


def test_fetch_ticker_universe_filters_requested_exchanges(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeListing:
        def __init__(self, source: str) -> None:
            assert source == "kbs"

        def symbols_by_exchange(self) -> pl.DataFrame:
            return pl.DataFrame(
                {
                    "symbol": ["VCB", "ACB", "VGI", "E1VFVN30"],
                    "exchange": ["HOSE", "HNX", "UPCOM", "HOSE"],
                    "type": ["STOCK", "STOCK", "STOCK", "ETF"],
                }
            )

    monkeypatch.setattr("vnstock.api.listing.Listing", FakeListing)

    universe = vnstock_ohlcv.fetch_ticker_universe(exchanges=["HOSE", "HNX", "UPCOM"])

    assert universe.get_column("symbol").to_list() == ["ACB", "VCB", "VGI"]


def test_save_parquet_writes_file(tmp_path: Path) -> None:
    output_path = tmp_path / "ohlcv" / "data.parquet"

    saved_path = vnstock_ohlcv.save_parquet(sample_ohlcv_frame(), output_path)

    assert saved_path == output_path
    assert output_path.is_file()


def test_read_tickers_from_file(tmp_path: Path) -> None:
    ticker_file = tmp_path / "tickers.csv"
    ticker_file.write_text("symbol\nvcb\nACB\nvcb\n", encoding="utf-8")

    tickers = vnstock_ohlcv.read_tickers_from_file(ticker_file)

    assert tickers == ["ACB", "VCB"]


def test_run_many_writes_one_combined_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: dict[str, str] = {}

    def fake_fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pl.DataFrame:
        assert start_date == "2026-05-10"
        assert end_date == "2026-06-10"
        return sample_ohlcv_frame()

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        uploaded["local_path"] = str(local_path)
        uploaded["object_name"] = object_name
        uploaded["bucket_name"] = bucket_name

    monkeypatch.setattr(vnstock_ohlcv, "fetch_ohlcv", fake_fetch_ohlcv)
    monkeypatch.setattr(vnstock_ohlcv, "upload_to_minio", fake_upload_to_minio)

    result = vnstock_ohlcv.run_many(
        tickers=["VCB", "ACB"],
        start_date="2026-05-10",
        end_date="2026-06-10",
        local_output_dir=tmp_path,
    )

    assert result["bucket"] == "bronze"
    assert result["object_name"].startswith("ohlcv/year=")
    assert "ticker=" not in result["object_name"]
    assert result["succeeded"] == "2"
    combined = pl.read_parquet(result["local_path"])
    assert sorted(combined.get_column("ticker").unique().to_list()) == ["ACB", "VCB"]
    assert uploaded["bucket_name"] == "bronze"


def test_run_many_continues_when_one_ticker_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pl.DataFrame:
        if ticker == "BAD":
            raise ValueError("provider error")
        return sample_ohlcv_frame()

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        assert local_path.is_file()
        assert bucket_name == "bronze"

    monkeypatch.setattr(vnstock_ohlcv, "fetch_ohlcv", fake_fetch_ohlcv)
    monkeypatch.setattr(vnstock_ohlcv, "upload_to_minio", fake_upload_to_minio)

    result = vnstock_ohlcv.run_many(
        tickers=["VCB", "BAD", "ACB"],
        start_date="2026-05-10",
        end_date="2026-06-10",
        local_output_dir=tmp_path,
    )

    assert result["requested"] == "3"
    assert result["succeeded"] == "2"
    assert result["skipped"] == "0"
    assert result["failed"] == "1"
    assert result["errors"][0]["ticker"] == "BAD"


def test_run_many_skips_existing_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    object_name = vnstock_ohlcv.build_bronze_object_name()
    existing_path = tmp_path / object_name
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    sample_ohlcv_frame().write_parquet(existing_path)

    def fail_fetch_ohlcv(ticker: str, start_date: str, end_date: str) -> pl.DataFrame:
        raise AssertionError("fetch should not be called when skip_existing=True")

    monkeypatch.setattr(vnstock_ohlcv, "fetch_ohlcv", fail_fetch_ohlcv)

    result = vnstock_ohlcv.run_many(
        tickers=["VCB"],
        start_date="2026-05-10",
        end_date="2026-06-10",
        local_output_dir=tmp_path,
        skip_existing=True,
    )

    assert result["skipped"] == "1"
    assert result["object_name"] == object_name
