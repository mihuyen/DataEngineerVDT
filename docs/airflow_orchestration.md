# Airflow Orchestration

Tài liệu này mô tả DAG production đầu tiên cho pipeline Data Lakehouse chứng khoán Việt Nam.

## DAG chính

File DAG:

```text
dags/stock_lakehouse_daily.py
```

DAG ID:

```text
stock_lakehouse_daily
```

Lịch chạy mặc định:

```text
18:00 từ thứ Hai đến thứ Sáu, theo timezone Asia/Ho_Chi_Minh
```

## Luồng xử lý

```text
init_minio_buckets
        |
        +--> bronze_ohlcv -----------------------> silver_ohlcv
        +--> bronze_company_profile_listing -----> silver_company_profile
        +--> bronze_market_index ----------------> silver_market_index
        +--> bronze_market_news -----------------> silver_news

silver_ohlcv
silver_company_profile
silver_market_index
silver_news
        |
        v
quality_all
        |
        v
migrate_gold_schema
        |
        v
load_gold
```

## Ghi chú triển khai

- Airflow dùng image local `stock-airflow-uv:local`.
- Image này được build từ `docker/airflow.Dockerfile` và có sẵn `uv`.
- Toàn bộ project được mount vào `/opt/airflow/project`.
- DAG gọi các script bằng `uv run python scripts/...`.
- DAG đặt `UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock` để container dùng virtualenv Linux riêng, tránh dùng nhầm `.venv` Windows trên máy host.
- OHLCV ingest dùng `--skip-existing` và `--request-delay-seconds 5` để hạn chế lỗi rate limit của vnstock.
- DAG đặt timezone `Asia/Ho_Chi_Minh`, nên lịch `0 18 * * 1-5` là 18:00 giờ Việt Nam.
- Task `quality_all` là quality gate bắt buộc trước khi load Gold.

## Cách chạy lại Airflow sau khi cập nhật Dockerfile

```powershell
docker compose up -d --build airflow-webserver airflow-scheduler
```

Sau đó mở Airflow UI:

```text
http://localhost:8080
```

Tài khoản local mặc định:

```text
admin / admin
```

## Phạm vi hiện tại

DAG hiện tự động hóa các bước chính:

- Tạo bucket MinIO.
- Ingest Bronze cho OHLCV, company listing, market index, news.
- Transform Silver cho OHLCV, company profile, market index, news.
- Chạy quality checks cho OHLCV, company profile, market index và news.
- Migrate schema Gold.
- Load Gold vào ClickHouse.

## TODO

- Tách OHLCV full-market ingest thành nhiều task nhỏ theo exchange hoặc batch ticker.
- Thêm task kiểm tra số lượng object/file sau mỗi bước.
- Bổ sung alert khi task fail.
