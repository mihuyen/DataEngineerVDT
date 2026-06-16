# Silver Layer

## Trạng thái hiện tại

Silver Layer hiện đã được mở rộng từ mẫu `VCB` sang các nhóm dữ liệu chính:

- OHLCV: transform toàn bộ ticker đã có trong Bronze local.
- Company profile: transform dữ liệu listing/profile doanh nghiệp.
- Market index: transform `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX`.
- News: transform tin tức đã crawl từ VnExpress, Vietstock, CafeF.

Các script chính:

```powershell
uv run python scripts/run_silver_transform.py --skip-existing
uv run python scripts/run_company_profile_silver.py
uv run python scripts/run_market_index_silver.py
uv run python scripts/run_news_silver.py
```

## OHLCV

Silver Layer là tầng dữ liệu đã được chuẩn hóa và kiểm tra chất lượng. Với Ngày 4, phạm vi chỉ gồm dữ liệu OHLCV đã ingest từ Bronze.

## Mục đích

- Đọc dữ liệu OHLCV thô từ Bronze.
- Chuẩn hóa tên cột và kiểu dữ liệu.
- Loại bỏ bản ghi lỗi cơ bản.
- Loại bỏ duplicate theo `ticker + date`.
- Chạy validation theo bộ rule kiểu Great Expectations.
- Ghi dữ liệu sạch xuống Silver.

Không thực hiện ClickHouse, dbt, dashboard, Kafka, Alert Engine hoặc Airflow DAG trong Ngày 4.

## Bronze input

```text
bronze/
└── ohlcv/
    └── ticker=VCB/
        └── year=2026/
            └── month=06/
                └── day=10/
                    └── data.parquet
```

## Silver output

```text
silver/
└── ohlcv/
    └── ticker=VCB/
        └── year=2026/
            └── month=06/
                └── data.parquet
```

Silver partition theo `ticker`, `year`, `month` để chuẩn bị cho Gold Layer và truy vấn theo giai đoạn.

## Transform rules

- Chuẩn hóa tên cột về lowercase snake_case.
- Alias hỗ trợ: `time`, `trading_date`, `tradingdate` -> `date`; `vol`, `match_volume` -> `volume`.
- Cast schema:
  - `date`: `Date`
  - `open`, `high`, `low`, `close`: `Float64`
  - `volume`: `Int64`
- Thêm metadata:
  - `ticker`
  - `ingested_at`
  - `processed_at`
  - `source_name`
- Loại duplicate theo `ticker + date`.
- Loại invalid records:
  - `volume < 0`
  - `open <= 0`
  - `high <= 0`
  - `low <= 0`
  - `close <= 0`
  - `high < low`

## Quality rules

Bộ validation được đặt tại `src/quality/ohlcv_expectations.py`.

Schema bắt buộc:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

Null validation:

- `date` không được null.
- `close` không được null.

Range validation:

- `open > 0`
- `high > 0`
- `low > 0`
- `close > 0`
- `volume >= 0`

Consistency validation:

- `high >= low`
- `high >= open`
- `high >= close`
- `low <= open`
- `low <= close`

Duplicate validation:

- `ticker + date` phải unique.

## Great Expectations workflow

Project thêm dependency `great-expectations` để chuẩn bị chuẩn validation dài hạn. Trong Ngày 4, validation được viết bằng Polars theo format expectation rõ ràng và report có ghi `gx_version` để truy vết phiên bản Great Expectations.

Luồng:

```text
Bronze parquet
↓
Polars transform
↓
OHLCV expectations
↓
quality_reports/YYYY-MM-DD_validation.json
↓
Silver parquet
```

## Cách chạy

Chạy transform Bronze -> Silver:

```powershell
uv run python scripts/run_silver_transform.py
```

Chỉ chạy quality check:

```powershell
uv run python scripts/run_quality_check.py
```

Chạy kiểm thử:

```powershell
uv run pytest
uv run ruff check .
```

## Quality report mẫu

```json
{
  "source_name": "vnstock_ohlcv",
  "record_count": 2,
  "error_count": 0,
  "success": true,
  "expectations": []
}
```

Report thực tế có đầy đủ từng expectation, `failed_count`, `details` và `generated_at`.
