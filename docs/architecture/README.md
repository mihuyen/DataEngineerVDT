# Sơ đồ kiến trúc và schema

Các bản dùng để trình bày chính:

- `system_architecture`: kiến trúc và luồng dữ liệu end-to-end.
- `gold_star_schema`: mô hình dữ liệu Gold logic để đánh giá nhanh grain và quan hệ.
- `final_data_schema`: schema vật lý đầy đủ, gồm streaming internals và PostgreSQL.

## Phạm vi

- Thị trường phục vụ: cổ phiếu HOSE, VNINDEX và VN30.
- Lakehouse bền vững: Parquet Bronze, Silver và Gold trên MinIO.
- Serving phân tích: ClickHouse.
- Trạng thái người dùng: PostgreSQL.
- Điều phối batch: Airflow; streaming: Kafka và ClickHouse Materialized View.

## Grain của các fact chính

| Bảng | Grain | Khóa nghiệp vụ |
| --- | --- | --- |
| `fact_daily_price` | Một mã trong một ngày giao dịch | `ticker + date_id` |
| `fact_market_index` | Một chỉ số trong một ngày giao dịch | `index_id + date_id` |
| `fact_intraday_ohlcv` | Một mã, độ phân giải và phút | `ticker + resolution + minute_ts` |
| `fact_news_sentiment_daily` | Một mã trong một ngày tin | `ticker + date_id` |
| `fact_realtime_vwap_1m_state` | Một nguồn, mã và phút | `data_source + ticker + minute_ts` |
| `fact_alert_event` | Một lần kích hoạt và gửi cảnh báo | `alert_id` |
| `fact_alert_rule_state` | Trạng thái gần nhất của rule trên một mã | `alert_id + ticker` |

## Lưu ý mô hình

- Các quan hệ FK trong ClickHouse là quan hệ logic, không có constraint vật lý.
- `fact_realtime_vwap` là VIEW, được tính từ aggregate state theo phút.
- `watchlist` và `user_alerts` nằm trong PostgreSQL, không phải dimension của Gold.
- `fact_daily_price_indicators` là mart dbt dẫn xuất từ `fact_daily_price`, không phải một nguồn fact độc lập.
- Luồng NLP đã có service và script inference nhưng chưa được nối hoàn chỉnh vào DAG sản xuất; đường này được vẽ nét đứt trong sơ đồ kiến trúc.
