# Bronze Layer - Market News

Ngày 7 theo `Report.md` ingest thử dữ liệu tin tức thị trường vào Bronze. Phạm vi chỉ gồm dữ liệu raw, chưa làm Silver, sentiment, entity linking, Gold hoặc dashboard.

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
