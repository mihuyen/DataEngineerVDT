# Architecture

## Kiến trúc Medallion

Hệ thống dùng kiến trúc Bronze/Silver/Gold để tách trách nhiệm giữa lưu trữ thô, làm sạch dữ liệu và phục vụ phân tích.

## Bronze Layer

Bronze lưu dữ liệu thô 100% từ nguồn trong MinIO. Dữ liệu không bị chỉnh sửa, chỉ thêm metadata thu thập như ingestion time, source name và partition path nếu cần.

## Silver Layer

Silver chuẩn hóa tên cột, kiểu dữ liệu, timezone, mã cổ phiếu, ngày giao dịch và loại bỏ lỗi cơ bản như giá âm, volume âm, `high < low`, bản ghi trùng. Polars xử lý transform, Great Expectations kiểm tra chất lượng.

## Gold Layer

Gold là lớp phục vụ analytics trong ClickHouse. dbt tạo dimension/fact tables, tính chỉ báo kỹ thuật và tổng hợp dữ liệu cho dashboard.

## Vai trò công nghệ

- MinIO: object storage tương thích S3 để lưu Bronze và Silver.
- Polars: xử lý dữ liệu batch nhanh, phù hợp file Parquet/CSV/JSON.
- Great Expectations: định nghĩa expectation suite và báo cáo chất lượng dữ liệu.
- ClickHouse: OLAP database cho truy vấn dashboard và Gold tables.
- dbt: quản lý SQL model, lineage và test cho Gold Layer.
- Airflow: orchestration cho lịch ingest, transform, quality check và dbt run.
- Kafka: message broker cho realtime/order book.
- Superset: dashboard phân tích nghiệp vụ.
- Grafana: monitoring pipeline, service health, Kafka lag và alert trạng thái hệ thống.

## Batch pipeline

1. Airflow trigger DAG theo lịch.
2. Ingestion job lấy dữ liệu batch từ `vnstock`, API niêm yết/Finnhub, chỉ số thị trường và tin tức.
3. Dữ liệu thô được lưu vào MinIO Bronze theo source/date.
4. Polars đọc Bronze, chuẩn hóa và ghi Silver.
5. Great Expectations kiểm tra chất lượng dữ liệu Silver.
6. dbt chạy model Gold trong ClickHouse.
7. Superset đọc Gold tables để hiển thị dashboard.

## Streaming pipeline

1. DNSE WebSocket client nhận realtime/order book trong giờ giao dịch.
2. Message được publish vào Kafka topic.
3. ClickHouse Kafka Engine đọc message từ Kafka.
4. Materialized View ghi dữ liệu vào bảng realtime.
5. Aggregation tính VWAP theo phút/session.
6. Grafana hoặc Superset hiển thị Realtime VWAP Monitoring.

## Alert Engine

Alert Engine đọc điều kiện cảnh báo từ PostgreSQL bảng `user_alerts`, kiểm tra dữ liệu Gold hoặc realtime aggregation, chống spam theo cooldown window, ghi `fact_alert_event` và gửi Telegram/Email. Ngày 1 chỉ thiết kế, chưa kết nối API thật.

## Data Pipeline Monitor

Data Pipeline Monitor tổng hợp trạng thái Airflow DAG, Great Expectations, dbt tests, Kafka lag, thời điểm dữ liệu cập nhật cuối cùng và tình trạng các service chính. Dashboard này giúp phát hiện dữ liệu trễ, pipeline fail và chất lượng dữ liệu giảm.
