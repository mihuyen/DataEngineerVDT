# Gold Layer

Gold là tầng phục vụ truy vấn trong ClickHouse, tổ chức theo mô hình star schema — 4 bảng chiều, 9 bảng sự kiện (chi tiết đầy đủ tại `star_schema.md`). Gold là **điểm hội tụ của 3 luồng xử lý** (Batch, Tin tức, Realtime), mỗi luồng nạp Gold theo cách khác nhau.

## 3 cách nạp Gold, theo từng luồng

| Luồng | Công cụ nạp | Ghi chú |
|---|---|---|
| Batch | Python Gold Loader (`scripts/load_gold.py`) tính giá + EMA/MACD → dbt tính tiếp SMA/RSI/Bollinger | EMA đệ quy, ClickHouse SQL không tính hiệu quả được nên phải dùng Python; dbt tái sử dụng EMA đã tính, không tính lại |
| Tin tức | News Gold Loader (`src/loaders/load_fact_news_sentiment.py`), sau Entity Linking + PhoBERT | Có Sentiment Quality Gate chặn trước khi ghi |
| Realtime | ClickHouse tự ghi qua Kafka Engine + Materialized View | Không qua Python/dbt, không qua Silver |

## Lưu trữ

- **ClickHouse** — lớp phục vụ truy vấn chính cho toàn bộ 3 luồng.
- **MinIO** (`export_gold_to_minio.py`) — backup Parquet cho Batch và Tin tức, chạy 1 lần/ngày (nằm trong nhánh song song sau Reconciliation của DAG Batch). Luồng Tin tức không tự backup, mà "đi nhờ" export chung này. Riêng bảng dbt `fact_daily_price_indicators` **chưa** nằm trong danh sách export MinIO.
- Realtime (`fact_intraday_ohlcv`, `fact_realtime_vwap`) cũng nằm trong danh sách export MinIO, nhưng cũng chỉ theo nhịp 1 lần/ngày của Batch, không theo nhịp cập nhật liên tục thật của Realtime.

## Watermark & incremental load

Gold Loader (Batch) và dbt đều dùng watermark lùi **35 ngày** — đủ dư so với cửa sổ dài nhất cần dùng (EMA26), đồng thời chừa đệm cho ngày nghỉ lễ/dữ liệu tới trễ. ClickHouse phân vùng bảng sự kiện theo tháng, nên bộ nạp xác định tháng bị ảnh hưởng, xóa đúng phân vùng đó rồi chèn lại toàn bộ tháng (tránh mất dữ liệu đầu tháng nếu chỉ nạp phần sau watermark).

## Validate — 2 lớp tách biệt

**Lớp 1 — kiểm tra giá trị mới sinh ra, chạy trước khi ghi:**
- Batch: `dbt test` — RSI∈[0,100], MACD = EMA12−EMA26, Bollinger đúng thứ tự upper≥middle≥lower (`dbt/tests/*.sql`)
- Tin tức: Sentiment Quality Gate — `sentiment_score`∈[-1,1], `confidence_score`∈[0,1], nhãn hợp lệ, không trùng `(article_id, ticker)` (`src/quality/news_sentiment_expectations.py`)

**Lớp 2 — Reconciliation, đối soát liên tầng, chạy sau khi ghi** (`src/quality/reconciliation.py`):
- Batch (10 điều kiện — 5 loại kiểm tra × 2 domain OHLCV/Market Index): tỷ lệ giảm Bronze→Silver ≤5%, Silver→Gold khớp tuyệt đối (anti-join 2 chiều), không trùng khóa, freshness theo ngày làm việc.
- Tin tức (4 điều kiện): tỷ lệ giảm Bronze→Silver ≤5%, Gold không có bản ghi "mồ côi" so với Silver (không đòi khớp tuyệt đối vì Entity Linking chủ động lọc bài không thuộc HOSE), không trùng khóa `(article_id, ticker)`, freshness theo lịch dương.
- Realtime: không nằm trong Reconciliation — độ tin cậy đảm bảo qua cơ chế đối chiếu chéo khối lượng giữa nhánh trade tick và nhánh nến (`src/quality/realtime_expectations.py`).

Reconciliation chạy sau khi ghi (không thể chạy trước) vì nó kiểm tra chính kết quả của thao tác ghi, không kiểm tra dữ liệu đầu vào. Nếu fail: Airflow báo lỗi qua Telegram, chặn 5 nhánh song song phía sau — không có rollback tự động, dữ liệu đã ghi vẫn tồn tại, cần xử lý thủ công.

## Danh sách bảng

Xem chi tiết cột từng bảng tại `star_schema.md` và DDL thật tại `sql/ddl/*.sql` (Batch/Tin tức) + `sql/streaming/realtime_vwap_kafka_engine.sql` (Realtime).

| Bảng | Loại |
|---|---|
| `dim_date`, `dim_sector`, `dim_stock`, `dim_index` | Chiều |
| `fact_daily_price`, `fact_daily_price_indicators`, `fact_market_index` | Sự kiện — Batch |
| `fact_news_sentiment_detail`, `fact_news_sentiment_daily` | Sự kiện — Tin tức |
| `fact_intraday_ohlcv`, `fact_realtime_vwap` (view) | Sự kiện — Realtime |
| `fact_alert_event`, `fact_alert_rule_state` (trạng thái) | Cảnh báo |

## Script vận hành

```bash
# Tạo/cập nhật schema ClickHouse từ DDL
uv run python scripts/migrate_gold_schema.py

# Nạp Gold (Batch)
uv run python scripts/load_gold.py

# Đối soát liên tầng (Batch + Tin tức)
uv run python scripts/run_reconciliation_check.py

# dbt — tính chỉ báo còn lại + kiểm tra công thức
cd dbt && uv run dbt run --project-dir . --profiles-dir . && uv run dbt test --project-dir . --profiles-dir .

# Export Gold ra Parquet (MinIO)
uv run python scripts/export_gold_to_minio.py

# Backup toàn bộ (ClickHouse + PostgreSQL)
uv run python scripts/run_backup.py
```

## Nợ kỹ thuật đã biết

- `fact_daily_price` và `fact_daily_price_indicators` có nhiều cột chỉ báo tính trùng (SMA/RSI/Bollinger) — Python tính độc lập ở `fact_daily_price` nhưng không còn nơi nào đọc các cột đó nữa (StockDetail/StockScreener/Alert Engine đều đã chuyển sang đọc `fact_daily_price_indicators`, bảng có dbt test bảo vệ). Chưa dọn vì không gây sai dữ liệu, chỉ dư tính toán.
- Bảng dbt `fact_daily_price_indicators` chưa nằm trong danh sách export Parquet lên MinIO — chấp nhận được vì có thể tái tạo bất kỳ lúc nào bằng `dbt run` từ `fact_daily_price` (đã backup).
