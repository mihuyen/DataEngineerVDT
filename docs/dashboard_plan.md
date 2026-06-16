# Dashboard Plan

## 1. Market Overview

- Mục đích: theo dõi sức khỏe thị trường trong ngày và theo giai đoạn.
- Nguồn dữ liệu: `fact_market_index`, `fact_daily_price`, `dim_stock`, `dim_sector`.
- Bộ lọc chính: ngày, sàn, ngành, chỉ số.
- Thông tin hiển thị: VN-Index, HNX-Index, VN30, top tăng/giảm, thanh khoản, heatmap ngành.
- Biểu đồ nên dùng: line chart, bar chart, treemap/heatmap, KPI cards.
- Drill-down: từ ngành sang danh sách mã cổ phiếu.

## 2. Stock Detail

- Mục đích: phân tích chi tiết một mã cổ phiếu.
- Nguồn dữ liệu: `fact_daily_price`, `dim_stock`, `dim_sector`.
- Bộ lọc chính: ticker, khoảng thời gian, chỉ báo kỹ thuật.
- Thông tin hiển thị: candlestick, volume, RSI, MACD, Bollinger Band, market cap.
- Biểu đồ nên dùng: candlestick, volume bar, line chart, indicator panels.
- Drill-down: từ tín hiệu kỹ thuật sang lịch sử giá.

## 3. Technical Signal Scanner

- Mục đích: quét các mã có tín hiệu kỹ thuật đáng chú ý.
- Nguồn dữ liệu: `fact_daily_price`, Gold technical indicator models.
- Bộ lọc chính: ngày, ngành, sàn, loại tín hiệu.
- Thông tin hiển thị: RSI quá mua/quá bán, breakout, breakdown, volume đột biến.
- Biểu đồ nên dùng: table, scatter plot, bar chart.
- Drill-down: từ mã trong scanner sang Stock Detail.

## 4. Data Pipeline Monitor

- Mục đích: giám sát trạng thái pipeline và chất lượng dữ liệu.
- Nguồn dữ liệu: Airflow metadata, Great Expectations results, dbt artifacts, Kafka metrics.
- Bộ lọc chính: DAG, source, ngày chạy, trạng thái.
- Thông tin hiển thị: DAG status, quality checks, dbt tests, Kafka lag, service health.
- Biểu đồ nên dùng: status table, timeline, KPI cards, bar chart.
- Drill-down: từ job fail sang log hoặc expectation result.

## 5. Realtime VWAP Monitoring

- Mục đích: theo dõi VWAP theo phút và session trong giờ giao dịch.
- Nguồn dữ liệu: DNSE WebSocket API, Kafka, ClickHouse realtime tables, `fact_realtime_vwap`.
- Bộ lọc chính: ticker, phiên giao dịch, khoảng thời gian.
- Thông tin hiển thị: matched price, volume, minute VWAP, session VWAP, chênh lệch giá so với VWAP.
- Biểu đồ nên dùng: realtime line chart, table, alert marker.
- Drill-down: từ phút bất thường sang order book raw events.

## 6. News & Sentiment

- Mục đích: theo dõi tin tức, nguồn tin và sentiment theo mã cổ phiếu.
- Nguồn dữ liệu: Silver news, `fact_news_sentiment_daily`, `dim_stock`.
- Bộ lọc chính: ngày, ticker, nguồn tin, sentiment.
- Thông tin hiển thị: số lượng tin, title, source, sentiment score, ticker liên quan.
- Biểu đồ nên dùng: table, time series, stacked bar, word cloud nếu cần.
- Drill-down: từ ngày/ticker sang danh sách bài viết.

## 7. Alert History

- Mục đích: xem lịch sử cảnh báo và trạng thái gửi.
- Nguồn dữ liệu: `fact_alert_event`, PostgreSQL `user_alerts`.
- Bộ lọc chính: ticker, loại điều kiện, trạng thái gửi, kênh gửi.
- Thông tin hiển thị: alert time, condition, actual value, threshold, delivery status, cooldown.
- Biểu đồ nên dùng: table, KPI cards, timeline.
- Drill-down: từ alert sang dữ liệu giá hoặc VWAP tại thời điểm kích hoạt.
