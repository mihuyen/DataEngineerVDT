# Data Lakehouse Stock

Project Data Lakehouse theo dõi thị trường chứng khoán Việt Nam, tập trung xây dựng nền tảng dữ liệu có thể mở rộng từ batch analytics đến realtime monitoring.

## Mục tiêu hệ thống

- Thu thập, lưu trữ và xử lý dữ liệu thị trường chứng khoán Việt Nam theo kiến trúc Lakehouse.
- Tách rõ Bronze, Silver, Gold để dễ kiểm soát chất lượng dữ liệu.
- Phục vụ dashboard phân tích thị trường, theo dõi pipeline và cảnh báo giao dịch.
- Chuẩn bị nền tảng để Ngày 2 setup Docker Compose cho MinIO, ClickHouse, Airflow, Kafka, Superset và Grafana.

## Vấn đề cần giải quyết

Dữ liệu chứng khoán đến từ nhiều nguồn, nhiều định dạng và có độ tin cậy khác nhau. Hệ thống cần lưu dữ liệu thô, làm sạch có kiểm soát, tổng hợp thành mô hình phân tích và cung cấp dashboard kịp thời cho người dùng.

## Kiến trúc tổng quan

- Bronze Layer: lưu dữ liệu thô trong MinIO dưới dạng Parquet hoặc JSON.
- Silver Layer: làm sạch, chuẩn hóa schema và kiểm tra chất lượng bằng Polars + Great Expectations.
- Gold Layer: tạo mô hình phân tích và chỉ báo kỹ thuật bằng dbt trên ClickHouse.
- Serving Layer: Superset dashboard, Grafana monitoring và Alert Engine.
- Orchestration: Airflow quản lý batch pipeline.
- Streaming: Kafka, ClickHouse Kafka Engine và Materialized View cho dữ liệu realtime/order book.

## 5 luồng dữ liệu chính

1. OHLCV cổ phiếu từ `vnstock`.
2. Thông tin doanh nghiệp niêm yết từ API niêm yết hoặc Finnhub.
3. Chỉ số thị trường như VN-Index, HNX-Index, VN30.
4. Tin tức thị trường từ Finnhub News, RSS hoặc HTML crawl.
5. Dữ liệu realtime/order book từ DNSE WebSocket API.

## Công nghệ sử dụng

- Python, uv
- MinIO, Apache Parquet
- Polars, Great Expectations
- ClickHouse, dbt
- Airflow
- Kafka
- Superset, Grafana
- PostgreSQL cho bảng `user_alerts`
- Telegram Bot API hoặc SMTP Email cho cảnh báo

## Cấu trúc thư mục

```text
data-lakehouse-stock/
├── README.md
├── docs/
├── configs/
├── src/
├── dags/
├── dbt/
├── sql/
├── docker/
├── tests/
└── scripts/
```

## Setup môi trường bằng uv

TODO Ngày 1: máy hiện tại cần có `uv` trong PATH để chạy các lệnh bên dưới.

```bash
uv sync
uv run python scripts/check_env.py
uv run pytest
uv run ruff check .
```

Không dùng `pip install` và không tạo `requirements.txt`.

## Roadmap 4 tuần

- Tuần 1: phân tích yêu cầu, setup project, chuẩn bị môi trường, ingest Bronze cho OHLCV, thông tin doanh nghiệp, chỉ số thị trường và thử nghiệm tin tức.
- Tuần 2: xây dựng Silver Layer bằng Polars, Great Expectations, làm sạch dữ liệu chính và tạo Airflow DAG.
- Tuần 3: xây dựng Gold Layer trong ClickHouse, dbt models, Star Schema, chỉ báo kỹ thuật, sentiment demo và realtime VWAP demo.
- Tuần 4: xây dựng Superset dashboard, Data Pipeline Monitor, Alert Engine, báo cáo và demo.

## TODO cho Ngày 2

- Cài hoặc đưa `uv` vào PATH nếu môi trường chưa có.
- Sinh `uv.lock` bằng `uv sync` sau khi dependency được resolve.
- Setup Docker Compose cho MinIO, ClickHouse, PostgreSQL, Kafka, Airflow, Superset và Grafana.
- Tạo bucket/path Bronze trong MinIO.
- Viết ingestion skeleton cho OHLCV batch đầu tiên.

## Ngày 2 - Docker Compose nền tảng

Ngày 2 bổ sung `docker-compose.yml` để chạy local các service nền tảng:

| Service | Port | Mục đích |
|---|---:|---|
| MinIO | `9000`, `9001` | Lưu Bronze/Silver data |
| ClickHouse | `8123`, `9002` | OLAP database cho Gold Layer |
| PostgreSQL | `5432` | Airflow metadata và cấu hình alert |
| Zookeeper | `2181` | Điều phối Kafka local |
| Kafka | `9092` | Streaming broker cho realtime/order book |
| Airflow Webserver | `8080` | UI orchestration |
| Airflow Scheduler | internal | Lập lịch DAG |
| Superset | `8088` | Dashboard phân tích |
| Grafana | `3000` | Monitoring |

### Setup bằng uv

```powershell
uv sync
uv run python scripts/check_env.py
uv run pytest
uv run ruff check .
```

### Start service bằng Docker Compose

```powershell
docker compose up -d
```

Nếu máy yếu, có thể start trước nhóm service nền tảng:

```powershell
docker compose up -d minio clickhouse postgres zookeeper kafka grafana
```

### Kiểm tra service

```powershell
uv run python scripts/check_services.py
```

### Kiểm tra cấu hình Docker Compose

```powershell
docker compose config
```

Chi tiết xem thêm tại `docs/docker_setup.md`.

## Bronze Layer

Bronze Layer lưu dữ liệu thô trong MinIO. Ngày 3 tập trung duy nhất vào dữ liệu OHLCV từ `vnstock`, ghi Parquet vào bucket `bronze`.

### OHLCV ingestion

Luồng xử lý:

```text
vnstock -> DataFrame -> Polars DataFrame -> Parquet -> MinIO Bronze
```

Module chính:

- `src/ingestion/vnstock_ohlcv.py`
- `src/common/minio_client.py`
- `scripts/init_minio.py`
- `scripts/run_ohlcv_ingest.py`

### MinIO bucket structure

```text
bronze/
└── ohlcv/
    └── ticker=<SYMBOL>/
        └── year=2026/
            └── month=06/
                └── day=10/
                    └── data.parquet
```

Partition theo ticker và ngày ingest.

### Cách chạy Bronze OHLCV

Start MinIO:

```powershell
docker compose up -d minio
```

Tạo bucket:

```powershell
uv run python scripts/init_minio.py
```

Chạy ingest thử mã `VCB` trong 30 ngày gần nhất:

```powershell
uv run python scripts/run_ohlcv_ingest.py
```

Mặc định script lấy danh sách mã thuộc `HOSE`, `HNX`, `UPCOM` từ `vnstock` và ingest từng mã vào Bronze. Có thể test nhanh trước:

```powershell
uv run python scripts/run_ohlcv_ingest.py --exchanges HOSE HNX UPCOM --limit 10
```

Hoặc chỉ chạy một nhóm mã cụ thể:

```powershell
uv run python scripts/run_ohlcv_ingest.py --tickers VCB ACB FPT
```

Chi tiết xem thêm tại `docs/bronze_layer.md`.

### Company profile Bronze ingestion

Company profile Bronze lấy thông tin tổng quan doanh nghiệp cho toàn bộ mã cổ phiếu thuộc `HOSE`, `HNX`, `UPCOM` từ `vnstock`.

Layout:

```text
bronze/
└── company_profile/
    └── dataset=listing/
        └── year=2026/
        └── month=06/
            └── day=14/
                └── data.parquet
```

Chạy nhanh danh mục doanh nghiệp toàn bộ universe:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode listing
```

Chạy profile chi tiết cho một vài mã:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode profile --tickers VCB ACB FPT
```

Chi tiết xem thêm tại `docs/company_profile_bronze.md`.

### Market index Bronze ingestion

Ngày 6 ingest dữ liệu chỉ số thị trường vào Bronze cho các mã:

- `VNINDEX`
- `VN30`
- `HNXINDEX`

Layout:

```text
bronze/
└── market_index/
    └── index_code=VNINDEX/
        └── year=2026/
            └── month=06/
                └── day=14/
                    └── data.parquet
```

Chạy ingest:

```powershell
uv run python scripts/run_market_index_ingest.py
```

Chi tiết xem thêm tại `docs/market_index_bronze.md`.

### Market news Bronze ingestion

Ngày 7 crawl tin tức thị trường từ 3 nguồn:

- VnExpress
- Vietstock
- CafeF

Raw fields:

- `url`
- `title`
- `published_at`
- `description`
- `content`
- `tags`
- `source`
- `category`
- `crawl_at`

Chạy ingest:

```powershell
uv run python scripts/run_news_ingest.py
```

Chi tiết xem thêm tại `docs/news_bronze.md`.

## Silver Layer

Silver Layer chuẩn hóa OHLCV từ Bronze bằng Polars, kiểm tra chất lượng dữ liệu và ghi Parquet sạch xuống bucket `silver`.

### Data Quality

Các rule chính:

- Cột bắt buộc: `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`.
- `date` và `close` không được null.
- Giá OHLC phải dương.
- `volume >= 0`.
- `high >= low`, `high >= open`, `high >= close`.
- `low <= open`, `low <= close`.
- `ticker + date` phải unique.

### Great Expectations

Project dùng dependency `great-expectations` cho hướng validation dài hạn. Module Ngày 4 đặt các expectation tại `src/quality/ohlcv_expectations.py` và sinh JSON report trong `quality_reports/`.

### Cách chạy Silver OHLCV

Chạy transform Bronze -> Silver:

```powershell
uv run python scripts/run_silver_transform.py
```

Chỉ chạy quality check:

```powershell
uv run python scripts/run_quality_check.py
```

Chi tiết xem thêm tại `docs/silver_layer.md`.

## Gold Layer

Gold Layer v1 dùng ClickHouse và mô hình Star Schema để phục vụ phân tích OLAP.

### ClickHouse

Service ClickHouse được cấu hình trong `docker-compose.yml`:

- HTTP port: `8123`
- Native port: `9002`
- Database mặc định: `stock_lakehouse`

### Star Schema

Dimension tables:

- `dim_date`
- `dim_stock`
- `dim_sector`
- `dim_index`

Fact tables:

- `fact_daily_price`
- `fact_market_index`
- `fact_news_sentiment_daily`
- `fact_realtime_vwap`

### Cách khởi tạo

```powershell
uv run python scripts/init_clickhouse.py
```

### Cách load dữ liệu

```powershell
uv run python scripts/load_gold.py
```

### Cách validate Gold

```powershell
uv run python scripts/validate_gold.py
```

Query mẫu:

```sql
SELECT *
FROM fact_daily_price
LIMIT 10;
```

Chi tiết xem thêm tại `docs/star_schema.md` và `docs/gold_layer.md`.

## Realtime DNSE WebSocket

Project có connector DNSE Market Data WebSocket thật để lấy trade tick và tính realtime VWAP.

Biến môi trường cần có:

```bash
export DNSE_API_KEY=...
export DNSE_API_SECRET=...
export DNSE_WS_SYMBOLS=ALL
```

Chạy ingest DNSE thật và lưu Bronze local:

```bash
uv run python scripts/run_dnse_realtime_ingest.py --symbols ALL --max-messages 100 --timeout-seconds 300
```

Chạy ingest DNSE thật và load `fact_realtime_vwap`:

```bash
uv run python scripts/run_dnse_realtime_ingest.py --symbols ALL --max-messages 100 --timeout-seconds 300 --load-vwap
```

Chi tiết xem thêm tại `docs/realtime_vwap_day21.md`.

## Alert Engine

Alert Engine tách cấu hình và lịch sử cảnh báo theo đúng kiến trúc trong `docs/architecture.md`:

- `user_alerts` (PostgreSQL): cấu hình cảnh báo của người dùng — `ticker`, `condition_type`, `threshold_value`, `channel`, `cooldown_minutes`, `is_active`.
- `fact_alert_event` (ClickHouse): lịch sử mọi lần điều kiện được kích hoạt, bao gồm cả lần bị bỏ qua do cooldown (`is_sent = 0`) để giữ đầy đủ audit trail.

Loại điều kiện hỗ trợ: `PRICE_ABOVE`, `PRICE_BELOW`, `RSI_ABOVE`, `RSI_BELOW`, `BB_BREAK`, `VWAP_DEVIATION`.

Module chính:

- `src/alert_engine/rules.py` — logic đánh giá điều kiện (pure function, không phụ thuộc DB).
- `src/alert_engine/engine.py` — đọc rule đang active, lấy dữ liệu mới nhất từ `fact_daily_price`/`fact_realtime_vwap`, kiểm tra cooldown qua `fact_alert_event`, ghi log.
- `src/alert_engine/notifier.py` — gửi Telegram (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`); nếu chưa cấu hình, cảnh báo vẫn được ghi log với `is_sent = 0`.

Khởi tạo bảng `user_alerts` và seed vài rule demo:

```bash
uv run python scripts/init_user_alerts.py
```

Chạy kiểm tra một lần:

```bash
uv run python scripts/run_alert_engine.py --run-once
```

Chạy liên tục mỗi 60 giây (đúng thiết kế Alert Checker):

```bash
uv run python scripts/run_alert_engine.py --interval-seconds 60
```

Service `alert-engine` trong `docker-compose.yml` đã đóng gói sẵn vòng lặp này (tự `init_user_alerts.py` rồi `run_alert_engine.py --interval-seconds ${ALERT_CHECK_INTERVAL_SECONDS:-60}`), chạy độc lập với lịch Airflow:

```bash
docker compose up -d alert-engine
docker logs -f stock-alert-engine
```

DAG `stock_lakehouse_daily` vẫn có task `init_user_alerts >> check_alerts` chạy sau `load_gold` mỗi lần pipeline daily chạy — đó là lớp batch dự phòng; `alert-engine` service mới là nơi cảnh báo chạy gần thời gian thực.

## Realtime VWAP qua Kafka Engine (streaming thật)

Ngoài luồng demo/DNSE-bronze trực tiếp, project có pipeline streaming thật: `Kafka topic -> ClickHouse Kafka Engine -> Materialized View -> bảng raw -> Python consumer tính VWAP đúng (cumulative session VWAP) -> fact_realtime_vwap`.

Khởi tạo các object ClickHouse (Kafka Engine table, bảng raw, Materialized View):

```bash
uv run python scripts/init_realtime_streaming.py
uv run python scripts/create_realtime_kafka_topic.py
```

Bơm tick demo vào Kafka thật (khi ngoài giờ giao dịch hoặc chưa có `DNSE_API_KEY`):

```bash
uv run python scripts/produce_demo_ticks_to_kafka.py --tickers VCB,FPT,HPG --minutes 10
```

Hoặc publish tick DNSE thật lên Kafka khi đang trong phiên:

```bash
uv run python scripts/run_dnse_realtime_ingest.py --symbols ALL --produce-to-kafka --timeout-seconds 300
```

Chạy consumer để tổng hợp tick thành VWAP (đã đóng gói sẵn trong service `realtime-vwap-consumer` của docker-compose, chạy liên tục mỗi 15s):

```bash
docker compose up -d realtime-vwap-consumer
# hoặc chạy tay:
uv run python scripts/run_realtime_vwap_kafka_consumer.py --interval-seconds 15
```

## Superset dashboard thật

```bash
docker compose up -d superset
uv run python scripts/setup_superset_day22.py
uv run python scripts/setup_superset_dashboard.py
```

Tạo dashboard "Stock Lakehouse Gold Overview" với 3 chart thật query trực tiếp ClickHouse Gold: VN-Index theo ngày, Top 10 mã theo thanh khoản, News sentiment trung bình theo ngày. Truy cập `http://localhost:8088` (admin/admin).

## Grafana monitoring thật

Khác với Superset (phân tích nghiệp vụ trên Gold), Grafana phục vụ đúng vai trò ban đầu trong `docs/architecture.md`: giám sát vận hành — pipeline, service health, Kafka lag và trạng thái alert.

```bash
docker compose up -d grafana
```

Service tự cài plugin `grafana-clickhouse-datasource` qua `GF_INSTALL_PLUGINS`, tự provision 2 datasource (ClickHouse Gold + Airflow Metadata trên Postgres) và 1 dashboard "Stock Lakehouse Ops Monitor" từ `docker/grafana/provisioning/` và `docker/grafana/dashboards/` — không cần bấm tay. Dashboard gồm 7 panel: số cảnh báo 24h, độ trễ Kafka trung bình (60 tick gần nhất), độ tuổi dữ liệu giá, tổng số sự kiện cảnh báo, độ tươi/số dòng từng bảng Gold, cảnh báo theo loại điều kiện, và lịch sử DAG run của Airflow (đọc trực tiếp từ Postgres metadata, không qua API). Truy cập `http://localhost:3000` (admin/admin).
