# Requirements

## Bài toán cần giải quyết

Xây dựng hệ thống Data Lakehouse theo dõi thị trường chứng khoán Việt Nam, có khả năng thu thập dữ liệu từ nhiều nguồn, lưu dữ liệu thô, làm sạch, kiểm tra chất lượng, tổng hợp chỉ báo và phục vụ dashboard/alert.

## Người dùng mục tiêu

- Nhà phân tích dữ liệu tài chính.
- Nhà đầu tư cá nhân cần dashboard theo dõi thị trường.
- Data engineer cần quan sát pipeline và chất lượng dữ liệu.
- Người vận hành hệ thống cần theo dõi realtime VWAP và cảnh báo.

## Input của hệ thống

- OHLCV cổ phiếu từ `vnstock`.
- Thông tin doanh nghiệp niêm yết từ API niêm yết hoặc Finnhub.
- Chỉ số thị trường như VN-Index, HNX-Index, VN30.
- Tin tức thị trường từ Finnhub News, RSS hoặc HTML crawl.
- Dữ liệu realtime/order book từ DNSE WebSocket API.

## Output của hệ thống

- Dữ liệu Bronze thô trong MinIO.
- Dữ liệu Silver đã làm sạch và kiểm tra chất lượng.
- Bảng Gold trong ClickHouse theo Star Schema.
- Dashboard Superset cho phân tích thị trường.
- Monitoring Grafana cho pipeline và service.
- Alert event gửi qua Telegram hoặc Email.

## 5 luồng dữ liệu chính

1. OHLCV cổ phiếu theo ngày.
2. Hồ sơ và chỉ tiêu cơ bản của doanh nghiệp niêm yết.
3. Chỉ số thị trường.
4. Tin tức và sentiment theo mã cổ phiếu.
5. Realtime/order book để tính VWAP và cảnh báo.

## Phạm vi bắt buộc

- Pipeline OHLCV batch.
- Bronze/Silver/Gold.
- Great Expectations.
- ClickHouse + Star Schema.
- Chỉ báo kỹ thuật.
- Market Overview.
- Stock Detail.
- Technical Signal Scanner.
- Data Pipeline Monitor.

## Phạm vi nâng cao

- Realtime VWAP.
- News & Sentiment.
- Alert Engine.
- Text-to-SQL demo.

## Các giả định

- Nguồn dữ liệu có thể thay đổi schema, cần có kiểm tra schema ở Silver.
- Một số API có rate limit hoặc yêu cầu API key.
- Dữ liệu realtime DNSE cần xác thực và có thể thay đổi theo phiên giao dịch.
- Giai đoạn đầu ưu tiên dữ liệu ngày, realtime triển khai sau khi nền tảng ổn định.

## Các rủi ro

- API bị giới hạn, đổi endpoint hoặc thiếu dữ liệu lịch sử.
- Dữ liệu tài chính có lỗi bất thường như giá âm, volume âm, trùng ngày giao dịch.
- Tin tức crawl từ HTML dễ hỏng khi website đổi giao diện.
- Realtime WebSocket có thể mất kết nối hoặc gửi message không đồng nhất.
- Dashboard có thể chậm nếu mô hình Gold chưa tối ưu partition/index.
- TODO: xác minh điều khoản sử dụng từng nguồn dữ liệu trước khi vận hành chính thức.
