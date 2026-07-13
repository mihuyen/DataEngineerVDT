# Bronze Layer - Market Index

Ingest dữ liệu chỉ số thị trường vào Bronze, là 1 trong 3 nhánh song song của DAG Batch (cùng OHLCV và danh sách/hồ sơ doanh nghiệp).

## Nguồn dữ liệu

Nguồn chính: Vnstock (VCI).

Chỉ số theo dõi:

- `VNINDEX`
- `VN30`

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
