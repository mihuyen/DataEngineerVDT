# Bronze Layer

Bronze là tầng lưu dữ liệu gần nguyên trạng nhất, chỉ thêm nguồn, thời điểm thu thập và khóa truy vết — chưa làm sạch nghiệp vụ. Phạm vi hiện tại: 404 mã HOSE (không gồm HNX/UPCOM), dữ liệu giá từ Vnstock (VCI), hồ sơ doanh nghiệp từ Vnstock (KBS), chỉ số thị trường, tin tức, và giao dịch DNSE.

## Nguyên tắc Bronze

- Lưu dữ liệu gần nhất với nguồn, chưa lọc nội dung.
- Không tính chỉ báo kỹ thuật.
- Chỉ validate tối thiểu: đọc được, đúng schema (tương ứng chiều Completeness).
- Giữ nguyên gốc để có thể chạy lại Silver bất kỳ lúc nào mà không cần gọi lại API nguồn (rate limit).
- Credential MinIO đọc từ environment, không hardcode trong code.

## Partition strategy — gộp theo ngày thu thập, không tách theo từng mã

```text
bronze/ohlcv/year=2026/month=07/day=10/data.parquet
```

**Quyết định thiết kế quan trọng**: toàn bộ 404 mã của 1 ngày thu thập nằm trong **1 file duy nhất** (`ticker` là 1 cột dữ liệu bên trong, không phải segment đường dẫn). Nếu tách theo từng mã (`ticker=VCB/year=.../...`) sẽ tạo ra hàng trăm file nhỏ mỗi ngày, gây tốn chi phí liệt kê và mở file trên MinIO.

`year/month/day` là **ngày thu thập (ingest)**, không nhất thiết là ngày giao dịch — trả lời câu hỏi "chu kỳ nào đã lấy dữ liệu này", phục vụ truy vết/replay.

Các dataset khác dùng partition tương tự, chỉ thêm cột phân biệt:

| Dataset | Path | Ghi chú |
|---|---|---|
| OHLCV | `ohlcv/year=/month=/day=/data.parquet` | `ticker` là cột |
| Chỉ số thị trường | `market_index/index_code=<CODE>/year=/month=/day=/data.parquet` | tách theo `index_code` vì số lượng chỉ số rất ít |
| Hồ sơ doanh nghiệp | `company_profile/dataset=listing\|profile/year=/month=/day=/data.parquet` | |
| Tin tức | `news/source=multi/year=/month=/day=/data.parquet` | nguồn báo là cột dữ liệu |
| DNSE (Realtime) | Ghi Parquet cục bộ, sao lưu lên MinIO Bronze theo khả năng | không chặn luồng Kafka/ClickHouse nếu MinIO lỗi tạm thời |

## Luồng ingest

```text
Vnstock/Nguồn báo/DNSE → DataFrame → Polars → Parquet → MinIO bucket bronze
```

## Module chính

- `src/ingestion/vnstock_ohlcv.py` — OHLCV từ Vnstock (VCI)
- `src/ingestion/market_news.py` — crawl tin tức
- `src/common/minio_client.py` — helper kết nối/upload MinIO
- `scripts/run_ohlcv_ingest.py`, `scripts/run_market_index_ingest.py`, `scripts/run_company_profile_ingest.py`, `scripts/run_news_ingest.py`

## Biến môi trường cần có

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

## Cách chạy (thủ công, ngoài Airflow)

```bash
docker compose up -d minio
uv run python scripts/run_ohlcv_ingest.py --tickers VCB ACB FPT   # thử vài mã
uv run python scripts/run_ohlcv_ingest.py                        # toàn bộ HOSE (đọc từ dim_stock/ClickHouse)
```

Bình thường luồng này chạy tự động qua DAG `stock_lakehouse_daily` (18:00 T2–T6), không cần chạy tay trừ khi debug hoặc bù dữ liệu bị lỡ.

## Kiểm thử

```bash
uv run pytest
```

## Hạn chế đã biết

- Không phải mã nào cũng có bản ghi mỗi ngày — mã vốn hóa nhỏ/thanh khoản thấp có thể không giao dịch, hoặc bị rate limit khi gọi API nguồn.
- Backfill lịch sử xa bị giới hạn bởi rate limit Vnstock.
