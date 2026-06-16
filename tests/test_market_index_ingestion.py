from datetime import date
from pathlib import Path

import polars as pl
import pytest

from src.ingestion import market_index


def sample_index_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2026, 6, 14)],
            "open": [1300.0],
            "high": [1310.0],
            "low": [1290.0],
            "close": [1305.0],
            "volume": [100_000_000],
            "trading_value": [2_500_000_000.0],
            "index_code": ["VNINDEX"],
        }
    )


def test_load_config_reads_market_index_source() -> None:
    config = market_index.load_config()

    assert config["name"] == "market_index"
    assert config["source_type"] == "market_index_ohlcv"
    assert config["bronze_bucket"] == "bronze"
    assert config["bronze_path"] == "market_index/"
    assert [item["index_code"] for item in config["index_codes"]] == [
        "VNINDEX",
        "VN30",
        "HNXINDEX",
        "UPCOMINDEX",
    ]
    assert config["provider_source"] == "vci"
    assert config["index_codes"][0]["provider_symbol"] == "VNINDEX"


def test_validate_schema_accepts_required_columns() -> None:
    market_index.validate_schema(sample_index_frame())


def test_validate_schema_rejects_missing_column() -> None:
    frame = sample_index_frame().drop("volume")

    with pytest.raises(ValueError, match="volume"):
        market_index.validate_schema(frame)


def test_build_bronze_object_name_partitions_by_index_and_ingest_date() -> None:
    object_name = market_index.build_bronze_object_name(
        index_code="vnindex",
        ingest_date=date(2026, 6, 14),
        bronze_path="market_index/",
    )

    assert object_name == "market_index/index_code=VNINDEX/year=2026/month=06/day=14/data.parquet"


def test_save_parquet_writes_file(tmp_path: Path) -> None:
    output_path = tmp_path / "market_index" / "index_code=VNINDEX" / "data.parquet"

    saved_path = market_index.save_parquet(sample_index_frame(), output_path)

    assert saved_path == output_path
    assert output_path.is_file()


def test_run_uses_mocked_fetch_and_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: list[dict[str, str]] = []

    def fake_fetch_index_ohlcv(
        index_code: str,
        start_date: str,
        end_date: str,
        provider_symbol: str | None = None,
        provider_source: str = "vci",
    ) -> pl.DataFrame:
        assert index_code in {"VNINDEX", "VN30"}
        assert start_date == "2026-05-14"
        assert end_date == "2026-06-14"
        assert provider_symbol in {"VNINDEX", "VN30"}
        assert provider_source == "vci"
        return sample_index_frame().with_columns(pl.lit(index_code).alias("index_code"))

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        uploaded.append(
            {
                "local_path": str(local_path),
                "object_name": object_name,
                "bucket_name": bucket_name,
            }
        )

    monkeypatch.setattr(market_index, "fetch_index_ohlcv", fake_fetch_index_ohlcv)
    monkeypatch.setattr(market_index, "upload_to_minio", fake_upload_to_minio)

    results = market_index.run(
        index_codes=["VNINDEX", "VN30"],
        start_date="2026-05-14",
        end_date="2026-06-14",
        local_output_dir=tmp_path,
    )

    assert len(results) == 2
    assert all(result["bucket"] == "bronze" for result in results)
    assert all(result["status"] == "SUCCESS" for result in results)
    assert all(Path(result["local_path"]).is_file() for result in results)
    assert uploaded[0]["object_name"].startswith("market_index/index_code=VNINDEX/")


def test_run_continues_when_one_index_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_index_ohlcv(
        index_code: str,
        start_date: str,
        end_date: str,
        provider_symbol: str | None = None,
        provider_source: str = "vci",
    ) -> pl.DataFrame:
        if index_code == "VN30":
            raise ConnectionError("provider unavailable")
        return sample_index_frame().with_columns(pl.lit(index_code).alias("index_code"))

    monkeypatch.setattr(market_index, "fetch_index_ohlcv", fake_fetch_index_ohlcv)
    monkeypatch.setattr(market_index, "upload_to_minio", lambda **kwargs: None)

    results = market_index.run(
        index_codes=["VNINDEX", "VN30"],
        start_date="2026-05-14",
        end_date="2026-06-14",
        local_output_dir=tmp_path,
    )

    assert results[0]["status"] == "SUCCESS"
    assert results[1]["status"] == "FAILED"
    assert "provider unavailable" in results[1]["error"]
