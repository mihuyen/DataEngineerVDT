# Ngày 16 - Gold fact_daily_price

## Mục tiêu

Ngày 16 hoàn thiện bảng trung tâm `fact_daily_price` trong Gold Layer theo scheme của project.

Mục tiêu chính:

- Tạo bảng `fact_daily_price` trong ClickHouse.
- Dùng `MergeTree`.
- Partition theo tháng giao dịch.
- Order theo mã cổ phiếu và ngày giao dịch.
- Load dữ liệu từ Silver OHLCV.
- Bổ sung các trường phục vụ dashboard và phân tích kỹ thuật cơ bản.

## Grain

Grain của bảng:

```text
1 mã cổ phiếu x 1 ngày giao dịch
```

Khóa logic:

- `ticker`
- `trading_date`

## DDL

File DDL:

```text
sql/ddl/fact_daily_price.sql
```

Thiết kế vật lý:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (ticker, trading_date)
```

Lý do:

- `PARTITION BY toYYYYMM(trading_date)` phù hợp dữ liệu lịch sử theo ngày và quản lý theo tháng.
- `ORDER BY (ticker, trading_date)` tối ưu truy vấn lịch sử giá và chỉ báo của một mã cổ phiếu.

## Cột chính

Nhóm định danh:

- `ticker`
- `date_id`
- `trading_date`

Nhóm OHLCV:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `value`

Nhóm vốn hóa:

- `shares_outstanding`
- `market_cap`

Nhóm biến động giá:

- `price_change`
- `pct_change`

Nhóm chỉ báo kỹ thuật:

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

Nhóm tín hiệu:

- `overbought_flag`
- `oversold_flag`
- `breakout_flag`
- `breakdown_flag`

Nhóm audit:

- `created_at`
- `updated_at`

## Nguồn dữ liệu

Nguồn chính:

```text
data/silver_local/ohlcv/ticker=*/year=*/month=*/data.parquet
```

Nguồn phụ để lấy `shares_outstanding`:

```text
data/silver_local/company_profile/year=*/month=*/data.parquet
```

Nếu chưa có `shares_outstanding`, loader đặt giá trị `0` để không làm fail batch load.

## Loader

Module:

```text
src/loaders/load_fact_daily_price.py
```

Hàm chính:

- `load_silver_ohlcv()`
- `load_silver_company_shares()`
- `add_technical_indicators()`
- `build_fact_daily_price()`
- `load_fact_daily_price()`

## Kết quả hiện tại

Sau khi recreate Gold schema và load lại:

```text
fact_daily_price: 35.142 dòng
```

## Lệnh chạy

Recreate schema:

```bash
uv run python scripts/migrate_gold_schema.py
```

Load Gold:

```bash
uv run python scripts/load_gold.py
```

Validate:

```bash
uv run python scripts/validate_gold.py
```

Test:

```bash
uv run pytest tests/test_fact_daily_price_day16.py tests/test_clickhouse_schema.py tests/test_gold_loader.py
```

Lint:

```bash
uv run ruff check .
```

## Trạng thái

Ngày 16 đã hoàn thành ở mức Gold batch table:

- Bảng `fact_daily_price` đã có trong ClickHouse.
- Schema đã theo scheme của project.
- Có dữ liệu thực tế từ Silver OHLCV.
- Có partition và order key đúng thiết kế.
- Có test bảo vệ DDL và loader.

Phần dbt model cho các chỉ báo kỹ thuật thuộc Ngày 17, chưa tính vào phạm vi Ngày 16.
