from pathlib import Path

import polars as pl

from src.transform import news_transform


def sample_news() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "url": ["https://example.com/a", "https://example.com/a", "https://example.com/b"],
            "title": [" Tin   A ", "Tin A update", "Tin B"],
            "published_at": ["2026-06-14", "2026-06-14", "2026-06-13"],
            "description": ["Mo ta", "Mo ta update", "Mo ta B"],
            "content": [
                "Noi dung bai viet A du dai de vuot qua nguong kiem tra toi thieu.",
                "Noi dung bai viet A ban cap nhat du dai de vuot qua nguong kiem tra.",
                "short",
            ],
            "source": ["CafeF", "CafeF", "VnExpress"],
            "category": ["Chung khoan", "Chung khoan", "Vi mo"],
        }
    )


def test_transform_news_deduplicates_and_filters_short_content() -> None:
    transformed = news_transform.transform_news(sample_news())

    assert transformed.height == 1
    assert transformed.get_column("url").to_list() == ["https://example.com/a"]
    assert "processed_at" in transformed.columns


def test_run_news_transform_from_local(tmp_path: Path) -> None:
    bronze_file = tmp_path / "bronze" / "news" / "source=multi" / "year=2026" / "month=06" / "day=14" / "data.parquet"
    bronze_file.parent.mkdir(parents=True)
    sample_news().write_parquet(bronze_file)

    result = news_transform.run(
        local_bronze_dir=tmp_path / "bronze",
        local_silver_dir=tmp_path / "silver",
        upload_to_minio=False,
    )

    assert result["record_count"] == 1
    assert Path(result["local_path"]).is_file()
