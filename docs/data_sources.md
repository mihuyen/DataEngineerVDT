# Data Sources

| Tên nguồn | Loại dữ liệu | Batch hay streaming | Tần suất thu thập | Dữ liệu thu thập | Đích lưu Bronze | Đích Silver | Đích Gold | Rủi ro khi thu thập |
|---|---|---|---|---|---|---|---|---|
| `vnstock` | OHLCV cổ phiếu | Batch | Hàng ngày sau giờ giao dịch | open, high, low, close, volume, trading_date, ticker | `bronze/vnstock/ohlcv/` | `silver/vnstock/ohlcv/` | `fact_daily_price`, `dim_stock`, `dim_date` | Thay đổi thư viện/API, thiếu dữ liệu lịch sử, ngày nghỉ giao dịch |
| API niêm yết/Finnhub | Thông tin doanh nghiệp | Batch | Hàng ngày hoặc hàng tuần | ticker, company_name, exchange, sector, market_cap, P/E, EPS, ROE, ROA, shares_outstanding | `bronze/company/profile/` | `silver/company/profile/` | `dim_stock`, `dim_sector` | Rate limit, API key hết hạn, schema thay đổi |
| VN-Index/HNX-Index/VN30 | Chỉ số thị trường | Batch | Hàng ngày sau giờ giao dịch | open, high, low, close, volume, trading_value, index_code | `bronze/market/index/` | `silver/market/index/` | `fact_market_index`, `dim_index`, `dim_date` | Nguồn không đồng nhất, mã chỉ số khác nhau giữa các provider |
| Finnhub News/RSS/HTML crawl | Tin tức thị trường | Batch | Mỗi 30-60 phút hoặc theo lịch Airflow | title, content, url, published_at, source | `bronze/news/market/` | `silver/news/market/` | `fact_news_sentiment_daily`, `dim_stock`, `dim_date` | Website đổi HTML, trùng tin, thiếu mapping ticker, giới hạn API |
| DNSE WebSocket API | Realtime/order book | Streaming | Realtime trong giờ giao dịch | bid/ask, matched price, volume, timestamp, ticker | `bronze/dnse/order_book/` hoặc Kafka raw topic | `silver/dnse/order_book/` | `fact_realtime_vwap`, `fact_alert_event` | Mất kết nối WebSocket, cần xác thực, message out-of-order, biến động tải cao |
