# Báo cáo hiện trạng project - Data Lakehouse chứng khoán Việt Nam

Ngày cập nhật: 2026-06-14

## 1. Tổng quan

Project đã xây dựng được nền tảng Data Lakehouse theo dõi thị trường chứng khoán Việt Nam với các lớp chính:

- Bronze Layer: lưu dữ liệu thô.
- Silver Layer: chuẩn hóa và kiểm tra chất lượng dữ liệu.
- Gold Layer: load dữ liệu phân tích vào ClickHouse.
- Orchestration: Airflow DAG tự động hóa pipeline.
- Local services: MinIO, ClickHouse, PostgreSQL, Kafka, Airflow, Superset, Grafana.

Project hiện đã chuyển sang chạy chính trong môi trường Linux/WSL:

```text
~/projects/DataEngineerVDT
```

Bản Windows cũ vẫn còn tại:

```text
D:\VDT\DataEngineerVDT
```

Từ thời điểm này nên ưu tiên thao tác trong Linux/WSL để tránh lỗi khác biệt `.venv` giữa Windows và Linux.

## 2. Môi trường hiện tại

### Python và package manager

- Dùng `uv`.
- Không dùng `pip` trực tiếp.
- Không dùng `requirements.txt`.
- Linux uv version: `uv 0.11.21`.
- Python trong WSL: Python 3.12.

### Docker services

Các service đã có trong `docker-compose.yml`:

- MinIO.
- ClickHouse.
- PostgreSQL.
- Zookeeper.
- Kafka.
- Airflow webserver.
- Airflow scheduler.
- Superset.
- Grafana.

Các container chính đang chạy được từ môi trường Linux/WSL.

## 3. Bronze Layer

### 3.1. OHLCV

Nguồn:

```text
vnstock
```

Module/script:

```text
src/ingestion/vnstock_ohlcv.py
scripts/run_ohlcv_ingest.py
```

Layout:

```text
data/bronze_local/ohlcv/ticker=<TICKER>/year=<YYYY>/month=<MM>/day=<DD>/data.parquet
```

Trạng thái:

- Listing có 1.531 mã.
- Bronze OHLCV có 1.529 mã.
- Hai mã chưa lấy được OHLCV ổn định: `EGL`, `UTT`.
- Project tạm xem universe OHLCV thực tế là 1.529 mã.

### 3.2. Company profile

Module/script:

```text
src/ingestion/company_profile.py
scripts/run_company_profile_ingest.py
```

Trạng thái:

- Bronze listing doanh nghiệp: 1.531 mã.
- Bronze profile chi tiết: 1.531 mã.
- Phân bổ listing:
  - HOSE: 403 mã.
  - HNX: 300 mã.
  - UPCOM: 828 mã.

### 3.3. Market index

Module/script:

```text
src/ingestion/market_index.py
scripts/run_market_index_ingest.py
```

Các chỉ số đã có:

- `VNINDEX`
- `VN30`
- `HNXINDEX`
- `UPCOMINDEX`

### 3.4. News

Module/script:

```text
src/ingestion/market_news.py
scripts/run_news_ingest.py
```

Nguồn crawl:

- VnExpress.
- Vietstock.
- CafeF.

Trạng thái:

- Bronze news đã có dữ liệu batch.
- Crawler hiện là batch crawler, chưa phải streaming/news scheduler production riêng.

## 4. Silver Layer

Silver Layer đã có dữ liệu sạch cho 4 nhóm chính.

### 4.1. Silver OHLCV

Module/script:

```text
src/transform/ohlcv_transform.py
scripts/run_silver_transform.py
```

Trạng thái:

```text
Silver OHLCV tickers: 1.529
Silver OHLCV rows: 35.142
```

### 4.2. Silver company profile

Module/script:

```text
src/transform/company_profile_transform.py
scripts/run_company_profile_silver.py
```

Trạng thái:

```text
Silver company profile rows: 1.531
```

Các trường chính đã chuẩn hóa:

- `ticker`
- `company_name`
- `company_name_en`
- `exchange`
- `sector_id`
- `sector_name`
- `shares_outstanding`
- `market_cap_latest`
- `business_model`
- `address`
- `website`

### 4.3. Silver market index

Module/script:

```text
src/transform/market_index_transform.py
scripts/run_market_index_silver.py
```

Trạng thái:

```text
Silver market index rows: 92
```

### 4.4. Silver news

Module/script:

```text
src/transform/news_transform.py
scripts/run_news_silver.py
```

Trạng thái:

```text
Silver news rows: 60
```

Đã xử lý:

- Loại bài trùng theo URL.
- Chuẩn hóa thời gian.
- Loại bài quá ngắn.
- Chuẩn hóa text cơ bản.

## 5. Data Quality

Đã có quality checks cho 4 pipeline chính.

### 5.1. Modules

```text
src/quality/ohlcv_expectations.py
src/quality/company_profile_expectations.py
src/quality/market_index_expectations.py
src/quality/news_expectations.py
```

### 5.2. Scripts

```text
scripts/run_quality_check.py
scripts/run_company_profile_quality_check.py
scripts/run_market_index_quality_check.py
scripts/run_news_quality_check.py
scripts/run_all_quality_checks.py
```

### 5.3. Reports

```text
quality_reports/ohlcv_silver_validation.json
quality_reports/company_profile_silver_validation.json
quality_reports/market_index_silver_validation.json
quality_reports/news_silver_validation.json
```

### 5.4. Kết quả hiện tại

```text
OHLCV: 35.142 rows, error_count = 0
Company profile: 1.531 rows, error_count = 0
Market index: 92 rows, error_count = 0
News: 60 rows, error_count = 0
```

Tất cả đều pass:

```text
passed: 4
failed: 0
```

Ghi chú:

- Project đã cài `great-expectations`.
- Các report có `gx_version`.
- Rule hiện chạy bằng Polars theo style expectation để nhẹ và phù hợp môi trường local.
- Chưa dùng persistent Great Expectations DataContext.

## 6. Gold Layer

Gold Layer đang load vào ClickHouse.

### 6.1. DDL

```text
sql/ddl/dim_date.sql
sql/ddl/dim_sector.sql
sql/ddl/dim_stock.sql
sql/ddl/dim_index.sql
sql/ddl/fact_daily_price.sql
sql/ddl/fact_market_index.sql
```

### 6.2. Loaders

```text
src/loaders/load_dimensions.py
src/loaders/load_fact_daily_price.py
src/loaders/load_fact_market_index.py
```

### 6.3. Scripts

```text
scripts/init_clickhouse.py
scripts/migrate_gold_schema.py
scripts/load_gold.py
scripts/validate_gold.py
```

### 6.4. ClickHouse row counts

```text
dim_date: 4.018
dim_sector: 5
dim_stock: 1.531
dim_index: 4
fact_daily_price: 35.142
fact_market_index: 92
```

### 6.5. Chỉ báo kỹ thuật đã có trong fact_daily_price

- `sma_20`
- `ema_12`
- `ema_26`
- `macd`
- `macd_signal`
- `rsi_14`
- `bb_upper`
- `bb_middle`
- `bb_lower`

Ghi chú:

- `dim_stock` dùng dữ liệu Silver company profile đủ 1.531 mã.
- `fact_daily_price` dùng universe OHLCV thực tế 1.529 mã.
- Gold schema đã được chỉnh lại theo scheme nghiệp vụ: `dim_stock` dùng khóa logic `ticker`, `fact_daily_price` dùng `ticker` và `trading_date`.

## 7. Airflow

### 7.1. DAG

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

Trạng thái hiện tại:

```text
is_paused: False
import errors: No data found
```

### 7.2. Task graph

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

### 7.3. Quality gate

Task:

```text
quality_all
```

Script:

```text
scripts/run_all_quality_checks.py
```

Nếu một quality check fail, Gold sẽ không được load.

### 7.4. Airflow Linux runtime

Airflow container dùng:

```text
UV_PROJECT_ENVIRONMENT=/opt/airflow/.venv-stock
```

Mục đích:

- Dùng virtualenv Linux riêng trong container.
- Tránh dùng nhầm `.venv` Windows.

### 7.5. Smoke check

Script:

```text
scripts/airflow_day14_check.sh
```

Kết quả đã kiểm chứng:

```text
Airflow DAG parse: OK
Airflow import errors: No data found
Task graph: OK
Quality checks inside Airflow container: PASSED
DAG is_paused: False
```

## 8. Tài liệu đã có

Các tài liệu chính:

```text
docs/requirements.md
docs/architecture.md
docs/data_sources.md
docs/timeline.md
docs/dashboard_plan.md
docs/bronze_layer.md
docs/company_profile_bronze.md
docs/market_index_bronze.md
docs/news_bronze.md
docs/silver_layer.md
docs/gold_layer.md
docs/star_schema.md
docs/docker_setup.md
docs/airflow_orchestration.md
docs/airflow_day14.md
docs/data_quality_day13.md
docs/ohlcv_quality_day9.md
docs/company_profile_silver_day10.md
docs/market_index_silver_day11.md
docs/news_silver_day12.md
```

## 9. Kiểm thử

Kết quả kiểm thử trong Linux/WSL:

```text
uv run pytest
86 passed
```

Lint:

```text
uv run ruff check .
All checks passed
```

Docker Compose config:

```text
docker compose config --quiet
passed
```

## 10. Các mốc đã hoàn thành

### Ngày 1

- Khởi tạo project.
- Tạo cấu trúc thư mục.
- Tạo tài liệu nền tảng.
- Thiết lập `uv`.

### Ngày 2

- Thiết lập Docker Compose.
- Có MinIO, ClickHouse, PostgreSQL, Kafka, Airflow, Superset, Grafana.

### Ngày 3

- Bronze OHLCV ingestion.
- MinIO helper.
- Script init bucket.

### Ngày 4

- Silver OHLCV và quality rule ban đầu.

### Ngày 5

- Gold Layer v1 trong ClickHouse.
- Star schema cơ bản.

### Ngày 6

- Bronze market index.
- Có `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX`.

### Ngày 7

- Bronze news crawl từ VnExpress, Vietstock, CafeF.

### Ngày 8

- Bronze → Silver OHLCV cho toàn bộ universe thực tế.

### Ngày 9

- Quality check OHLCV trên 35.142 dòng, pass.

### Ngày 10

- Silver company profile cho 1.531 mã.
- `dim_stock` và `dim_sector` dùng dữ liệu doanh nghiệp thật.

### Ngày 11

- Silver market index.
- Quality check market index pass.

### Ngày 12

- Silver news.
- Quality check news pass.

### Ngày 13

- Quality checks cho 4 pipeline chính.
- Script tổng hợp `run_all_quality_checks.py`.
- Quality gate trong Airflow.

### Ngày 14

- Airflow DAG Bronze → Silver → Quality → Gold.
- Chạy trong Linux/WSL.
- DAG đã bật và không có import error.

## 11. Những việc còn lại

### 11.1. dbt

Hiện Gold đang load bằng Python/SQL script. Chưa có dbt project hoàn chỉnh.

Cần làm:

- dbt source models.
- dbt staging models.
- dbt marts/fact/dim models.
- dbt tests.
- dbt docs/lineage.

### 11.2. Dashboard

Superset và Grafana đã có service, nhưng dashboard thực tế chưa hoàn thiện.

Cần làm:

- Market Overview.
- Stock Detail.
- Technical Signal Scanner.
- Data Pipeline Monitor.
- News & Sentiment.
- Alert History.

### 11.3. News sentiment

News đã có Bronze/Silver, nhưng chưa có:

- Entity linking ticker với bài viết.
- Sentiment scoring.
- `fact_news_sentiment_daily`.

### 11.4. Streaming realtime

Kafka đã có service, nhưng chưa hoàn thiện:

- DNSE WebSocket ingest.
- Kafka topic realtime.
- ClickHouse Kafka Engine.
- Materialized View.
- `fact_realtime_vwap`.

### 11.5. Alert Engine

Chưa hoàn thiện:

- Bảng user alert.
- Alert checker.
- Cooldown.
- Telegram/email notification.
- `fact_alert_event`.

### 11.6. Monitoring nâng cao

Hiện có Airflow logs và quality reports, nhưng chưa có dashboard monitoring đầy đủ.

Cần làm:

- Data Pipeline Monitor.
- Kafka lag monitor.
- Service health monitor.
- Alert khi task fail.

## 12. Kết luận

Project hiện đã có nền tảng Data Lakehouse chạy được end-to-end ở mức batch:

```text
Bronze → Silver → Quality → Gold
```

Dữ liệu chính đã có:

- OHLCV: 1.529 mã, 35.142 dòng Silver.
- Company profile: 1.531 mã.
- Market index: 92 dòng.
- News: 60 bài.

Airflow đã tự động hóa pipeline và có quality gate trước Gold. Môi trường chính đã chuyển sang Linux/WSL, test và lint đều pass. Các phần còn lại tập trung vào dbt, dashboard, sentiment, realtime streaming và alert.
