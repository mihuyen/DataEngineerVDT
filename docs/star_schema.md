# Star Schema Gold Layer

Gold Layer lưu dữ liệu phân tích trong ClickHouse theo mô hình Star Schema — 4 bảng chiều, 9 bảng sự kiện (đúng 1 trong 9 là bảng trạng thái nội bộ phục vụ cảnh báo cắt ngưỡng, không phải sự kiện nghiệp vụ).

## Dimension tables

| Bảng | Khóa logic | Mục đích |
| --- | --- | --- |
| `dim_date` | `date_id` | Phân tích theo ngày, tuần, tháng, quý, năm và ngày giao dịch |
| `dim_sector` | `sector_id` | Phân tích theo ngành/nhóm ngành |
| `dim_stock` | `ticker` | Thông tin mô tả cổ phiếu niêm yết |
| `dim_index` | `index_id` | Danh mục chỉ số thị trường |

## Fact tables

| Bảng | Grain | Nạp bởi |
| --- | --- | --- |
| `fact_daily_price` | 1 mã × 1 ngày | Python Gold Loader (giá + EMA/MACD) |
| `fact_daily_price_indicators` | 1 mã × 1 ngày | dbt (SMA/RSI/Bollinger, dùng lại EMA từ bảng trên) |
| `fact_market_index` | 1 chỉ số × 1 ngày | Python Gold Loader |
| `fact_news_sentiment_detail` | 1 bài báo × 1 mã × 1 phiên bản model | News Gold Loader (sau Entity Linking + PhoBERT) |
| `fact_news_sentiment_daily` | 1 mã × 1 ngày | News Gold Loader (tổng hợp từ bảng detail) |
| `fact_intraday_ohlcv` | 1 mã × 1 phút | ClickHouse tự ghi qua Kafka Engine + MV (nhánh nến) |
| `fact_realtime_vwap` | 1 mã × 1 phút (VIEW, không lưu trữ) | Tính lúc đọc, gộp từ `fact_realtime_vwap_1m_state` (AggregatingMergeTree, nhánh trade tick) |
| `fact_alert_event` | 1 lần điều kiện cảnh báo được kích hoạt | Alert Engine |
| `fact_alert_rule_state` | 1 rule × 1 mã (trạng thái, không phải sự kiện) | Alert Engine — lưu giá trị lần kiểm tra trước, phục vụ cảnh báo cắt ngưỡng |

**Lưu ý về `fact_realtime_vwap`**: đây là VIEW thường (không phải Materialized View), vì VWAP lũy kế cả phiên cần cộng dồn không giới hạn số phút trước đó — việc này không thể duy trì kiểu "ghi sẵn mỗi khi có dòng mới" như MV, nên buộc phải tính lại mỗi lần đọc từ bảng trạng thái `fact_realtime_vwap_1m_state` (nhỏ, đã gộp sẵn theo phút).

## Quan hệ logic

```text
dim_sector 1 --- n dim_stock

dim_stock  1 --- n fact_daily_price
dim_stock  1 --- n fact_daily_price_indicators
dim_stock  1 --- n fact_intraday_ohlcv
dim_stock  1 --- n fact_realtime_vwap
dim_stock  1 --- n fact_news_sentiment_daily
dim_stock  1 --- n fact_news_sentiment_detail
dim_stock  1 --- n fact_alert_event
dim_stock  1 --- n fact_alert_rule_state

dim_date   1 --- n fact_daily_price
dim_date   1 --- n fact_daily_price_indicators
dim_date   1 --- n fact_market_index
dim_date   1 --- n fact_news_sentiment_daily

dim_index  1 --- n fact_market_index
```

ClickHouse không tạo foreign key vật lý. Các khóa trên là khóa logic dùng trong SQL model, dbt và dashboard.

## Thiết kế vật lý

| Bảng | Partition | Order By | Engine |
| --- | --- | --- | --- |
| `fact_daily_price` | `toYYYYMM(trading_date)` | `(ticker, trading_date)` | MergeTree |
| `fact_daily_price_indicators` | (theo `stg_fact_daily_price`) | `(ticker, date_id)` | MergeTree (dbt incremental, delete_insert) |
| `fact_market_index` | `toYYYYMM(trading_date)` | `(index_id, trading_date)` | MergeTree |
| `fact_intraday_ohlcv` | `toYYYYMMDD(trading_date)` | `(ticker, resolution, minute_ts)` | ReplacingMergeTree(ingested_at) |
| `fact_realtime_vwap_1m_state` | `toYYYYMMDD(trading_date)` | `(data_source, ticker, minute_ts)` | AggregatingMergeTree, TTL 30 ngày |
| `fact_news_sentiment_detail` | `toYYYYMM(published_at)` | `(ticker, published_at, article_id)` | ReplacingMergeTree(inferred_at) |
| `fact_news_sentiment_daily` | `toYYYYMM(news_date)` | `(ticker, news_date)` | MergeTree |
| `fact_alert_event` | `toYYYYMM(triggered_at)` | `(user_id, triggered_at)` | MergeTree |
| `fact_alert_rule_state` | — | `(alert_id, ticker)` | ReplacingMergeTree(updated_at) |

## Ghi chú thiết kế

- `dim_stock` dùng `ticker` làm khóa nghiệp vụ.
- `fact_daily_price` và `fact_daily_price_indicators` có nhiều cột chỉ báo trùng tên (SMA/RSI/Bollinger) — đây là nợ kỹ thuật đã biết: Python tính độc lập ở `fact_daily_price` nhưng không còn ai đọc các cột đó (StockDetail/StockScreener/Alert Engine đều đã chuyển sang đọc `fact_daily_price_indicators`). Chỉ `ema_12`/`ema_26`/`macd`/`macd_signal` là được dbt **tái sử dụng** (không tính lại) từ `fact_daily_price`, vì EMA có tính đệ quy mà ClickHouse SQL không tính hiệu quả được.
- `fact_intraday_ohlcv` và `fact_realtime_vwap*` thuộc luồng Realtime — **không đi qua Silver**, ghi thẳng từ Bronze/Kafka lên Gold.
- DDL đầy đủ tại `sql/ddl/*.sql` (Batch/Tin tức) và `sql/streaming/realtime_vwap_kafka_engine.sql` (Realtime).
