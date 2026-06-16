# Gold Layer

## Trạng thái hiện tại

Gold Layer đã được chuẩn hóa lại theo scheme thiết kế của project. Schema hiện không còn dùng bản v1 tối giản với `stock_id/full_date/sma20`, mà chuyển sang tên cột nghiệp vụ như `ticker`, `trading_date`, `sma_20`, `rsi_14`.

Đã có DDL trong ClickHouse cho đầy đủ các bảng:

- `dim_date`
- `dim_sector`
- `dim_stock`
- `dim_index`
- `fact_daily_price`
- `fact_market_index`
- `fact_realtime_vwap`
- `fact_news_sentiment_daily`
- `fact_alert_event`

Các bảng đã có dữ liệu thực tế:

- `dim_date`: 4.018 dòng.
- `dim_sector`: 5 dòng.
- `dim_stock`: 1.531 dòng.
- `dim_index`: 4 dòng.
- `fact_daily_price`: 35.142 dòng.
- `fact_market_index`: 92 dòng.
- `fact_news_sentiment_daily`: 144 dòng.
- `fact_realtime_vwap`: 30 dòng demo.

Các bảng đã tạo schema nhưng chưa có dữ liệu vì thuộc các ngày tiếp theo:

- `fact_alert_event`

## Dimension

### dim_date

Grain: 1 dòng cho 1 ngày lịch.

Cột chính:

- `date_id`
- `date`
- `year`
- `quarter`
- `month`
- `week`
- `day_of_week`
- `is_trading_day`

### dim_sector

Cột chính:

- `sector_id`
- `sector_name`
- `industry_group`
- `description`

### dim_stock

Khóa nghiệp vụ chính: `ticker`.

Cột chính:

- `ticker`
- `company_name`
- `exchange`
- `sector_id`
- `listed_date`
- `status`
- `shares_outstanding`
- `free_float_rate`
- `market_cap_latest`
- `pe_latest`
- `eps_latest`
- `roe_latest`
- `roa_latest`
- `updated_at`

### dim_index

Cột chính:

- `index_id`
- `index_name`
- `exchange`
- `description`

Hiện có:

- `VNINDEX`
- `VN30`
- `HNXINDEX`
- `UPCOMINDEX`

## Fact

### fact_daily_price

Grain: 1 mã cổ phiếu x 1 ngày giao dịch.

Nguồn: Silver OHLCV và Silver company profile.

Cột chính:

- `ticker`
- `date_id`
- `trading_date`
- OHLCV: `open`, `high`, `low`, `close`, `volume`
- `value`
- `shares_outstanding`
- `market_cap`
- `price_change`
- `pct_change`
- `sma_20`, `ema_12`, `ema_26`
- `macd`, `macd_signal`
- `rsi_14`
- `bb_upper`, `bb_middle`, `bb_lower`
- `volume_sma_20`
- `overbought_flag`, `oversold_flag`, `breakout_flag`, `breakdown_flag`
- `created_at`, `updated_at`

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (ticker, trading_date)
```

### fact_market_index

Grain: 1 chỉ số thị trường x 1 ngày giao dịch.

Cột chính:

- `index_id`
- `date_id`
- `trading_date`
- `open_point`, `high_point`, `low_point`, `close_point`
- `point_change`
- `pct_change`
- `total_volume`
- `total_value`
- `advance_count`, `decline_count`, `unchanged_count`
- `advance_decline_ratio`
- `sma_20`
- `rsi_14`
- `created_at`

Breadth hiện được tính từ Silver OHLCV và Silver company profile:

- `HOSE -> VNINDEX`
- `HNX -> HNXINDEX`
- `UPCOM -> UPCOMINDEX`
- `VN30`: demo top 30 HOSE theo `shares_outstanding`

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (index_id, trading_date)
```

### fact_realtime_vwap

Đã có dữ liệu demo Ngày 21 từ trade ticks giả lập.

Metric chính:

- `vwap_1m`
- `session_vwap`
- `total_volume`
- `total_value`
- `session_volume`
- `session_value`
- `price_vs_vwap_pct`
- `price_vs_session_vwap_pct`

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trading_date)
ORDER BY (ticker, minute_ts)
```

### fact_news_sentiment_daily

Đã có dữ liệu sentiment demo từ entity links Ngày 19.

Các metric:

- `news_count`
- `source_count`
- `positive_count`
- `negative_count`
- `neutral_count`
- `avg_sentiment_score`
- `top_headline`

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(news_date)
ORDER BY (ticker, news_date)
```

### fact_alert_event

Schema đã tạo để phục vụ Alert Engine.

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(triggered_at)
ORDER BY (user_id, triggered_at)
```

## Script

Recreate Gold schema từ DDL hiện tại:

```bash
uv run python scripts/migrate_gold_schema.py
```

Load riêng dimension:

```bash
uv run python scripts/load_dimensions.py
```

Load Gold batch hiện có:

```bash
uv run python scripts/load_gold.py
```

Validate:

```bash
uv run python scripts/validate_gold.py
```

Chạy dbt models Ngày 17:

```bash
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

## Ghi chú

- `fact_alert_event` hiện mới có schema, chưa có dữ liệu.
- `fact_realtime_vwap` hiện là demo giả lập; chưa kết nối DNSE WebSocket thật.
- ClickHouse không ép foreign key vật lý; quan hệ được quản lý ở tầng model/loader/dbt.
- Gold schema hiện ưu tiên khớp với scheme nghiệp vụ của project để thuận tiện viết báo cáo, dashboard và dbt model.
- dbt model `fact_daily_price_indicators` đã được tạo ở Ngày 17 để phục vụ chỉ báo kỹ thuật và kiểm thử logic.
