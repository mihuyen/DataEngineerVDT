from pathlib import Path

import polars as pl
import pytest

from src.ingestion import company_profile


def sample_company_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "symbol": ["VCB"],
            "exchange": ["HOSE"],
            "company_type": ["Ngân hàng"],
            "website": ["https://vietcombank.com.vn"],
        }
    )


def test_load_config_reads_company_profile_source() -> None:
    config = company_profile.load_config()

    assert config["name"] == "company_profile"
    assert config["source_type"] == "listed_company_profile"
    assert config["bronze_bucket"] == "bronze"
    assert config["bronze_path"] == "company_profile/"


def test_validate_schema_accepts_symbol_column() -> None:
    company_profile.validate_schema(sample_company_frame())


def test_validate_schema_rejects_missing_symbol() -> None:
    frame = sample_company_frame().drop("symbol")

    with pytest.raises(ValueError, match="symbol"):
        company_profile.validate_schema(frame)


def test_build_bronze_object_name_partitions_by_ingest_date() -> None:
    object_name = company_profile.build_bronze_object_name(
        ingest_date=company_profile.date(2026, 6, 14),
        bronze_path="company_profile/",
    )

    assert object_name == "company_profile/year=2026/month=06/day=14/data.parquet"


def test_resolve_ticker_universe_from_explicit_tickers() -> None:
    universe = company_profile.resolve_ticker_universe(tickers=["vcb", " acb "])

    assert universe.get_column("symbol").to_list() == ["VCB", "ACB"]


def test_save_parquet_writes_file(tmp_path: Path) -> None:
    output_path = tmp_path / "company_profile" / "data.parquet"

    saved_path = company_profile.save_parquet(sample_company_frame(), output_path)

    assert saved_path == output_path
    assert output_path.is_file()


def test_run_uses_mocked_fetch_and_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: dict[str, str] = {}

    def fake_fetch_company_profile(ticker: str, exchange: str | None, source: str) -> pl.DataFrame:
        assert source == "kbs"
        if ticker == "BAD":
            raise ValueError("provider error")
        return pl.DataFrame(
            {
                "symbol": [ticker],
                "exchange": [exchange or "HOSE"],
                "company_type": ["sample"],
            }
        )

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        uploaded["local_path"] = str(local_path)
        uploaded["object_name"] = object_name
        uploaded["bucket_name"] = bucket_name

    monkeypatch.setattr(company_profile, "fetch_company_profile", fake_fetch_company_profile)
    monkeypatch.setattr(company_profile, "upload_to_minio", fake_upload_to_minio)

    result = company_profile.run(
        tickers=["VCB", "BAD", "ACB"],
        local_output_dir=tmp_path,
        mode="profile",
    )

    assert result["requested"] == "3"
    assert result["succeeded"] == "2"
    assert result["skipped"] == "0"
    assert result["failed"] == "1"
    assert len(result["results"]) == 2
    assert all(Path(item["local_path"]).is_file() for item in result["results"])
    assert uploaded["bucket_name"] == "bronze"
    assert uploaded["object_name"].startswith("company_profile/dataset=profile/ticker=ACB/")


def test_run_listing_mode_saves_full_listing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uploaded: dict[str, str] = {}

    def fake_fetch_company_listing(exchanges: list[str], listing_source: str) -> pl.DataFrame:
        assert exchanges == ["HOSE", "HNX", "UPCOM"]
        assert listing_source == "kbs"
        return pl.DataFrame(
            {
                "symbol": ["VCB", "ACB"],
                "exchange": ["HOSE", "HNX"],
                "organ_name": ["Vietcombank", "ACB"],
                "source": ["KBS", "KBS"],
                "ingested_at": ["2026-06-14T00:00:00", "2026-06-14T00:00:00"],
            }
        )

    def fake_upload_to_minio(local_path: Path, object_name: str, bucket_name: str) -> None:
        uploaded["local_path"] = str(local_path)
        uploaded["object_name"] = object_name
        uploaded["bucket_name"] = bucket_name

    monkeypatch.setattr(company_profile, "fetch_company_listing", fake_fetch_company_listing)
    monkeypatch.setattr(company_profile, "upload_to_minio", fake_upload_to_minio)

    result = company_profile.run(local_output_dir=tmp_path, mode="listing")

    assert result["mode"] == "listing"
    assert result["requested"] == "2"
    assert result["succeeded"] == "2"
    assert result["failed"] == "0"
    assert Path(result["local_path"]).is_file()
    assert uploaded["object_name"].startswith("company_profile/")


def test_run_profile_mode_skips_existing_ticker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    object_name = company_profile.build_bronze_object_name(
        bronze_path="company_profile/dataset=profile/ticker=VCB/"
    )
    existing_path = tmp_path / object_name
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    sample_company_frame().write_parquet(existing_path)

    def fail_fetch_company_profile(ticker: str, exchange: str | None, source: str) -> pl.DataFrame:
        raise AssertionError("fetch should not be called when skip_existing=True")

    monkeypatch.setattr(company_profile, "fetch_company_profile", fail_fetch_company_profile)

    result = company_profile.run(
        tickers=["VCB"],
        local_output_dir=tmp_path,
        mode="profile",
        skip_existing=True,
    )

    assert result["requested"] == "1"
    assert result["succeeded"] == "0"
    assert result["skipped"] == "1"
    assert result["failed"] == "0"
    assert result["results"][0]["status"] == "SKIPPED"
