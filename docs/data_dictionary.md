# Data Dictionary

Tài liệu mô tả schema đang dùng, phạm vi hiện tại là 404 mã HOSE. Bronze/Silver là Parquet trên MinIO/local, Gold là bảng ClickHouse (một phần được export lại Parquet vào bucket `gold`).

## Bronze Layer

Gộp toàn bộ mã vào 1 file theo ngày thu thập (không tách theo từng ticker).

| Dataset | Path pattern | Grain | Cột chính |
| --- | --- | --- | --- |
| `bronze_ohlcv` | `bronze/ohlcv/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dòng / ticker / ngày (toàn bộ mã gộp 1 file) | `ticker`, `date`, `open`, `high`, `low`, `close`, `volume` |
| `bronze_company_listing` | `bronze/company_profile/dataset=listing/year=/month=/day=/data.parquet` | 1 dòng / mã niêm yết | `symbol`, `organ_name`, `en_organ_name`, `exchange`, `type`, `source`, `ingested_at` |
| `bronze_market_index` | `bronze/market_index/index_code={index_code}/year=/month=/day=/data.parquet` | 1 dòng / index / ngày | `date`, `open`, `high`, `low`, `close`, `volume`, `index_code` |
| `bronze_news` | `bronze/news/source=multi/year=/month=/day=/data.parquet` | 1 dòng / bài viết | `url`, `title`, `published_at`, `content`, `source`, `crawl_at` |
| `bronze_dnse_trades` | Parquet cục bộ, sao lưu MinIO theo khả năng | 1 dòng / tick giao dịch | `ticker`, `trade_ts`, `price`, `volume` |
| `bronze_dnse_ohlcv_1m` | Parquet cục bộ | 1 dòng / mã / phút | `ticker`, `minute_ts`, `open/high/low/close`, `volume` |

## Silver Layer

Gộp theo `year/month` (thô hơn Bronze), không tách theo ticker.

| Dataset | Path pattern | Grain | Khóa khử trùng |
| --- | --- | --- | --- |
| `silver_ohlcv` | `silver/ohlcv/year=/month=/data.parquet` | 1 dòng / ticker / ngày | `ticker + date` |
| `silver_company_profile` | `silver/company_profile/year=/month=/data.parquet` | 1 dòng / ticker | `ticker` |
| `silver_market_index` | `silver/market_index/year=/month=/data.parquet` | 1 dòng / index / ngày | `index_code + date` |
| `silver_news` | `silver/news/year=/month=/data.parquet` | 1 dòng / bài viết | `url` → `article_id` |

## Gold Layer (ClickHouse — 4 bảng chiều, 9 bảng sự kiện)

### Dimension Tables

| Table | Grain | Cột chính |
| --- | --- | --- |
| `dim_date` | 1 dòng / ngày | `date_id`, `date`, `year`, `quarter`, `month`, `week`, `day_of_week`, `is_trading_day` |
| `dim_stock` | 1 dòng / ticker | `ticker`, `company_name`, `exchange`, `sector_id`, `listed_date`, `status`, `shares_outstanding`, `free_float_rate`, `market_cap_latest`, `pe_latest`, `eps_latest`, `roe_latest`, `roa_latest`, `updated_at` |
| `dim_sector` | 1 dòng / ngành | `sector_id`, `sector_name`, `industry_group`, `description` |
| `dim_index` | 1 dòng / chỉ số | `index_id`, `index_name`, `exchange`, `description` |

### Fact Tables

| Table | Grain | Partition · Order By | Cột chính |
| --- | --- | --- | --- |
| `fact_daily_price` | ticker × ngày | `toYYYYMM(trading_date)` · `(ticker, trading_date)` | OHLCV, `value`, `market_cap`, `price_change`, `pct_change`, `sma_20`/`ema_12`/`ema_26`/`macd`/`macd_signal`/`rsi_14`/`bb_upper`/`bb_middle`/`bb_lower`/`volume_sma_20` (chỉ EMA/MACD được Python tính đầy đủ), `overbought/oversold/breakout/breakdown_flag` |
| `fact_daily_price_indicators` | ticker × ngày | dbt incremental · `(ticker, date_id)` | Giống trên nhưng SMA/RSI/Bollinger do dbt tính bằng SQL, EMA/MACD tái sử dụng từ `fact_daily_price` |
| `fact_market_index` | index × ngày | `toYYYYMM(trading_date)` · `(index_id, trading_date)` | điểm số, `total_volume/value`, `advance/decline/unchanged_count`, `advance_decline_ratio`, `sma_20`, `rsi_14` |
| `fact_intraday_ohlcv` | ticker × phút | `toYYYYMMDD(trading_date)` · `(ticker, resolution, minute_ts)` | OHLCV phút, `is_final`, `data_source`, `ingested_at` (ReplacingMergeTree) |
| `fact_realtime_vwap` | ticker × phút (VIEW) | tính lúc đọc từ `fact_realtime_vwap_1m_state` | `vwap_1m`, `session_vwap`, `total_volume/value`, `session_volume/value`, `price_vs_vwap_pct`, `price_vs_session_vwap_pct` |
| `fact_news_sentiment_detail` | bài báo × ticker × phiên bản model | `toYYYYMM(published_at)` · `(ticker, published_at, article_id)` | `sentiment_label/score`, `confidence_score`, `model_version`, `match_method/score` (ReplacingMergeTree) |
| `fact_news_sentiment_daily` | ticker × ngày | `toYYYYMM(news_date)` · `(ticker, news_date)` | `news_count`, `positive/negative/neutral_count`, `avg_sentiment_score`, `top_headline` |
| `fact_alert_event` | 1 lần điều kiện kích hoạt | `toYYYYMM(triggered_at)` · `(user_id, triggered_at)` | `condition_type`, `threshold_value`, `actual_value`, `channel`, **`delivery_status`** (`sent`/`send_failed`/`channel_not_configured`/`unknown_channel`) |
| `fact_alert_rule_state` | rule × ticker (trạng thái, không phải sự kiện) | — · `(alert_id, ticker)` | `metric_value`, `updated_at` — lưu giá trị lần kiểm tra trước, phục vụ cảnh báo cắt ngưỡng |

## Dashboard Usage

| Trang frontend | Bảng dùng chính |
| --- | --- |
| Tổng quan thị trường | `fact_market_index`, `fact_daily_price`, `dim_stock`, `dim_sector`, `dim_index` |
| Bảng giá & Watchlist | `fact_daily_price`, `dim_stock`, `watchlist` (Postgres) |
| Chi tiết cổ phiếu | `fact_daily_price_indicators` (nến ngày), `fact_intraday_ohlcv` (nến trong phiên) |
| Bộ lọc tín hiệu kỹ thuật | `fact_daily_price_indicators` |
| Tin tức & cảm xúc | `fact_news_sentiment_daily`, `fact_news_sentiment_detail` |
| Lịch sử cảnh báo | `fact_alert_event` |
| Giám sát pipeline | Airflow REST API (fallback: độ mới/số dòng bảng Gold), quality_reports |
