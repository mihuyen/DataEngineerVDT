# Docker setup Ngày 2

Tài liệu này mô tả Docker Compose local cho các service nền tảng của project Data Lakehouse chứng khoán Việt Nam.

## Danh sách service

| Service | Port | Vai trò |
|---|---:|---|
| MinIO | `9000`, `9001` | Object storage cho Bronze/Silver data |
| ClickHouse | `8123`, `9002` | OLAP database cho Gold Layer |
| PostgreSQL | `5432` | Airflow metadata, `user_alerts`, cấu hình cảnh báo |
| Zookeeper | `2181` | Điều phối Kafka local |
| Kafka | `9092` | Streaming broker cho `raw_trades` và dữ liệu realtime |
| Airflow Webserver | `8080` | UI orchestration batch pipeline |
| Airflow Scheduler | internal | Scheduler chạy DAG |
| Superset | `8088` | Dashboard phân tích kết nối ClickHouse ở các ngày sau |
| Grafana | `3000` | Monitoring pipeline, Kafka lag, service health |

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

Kafka bật `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`, vì vậy topic demo `raw_trades` có thể được tạo tự động khi producer/consumer đầu tiên sử dụng.

TODO Ngày 3: tạo script chính thức để quản lý topic như `raw_trades`, `raw_order_book` và các topic realtime khác.

## Ghi chú bảo mật

- Không commit secret thật.
- Các giá trị trong `configs/.env.example` chỉ là placeholder local.
- Khi triển khai thật cần đổi password mặc định của MinIO, ClickHouse, PostgreSQL, Airflow, Superset và Grafana.
