# Data Lakehouse — Theo dõi thị trường Chứng khoán Việt Nam (HOSE)

Nền tảng dữ liệu hợp nhất giá cổ phiếu, hồ sơ doanh nghiệp, chỉ số thị trường, tin tức và giao dịch trong phiên của 404 mã HOSE vào cùng một hệ thống — theo kiến trúc Lakehouse 3 tầng Bronze–Silver–Gold, kết hợp 3 luồng xử lý độc lập (batch, tin tức, thời gian thực), có kiểm soát chất lượng tích hợp xuyên suốt và cảnh báo tự động qua Telegram.

Người thực hiện: Bùi Huyền Mi · Mentor: Bùi Lê Huy

## Mục lục

- [Vấn đề & mục tiêu](#vấn-đề--mục-tiêu)
- [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
- [Nguồn dữ liệu](#nguồn-dữ-liệu)
- [Ba luồng xử lý](#ba-luồng-xử-lý)
- [Mô hình dữ liệu Gold (Star Schema)](#mô-hình-dữ-liệu-gold-star-schema)
- [Kiểm soát chất lượng dữ liệu](#kiểm-soát-chất-lượng-dữ-liệu)
- [Cảnh báo (Alert Engine)](#cảnh-báo-alert-engine)
- [Giám sát vận hành](#giám-sát-vận-hành)
- [Frontend & API](#frontend--api)
- [Mô hình NLP phân tích cảm xúc](#mô-hình-nlp-phân-tích-cảm-xúc)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Cài đặt & chạy thử](#cài-đặt--chạy-thử)
- [Kiểm thử](#kiểm-thử)
- [Hạn chế & hướng phát triển](#hạn-chế--hướng-phát-triển)

## Vấn đề & mục tiêu

Dữ liệu thị trường chứng khoán có nhiều nhịp cập nhật khác nhau: giá và chỉ báo kỹ thuật theo phiên, hồ sơ doanh nghiệp thay đổi chậm, tin tức phát sinh trong ngày, còn giao dịch khớp lệnh và nến phút phát sinh liên tục trong giờ giao dịch. Dữ liệu cũng phân mảnh trên nhiều nguồn, và thiếu cơ chế cảnh báo chủ động khi thị trường biến động.

4 mục tiêu chính:

1. **Hợp nhất & chuẩn hóa** — gộp dữ liệu đa nguồn qua 3 tầng Bronze–Silver–Gold.
2. **Tách biệt xử lý** — 3 luồng độc lập theo đúng nhịp cập nhật của từng loại dữ liệu.
3. **Kiểm soát chất lượng** — validate tích hợp ở mọi bước, đối soát tự động liên tầng.
4. **Truy vấn & phục vụ** — tối ưu cho ClickHouse, dashboard React/FastAPI và cảnh báo Telegram.

## Kiến trúc tổng quan

```
                         ┌────────────────────────────┐
Vnstock (KBS/VCI) ──┐    │   MinIO (Bronze→Silver→Gold) │
CafeF/Vietstock/    ├───▶│         Data Lake            │──▶ ClickHouse ──▶ FastAPI/React
VnExpress            │    └────────────────────────────┘         │
                      │                                            ├──▶ Alert Engine ──▶ Telegram
DNSE WebSocket ───────┴──▶ Kafka ──▶ ClickHouse (Kafka Engine + MV)│
                                                                    └──▶ PostgreSQL (watchlist/rule)
```

Airflow điều phối 2 DAG (batch hằng ngày, tin tức mỗi 5 phút). Luồng Realtime ghi thẳng vào ClickHouse qua Kafka Engine, bỏ qua Silver để giữ độ trễ thấp.

## Nguồn dữ liệu

| Nguồn | Dữ liệu | Nhịp cập nhật |
|---|---|---|
| Vnstock (KBS) | Danh sách mã HOSE, hồ sơ doanh nghiệp | Sau giờ giao dịch |
| Vnstock (VCI) | OHLCV ngày, VNINDEX/VN30 | Sau giờ giao dịch |
| VnExpress, Vietstock, CafeF | Tin tức tài chính | Crawl mỗi 5 phút |
| DNSE WebSocket | Giao dịch khớp lệnh, nến 1 phút | Liên tục trong phiên |

## Ba luồng xử lý

### 1. Luồng theo lô (Batch) — DAG `stock_lakehouse_daily`, chạy 18:00 T2–T6

```
Ingest song song (OHLCV, listing HOSE, VNINDEX/VN30) → Bronze
  → Silver Transform (Polars) → Quality Gate
  → Gold Loader (giá + EMA) → ClickHouse/MinIO
  → Reconciliation (đối soát liên tầng, 10 điều kiện)
  → 5 nhánh song song: dbt (SMA/RSI/Bollinger/MACD + dbt test)
                         · export Gold → MinIO
                         · Alert Engine (init + check)
                         · backup toàn bộ lakehouse (ClickHouse + PostgreSQL)
                         · backfill nến phút còn thiếu (Vnstock)
```

### 2. Luồng tin tức — DAG `news_crawl_5m`, chạy mỗi 5 phút, 24/7

```
Crawl (VnExpress/Vietstock/CafeF) → Bronze
  → Silver Transform → News Quality Gate
  → Entity Linking (gán ticker HOSE) → PhoBERT (phân tích cảm xúc)
  → Sentiment Quality Gate → News Gold Loader → ClickHouse
  → Reconciliation (kiểu "không mồ côi", 4 điều kiện)
```

### 3. Luồng thời gian thực — bỏ qua Silver, ghi thẳng ClickHouse

- **Nhánh trade tick**: DNSE → chuẩn hóa → Kafka → ClickHouse (Kafka Engine + Materialized View) → gộp theo phút (`AggregatingMergeTree`) → VWAP phút/phiên.
- **Nhánh nến 1 phút**: DNSE → chuẩn hóa → ghi thẳng `fact_intraday_ohlcv` (`ReplacingMergeTree`, tự ghi đè khi có nến hiệu chỉnh).
- 2 nhánh đối chiếu chéo khối lượng để phát hiện rớt kết nối WebSocket (`expect_vwap_volume_matches_intraday_volume`, ngưỡng lệch 15%).

## Mô hình dữ liệu Gold (Star Schema)

**4 bảng chiều**: `dim_date`, `dim_stock`, `dim_sector`, `dim_index`

**Bảng sự kiện**: `fact_daily_price`, `fact_daily_price_indicators` (dbt), `fact_market_index`, `fact_news_sentiment_daily`, `fact_news_sentiment_detail`, `fact_intraday_ohlcv`, `fact_realtime_vwap` (view), `fact_alert_event`, `fact_alert_rule_state`

DDL đầy đủ tại `sql/ddl/`, luồng streaming tại `sql/streaming/realtime_vwap_kafka_engine.sql`.

## Kiểm soát chất lượng dữ liệu

Tích hợp xuyên suốt từng bước, không phải 1 cổng chặn duy nhất:

| Tầng | Kiểm tra | Chặn nếu fail |
|---|---|---|
| Bronze | Schema, đọc được | Không |
| Silver | Completeness, Validity, Uniqueness (Quality Gate) | Có — không công bố sang Gold |
| Gold (giá trị) | dbt test: RSI∈[0,100], MACD đúng công thức, Bollinger đúng thứ tự / Sentiment Quality Gate: score∈[-1,1], confidence∈[0,1] | Có — không ghi ClickHouse |
| Gold (liên tầng) | Reconciliation: tỷ lệ giảm Bronze→Silver ≤5%, Silver→Gold khớp tuyệt đối (Batch) hoặc không "mồ côi" (Tin tức), không trùng khóa, freshness | Chặn 5 nhánh song song phía sau, không rollback tự động |
| Realtime | Đối chiếu chéo tick–nến, giờ giao dịch hợp lệ, độ phủ HOSE | Chẩn đoán, không chặn công bố |

Chạy đối soát thủ công: `uv run python scripts/run_reconciliation_check.py`

## Cảnh báo (Alert Engine)

- Cấu hình theo người dùng lưu ở PostgreSQL (`watchlist`, `user_alerts`).
- **14 loại quy tắc**: giá trên/dưới ngưỡng, RSI, phá dải Bollinger, độ lệch VWAP, tăng vọt khối lượng, phá vùng trong phiên, cắt lỗ/chốt lời và 4 điều kiện cắt ngưỡng.
- 2 hành vi: **cảnh báo tĩnh** (gửi lại mỗi cooldown) vs **cắt ngưỡng** (chỉ gửi đúng khoảnh khắc vượt ngưỡng).
- Đọc chỉ báo từ `fact_daily_price_indicators` (đã qua dbt test), không dùng bản Python độc lập trong `fact_daily_price`.
- Gửi qua Telegram, ghi log `fact_alert_event` với trạng thái `sent`/`send_failed`/`channel_not_configured`/`unknown_channel`.

## Giám sát vận hành

3 nguồn cảnh báo độc lập, cùng gửi về 1 kênh Telegram:

- **Grafana** — giám sát hạ tầng, đọc độc lập từ ClickHouse/Postgres (không phụ thuộc Airflow còn sống hay không) — lưới an toàn cuối cùng.
- **Airflow** — callback tự động khi task hết retry hoặc DAG hoàn tất — phát hiện nhanh, chi tiết đến từng task.
- **Alert Engine** — cảnh báo nghiệp vụ theo rule người dùng.

## Frontend & API

React (Vite) + FastAPI, các trang chính: Tổng quan thị trường, Bảng giá & Watchlist, Chi tiết cổ phiếu (nến ngày/nến trong phiên 1m–1h), Bộ lọc tín hiệu kỹ thuật, Tin tức & cảm xúc, Lịch sử cảnh báo, Giám sát pipeline. API trả kèm `dataMode`/`isRealtime`/`liveAsOf` để phân biệt dữ liệu cuối ngày với dữ liệu đang cập nhật.

## Mô hình NLP phân tích cảm xúc

Fine-tune PhoBERT (`vinai/phobert-base-v2`) trên dữ liệu tài chính tiếng Việt, 3 lớp positive/negative/neutral:

- **Gán nhãn train**: kết hợp LLM (Gemini/DeepSeek/GPT-4o-mini) và model PhoBERT có sẵn đối chiếu với từ điển từ khóa tài chính — chỉ giữ mẫu 2 nguồn đồng thuận để giảm nhiễu.
- **Train**: Focal Loss, oversampling lớp hiếm, đánh giá bằng accuracy ≥0.80 và macro F1 ≥0.78 trên tập test tách riêng.
- **Serving**: model đẩy lên Hugging Face Hub (`mihuyen/VDT2026-sentiment`), `nlp-service` tải về và suy luận cục bộ — không gọi API ngoài lúc chạy thật. Có fallback luật đơn giản nếu tải model lỗi, và pipeline từ chối công bố kết quả từ fallback.

Chi tiết tại `nlp/`.

## Công nghệ sử dụng

| Nhóm | Công nghệ |
|---|---|
| Lưu trữ | MinIO (Parquet), ClickHouse, PostgreSQL |
| Điều phối | Apache Airflow |
| Streaming | Apache Kafka, ClickHouse Kafka Engine |
| Transform | Polars, dbt |
| NLP | PhoBERT (fine-tuned), Hugging Face Transformers |
| Phục vụ | FastAPI, React (Vite) |
| Cảnh báo & giám sát | Telegram Bot API, Grafana |
| Ngôn ngữ/Build | Python, uv, TypeScript |

## Cấu trúc thư mục

```text
DataEngineerVDT/
├── src/               # ingestion, transform, loaders, quality, alert_engine, api, streaming
├── dags/              # Airflow DAG: stock_lakehouse_daily, news_crawl_5m
├── dbt/               # models (marts) + tests (RSI/MACD/Bollinger)
├── sql/               # ddl/ (Gold), streaming/ (Kafka Engine + MV), ddl_postgres/
├── nlp/                # train/evaluate PhoBERT, serving (FastAPI), data_preparation
├── frontend/           # React + Vite dashboard
├── services/           # alert-engine, vwap-consumer, dnse-producer (container riêng)
├── scripts/            # entrypoint CLI cho từng bước pipeline (46 script)
├── docker/             # provisioning Grafana
├── tests/              # pytest (231 test)
├── docs/               # tài liệu chi tiết từng tầng/luồng
└── docker-compose.yml
```

## Cài đặt & chạy thử

### Yêu cầu

- `uv` (Python package manager), Docker + Docker Compose
- File `.env` (copy từ `.env.example`, điền `HF_TOKEN`/`DNSE_API_KEY` nếu cần)

### Khởi động hạ tầng

```bash
docker compose up -d
```

Gồm: MinIO, ClickHouse, PostgreSQL, Kafka/ZooKeeper, Airflow (webserver+scheduler), NLP service, Alert Engine, DNSE producer/consumer, Grafana, Superset.

### Cài dependency & chạy pipeline lần đầu

```bash
uv sync
uv run python scripts/migrate_gold_schema.py     # tạo schema ClickHouse
uv run python scripts/load_gold.py                # nạp Gold từ Silver (cần Bronze/Silver có dữ liệu trước)
uv run python scripts/run_reconciliation_check.py # đối soát liên tầng
cd dbt && uv run dbt run && uv run dbt test        # chỉ báo kỹ thuật + kiểm tra công thức
```

### Chạy frontend cục bộ

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Chạy API cục bộ (ngoài Docker, cho hot-reload)

```bash
uv run uvicorn src.api.dashboard_api:app --host 0.0.0.0 --port 8000
```

Airflow UI: `http://localhost:8080` · Grafana: `http://localhost:3000` · MinIO Console: `http://localhost:9001`

## Kiểm thử

```bash
uv run pytest                    # 231 test (unit, không cần Docker chạy)
cd dbt && uv run dbt test        # 5 test SQL trên ClickHouse thật
```

## Hạn chế & hướng phát triển

**Hạn chế đã biết:**
- Chiều sâu lịch sử chưa đồng đều giữa các mã, backfill bị giới hạn bởi rate limit nguồn.
- ClickHouse chỉ giữ dữ liệu realtime 30 ngày (TTL); có backup Parquet nhưng chưa có luồng khôi phục tự động.
- Mô hình cảm xúc chưa được đánh giá trên tập nhãn tài chính tiếng Việt gán tay quy mô lớn.
- Chưa có Accuracy (theo DAMA-DMBOK) do thiếu nguồn tham chiếu giá độc lập bên ngoài.
- Phù hợp môi trường một người dùng: API chưa xác thực, một số image Docker còn dùng tag `latest`.

**Hướng phát triển:**
- Apache Iceberg cho quản lý phiên bản bảng, giảm vấn đề file nhỏ trên MinIO.
- OpenMetadata/DataHub cho danh mục và dòng dõi dữ liệu khi số bảng tăng.
- OpenTelemetry + Grafana Tempo cho distributed tracing xuyên suốt WebSocket→Kafka→ClickHouse.
- Giám sát Data/Model Drift cho pipeline NLP.
