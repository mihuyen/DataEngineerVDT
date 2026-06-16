from pathlib import Path

import polars as pl

from src.transform import company_profile_transform


def sample_company_profile() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "symbol": ["vcb", "VCB", "fpt"],
            "organ_name": [" Vietcombank ", "Vietcombank updated", "FPT"],
            "exchange": ["hose", "HOSE", "hose"],
            "company_type": ["Ngân hàng", None, "Công nghệ"],
            "outstanding_shares": [1000, 2000, 3000],
        }
    )


def test_transform_company_profile_deduplicates_symbol() -> None:
    transformed = company_profile_transform.transform_company_profile(sample_company_profile())

    assert transformed.height == 2
    assert transformed.get_column("ticker").to_list() == ["FPT", "VCB"]
    assert transformed.get_column("company_name").to_list() == ["FPT", "Vietcombank"]
    assert transformed.get_column("shares_outstanding").to_list() == [3000, 1000]
    assert "sector_id" in transformed.columns
    assert "processed_at" in transformed.columns


def test_run_company_profile_transform_from_local(tmp_path: Path) -> None:
    bronze_file = tmp_path / "bronze" / "company_profile" / "dataset=listing" / "year=2026" / "month=06" / "day=14" / "data.parquet"
    bronze_file.parent.mkdir(parents=True)
    sample_company_profile().write_parquet(bronze_file)

    result = company_profile_transform.run(
        local_bronze_dir=tmp_path / "bronze",
        local_silver_dir=tmp_path / "silver",
        upload_to_minio=False,
    )

    assert result["record_count"] == 2
    assert Path(result["local_path"]).is_file()
