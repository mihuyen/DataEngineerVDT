# Timeline triển khai theo Report.md

Tài liệu này lấy timeline trong `Report.md` làm nguồn chuẩn để triển khai project.

## Tuần 1: Phân tích yêu cầu, khởi tạo hệ thống và ingest dữ liệu Bronze

Mục tiêu tuần 1: hoàn thiện phạm vi dự án, xác định đầy đủ 5 nguồn dữ liệu, khởi tạo môi trường hệ thống và bắt đầu thu thập dữ liệu thô vào tầng Bronze.

| Ngày | Công việc | Kết quả đầu ra |
|---|---|---|
| Ngày 1 | Phân tích yêu cầu, xác định bài toán, use case, dashboard, phạm vi demo và 5 luồng dữ liệu chính | Hoàn thành phần đặt vấn đề, mục tiêu, input/output và phạm vi hệ thống |
| Ngày 2 | Khởi tạo project, tạo cấu trúc thư mục, cấu hình môi trường Python, Docker Compose | Project chạy được ở mức cơ bản |
| Ngày 3 | Cấu hình các service chính: MinIO, ClickHouse, Airflow, Kafka, Superset/Grafana | Môi trường local có đủ service cần thiết |
| Ngày 4 | Xây dựng pipeline ingest dữ liệu OHLCV từ `vnstock` | Dữ liệu giá cổ phiếu thô được lưu vào Bronze |
| Ngày 5 | Ingest thông tin doanh nghiệp niêm yết: ticker, tên công ty, sàn, ngành, shares_outstanding, P/E, EPS, ROE, ROA | Dữ liệu thô phục vụ `dim_stock` và `dim_sector` |
| Ngày 6 | Ingest dữ liệu chỉ số thị trường: VN-Index, HNX-Index, VN30 | Dữ liệu thô phục vụ `fact_market_index` |
| Ngày 7 | Ingest thử dữ liệu tin tức từ Finnhub News hoặc RSS/HTML crawl, lưu title, content, url, published_at, source | Dữ liệu tin tức thô được lưu vào Bronze |

Kết quả cuối tuần 1:

- Hoàn thành phân tích yêu cầu và phạm vi hệ thống.
- Có môi trường chạy local bằng Docker.
- Có dữ liệu Bronze cho OHLCV.
- Có dữ liệu Bronze cho thông tin doanh nghiệp.
- Có dữ liệu Bronze cho chỉ số thị trường.
- Có dữ liệu Bronze cho tin tức.
- Cấu trúc lưu trữ trong MinIO được tổ chức theo nguồn dữ liệu và ngày xử lý.

## Tuần 2: Xây dựng tầng Silver và kiểm soát chất lượng dữ liệu

Mục tiêu tuần 2: làm sạch dữ liệu từ Bronze sang Silver, chuẩn hóa kiểu dữ liệu, xử lý lỗi và tích hợp Great Expectations để kiểm soát chất lượng dữ liệu.

| Ngày | Công việc | Kết quả đầu ra |
|---|---|---|
| Ngày 8 | Xây dựng script Bronze -> Silver cho dữ liệu OHLCV bằng Polars | Dữ liệu OHLCV sạch ở tầng Silver |
| Ngày 9 | Kiểm tra lỗi OHLCV: giá âm, volume âm/null, high < low, trùng ticker + ngày | Bộ dữ liệu giá đáng tin cậy hơn |
| Ngày 10 | Xử lý Silver cho dữ liệu doanh nghiệp: chuẩn hóa ticker, tên công ty, ngành, sàn, shares_outstanding | Dữ liệu sạch phục vụ dimension |
| Ngày 11 | Xử lý Silver cho dữ liệu chỉ số thị trường: chuẩn hóa ngày, điểm số, khối lượng, giá trị giao dịch | Dữ liệu sạch phục vụ market index |
| Ngày 12 | Xử lý Silver cho tin tức: loại bài trùng, chuẩn hóa thời gian, bỏ bài quá ngắn, làm sạch HTML tags | Dữ liệu tin tức sạch ở Silver |
| Ngày 13 | Tích hợp Great Expectations cho các pipeline chính: OHLCV, doanh nghiệp, index, tin tức | Bộ rule kiểm tra chất lượng dữ liệu |
| Ngày 14 | Cấu hình Airflow DAG chạy tự động các bước Bronze -> Silver, kiểm thử toàn bộ pipeline | Pipeline Silver chạy ổn định |

Kết quả cuối tuần 2:

- Có dữ liệu Silver cho OHLCV.
- Có dữ liệu Silver cho thông tin doanh nghiệp.
- Có dữ liệu Silver cho chỉ số thị trường.
- Có dữ liệu Silver cho tin tức.
- Có Great Expectations kiểm tra chất lượng dữ liệu.
- Airflow chạy được pipeline Bronze -> Silver.
- Có log lỗi rõ ràng khi pipeline fail.

## Tuần 3: Xây dựng tầng Gold, Star Schema, dbt và xử lý realtime

| Ngày | Công việc | Kết quả đầu ra |
|---|---|---|
| Ngày 15 | Thiết kế và tạo các bảng Dimension: `dim_date`, `dim_stock`, `dim_sector`, `dim_index` | Có các bảng dimension trong ClickHouse |
| Ngày 16 | Tạo bảng `fact_daily_price`, cấu hình MergeTree, Partition, Order By | Có bảng fact trung tâm cho dữ liệu OHLCV |
| Ngày 17 | Xây dựng dbt models tính SMA20, EMA12, EMA26, MACD, RSI14, Bollinger Band, market_cap | Có chỉ báo kỹ thuật trong `fact_daily_price` |
| Ngày 18 | Xây dựng `fact_market_index`: VN-Index, HNX-Index, VN30, advance/decline ratio | Có dữ liệu Gold cho tổng quan thị trường |
| Ngày 19 | Xử lý entity linking cho tin tức: gán bài viết với ticker bằng từ điển tên công ty/ticker và regex | Tin tức được gắn với mã cổ phiếu |
| Ngày 20 | Tính sentiment ở mức demo và tổng hợp vào `fact_news_sentiment_daily` | Có dữ liệu Gold cho News & Sentiment |
| Ngày 21 | Xây dựng thử luồng realtime: Kafka topic, ClickHouse Kafka Engine, Materialized View, `fact_realtime_vwap` hoặc dữ liệu giả lập | Có demo luồng realtime/VWAP cơ bản |

## Tuần 4: Dashboard, Alert Engine, Data Pipeline Monitor và hoàn thiện báo cáo

| Ngày | Công việc | Kết quả đầu ra |
|---|---|---|
| Ngày 22 | Kết nối Superset với ClickHouse, tạo dataset cho các bảng Gold | Superset đọc được dữ liệu ClickHouse |
| Ngày 23 | Xây dựng dashboard Market Overview: VN-Index, top tăng/giảm, thanh khoản, heatmap ngành | Dashboard tổng quan thị trường |
| Ngày 24 | Xây dựng dashboard Stock Detail: candlestick, volume, RSI, MACD, Bollinger Band, market cap | Dashboard chi tiết mã cổ phiếu |
| Ngày 25 | Xây dựng Technical Signal Scanner: RSI quá mua/quá bán, breakout, breakdown, volume đột biến | Dashboard quét tín hiệu kỹ thuật |
| Ngày 26 | Xây dựng Data Pipeline Monitor: Airflow DAG status, số lỗi GX/dbt, Kafka consumer lag, trạng thái service | Dashboard/section giám sát pipeline |
| Ngày 27 | Xây dựng Alert Engine demo: `user_alerts`, Alert Checker, cooldown chống spam, ghi log vào `fact_alert_event` | Demo cảnh báo và lịch sử alert |
| Ngày 28 | Hoàn thiện báo cáo, chỉnh format, chuẩn bị slide, chạy thử kịch bản demo cuối | Báo cáo, slide và demo hoàn chỉnh |
