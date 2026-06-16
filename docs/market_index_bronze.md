# Bronze Layer - Market Index

Ngày 6 theo `Report.md` tập trung ingest dữ liệu chỉ số thị trường vào Bronze. Phạm vi chỉ gồm dữ liệu thô, chưa làm Silver, Gold, Kafka hoặc dashboard.

## Nguồn dữ liệu

Nguồn chính: `vnstock`.

Chỉ số mặc định:

- `VNINDEX`
- `VN30`
- `HNXINDEX`

## Schema raw tối thiểu

- `index_code`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `trading_value` nếu nguồn có cung cấp

## Bronze layout

Bucket:

```text
bronze
```

Object path:

```text
market_index/
└── index_code=VNINDEX/
    └── year=2026/
        └── month=06/
            └── day=14/
                └── data.parquet
```

Partition theo `index_code` và ngày ingest.

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
uv run python scripts/run_market_index_ingest.py
```

## Kiểm thử

Tests mock phần fetch/upload, không gọi API thật.

```powershell
uv run pytest
uv run ruff check .
```
