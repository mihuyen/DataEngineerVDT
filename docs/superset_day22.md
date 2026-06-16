# Ngày 22 - Superset kết nối ClickHouse Gold

## Mục tiêu

Ngày 22 chuyển Gold Layer từ trạng thái chỉ truy vấn trực tiếp trong ClickHouse sang trạng thái sẵn sàng phục vụ dashboard trong Superset.

Phạm vi gồm:

- Cài ClickHouse SQLAlchemy driver cho Superset container.
- Tạo cấu hình danh sách dataset Gold cần expose cho dashboard.
- Tạo script tự động đăng nhập Superset, tạo database connection và tạo/cập nhật dataset.
- Kiểm tra được cấu hình bằng chế độ dry-run, không phụ thuộc Superset đang chạy.

## Thành phần triển khai

Docker Compose:

```text
docker-compose.yml
```

Superset service cài thêm `clickhouse-connect` trước khi khởi động để hỗ trợ SQLAlchemy URI dạng:

```text
clickhousedb://default:clickhouse@clickhouse:8123/stock_lakehouse
```

Cấu hình dataset:

```text
configs/superset_datasets.yaml
```

Script setup:

```text
scripts/setup_superset_day22.py
```

## Dataset Gold được tạo trong Superset

| Dataset | Mục đích dashboard |
| --- | --- |
| `dim_date` | Bộ lọc ngày, tuần, tháng, quý, năm |
| `dim_sector` | Bộ lọc và nhóm dữ liệu theo ngành |
| `dim_stock` | Metadata cổ phiếu, sàn, ngành, shares outstanding |
| `dim_index` | Danh mục chỉ số thị trường |
| `fact_daily_price` | Stock Detail và Technical Signal Scanner |
| `fact_market_index` | Market Overview |
| `fact_news_sentiment_daily` | News & Sentiment |
| `fact_realtime_vwap` | Realtime VWAP Monitoring |
| `fact_alert_event` | Alert History |

## Cách chạy

Khởi động ClickHouse và Superset:

```bash
docker compose up -d clickhouse postgres superset
```

Kiểm tra cấu hình ở chế độ dry-run:

```bash
uv run python scripts/setup_superset_day22.py --dry-run
```

Tạo database connection và datasets trong Superset:

```bash
uv run python scripts/setup_superset_day22.py
```

Các biến môi trường có thể override:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `SUPERSET_URL` | `http://localhost:8088` | URL Superset API |
| `SUPERSET_USERNAME` | `admin` | Tài khoản admin Superset |
| `SUPERSET_PASSWORD` | `admin` | Mật khẩu admin Superset |
| `SUPERSET_CLICKHOUSE_SQLALCHEMY_URI` | `clickhousedb://default:clickhouse@clickhouse:8123/stock_lakehouse` | URI ClickHouse nhìn từ Superset container |
| `CLICKHOUSE_DATABASE` | `stock_lakehouse` | Schema/database chứa bảng Gold |

## Kiểm tra sau khi setup

Trong Superset UI:

1. Vào Data > Databases, kiểm tra database `ClickHouse Gold`.
2. Vào Data > Datasets, kiểm tra các dataset `dim_*` và `fact_*`.
3. Mở SQL Lab và chạy thử:

```sql
SELECT count()
FROM fact_daily_price;
```

4. Tạo chart thử từ `fact_market_index` hoặc `fact_daily_price`.

## Trạng thái

Ngày 22 hoàn thành ở mức Superset đọc được Gold Layer từ ClickHouse và có dataset nền tảng để triển khai dashboard các ngày 23-26.

Dashboard cụ thể như Market Overview, Stock Detail, Technical Signal Scanner và Data Pipeline Monitor thuộc phạm vi các ngày tiếp theo.
