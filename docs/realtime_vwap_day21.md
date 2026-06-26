# Ngày 21 - Realtime VWAP

## Mục tiêu

Ngày 21 xây dựng realtime VWAP cho Gold Layer.

Phạm vi hoàn thành:

- Có Kafka topic script cho realtime raw trades.
- Có SQL tham khảo cho ClickHouse Kafka Engine và Materialized View.
- Có demo dữ liệu giả lập trade ticks.
- Có loader tính VWAP theo phút và load vào `fact_realtime_vwap`.
- Có connector DNSE Market Data WebSocket thật cho dữ liệu khớp lệnh.

## Bảng Gold

```text
fact_realtime_vwap
```

Grain:

```text
1 ticker x 1 phút giao dịch
```

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trading_date)
ORDER BY (ticker, minute_ts)
```

## Công thức

```text
vwap_1m = total_value / total_volume
session_vwap = session_value / session_volume
price_vs_vwap_pct = (close_price - vwap_1m) / vwap_1m * 100
price_vs_session_vwap_pct = (close_price - session_vwap) / session_vwap * 100
```

## Demo giả lập

Module:

```text
src/loaders/load_fact_realtime_vwap.py
```

Script:

```text
scripts/load_realtime_vwap_demo.py
```

Chạy demo:

```bash
uv run python scripts/load_realtime_vwap_demo.py
```

Ví dụ tùy chỉnh:

```bash
uv run python scripts/load_realtime_vwap_demo.py --tickers ALL --minutes 10 --trades-per-minute 4
```

## DNSE WebSocket thật

DNSE Market Data WebSocket dùng:

```text
wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json
```

Channel khớp lệnh:

```text
tick.G1.json
```

Trong đó:

- `G1`: bảng lô chẵn.
- `json`: encoding dễ debug khi phát triển.
- Symbols phải viết hoa, ví dụ `VCB`, `FPT`, `HPG`.

Biến môi trường cần có:

```bash
export DNSE_API_KEY=...
export DNSE_API_SECRET=...
export DNSE_WS_SYMBOLS=ALL
```

Chạy lấy dữ liệu thật, lưu Bronze local:

```bash
uv run python scripts/run_dnse_realtime_ingest.py --symbols ALL --max-messages 100 --timeout-seconds 300
```

Chạy lấy dữ liệu thật và load vào `fact_realtime_vwap`:

```bash
uv run python scripts/run_dnse_realtime_ingest.py --symbols ALL --max-messages 100 --timeout-seconds 300 --load-vwap
```

Bronze local output:

```text
data/bronze_local/dnse/trades/year=YYYY/month=MM/day=DD/data.parquet
```

Module chính:

```text
src/streaming/dnse_websocket.py
```

Script:

```text
scripts/run_dnse_realtime_ingest.py
```

Connector hiện tập trung vào Trade tick để tính VWAP. DNSE cũng có channel order book/quotes:

```text
top_price.G1.json
```

TODO sau Ngày 21: mở rộng script để ingest quotes/order book riêng nếu dashboard cần độ sâu thị trường đầy đủ.

## Kafka topic

Script tạo topic:

```bash
uv run python scripts/create_realtime_kafka_topic.py
```

Nếu Kafka container chưa chạy:

```bash
docker compose up -d zookeeper kafka
```

Topic mặc định:

```text
dnse-trades-raw
```

## ClickHouse Kafka Engine

SQL tham khảo:

```text
sql/streaming/realtime_vwap_kafka_engine.sql
```

File này không nằm trong `sql/ddl/` để tránh làm hỏng batch migration khi Kafka chưa chạy. Khi triển khai streaming thật, apply thủ công sau khi Kafka đã sẵn sàng.

## Trạng thái

Ngày 21 hoàn thành ở hai mức:

- Demo realtime/VWAP bằng dữ liệu giả lập để kiểm thử end-to-end.
- Connector DNSE WebSocket thật sẵn sàng chạy khi có `DNSE_API_KEY` và `DNSE_API_SECRET`.

Giới hạn:

- Kafka Engine SQL hiện là bản tham khảo; demo chạy được bằng dữ liệu giả lập và load trực tiếp vào ClickHouse.
- `session_vwap` trong demo Python đã tính lũy kế theo phiên.
- Chưa chạy live DNSE nếu môi trường chưa có credential thật.
- Chưa ingest `top_price.G1.json` cho order book; hiện mới ingest Trade tick `tick.G1.json`.

## Nguồn tham chiếu

- DNSE Market Data WebSocket: https://developers.dnse.com.vn/docs/guide/market-data/connect/
- DNSE OpenAPI SDK: https://github.com/dnse-investment/dnse-openapi-sdk
