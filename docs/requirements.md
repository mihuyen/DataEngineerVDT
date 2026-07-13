# Requirements

## Bài toán cần giải quyết

Xây dựng hệ thống Data Lakehouse theo dõi thị trường chứng khoán Việt Nam, có khả năng thu thập dữ liệu từ nhiều nguồn, lưu dữ liệu thô, làm sạch, kiểm tra chất lượng, tổng hợp chỉ báo và phục vụ dashboard/alert.

## Người dùng mục tiêu

- Nhà phân tích dữ liệu tài chính.
- Nhà đầu tư cá nhân cần dashboard theo dõi thị trường.
- Data engineer cần quan sát pipeline và chất lượng dữ liệu.
- Người vận hành hệ thống cần theo dõi realtime VWAP và cảnh báo.

## Input của hệ thống

- OHLCV cổ phiếu và VNINDEX/VN30 từ Vnstock (VCI).
- Danh sách mã HOSE và hồ sơ doanh nghiệp từ Vnstock (KBS).
- Tin tức thị trường từ VnExpress, Vietstock, CafeF (crawl HTML).
- Dữ liệu realtime (trade tick + nến 1 phút) từ DNSE WebSocket API.

## Output của hệ thống

- Dữ liệu Bronze thô trong MinIO.
- Dữ liệu Silver đã làm sạch và kiểm tra chất lượng.
- Bảng Gold trong ClickHouse theo Star Schema, một phần export lại Parquet.
- Dashboard React/FastAPI cho phân tích thị trường và cổ phiếu.
- Monitoring Grafana cho hạ tầng; Airflow callback cho trạng thái pipeline.
- Alert event gửi qua Telegram.

## Ba luồng dữ liệu chính

1. Batch — OHLCV, hồ sơ doanh nghiệp, chỉ số thị trường (18:00 T2–T6).
2. Tin tức — crawl, entity linking, phân tích cảm xúc (mỗi 5 phút, 24/7).
3. Realtime — trade tick (VWAP qua Kafka) và nến 1 phút (ghi thẳng), bỏ qua Silver.

## Phạm vi bắt buộc

- Pipeline OHLCV batch qua Bronze/Silver/Gold.
- Quality rule tự viết bằng Polars (không dùng thư viện Great Expectations thật).
- ClickHouse + Star Schema.
- Chỉ báo kỹ thuật (dbt).
- Market Overview, Stock Detail, Technical Signal Scanner, Data Pipeline Monitor (frontend).

## Phạm vi nâng cao — đã triển khai

- Realtime VWAP + nến 1 phút.
- News & Sentiment (fine-tune PhoBERT riêng).
- Alert Engine (14 loại rule).
- Reconciliation liên tầng cho cả Batch và Tin tức.

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
