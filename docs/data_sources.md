# Data Sources

| Nguồn | Dữ liệu | Batch/Streaming | Tần suất | Trường chính | Bronze path | Đích Gold | Rủi ro |
|---|---|---|---|---|---|---|---|
| Vnstock (KBS) | Danh sách mã HOSE, hồ sơ doanh nghiệp | Batch | Sau giờ giao dịch | `symbol`, `organ_name`, `exchange`, `sector` | `bronze/company_profile/dataset=listing/` | `dim_stock`, `dim_sector` | Rate limit, thay đổi API |
| Vnstock (VCI) | OHLCV ngày, VNINDEX/VN30 | Batch | Sau giờ giao dịch | `date`, `open/high/low/close`, `volume`, `ticker` | `bronze/ohlcv/`, `bronze/market_index/index_code=<CODE>/` | `fact_daily_price`, `fact_market_index` | Rate limit — nguyên nhân chính khiến không phải mã nào cũng có bản ghi mỗi ngày |
| VnExpress, Vietstock, CafeF | Tin tức tài chính | Batch nhỏ | Crawl mỗi 5 phút, 24/7 | `url`, `title`, `content`, `published_at`, `source` | `bronze/news/source=multi/` | `fact_news_sentiment_detail`, `fact_news_sentiment_daily` | Website đổi HTML, trùng tin (chống bằng URL registry) |
| DNSE WebSocket | Giao dịch khớp lệnh, nến 1 phút đã đóng | Streaming | Liên tục trong giờ giao dịch | Trade tick: `ticker`, `trade_ts`, `price`, `volume`. Nến: OHLCV theo phút | Parquet cục bộ, sao lưu MinIO theo khả năng | `fact_realtime_vwap` (qua Kafka), `fact_intraday_ohlcv` (ghi thẳng) | Rớt kết nối WebSocket tạm thời — phát hiện qua đối chiếu chéo khối lượng 2 kênh |

## Ghi chú quan trọng

- **Không dùng Finnhub** — nguồn tin tức là 3 báo Việt Nam (VnExpress/Vietstock/CafeF), không phải Finnhub News.
- **Không có nguồn riêng cho HNX/UPCOM** — phạm vi hiện tại chỉ 404 mã HOSE.
- 2 nguồn Vnstock (KBS + VCI) bổ sung nhau: KBS mạnh về hồ sơ doanh nghiệp, VCI mạnh về giá — không nguồn nào đủ cả 2, nên phải gọi cả 2 dù cùng dùng chung 1 thư viện Vnstock.
- DNSE có 2 kênh độc lập (trade tick qua Kafka, nến ghi thẳng) — không suy nến từ tick để giữ khả năng đối chiếu chéo phát hiện sự cố kết nối.
