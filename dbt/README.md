# dbt project - Stock Lakehouse

## Mục tiêu

dbt project này phục vụ Tuần 3, bắt đầu từ Ngày 17. Phạm vi hiện tại là model hóa dữ liệu Gold `fact_daily_price` để tính và kiểm thử các chỉ báo kỹ thuật phục vụ dashboard.

## Cách chạy

Từ root project:

```bash
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

## Model hiện có

- `stg_fact_daily_price`: staging view đọc từ ClickHouse `fact_daily_price`.
- `fact_daily_price_indicators`: marts view tính/chuẩn hóa:
  - `sma_20`
  - `ema_12`
  - `ema_26`
  - `macd`
  - `macd_signal`
  - `rsi_14`
  - Bollinger Band
  - `market_cap`
  - signal flags

## Ghi chú

EMA hiện kế thừa từ Gold Python loader vì ClickHouse SQL không có recursive EMA window đơn giản. Các chỉ báo rolling như SMA, RSI và Bollinger Band được tính trực tiếp trong dbt SQL model.
