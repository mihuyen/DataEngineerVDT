# Bronze Layer - OHLCV

Bronze Layer là tầng lưu dữ liệu thô nhất của hệ thống Data Lakehouse. Với Ngày 3, phạm vi chỉ gồm ingest dữ liệu OHLCV từ `vnstock` và lưu vào MinIO dưới dạng Parquet.

## Nguyên tắc Bronze

- Lưu dữ liệu gần nhất với nguồn, chưa làm sạch nghiệp vụ.
- Không tính chỉ báo kỹ thuật.
- Không ghi vào Silver, Gold, ClickHouse hoặc dashboard.
- Dữ liệu được partition để dễ truy vết theo mã cổ phiếu và ngày ingest.
- Credential MinIO đọc từ environment, không hardcode trong code.

## Partition strategy

Bucket sử dụng:

```text
bronze
```

Object path chuẩn:

```text
ohlcv/
└── ticker=VCB/
    └── year=2026/
        └── month=06/
            └── day=10/
                └── data.parquet
```

Ý nghĩa:

- `ticker`: mã cổ phiếu.
- `year/month/day`: ngày ingest vào Bronze, không nhất thiết là ngày giao dịch.
- `data.parquet`: file dữ liệu thô đã lấy từ nguồn.

## Luồng ingest

```text
vnstock
↓
DataFrame
↓
Polars DataFrame
↓
Parquet local
↓
MinIO bucket bronze
```

## Module chính

- `src/ingestion/vnstock_ohlcv.py`: ingest OHLCV từ `vnstock`.
- `src/common/minio_client.py`: helper kết nối và upload MinIO.
- `scripts/init_minio.py`: tạo bucket `bronze`, `silver`, `gold` nếu thiếu.
- `scripts/run_ohlcv_ingest.py`: chạy ingest một mã, một nhóm mã, hoặc toàn bộ `HOSE/HNX/UPCOM`.

## Biến môi trường cần có

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

Có thể dùng `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` thay cho access key/secret key trong môi trường local.

## Cách chạy

Start MinIO trước:

```powershell
docker compose up -d minio
```

Tạo bucket:

```powershell
uv run python scripts/init_minio.py
```

Chạy ingest toàn bộ các mã thuộc `HOSE`, `HNX`, `UPCOM`:

```powershell
uv run python scripts/run_ohlcv_ingest.py
```

Chạy thử một vài mã cụ thể:

```powershell
uv run python scripts/run_ohlcv_ingest.py --tickers VCB ACB FPT
```

Test nhanh 10 mã đầu tiên trước khi chạy toàn thị trường:

```powershell
uv run python scripts/run_ohlcv_ingest.py --exchanges HOSE HNX UPCOM --limit 10
```

Khi chạy toàn bộ thị trường, giữ delay để tránh quota `vnstock` và bật resume nếu phải chạy lại:

```powershell
uv run python scripts/run_ohlcv_ingest.py --exchanges HOSE HNX UPCOM --request-delay-seconds 3.5 --skip-existing
```

Nếu API listing của `vnstock` bị lỗi hoặc bị chặn, có thể chuẩn bị file CSV có cột `symbol` hoặc `ticker` rồi chạy:

```powershell
uv run python scripts/run_ohlcv_ingest.py --ticker-file configs/tickers.csv
```

## Kiểm thử

Test không gọi API thật và không kết nối MinIO thật. Các phần fetch/upload được mock khi cần.

```powershell
uv run pytest
uv run ruff check .
```

## TODO

- Ngày 4: xây dựng Silver Layer đọc từ Bronze.
- Bổ sung retry/backoff cho fetch `vnstock`.
- Bổ sung metadata file như `ingested_at`, `source_name`, `ticker`, `start_date`, `end_date` nếu cần truy vết sâu hơn.
