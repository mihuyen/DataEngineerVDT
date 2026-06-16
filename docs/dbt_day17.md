# Ngày 17 - dbt models cho fact_daily_price

## Mục tiêu

Ngày 17 xây dựng dbt project và dbt models cho các chỉ báo kỹ thuật trong Gold Layer.

Chỉ báo mục tiêu:

- `sma_20`
- `ema_12`
- `ema_26`
- `macd`
- `rsi_14`
- Bollinger Band
- `market_cap`

## Dependency

Đã thêm bằng `uv`:

```bash
uv add dbt-core dbt-clickhouse
```

Không dùng `pip`.

## Cấu trúc dbt

```text
dbt/
├── dbt_project.yml
├── profiles.yml
├── README.md
├── models/
│   ├── sources.yml
│   ├── staging/
│   │   └── stg_fact_daily_price.sql
│   └── marts/
│       ├── fact_daily_price_indicators.sql
│       └── schema.yml
└── tests/
    ├── assert_fact_daily_price_indicators_unique_key.sql
    ├── assert_fact_daily_price_indicators_market_cap.sql
    └── assert_fact_daily_price_indicators_macd.sql
```

## Model

### stg_fact_daily_price

Staging view đọc từ ClickHouse table:

```text
stock_lakehouse.fact_daily_price
```

### fact_daily_price_indicators

Marts view tính và chuẩn hóa:

- `value`
- `market_cap = close * shares_outstanding`
- `price_change`
- `pct_change`
- `sma_20`
- `rsi_14`
- `bb_upper`
- `bb_middle`
- `bb_lower`
- `volume_sma_20`
- signal flags

`ema_12`, `ema_26`, `macd_signal` hiện kế thừa từ Gold Python loader. `macd` được tính lại trong dbt bằng:

```text
macd = ema_12 - ema_26
```

## Cách chạy

```bash
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

## Test dbt

Đã có:

- `not_null` cho `ticker`, `trading_date`, `close`, `market_cap`.
- Không trùng `ticker + trading_date`.
- `market_cap` đúng công thức.
- `macd` đúng công thức.

## Trạng thái

Ngày 17 hoàn thành ở mức dbt project và dbt model chạy được với ClickHouse.

Ghi chú kỹ thuật: EMA chính xác dạng recursive chưa chuyển hoàn toàn sang SQL dbt vì ClickHouse không có recursive EMA window đơn giản. Logic EMA hiện vẫn nằm trong Python Gold loader, còn dbt model đọc lại và kiểm soát kết quả.
