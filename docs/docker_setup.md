# Docker Setup

Tài liệu này mô tả Docker Compose local cho toàn bộ service của hệ thống.

## Danh sách service

| Service | Port | Vai trò |
|---|---:|---|
| MinIO | `9000`, `9001` | Object storage Bronze/Silver/Gold |
| ClickHouse | `8123`, `9002` | OLAP database cho Gold Layer |
| PostgreSQL | `5432` | `watchlist`, `user_alerts`, Airflow metadata |
| Zookeeper | `2181` | Điều phối Kafka |
| Kafka | `9092` | Streaming broker cho trade tick Realtime |
| `init-realtime-streaming` | — | Job chạy 1 lần: tạo Kafka Engine table + Materialized View trong ClickHouse |
| `dnse-producer` | — | Kết nối DNSE WebSocket (trade tick), đẩy vào Kafka |
| `dnse-ohlc-consumer` | — | Kết nối DNSE WebSocket (nến 1 phút), ghi thẳng ClickHouse |
| `nlp-service` | `8002` | Serving PhoBERT (tải model từ Hugging Face Hub, suy luận cục bộ) |
| `alert-engine` | — | Vòng lặp quét rule cảnh báo, gửi Telegram |
| Airflow Webserver | `8080` | UI orchestration |
| Airflow Scheduler | internal | Chạy DAG `stock_lakehouse_daily` + `news_crawl_5m` |
| Grafana | `3000` | Giám sát vận hành — hạ tầng, Kafka lag, trạng thái DAG |
| Superset | `8088` | Dashboard BI (tùy chọn) |

## Cách chạy

```powershell
docker compose up -d
```

Nếu vừa cập nhật Dockerfile Airflow hoặc muốn build lại image có `uv`:

```powershell
docker compose up -d --build airflow-webserver airflow-scheduler
```

Nếu máy yếu, có thể start trước các service nhẹ/cốt lõi:

```powershell
docker compose up -d minio clickhouse postgres zookeeper kafka grafana
```

Airflow và Superset là service nặng hơn, có thể start sau khi các service nền tảng đã ổn.

## Xem log

```powershell
docker compose logs -f
```

Xem log một service:

```powershell
docker compose logs -f clickhouse
```

## Dừng service

```powershell
docker compose down
```

## Xóa volume nếu cần reset dữ liệu local

```powershell
docker compose down -v
```

Chỉ dùng lệnh này khi muốn xóa toàn bộ dữ liệu container local.

## Kiểm tra cấu hình

```powershell
docker compose config
```

## Kiểm tra port local

```powershell
uv run python scripts/check_services.py
```

## Kafka topic

Topic chính: `dnse-trades-raw` (trade tick từ `dnse-producer`, ClickHouse Kafka Engine đọc trực tiếp). `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true` nên topic tự tạo khi producer/consumer đầu tiên dùng tới.

## Ghi chú bảo mật

- Không commit secret thật.
- Các giá trị trong `configs/.env.example` chỉ là placeholder local.
- Khi triển khai thật cần đổi password mặc định của MinIO, ClickHouse, PostgreSQL, Airflow, Superset và Grafana.
