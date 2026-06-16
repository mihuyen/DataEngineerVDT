# Ngày 14 - Airflow DAG Bronze → Silver → Quality → Gold

Ngày cập nhật: 2026-06-14

## Mục tiêu

Ngày 14 cấu hình Airflow DAG để tự động hóa pipeline batch chính của project:

```text
Bronze ingest
    → Silver transform
    → Quality check
    → Gold schema migration
    → Gold load
```

## DAG chính

File:

```text
dags/stock_lakehouse_daily.py
```

DAG ID:

```text
stock_lakehouse_daily
```

Lịch chạy:

```text
18:00 từ thứ Hai đến thứ Sáu, timezone Asia/Ho_Chi_Minh
```

Airflow schedule:

```text
0 18 * * 1-5
```

## Task graph

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

## Quality gate

Task:

```text
quality_all
```

Script:

```text
scripts/run_all_quality_checks.py
```

Nếu một trong bốn quality check fail, task `quality_all` fail và Airflow không chạy `migrate_gold_schema` hoặc `load_gold`.

Các dataset được kiểm tra:

- OHLCV.
- Company profile.
- Market index.
- News.

## Môi trường Linux/Airflow

Project hiện đã được chuyển sang WSL/Linux tại:

```text
~/projects/DataEngineerVDT
```

Airflow container mount project vào:

```text
/opt/airflow/project
```

DAG đặt:

```text
UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock
```

Mục đích là để Airflow dùng virtualenv Linux riêng trong container, không dùng nhầm `.venv` Windows.

## Cách chạy Airflow

Từ Linux/WSL:

```bash
cd ~/projects/DataEngineerVDT
docker compose up -d --build
```

Mở UI:

```text
http://localhost:8080
```

Tài khoản local:

```text
admin / admin
```

## Bật DAG

```bash
docker exec stock-airflow-webserver airflow dags unpause stock_lakehouse_daily
```

Kiểm tra trạng thái:

```bash
docker exec stock-airflow-webserver airflow dags list | grep stock_lakehouse_daily
```

Kết quả mong muốn:

```text
stock_lakehouse_daily ... False
```

`False` ở cột `is_paused` nghĩa là DAG đang bật.

## Trigger thủ công

Chỉ nên trigger thủ công khi muốn chạy toàn pipeline thật:

```bash
docker exec stock-airflow-webserver airflow dags trigger stock_lakehouse_daily
```

Lưu ý: task `bronze_ohlcv` có thể chạy lâu và gọi `vnstock`, nên khi chỉ muốn kiểm tra hệ thống thì dùng script smoke check bên dưới.

## Smoke check Ngày 14

Script:

```text
scripts/airflow_day14_check.sh
```

Chạy:

```bash
cd ~/projects/DataEngineerVDT
bash scripts/airflow_day14_check.sh
```

Script kiểm tra:

- Airflow nhìn thấy DAG.
- DAG không có import error.
- Task graph có đủ Bronze, Silver, Quality, Gold.
- Container chạy được `uv run`.
- Quality checks pass trong chính Airflow container.

## Kết quả kiểm chứng hiện tại

Đã kiểm tra:

```text
Airflow DAG parse: OK
Airflow import errors: No data found
Task graph: OK
Quality checks inside Airflow container: PASSED
DAG is_paused: False
```

Quality checks trong Airflow container:

```text
OHLCV: 35.142 rows, error_count = 0
Company profile: 1.531 rows, error_count = 0
Market index: 92 rows, error_count = 0
News: 60 rows, error_count = 0
```

## Kết luận

Ngày 14 đã hoàn thành:

- Có DAG production đầu tiên.
- Có lịch chạy tự động theo giờ Việt Nam.
- Có Bronze ingest tasks.
- Có Silver transform tasks.
- Có `quality_all` làm quality gate.
- Có Gold migration/load tasks.
- Airflow đã chạy trong môi trường Linux/WSL.
- DAG đã được unpause và sẵn sàng chạy theo lịch.
