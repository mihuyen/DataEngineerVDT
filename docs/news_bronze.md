# Bronze Layer - Market News

Tài liệu này mô tả riêng bước Bronze (crawl thô) của luồng Tin tức — bước đầu tiên trong DAG `news_crawl_5m`. Các bước sau (Silver, Entity Linking, PhoBERT sentiment, Gold) xem tại `architecture.md` và README phần "Luồng tin tức".

## Nguồn crawl

- VnExpress
- Vietstock
- CafeF

## Schema raw

- `url`
- `title`
- `published_at`
- `description`
- `content`
- `tags`
- `source`
- `category`
- `crawl_at`

## Bronze layout

```text
bronze/
└── news/
    └── source=multi/
        └── year=2026/
            └── month=06/
                └── day=14/
                    └── data.parquet
```

## Cách chạy

Start MinIO:

```powershell
docker compose up -d minio
```

Tạo bucket nếu thiếu:

```powershell
uv run python scripts/init_minio.py
```

Chạy ingest:

```powershell
uv run python scripts/run_news_ingest.py
```

## Ghi chú

- Không dùng Kafka/Redis trong project Ngày 7.
- Crawler có deduplicate URL trong một lượt chạy.
- Có lọc bài cũ theo `max_age_days` trong `configs/sources.yaml`.
- Tests mock HTML/HTTP, không gọi website thật.
