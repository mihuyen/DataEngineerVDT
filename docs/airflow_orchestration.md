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

## Luồng xử lý (DAG `stock_lakehouse_daily` — chỉ luồng Batch, không gồm Tin tức)

Tin tức có DAG riêng `news_crawl_5m`, chạy độc lập mỗi 5 phút, 24/7 — không nằm trong DAG này.

```text
init_minio_buckets
        |
        +--> bronze_ohlcv -----------------------> silver_ohlcv
        +--> bronze_company_profile_listing -----> silver_company_profile
        +--> bronze_market_index ----------------> silver_market_index

silver_ohlcv, silver_company_profile, silver_market_index
        |
        v
quality_all  (Quality Gate — chặn nếu fail, không nạp Gold)
        |
        v
migrate_gold_schema
        |
        v
load_gold  (Python Gold Loader: giá + EMA/MACD)
        |
        v
reconcile_gold  (đối soát liên tầng — 10 điều kiện)
        |
        +--> dbt_run --> dbt_test          (tính SMA/RSI/Bollinger + kiểm tra công thức)
        +--> export_gold_to_minio
        +--> init_user_alerts --> check_alerts
        +--> backup_lakehouse              (ClickHouse + PostgreSQL)
        +--> intraday_ohlcv_backfill --> realtime_quality_check
        |
        v
export_frontend_data --> notify_dag_success (Telegram)
```

5 nhánh sau `reconcile_gold` chạy **song song, hoàn toàn độc lập** — không phụ thuộc lẫn nhau. `intraday_ohlcv_backfill` không được phép chặn công bố Gold (phụ thuộc API ngoài, dễ rate limit).

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

## DAG thứ hai — `news_crawl_5m`

File: `dags/news_crawl_5m.py`. Chạy mỗi 5 phút, 24/7, `max_active_runs=1`. Trong 1 vòng: crawl → Silver Transform → News Quality Gate → Entity Linking → PhoBERT → Sentiment Quality Gate → News Gold Loader → ClickHouse. Không có bước Reconciliation riêng (chạy chung với `reconcile_gold` của DAG Batch, cộng dồn cả ngày).

## Cảnh báo khi task fail — đã có, không phải TODO

`on_failure_callback: notify_failure` (Telegram) đã gắn cho cả 2 DAG — task hết retry gửi cảnh báo ngay lập tức; DAG batch hoàn tất gửi báo cáo thành công; DAG tin tức chỉ báo lỗi (tránh spam mỗi 5 phút).

## Hướng cải thiện còn mở

- Tách OHLCV full-market ingest thành nhiều task nhỏ theo batch ticker để song song hóa.
- Thêm task kiểm tra số lượng object/file sau mỗi bước.
