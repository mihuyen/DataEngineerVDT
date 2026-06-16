from datetime import date
from pathlib import Path

import polars as pl

from src.transform import market_index_transform


def sample_market_index() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2026, 6, 10), date(2026, 6, 10), date(2026, 6, 11)],
            "open": [1000.0, 1000.0, 1001.0],
            "high": [1010.0, 1010.0, 1005.0],
            "low": [990.0, 990.0, 1000.0],
            "close": [1005.0, 1006.0, 1004.0],
            "volume": [1_000_000, 1_000_000, 2_000_000],
            "trading_value": [None, None, None],
            "index_code": ["vnindex", "VNINDEX", "VNINDEX"],
        }
    )


def test_transform_market_index_deduplicates_index_date() -> None:
    transformed = market_index_transform.transform_market_index(sample_market_index())

    assert transformed.height == 2
    assert transformed.get_column("index_code").to_list() == ["VNINDEX", "VNINDEX"]
    assert "processed_at" in transformed.columns


def test_run_market_index_transform_from_local(tmp_path: Path) -> None:
    bronze_file = tmp_path / "bronze" / "market_index" / "index_code=VNINDEX" / "year=2026" / "month=06" / "day=14" / "data.parquet"
    bronze_file.parent.mkdir(parents=True)
    sample_market_index().write_parquet(bronze_file)

    result = market_index_transform.run(
        local_bronze_dir=tmp_path / "bronze",
        local_silver_dir=tmp_path / "silver",
        upload_to_minio=False,
    )

    assert result["record_count"] == 2
    assert Path(result["local_path"]).is_file()
