# Data Dictionary

Tai lieu nay mo ta schema dang dung trong project stock lakehouse, pham vi hien tai la HOSE. Bronze va Silver la parquet datasets trong MinIO/local, Gold la bang ClickHouse dong thoi duoc export parquet ve MinIO bucket `gold`.

## Bronze Layer

Bronze giu du lieu gan nguon nhat, uu tien audit va reprocess.

| Dataset | Path pattern | Grain | Cot chinh |
| --- | --- | --- | --- |
| `bronze_ohlcv` | `bronze/ohlcv/ticker={ticker}/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / ticker / ngay giao dich | `date`, `open`, `high`, `low`, `close`, `volume` |
| `bronze_company_listing` | `bronze/company_profile/dataset=listing/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / ma niem yet | `symbol`, `organ_name`, `en_organ_name`, `exchange`, `type`, `id`, `source`, `ingested_at` |
| `bronze_company_profile` | `bronze/company_profile/dataset=profile/ticker={ticker}/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / ticker profile | `symbol`, `exchange`, `business_model`, `charter_capital`, `listing_date`, `listed_volume`, `company_type`, `address`, `website`, `free_float`, `outstanding_shares`, `source`, `ingested_at` |
| `bronze_market_index` | `bronze/market_index/index_code={index_code}/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / index / ngay giao dich | `date`, `open`, `high`, `low`, `close`, `volume`, `trading_value`, `index_code` |
| `bronze_news` | `bronze/news/source={source}/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / bai viet | `url`, `title`, `published_at`, `description`, `content`, `tags`, `source`, `category`, `crawl_at` |
| `bronze_dnse_trades` | `bronze/dnse/trades/year={yyyy}/month={mm}/day={dd}/data.parquet` | 1 dong / tick giao dich | `ticker`, `trade_ts`, `price`, `volume`, `raw_json` |

## Silver Layer

Silver chuan hoa ten cot, kieu du lieu, metadata xu ly va cac rule co ban.

| Dataset | Path pattern | Grain | Cot |
| --- | --- | --- | --- |
| `silver_ohlcv` | `silver/ohlcv/ticker={ticker}/year={yyyy}/month={mm}/data.parquet` | 1 dong / ticker / ngay giao dich | `date`, `open`, `high`, `low`, `close`, `volume`, `ticker`, `ingested_at`, `processed_at`, `source_name` |
| `silver_company_profile` | `silver/company_profile/year={yyyy}/month={mm}/data.parquet` | 1 dong / ticker | `ticker`, `company_name`, `company_name_en`, `exchange`, `sector_id`, `sector_name`, `shares_outstanding`, `market_cap_latest`, `is_active`, `charter_capital`, `listed_volume`, `free_float`, `free_float_percentage`, `business_model`, `address`, `website`, `processed_at`, `source_name` |
| `silver_market_index` | `silver/market_index/year={yyyy}/month={mm}/data.parquet` | 1 dong / index / ngay giao dich | `date`, `open`, `high`, `low`, `close`, `volume`, `trading_value`, `index_code`, `processed_at`, `source_name` |
| `silver_news` | `silver/news/year={yyyy}/month={mm}/data.parquet` | 1 dong / bai viet | `url`, `title`, `published_at`, `description`, `content`, `tags`, `source`, `category`, `crawl_at`, `processed_at`, `source_name` |

## Gold Layer

Gold la lop phuc vu dashboard. Bang duoc load vao ClickHouse va export sang MinIO bucket `gold`.

### Dimension Tables

| Table | Grain | Partition parquet | Cot |
| --- | --- | --- | --- |
| `dim_date` | 1 dong / ngay calendar | `snapshot_date` | `date_id`, `date`, `year`, `quarter`, `month`, `week`, `day_of_week`, `is_trading_day` |
| `dim_stock` | 1 dong / ticker | `snapshot_date` | `ticker`, `company_name`, `exchange`, `sector_id`, `listed_date`, `status`, `shares_outstanding`, `free_float_rate`, `market_cap_latest`, `pe_latest`, `eps_latest`, `roe_latest`, `roa_latest`, `updated_at` |
| `dim_sector` | 1 dong / sector | `snapshot_date` | `sector_id`, `sector_name`, `industry_group`, `description` |
| `dim_index` | 1 dong / market index | `snapshot_date` | `index_id`, `index_name`, `exchange`, `description` |

### Fact Tables

| Table | Grain | Partition parquet | Cot |
| --- | --- | --- | --- |
| `fact_daily_price` | 1 dong / ticker / ngay giao dich | `year/month` theo `trading_date` | `ticker`, `date_id`, `trading_date`, `open`, `high`, `low`, `close`, `volume`, `value`, `shares_outstanding`, `market_cap`, `price_change`, `pct_change`, `sma_20`, `ema_12`, `ema_26`, `macd`, `macd_signal`, `rsi_14`, `bb_upper`, `bb_middle`, `bb_lower`, `volume_sma_20`, `overbought_flag`, `oversold_flag`, `breakout_flag`, `breakdown_flag`, `created_at`, `updated_at` |
| `fact_market_index` | 1 dong / index / ngay giao dich | `year/month` theo `trading_date` | `index_id`, `date_id`, `trading_date`, `open_point`, `high_point`, `low_point`, `close_point`, `point_change`, `pct_change`, `total_volume`, `total_value`, `advance_count`, `decline_count`, `unchanged_count`, `advance_decline_ratio`, `sma_20`, `rsi_14`, `created_at` |
| `fact_news_sentiment_daily` | 1 dong / ticker / ngay tin tuc | `year/month` theo `news_date` | `ticker`, `date_id`, `news_date`, `news_count`, `source_count`, `positive_count`, `negative_count`, `neutral_count`, `avg_sentiment_score`, `top_headline`, `created_at` |
| `fact_realtime_vwap` | 1 dong / ticker / phut | `trading_date` | `ticker`, `minute_ts`, `trading_date`, `open_price`, `high_price`, `low_price`, `close_price`, `vwap_1m`, `session_vwap`, `total_volume`, `total_value`, `session_volume`, `session_value`, `avg_price`, `trade_count`, `price_vs_vwap_pct`, `price_vs_session_vwap_pct`, `created_at` |
| `fact_alert_event` | 1 dong / alert event | `year/month` khi co du lieu, hien snapshot rong neu bang 0 dong | `alert_id`, `user_id`, `ticker`, `date_id`, `triggered_at`, `condition_type`, `threshold_value`, `actual_value`, `channel`, `is_sent`, `sent_at`, `created_at` |

## Dashboard Usage

| Dashboard | Bang/dataset dung chinh |
| --- | --- |
| Market Overview | `fact_market_index`, `fact_daily_price`, `dim_stock`, `dim_sector`, `dim_index` |
| Stock Detail | `fact_daily_price`, `dim_stock` |
| Technical Scanner | `fact_daily_price`, `dim_stock` |
| Realtime VWAP | `fact_realtime_vwap`, fallback DNSE Bronze trades |
| News Sentiment | `fact_news_sentiment_daily`, `dim_stock` |
| Alert History | `fact_alert_event` |
| Pipeline Monitor | row counts, latest dates, quality report snapshots |

