# Tiến độ thực hiện theo ngày

## Ngày 1 - Khởi tạo nền tảng project

### Việc đã hoàn thành

- Kiểm tra workspace hiện tại trước khi tạo file.
- Khởi tạo cấu trúc project Data Lakehouse trong thư mục `D:\VDT\DataEngineerVDT`.
- Tạo tài liệu tổng quan project trong `README.md`.
- Tạo bộ tài liệu kỹ thuật ban đầu trong thư mục `docs/`:
  - `docs/requirements.md`
  - `docs/architecture.md`
  - `docs/data_sources.md`
  - `docs/timeline.md`
  - `docs/dashboard_plan.md`
- Tạo cấu hình mẫu trong thư mục `configs/`:
  - `configs/.env.example`
  - `configs/sources.yaml`
- Tạo cấu trúc source code rỗng để chuẩn bị cho các ngày tiếp theo:
  - `src/ingestion/`
  - `src/transform/`
  - `src/quality/`
  - `src/alert_engine/`
  - `src/common/`
- Tạo các thư mục nền tảng cho orchestration, dbt, SQL, Docker, test và script:
  - `dags/`
  - `dbt/`
  - `sql/ddl/`
  - `sql/queries/`
  - `docker/`
  - `tests/`
  - `scripts/`
- Thêm `.gitkeep` cho các thư mục rỗng cần được Git theo dõi.
- Tạo `pyproject.toml` với dependency nền tảng cho project:
  - `polars`
  - `pyarrow`
  - `pandas`
  - `requests`
  - `python-dotenv`
  - `pydantic`
  - `pyyaml`
  - dev dependencies: `pytest`, `ruff`, `black`
- Tạo `scripts/check_env.py` để kiểm tra Python version và trạng thái biến môi trường mà không in secret.
- Tạo `tests/test_project_structure.py` để kiểm tra các thư mục/file chính của project.
- Kiểm tra được `uv` đã cài tại `C:\Users\DELL\.local\bin\uv.exe`.
- Cấu hình PATH/phiên PowerShell đã nhận diện được lệnh `uv` trực tiếp.
- Tạo được `uv.lock`.
- Tạo được `.venv`.
- Chạy kiểm thử project bằng `uv run pytest`.
- Chạy kiểm tra lint bằng `uv run ruff check .`.

### Việc đã kiểm tra

- `uv` đã được cài và gọi được trực tiếp trong PowerShell:

```powershell
uv --version
```

- Kết quả version đã thấy:

```text
uv 0.11.19
```

- `uv run pytest` đã chạy thành công:

```text
3 passed
```

- `uv run ruff check .` đã chạy thành công:

```text
All checks passed!
```

### Việc chưa hoàn tất hoặc cần xác nhận

- Chưa setup Docker Compose.
- Chưa ingest dữ liệu thật.
- Chưa kết nối MinIO, ClickHouse, Kafka, Airflow, Superset hoặc Grafana.

### Lệnh kiểm tra đã dùng

```powershell
uv sync
uv run python scripts/check_env.py
uv run pytest
uv run ruff check .
```

### Ghi chú quan trọng

- Chưa gọi API thật.
- Chưa ingest dữ liệu thật.
- Chưa hardcode API key hoặc secret.
- Chưa setup Docker Compose.
- Chưa tạo `requirements.txt`.
- Không dùng `pip install` trong tài liệu hoặc quy trình project.

## Ngày 2 - Việc tiếp theo đề xuất

- Setup Docker Compose cho các service nền tảng:
  - MinIO
  - ClickHouse
  - PostgreSQL
  - Kafka
  - Airflow
  - Superset
  - Grafana
- Tạo bucket/path Bronze trong MinIO.
- Bắt đầu skeleton ingestion Bronze cho OHLCV từ `vnstock`.

## Ngày 2 - Setup Docker Compose nền tảng

### Việc đã hoàn thành

- Kiểm tra baseline project bằng `uv --version`, `uv sync`, `uv run pytest`, `uv run ruff check .`.
- Tạo `docker-compose.yml` cho các service nền tảng:
  - `minio`
  - `clickhouse`
  - `postgres`
  - `zookeeper`
  - `kafka`
  - `airflow-webserver`
  - `airflow-scheduler`
  - `superset`
  - `grafana`
- Cập nhật `configs/.env.example` với biến môi trường phục vụ Docker Compose local.
- Tạo `scripts/check_services.py` để kiểm tra port local của các service mà không gọi API thật.
- Tạo `docs/docker_setup.md` hướng dẫn chạy, xem log, dừng và reset Docker Compose.
- Cập nhật `README.md` với hướng dẫn Ngày 2.
- Tạo `tests/test_docker_setup.py` để kiểm tra file Docker và danh sách service trong Compose.
- Cập nhật `scripts/check_env.py` để liệt kê thêm các biến môi trường phục vụ Docker Compose.
- Chạy `docker compose config` thành công để validate `docker-compose.yml`.
- Chạy `uv run pytest` thành công với 5 test pass.
- Chạy `uv run ruff check .` thành công.

### Ghi chú

- Chưa ingest dữ liệu thật.
- Chưa gọi API thật.
- Chưa hardcode secret thật.
- Chưa start container Docker; mới validate cấu hình bằng `docker compose config`.
- Airflow và Superset đang ở cấu hình local-minimal; khi triển khai nghiêm túc cần tách database/secret và hardening thêm.

### Việc tiếp theo cho Ngày 3

- Start từng nhóm service và kiểm tra health thực tế.
- Tạo bucket Bronze/Silver trong MinIO.
- Tạo DDL ban đầu cho ClickHouse.
- Tạo Kafka topic chính thức cho `raw_trades` hoặc `raw_order_book`.
- Bắt đầu ingestion skeleton cho OHLCV batch.

## Ngày 3 - Bronze OHLCV ingestion

### Việc đã hoàn thành

- Thêm dependency bằng `uv add`:
  - `vnstock`
  - `minio`
- Cập nhật `configs/sources.yaml` cho source `vnstock_ohlcv` với bucket/path Bronze.
- Tạo helper MinIO tại `src/common/minio_client.py`.
- Tạo module ingest OHLCV tại `src/ingestion/vnstock_ohlcv.py`.
- Tạo script bootstrap bucket tại `scripts/init_minio.py`.
- Tạo script ingest thử tại `scripts/run_ohlcv_ingest.py`.
- Tạo tài liệu Bronze tại `docs/bronze_layer.md`.
- Cập nhật `README.md` với phần Bronze Layer và cách chạy OHLCV ingest.
- Tạo test không gọi API thật:
  - `tests/test_minio_client.py`
  - `tests/test_vnstock_ingestion.py`

### Cấu trúc Bronze chuẩn

```text
bronze/
└── ohlcv/
    └── ticker=VCB/
        └── year=2026/
            └── month=06/
                └── day=10/
                    └── data.parquet
```

### Ghi chú

- Không làm Silver Layer.
- Không làm ClickHouse.
- Không làm Kafka.
- Không làm dashboard.
- Không làm dbt.
- Test không gọi API thật và không kết nối MinIO thật.

### Việc tiếp theo cho Ngày 4

- Xây dựng Silver Layer đọc Parquet từ Bronze.
- Chuẩn hóa schema OHLCV.
- Thêm Great Expectations cho OHLCV.
- Tạo test chất lượng dữ liệu cơ bản: null, duplicate, giá âm, volume âm, `high < low`.

## Ngày 4 - Silver OHLCV và Data Quality

### Việc đã hoàn thành

- Thêm dependency bằng `uv add`:
  - `great-expectations`
- Tạo transform module tại `src/transform/ohlcv_transform.py`.
- Tạo quality module tại `src/quality/ohlcv_expectations.py`.
- Tạo script chạy Silver transform:
  - `scripts/run_silver_transform.py`
- Tạo script chạy quality-only:
  - `scripts/run_quality_check.py`
- Tạo dữ liệu mẫu:
  - `tests/data/sample_ohlcv.parquet`
- Tạo test Silver transform:
  - `tests/test_ohlcv_transform.py`
- Tạo test quality expectations:
  - `tests/test_ohlcv_quality.py`
- Tạo tài liệu:
  - `docs/silver_layer.md`
- Cập nhật `README.md` với Silver Layer và Data Quality.

### Cấu trúc Silver chuẩn

```text
silver/
└── ohlcv/
    └── ticker=VCB/
        └── year=2026/
            └── month=06/
                └── data.parquet
```

### Quality rules

- Required columns: `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`.
- Null check: `date`, `close`.
- Range check: OHLC dương, `volume >= 0`.
- Consistency check: `high >= low`, `high >= open`, `high >= close`, `low <= open`, `low <= close`.
- Duplicate check: `ticker + date` unique.

### Việc tiếp theo cho Ngày 5

- Thiết kế Gold Layer schema cho OHLCV.
- Chuẩn bị ClickHouse DDL cho dimension/fact.
- Bắt đầu dbt project hoặc SQL model nền tảng.

## Ngày 5 - Gold Layer v1 trong ClickHouse

### Việc đã hoàn thành

- Thêm dependency `clickhouse-connect`.
- Tạo tài liệu Star Schema:
  - `docs/star_schema.md`
  - `docs/gold_layer.md`
- Tạo DDL ClickHouse:
  - `sql/ddl/dim_date.sql`
  - `sql/ddl/dim_sector.sql`
  - `sql/ddl/dim_stock.sql`
  - `sql/ddl/dim_index.sql`
  - `sql/ddl/fact_daily_price.sql`
  - `sql/ddl/fact_market_index.sql`
- Tạo ClickHouse helper:
  - `src/common/clickhouse_client.py`
- Tạo loaders:
  - `src/loaders/load_dimensions.py`
  - `src/loaders/load_fact_daily_price.py`
  - `src/loaders/load_fact_market_index.py`
- Tạo scripts:
  - `scripts/init_clickhouse.py`
  - `scripts/load_gold.py`
  - `scripts/validate_gold.py`
- Tạo tests:
  - `tests/test_clickhouse_schema.py`
  - `tests/test_gold_loader.py`
- Start được `minio` và `clickhouse`.
- Chạy ingest OHLCV thật cho `VCB`.
- Chạy Silver transform tạo 25 dòng dữ liệu sạch.
- Chạy `scripts/init_clickhouse.py` thành công.
- Chạy `scripts/load_gold.py` thành công.
- Chạy `scripts/validate_gold.py` thành công với query:

```sql
SELECT *
FROM fact_daily_price
LIMIT 10;
```

### Bảng Gold v1

- `dim_date`
- `dim_sector`
- `dim_stock`
- `dim_index`
- `fact_daily_price`
- `fact_market_index`

### Row counts thực tế sau khi load

| Bảng | Số dòng |
|---|---:|
| `dim_date` | 4018 |
| `dim_sector` | 1 |
| `dim_stock` | 1 |
| `dim_index` | 3 |
| `fact_daily_price` | 25 |
| `fact_market_index` | 25 |

### Ghi chú

- Không làm Dashboard.
- Không làm Kafka.
- Không làm Streaming.
- Không làm Superset.
- Không làm Alert Engine.
- Không làm News Sentiment.

### Việc tiếp theo cho Ngày 6

- Chạy thử với ClickHouse container thật nếu service đã sẵn sàng.
- Bổ sung dữ liệu doanh nghiệp để `dim_stock` giàu thông tin hơn.
- Chuẩn bị dbt project hoặc SQL model version tiếp theo.

## Ngày 6 - Bronze Market Index ingestion

### Việc đã hoàn thành

- Cập nhật `configs/sources.yaml` cho source `market_index`.
- Tạo module ingest chỉ số thị trường:
  - `src/ingestion/market_index.py`
- Tạo script chạy ingest:
  - `scripts/run_market_index_ingest.py`
- Tạo tài liệu:
  - `docs/market_index_bronze.md`
- Tạo test không gọi API thật:
  - `tests/test_market_index_ingestion.py`
- Chạy live ingest thử:
  - `VNINDEX`: thành công, đã ghi Bronze parquet.
  - `VN30`: provider hiện trả lỗi, script ghi nhận `FAILED`.
  - `HNXINDEX`: provider hiện trả lỗi, script ghi nhận `FAILED`.

### Chỉ số mặc định

- `VNINDEX`
- `VN30`
- `HNXINDEX`

### Cấu trúc Bronze

```text
bronze/
└── market_index/
    └── index_code=VNINDEX/
        └── year=2026/
            └── month=06/
                └── day=14/
                    └── data.parquet
```

### Ghi chú

- Chỉ làm Bronze raw ingest.
- Không làm Silver cho market index trong Ngày 6.
- Không làm Gold/ClickHouse mới trong Ngày 6.
- Không làm Kafka, dashboard, Airflow DAG hoặc Alert Engine.
- Source `vnstock` qua MSN hiện chỉ ingest thành công `VNINDEX` với provider symbol `VNI`; `VN30` và `HNXINDEX` cần xác minh provider symbol hoặc bổ sung nguồn khác.

### Việc tiếp theo cho Ngày 7

- Ingest thử dữ liệu tin tức từ Finnhub News hoặc RSS/HTML crawl vào Bronze.
- Lưu raw fields: `title`, `content`, `url`, `published_at`, `source`.

## Ngày 7 - Bronze Market News ingestion

### Việc đã hoàn thành

- Cập nhật `configs/sources.yaml` cho source `market_news`.
- Tạo crawler tin tức 3 nguồn:
  - `VnExpress`
  - `Vietstock`
  - `CafeF`
- Tạo module:
  - `src/ingestion/market_news.py`
- Tạo script chạy ingest:
  - `scripts/run_news_ingest.py`
- Tạo tài liệu:
  - `docs/news_bronze.md`
- Tạo test không gọi website thật:
  - `tests/test_market_news_ingestion.py`
- Chạy live crawl thành công và ghi Bronze:
  - Tổng số bài: 60
  - `VnExpress`: 20 bài
  - `Vietstock`: 20 bài
  - `CafeF`: 20 bài
  - File local: `data/bronze_local/news/source=multi/year=2026/month=06/day=14/data.parquet`

### Cấu trúc Bronze

```text
bronze/
└── news/
    └── source=multi/
        └── year=2026/
            └── month=06/
                └── day=14/
                    └── data.parquet
```

### Ghi chú

- Không dùng Kafka/Redis/scheduler trong project Ngày 7.
- Không làm Silver cho news.
- Không làm sentiment, entity linking, Gold hoặc dashboard.

### Việc tiếp theo

- Ngày tiếp theo: làm Silver cho OHLCV hoặc tiếp tục theo timeline mới nếu bạn cung cấp yêu cầu cụ thể.

## Ngày 8 - Bronze to Silver OHLCV bằng Polars

### Việc đã hoàn thành

- Rà soát lại pipeline Silver OHLCV đã xây trước đó:
  - `src/transform/ohlcv_transform.py`
  - `src/quality/ohlcv_expectations.py`
  - `scripts/run_silver_transform.py`
- Chạy Bronze -> Silver thực tế cho mã `VCB`.
- Đọc Bronze local:
  - `data/bronze_local/ohlcv/ticker=VCB/year=2026/month=06/day=10/data.parquet`
- Ghi Silver local:
  - `data/silver_local/ohlcv/ticker=VCB/year=2026/month=06/data.parquet`
- Upload Silver parquet lên bucket `silver` trong MinIO.
- Sinh quality report:
  - `quality_reports/2026-06-14_validation.json`

### Kết quả transform

- Ticker: `VCB`
- Số dòng Silver: 25
- Quality status: pass
- Error count: 0

### Schema Silver OHLCV

- `date`: Date
- `open`: Float64
- `high`: Float64
- `low`: Float64
- `close`: Float64
- `volume`: Int64
- `ticker`: String
- `ingested_at`: Datetime UTC
- `processed_at`: Datetime UTC
- `source_name`: String

### Quality rules đã pass

- Required columns tồn tại.
- `date` không null.
- `close` không null.
- `open`, `high`, `low`, `close` > 0.
- `volume >= 0`.
- `high >= low`.
- `high >= open`.
- `high >= close`.
- `low <= open`.
- `low <= close`.
- `ticker + date` unique.

### Ghi chú

- Ngày 8 chỉ làm OHLCV Bronze -> Silver.
- Không làm Silver cho doanh nghiệp, market index, news trong mốc này.
- Không làm Gold/ClickHouse mới.
- Không làm dashboard, Kafka, Airflow DAG hoặc Alert Engine.

## Ngày 15 - Gold Dimensions trong ClickHouse

### Việc đã hoàn thành

- Rà soát lại DDL và loader Gold hiện có cho các bảng dimension:
  - `sql/ddl/dim_date.sql`
  - `sql/ddl/dim_sector.sql`
  - `sql/ddl/dim_stock.sql`
  - `sql/ddl/dim_index.sql`
  - `src/loaders/load_dimensions.py`
- Tạo script chạy riêng cho Ngày 15:
  - `scripts/load_dimensions.py`
- Script `scripts/load_dimensions.py` thực hiện:
  - Tạo database ClickHouse nếu chưa có.
  - Tạo 4 bảng dimension nếu chưa có.
  - Load `dim_date` bằng calendar generated từ Polars.
  - Load `dim_sector` từ Silver company profile.
  - Load `dim_stock` từ Silver company profile, có fallback từ Silver OHLCV tickers.
  - Load `dim_index` với `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX`.
  - In row count sau khi load.
- Tạo tài liệu thiết kế Ngày 15:
  - `docs/gold_dimensions_day15.md`
- Cập nhật tài liệu Gold:
  - `docs/gold_layer.md`
  - `docs/star_schema.md`
- Tạo test bảo vệ thiết kế dimension:
  - `tests/test_day15_dimensions.py`

### Kết quả load thực tế trong ClickHouse

```text
table_name,row_count
dim_date,4018
dim_index,4
dim_sector,5
dim_stock,1531
```

### Cấu trúc dimension đã có

```text
dim_sector 1 --- n dim_stock
dim_stock  1 --- n fact_daily_price
dim_date   1 --- n fact_daily_price
dim_date   1 --- n fact_market_index
dim_index  1 --- n fact_market_index
```

### Lệnh đã chạy

```bash
uv run python scripts/load_dimensions.py
uv run pytest
uv run ruff check .
```

### Kết quả kiểm tra

```text
91 passed, 1 warning
All checks passed!
```

### Ghi chú

- Ngày 15 chỉ tập trung vào dimension.
- Chưa làm thêm fact mới trong mốc này.
- Chưa làm dbt trong mốc này.
- Chưa làm realtime trong mốc này.

### Việc tiếp theo cho Ngày 16

- Tập trung vào `fact_daily_price`.
- Rà soát `MergeTree`, `PARTITION BY toYYYYMM(trading_date)`, `ORDER BY (ticker, trading_date)`.
- Chuẩn hóa grain: 1 dòng cho 1 mã cổ phiếu trong 1 ngày giao dịch.
- Đảm bảo load từ Silver OHLCV vào ClickHouse ổn định.

## Ngày 16 - Gold fact_daily_price trong ClickHouse

### Việc đã hoàn thành

- Chuẩn hóa DDL `fact_daily_price` theo scheme của project:
  - `ticker`
  - `date_id`
  - `trading_date`
  - OHLCV
  - `value`
  - `shares_outstanding`
  - `market_cap`
  - `price_change`
  - `pct_change`
  - nhóm chỉ báo kỹ thuật
  - nhóm flag tín hiệu
  - `created_at`, `updated_at`
- Cấu hình ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (ticker, trading_date)
```

- Cập nhật loader:
  - `src/loaders/load_fact_daily_price.py`
- Loader đọc:
  - Silver OHLCV.
  - Silver company profile để lấy `shares_outstanding`.
- Recreate Gold schema và load lại dữ liệu vào ClickHouse.
- Tạo tài liệu:
  - `docs/fact_daily_price_day16.md`
- Tạo test:
  - `tests/test_fact_daily_price_day16.py`

### Kết quả load thực tế

```text
fact_daily_price: 35.142 dòng
```

### Lệnh đã chạy

```bash
uv run python scripts/migrate_gold_schema.py
uv run python scripts/load_gold.py
uv run python scripts/validate_gold.py
uv run pytest tests/test_fact_daily_price_day16.py tests/test_clickhouse_schema.py tests/test_gold_loader.py
uv run ruff check .
```

### Trạng thái

Ngày 16 đã hoàn thành.

### Việc tiếp theo cho Ngày 17

- Tạo dbt project/models hoặc chuẩn hóa lớp model cho các chỉ báo kỹ thuật.
- Đưa logic tính `sma_20`, `ema_12`, `ema_26`, `macd`, `rsi_14`, Bollinger Band và `market_cap` vào hướng dbt theo timeline.

## Ngày 17 - dbt models cho chỉ báo kỹ thuật

### Việc đã hoàn thành

- Thêm dependency bằng `uv`:
  - `dbt-core`
  - `dbt-clickhouse`
- Tạo dbt project trong thư mục `dbt/`:
  - `dbt/dbt_project.yml`
  - `dbt/profiles.yml`
  - `dbt/models/sources.yml`
  - `dbt/models/staging/stg_fact_daily_price.sql`
  - `dbt/models/marts/fact_daily_price_indicators.sql`
  - `dbt/models/marts/schema.yml`
  - `dbt/tests/*.sql`
- Tạo model staging đọc từ ClickHouse `fact_daily_price`.
- Tạo model marts `fact_daily_price_indicators` cho:
  - `sma_20`
  - `ema_12`
  - `ema_26`
  - `macd`
  - `macd_signal`
  - `rsi_14`
  - `bb_upper`
  - `bb_middle`
  - `bb_lower`
  - `volume_sma_20`
  - `market_cap`
  - signal flags
- Tạo dbt tests:
  - Không trùng `ticker + trading_date`.
  - `market_cap = close * shares_outstanding`.
  - `macd = ema_12 - ema_26`.
  - `not_null` cho các cột chính.
- Tạo tài liệu:
  - `docs/dbt_day17.md`
  - `dbt/README.md`
- Tạo test Python bảo vệ cấu trúc dbt:
  - `tests/test_dbt_day17.py`

### Lệnh đã chạy

```bash
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

### Kết quả dbt

```text
dbt debug: All checks passed
dbt run: PASS=2
dbt test: PASS=7
```

### Ghi chú

- dbt model hiện materialized dạng `view`.
- EMA chính xác dạng recursive vẫn kế thừa từ Gold Python loader vì ClickHouse SQL không có recursive EMA window đơn giản.
- SMA, RSI, Bollinger Band, `market_cap`, MACD và flags đã có trong dbt model.

### Trạng thái

Ngày 17 đã hoàn thành ở mức dbt project, dbt models và dbt tests cơ bản.

### Việc tiếp theo cho Ngày 18

- Hoàn thiện `fact_market_index`.
- Bổ sung breadth metrics chuẩn hơn: `advance_count`, `decline_count`, `unchanged_count`, `advance_decline_ratio`.
- Đảm bảo VNINDEX, VN30, HNXINDEX, UPCOMINDEX có dữ liệu Gold phục vụ Market Overview.

## Ngày 18 - Gold fact_market_index

### Việc đã hoàn thành

- Hoàn thiện loader:
  - `src/loaders/load_fact_market_index.py`
- Cập nhật `scripts/load_gold.py` để truyền Silver OHLCV và Silver company profile vào loader market index.
- Tạo breadth metrics từ dữ liệu cổ phiếu:
  - `advance_count`
  - `decline_count`
  - `unchanged_count`
  - `advance_decline_ratio`
- Mapping breadth theo sàn:
  - `HOSE -> VNINDEX`
  - `HNX -> HNXINDEX`
  - `UPCOM -> UPCOMINDEX`
- Tạo demo breadth cho `VN30` bằng top 30 mã HOSE theo `shares_outstanding`.
- Tính thêm:
  - `point_change`
  - `pct_change`
  - `sma_20`
  - `rsi_14`
- Tạo tài liệu:
  - `docs/fact_market_index_day18.md`
- Tạo test:
  - `tests/test_fact_market_index_day18.py`

### Kết quả load thực tế

```text
fact_market_index: 92 dòng
```

Tổng breadth sau khi load:

```text
HNXINDEX    rows=23  advances=1440  declines=1314  unchanged=1985
UPCOMINDEX  rows=23  advances=1969  declines=2148  unchanged=4484
VN30        rows=23  advances=281   declines=355   unchanged=52
VNINDEX     rows=23  advances=3149  declines=3896  unchanged=1479
```

### Lệnh đã chạy

```bash
uv run python scripts/migrate_gold_schema.py
uv run python scripts/load_gold.py
uv run python scripts/validate_gold.py
uv run pytest tests/test_fact_market_index_day18.py tests/test_gold_loader.py
uv run ruff check .
```

### Trạng thái

Ngày 18 đã hoàn thành ở mức Gold batch table và breadth demo.

### Ghi chú

- `VN30` hiện dùng demo rule top 30 HOSE theo `shares_outstanding` vì project chưa có danh sách constituents chính thức.
- TODO sau này: thay demo rule bằng danh sách VN30 chính thức.

### Việc tiếp theo cho Ngày 19

- Xử lý entity linking cho tin tức.
- Gán bài viết với ticker bằng từ điển ticker/tên công ty và regex.

## Ngày 19 - Entity linking cho tin tức

### Việc đã hoàn thành

- Tạo module:
  - `src/transform/news_entity_linking.py`
- Tạo script:
  - `scripts/run_news_entity_linking.py`
- Tạo script crawl lặp:
  - `scripts/run_news_crawl_loop.py`
- Cập nhật news ingest để append và dedupe theo `url` khi crawl nhiều lần trong cùng ngày.
- Cập nhật `scripts/run_news_ingest.py` hỗ trợ `--no-upload`.
- Tạo tài liệu:
  - `docs/news_entity_linking_day19.md`
- Tạo test:
  - `tests/test_news_entity_linking_day19.py`

### Logic entity linking

- Tạo dictionary từ Silver company profile:
  - `ticker`
  - `company_name`
  - `company_name_en`
  - alias rút gọn từ tên công ty
- Match vào bài báo qua:
  - `title`
  - `description`
  - `content`
  - `tags`
- Ticker match bằng regex phân biệt chữ hoa/thường để tránh match nhầm các từ thường như `thu`, `tin`, `usd`.
- Company alias match không phân biệt hoa thường, nhưng loại alias quá ngắn hoặc quá chung.

### Kết quả chạy thực tế

Input:

```text
Silver news: 60 bài
```

Output:

```text
linked_row_count: 221
linked_article_count: 57
linked_ticker_count: 104
```

File output:

```text
data/gold_local/news_entity_links/year=2026/month=06/data.parquet
```

### Crawl tin tức 5 phút/lần

Chạy đầy đủ Bronze -> Silver -> Entity linking mỗi 5 phút:

```bash
uv run python scripts/run_news_crawl_loop.py --interval-seconds 300
```

Nếu chỉ ghi local, không upload MinIO:

```bash
uv run python scripts/run_news_crawl_loop.py --interval-seconds 300 --no-upload
```

Test một vòng:

```bash
uv run python scripts/run_news_crawl_loop.py --run-once --no-upload
```

### Trạng thái

Ngày 19 đã hoàn thành ở mức rule-based entity linking và crawl loop 5 phút/lần.

### Việc tiếp theo cho Ngày 20

- Tính sentiment demo.
- Tổng hợp `news_count`, `source_count`, `avg_sentiment_score`, `top_headline`.
- Load vào `fact_news_sentiment_daily`.

## Ngày 20 - News sentiment và fact_news_sentiment_daily

### Việc đã hoàn thành

- Tạo loader:
  - `src/loaders/load_fact_news_sentiment.py`
- Tạo script load riêng:
  - `scripts/load_news_sentiment_gold.py`
- Cập nhật `scripts/load_gold.py` để load `fact_news_sentiment_daily` trong full Gold pipeline.
- Tạo sentiment demo bằng rule-based lexicon tiếng Việt.
- Tổng hợp theo `ticker + news_date`:
  - `news_count`
  - `source_count`
  - `positive_count`
  - `negative_count`
  - `neutral_count`
  - `avg_sentiment_score`
  - `top_headline`
- Tạo tài liệu:
  - `docs/news_sentiment_day20.md`
- Tạo test:
  - `tests/test_news_sentiment_day20.py`

### Kết quả load thực tế

```text
fact_news_sentiment_daily: 144 dòng
ticker_count: 104
```

### Lệnh đã chạy

```bash
uv run python scripts/load_news_sentiment_gold.py
uv run python scripts/migrate_gold_schema.py
uv run python scripts/load_gold.py
uv run python scripts/validate_gold.py
uv run pytest tests/test_news_sentiment_day20.py
uv run ruff check .
```

### Trạng thái

Ngày 20 đã hoàn thành ở mức sentiment demo và Gold fact table.

### Ghi chú

- Sentiment hiện là rule-based, chưa dùng NLP/model tiếng Việt nâng cao.
- Chất lượng `fact_news_sentiment_daily` phụ thuộc vào entity linking Ngày 19.

### Việc tiếp theo cho Ngày 21

- Xây dựng demo realtime VWAP.
- Tạo Kafka topic, ClickHouse Kafka Engine/Materialized View hoặc dữ liệu giả lập.
- Load/demo `fact_realtime_vwap`.

## Ngày 21 - Realtime VWAP và DNSE WebSocket

### Việc đã hoàn thành

- Tạo loader:
  - `src/loaders/load_fact_realtime_vwap.py`
- Tạo connector DNSE Market Data WebSocket thật:
  - `src/streaming/dnse_websocket.py`
- Tạo script load demo:
  - `scripts/load_realtime_vwap_demo.py`
- Tạo script ingest DNSE WebSocket thật:
  - `scripts/run_dnse_realtime_ingest.py`
- Tạo script tạo Kafka topic:
  - `scripts/create_realtime_kafka_topic.py`
- Tạo SQL tham khảo cho ClickHouse Kafka Engine và Materialized View:
  - `sql/streaming/realtime_vwap_kafka_engine.sql`
- Cập nhật `scripts/load_gold.py` để full Gold pipeline có demo `fact_realtime_vwap`.
- Tạo tài liệu:
  - `docs/realtime_vwap_day21.md`
- Tạo test:
  - `tests/test_realtime_vwap_day21.py`
  - `tests/test_dnse_websocket_day21_real.py`

### Kết quả demo

Demo trade ticks:

```text
input_ticks: 120
loaded_rows: 30
ticker_count: 3
```

Gold table:

```text
fact_realtime_vwap: 30 dòng
```

Kafka topic:

```text
dnse-trades-raw
```

DNSE WebSocket thật đã hỗ trợ:

```text
Base URL: wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json
Trade channel: tick.G1.json
Quote/order book channel dự kiến: top_price.G1.json
```

Lệnh chạy live khi đã có credential:

```bash
export DNSE_API_KEY=...
export DNSE_API_SECRET=...
uv run python scripts/run_dnse_realtime_ingest.py --symbols VCB,FPT,HPG --max-messages 100 --timeout-seconds 300 --load-vwap
```

Output Bronze live:

```text
data/bronze_local/dnse/trades/year=YYYY/month=MM/day=DD/data.parquet
```

### Lệnh đã chạy

```bash
docker compose up -d zookeeper kafka
uv run python scripts/create_realtime_kafka_topic.py
uv run python scripts/load_realtime_vwap_demo.py --tickers VCB,FPT,HPG --minutes 10 --trades-per-minute 4
uv run python scripts/migrate_gold_schema.py
uv run python scripts/load_gold.py
uv run python scripts/validate_gold.py
```

### Trạng thái

Ngày 21 đã hoàn thành ở mức demo realtime/VWAP và có connector DNSE WebSocket thật.

### Ghi chú

- Chưa thể xác nhận live nếu môi trường chưa có `DNSE_API_KEY` và `DNSE_API_SECRET`.
- ClickHouse Kafka Engine SQL hiện là bản tham khảo để triển khai streaming thật sau này.
- Demo VWAP hiện load trực tiếp vào ClickHouse bằng dữ liệu trade ticks giả lập.
- Connector thật hiện lấy Trade tick để tính VWAP; order book `top_price.G1.json` là bước mở rộng tiếp theo.

## Ngày 22 - Superset kết nối ClickHouse Gold

### Mục tiêu

- Kết nối Superset với ClickHouse Gold Layer.
- Tạo dataset cho các bảng dimension/fact chính.
- Chuẩn bị nền tảng để xây dựng các dashboard từ Ngày 23.

### Đã thực hiện

- Cập nhật Superset service để cài ClickHouse SQLAlchemy driver:
  - `clickhouse-connect`
- Tạo cấu hình dataset Gold:
  - `configs/superset_datasets.yaml`
- Tạo script setup Superset qua REST API:
  - `scripts/setup_superset_day22.py`
- Tạo tài liệu triển khai:
  - `docs/superset_day22.md`

### Dataset được expose cho Superset

- `dim_date`
- `dim_sector`
- `dim_stock`
- `dim_index`
- `fact_daily_price`
- `fact_market_index`
- `fact_news_sentiment_daily`
- `fact_realtime_vwap`
- `fact_alert_event`

### Lệnh chạy

Dry-run kiểm tra cấu hình:

```bash
uv run python scripts/setup_superset_day22.py --dry-run
```

Chạy setup thật khi Superset đã lên:

```bash
docker compose up -d clickhouse postgres superset
uv run python scripts/setup_superset_day22.py
```

### Trạng thái

Ngày 22 hoàn thành ở mức chuẩn bị connection/dataset Superset cho Gold Layer.

Dashboard cụ thể thuộc Ngày 23-26.
