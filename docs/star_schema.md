# Star Schema Gold Layer

Gold Layer lưu dữ liệu phân tích trong ClickHouse theo mô hình Star Schema. Schema hiện đã được chỉnh theo thiết kế nghiệp vụ của project.

## Dimension tables

| Bảng | Khóa logic | Mục đích |
| --- | --- | --- |
| `dim_date` | `date_id` | Phân tích theo ngày, tuần, tháng, quý, năm và ngày giao dịch |
| `dim_sector` | `sector_id` | Phân tích theo ngành/nhóm ngành |
| `dim_stock` | `ticker` | Thông tin mô tả cổ phiếu niêm yết |
| `dim_index` | `index_id` | Danh mục chỉ số thị trường |

## Fact tables

| Bảng | Grain | Trạng thái |
| --- | --- | --- |
| `fact_daily_price` | 1 mã cổ phiếu x 1 ngày | Đã có dữ liệu |
| `fact_market_index` | 1 chỉ số x 1 ngày | Đã có dữ liệu |
| `fact_realtime_vwap` | 1 mã cổ phiếu x 1 phút | Đã có schema, chờ Ngày 21 |
| `fact_news_sentiment_daily` | 1 mã cổ phiếu x 1 ngày | Đã có schema, chờ Ngày 20 |
| `fact_alert_event` | 1 cảnh báo được kích hoạt | Đã có schema, chờ Alert Engine |

## Quan hệ logic

```text
dim_sector 1 --- n dim_stock

dim_stock  1 --- n fact_daily_price
dim_stock  1 --- n fact_realtime_vwap
dim_stock  1 --- n fact_news_sentiment_daily
dim_stock  1 --- n fact_alert_event

dim_date   1 --- n fact_daily_price
dim_date   1 --- n fact_market_index
dim_date   1 --- n fact_news_sentiment_daily
dim_date   1 --- n fact_alert_event

dim_index  1 --- n fact_market_index
```

ClickHouse không tạo foreign key vật lý. Các khóa trên là khóa logic dùng trong SQL model, dbt và dashboard.

## Thiết kế vật lý

| Bảng | Partition | Order By |
| --- | --- | --- |
| `fact_daily_price` | `toYYYYMM(trading_date)` | `(ticker, trading_date)` |
| `fact_realtime_vwap` | `toYYYYMMDD(trading_date)` | `(ticker, minute_ts)` |
| `fact_market_index` | `toYYYYMM(trading_date)` | `(index_id, trading_date)` |
| `fact_news_sentiment_daily` | `toYYYYMM(news_date)` | `(ticker, news_date)` |
| `fact_alert_event` | `toYYYYMM(triggered_at)` | `(user_id, triggered_at)` |

## Ghi chú thiết kế

- `dim_stock` dùng `ticker` làm khóa nghiệp vụ theo scheme.
- `fact_daily_price` lưu cả giá, thanh khoản, vốn hóa ngày và chỉ báo kỹ thuật.
- `fact_market_index` lưu điểm chỉ số và breadth metrics.
- Các bảng realtime/news/alert đã có DDL để các ngày tiếp theo chỉ cần bổ sung loader/model.
