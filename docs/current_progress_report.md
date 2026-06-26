# Báo cáo tiến độ chi tiết - DataEngineerVDT

Ngày cập nhật: 2026-06-20

## 1. Tổng quan hiện trạng

Dự án DataEngineerVDT đang xây dựng hệ thống Data Lakehouse phục vụ theo dõi và phân tích thị trường chứng khoán Việt Nam. Kiến trúc chính là Medallion Architecture gồm Bronze, Silver và Gold Layer, kết hợp batch pipeline, realtime pipeline, ClickHouse serving layer, FastAPI backend và React dashboard frontend.

Tính đến hiện tại, project đã hoàn thành được một luồng end-to-end local tương đối đầy đủ:

```text
Nguồn dữ liệu -> Bronze -> Silver -> Gold ClickHouse -> API -> Frontend dashboard
```

Các service local chính đã chạy được:

- ClickHouse cho Gold Layer và dashboard query.
- MinIO/object storage theo thiết kế.
- Airflow cho orchestration.
- Kafka/Zookeeper cho hướng realtime.
- FastAPI backend tại `http://localhost:8000`.
- React/Vite frontend tại `http://localhost:5173`.

Snapshot ClickHouse hiện tại:

| Bảng | Trạng thái hiện tại |
| --- | --- |
| `dim_stock` | 1.531 mã |
| `dim_sector` | 31 ngành/nhóm |
| `dim_index` | 4 chỉ số |
| `fact_daily_price` | 40.530 dòng, 1.530 mã, từ 2024-06-24 đến 2026-06-19 |
| `fact_market_index` | 112 dòng, 4 chỉ số, từ 2026-05-13 đến 2026-06-19 |
| `fact_news_sentiment_daily` | 144 dòng, 104 mã, từ 2026-06-12 đến 2026-06-14 |
| `fact_realtime_vwap` | 15.310 dòng, 1.531 mã, từ 09:15 đến 09:24 ngày 2026-06-20 |
| `fact_alert_event` | 0 dòng, mới có schema/chưa vận hành alert thật |

## 2. Luồng dữ liệu OHLCV cổ phiếu

### Mục tiêu luồng

Luồng OHLCV là luồng dữ liệu lõi của project. Dữ liệu này dùng cho biểu đồ giá, chỉ báo kỹ thuật, scanner tín hiệu, tính vốn hóa, market breadth và một phần dashboard tổng quan.

Grain cuối cùng:

```text
1 mã cổ phiếu x 1 ngày giao dịch
```

### Nguồn dữ liệu

- Nguồn chính: `vnstock`.
- Dữ liệu lấy gồm open, high, low, close, volume và ngày giao dịch.

### Bronze

Đã hoàn thành ingest dữ liệu OHLCV thô.

Module/script liên quan:

- `src/ingestion/vnstock_ohlcv.py`
- `scripts/run_ohlcv_ingest.py`

Bronze lưu theo mã và ngày, ví dụ:

```text
bronze/ohlcv/ticker=<TICKER>/year=<YYYY>/month=<MM>/day=<DD>/data.parquet
```

Trạng thái:

- Đã có luồng ingest theo nhiều mã.
- Đã có test cho ingestion và MinIO/client helper.
- Một số mã có thể thiếu dữ liệu do nguồn không trả ổn định hoặc mã ít thanh khoản.

### Silver

Đã hoàn thành transform OHLCV sang dữ liệu sạch.

Module/script:

- `src/transform/ohlcv_transform.py`
- `scripts/run_silver_transform.py`
- `src/quality/ohlcv_expectations.py`
- `scripts/run_quality_check.py`

Các xử lý đã có:

- Chuẩn hóa ticker viết hoa.
- Chuẩn hóa kiểu dữ liệu ngày, giá, volume.
- Loại hoặc phát hiện bản ghi không hợp lệ.
- Kiểm tra giá âm, volume âm.
- Kiểm tra `high >= low`.
- Kiểm tra duplicate theo ticker/ngày.

### Gold

Đã hoàn thành bảng `fact_daily_price` trong ClickHouse.

DDL:

- `sql/ddl/fact_daily_price.sql`

Loader:

- `src/loaders/load_fact_daily_price.py`

Các trường đã có:

- OHLCV cơ bản.
- `shares_outstanding`
- `market_cap`
- `price_change`
- `pct_change`
- `sma_20`
- `ema_12`
- `ema_26`
- `macd`
- `macd_signal`
- `rsi_14`
- Bollinger Bands.
- Cờ overbought/oversold/breakout/breakdown.

Trạng thái hiện tại trong ClickHouse:

```text
fact_daily_price: 40.530 dòng
Số mã: 1.530
Khoảng ngày: 2024-06-24 -> 2026-06-19
```

### Dashboard sử dụng

Luồng này đang phục vụ các màn:

- Tổng quan thị trường.
- Chi tiết cổ phiếu.
- Tín hiệu kỹ thuật.

### Việc còn lại

- Tăng độ dài lịch sử giá cho từng mã nếu cần phân tích dài hạn.
- Bổ sung retry/backoff khi nguồn `vnstock` lỗi.
- Chuẩn hóa lại coverage report để biết mã nào còn thiếu OHLCV.
- Có thể thêm adjusted price nếu nguồn hỗ trợ.

## 3. Luồng dữ liệu Company Profile và danh mục mã

### Mục tiêu luồng

Luồng company profile dùng để xây dựng dimension cổ phiếu, phân loại ngành, sàn giao dịch, tên doanh nghiệp và các trường phục vụ join với fact table.

Grain cuối cùng:

```text
1 mã cổ phiếu x 1 bản ghi dimension
```

### Nguồn dữ liệu

- Listing và thông tin doanh nghiệp từ nguồn dữ liệu chứng khoán.
- Các trường chính gồm ticker, company name, exchange, sector, shares outstanding, market cap, website, business model.

### Bronze

Đã hoàn thành ingest company listing và company profile.

Module/script:

- `src/ingestion/company_profile.py`
- `scripts/run_company_profile_ingest.py`

Trạng thái đã đạt:

- Universe hiện tại có 1.531 mã.
- Phân bổ sàn trong `dim_stock`:
  - HOSE: 403 mã.
  - HNX: 300 mã.
  - UPCOM: 828 mã.

### Silver

Đã hoàn thành chuẩn hóa company profile.

Module/script:

- `src/transform/company_profile_transform.py`
- `scripts/run_company_profile_silver.py`

Các xử lý đã có:

- Chuẩn hóa ticker.
- Chuẩn hóa tên công ty.
- Chuẩn hóa exchange.
- Chuẩn hóa sector.
- Chuẩn hóa shares outstanding và market cap.

### Gold

Đã hoàn thành các bảng dimension:

- `dim_stock`
- `dim_sector`

Trạng thái hiện tại:

```text
dim_stock: 1.531 mã
dim_sector: 31 nhóm
```

### Dashboard sử dụng

Luồng này phục vụ join metadata cho gần như toàn bộ dashboard:

- Tên công ty trong màn Stock Detail.
- Ngành/sàn trong Market Overview.
- Bộ lọc ngành/sàn trong VWAP.
- Join news sentiment theo mã.

### Việc còn lại

- Kiểm tra lại chất lượng mapping ngành.
- Chuẩn hóa tên ngành tiếng Việt/tiếng Anh nếu cần báo cáo song ngữ.
- Bổ sung nguồn chính thức cho danh sách VN30 constituents.

## 4. Luồng dữ liệu Market Index

### Mục tiêu luồng

Luồng market index phục vụ theo dõi chỉ số thị trường và market breadth.

Grain cuối cùng:

```text
1 chỉ số x 1 ngày giao dịch
```

Các chỉ số hiện có:

- `VNINDEX`
- `VN30`
- `HNXINDEX`
- `UPCOMINDEX`

### Bronze

Đã hoàn thành ingest dữ liệu chỉ số thị trường.

Module/script:

- `src/ingestion/market_index.py`
- `scripts/run_market_index_ingest.py`

### Silver

Đã hoàn thành chuẩn hóa dữ liệu chỉ số.

Module/script:

- `src/transform/market_index_transform.py`
- `scripts/run_market_index_silver.py`

Các xử lý đã có:

- Chuẩn hóa mã chỉ số.
- Chuẩn hóa ngày giao dịch.
- Chuẩn hóa open/high/low/close điểm số.
- Chuẩn hóa volume/value nếu có.

### Gold

Đã hoàn thành:

- `dim_index`
- `fact_market_index`

Bảng `fact_market_index` có thêm market breadth:

- `advance_count`
- `decline_count`
- `unchanged_count`
- `advance_decline_ratio`
- `sma_20`
- `rsi_14`

Trạng thái hiện tại:

```text
dim_index: 4 chỉ số
fact_market_index: 112 dòng
Mỗi chỉ số: 28 dòng
Khoảng ngày: 2026-05-13 -> 2026-06-19
```

### Dashboard sử dụng

Luồng này phục vụ:

- Tổng quan thị trường.
- KPI chỉ số.
- Market breadth.
- Bối cảnh chung cho scanner và alert.

### Việc còn lại

- Mở rộng lịch sử index nếu cần backtest hoặc phân tích dài hơn.
- Thay logic VN30 demo bằng danh sách VN30 chính thức.
- Bổ sung kiểm tra chất lượng riêng cho breadth.

## 5. Luồng dữ liệu News và Sentiment

### Mục tiêu luồng

Luồng news dùng để thu thập tin tức thị trường, gắn tin với mã cổ phiếu và tổng hợp sentiment theo ngày.

Grain Gold cuối cùng:

```text
1 mã cổ phiếu x 1 ngày tin tức
```

### Bronze

Đã hoàn thành crawler batch cho tin tức.

Module/script:

- `src/ingestion/market_news.py`
- `scripts/run_news_ingest.py`

Nguồn hiện tại:

- VnExpress.
- Vietstock.
- CafeF.

### Silver

Đã hoàn thành transform news.

Module/script:

- `src/transform/news_transform.py`
- `scripts/run_news_silver.py`

Các xử lý đã có:

- Chuẩn hóa URL.
- Chuẩn hóa title.
- Chuẩn hóa source.
- Chuẩn hóa published date.
- Loại trùng theo URL.

### Entity Linking

Đã hoàn thành bước gắn tin tức với mã cổ phiếu.

Module/script:

- `src/transform/news_entity_linking.py`
- `scripts/run_news_entity_linking.py`

Logic hiện tại:

- Match ticker hoặc alias doanh nghiệp trong tiêu đề/nội dung.
- Sinh `match_score` và `matched_alias`.

### Gold

Đã hoàn thành bảng:

- `fact_news_sentiment_daily`

Sentiment hiện là rule-based tiếng Việt:

- Từ tích cực: tăng, lợi nhuận, tăng trưởng, khởi sắc, vượt kế hoạch...
- Từ tiêu cực: giảm, lỗ, khởi tố, cảnh báo, nợ xấu, rủi ro...

Trạng thái hiện tại:

```text
fact_news_sentiment_daily: 144 dòng
Số mã có sentiment: 104
Khoảng ngày: 2026-06-12 -> 2026-06-14
```

### Dashboard sử dụng

Luồng này phục vụ:

- Màn Tin tức & cảm xúc.
- Sentiment theo mã.
- Top headline theo ticker/ngày.

### Việc còn lại

- Sentiment hiện mới là rule-based, chưa phải NLP model chuyên sâu.
- Entity linking có thể sai nếu tên công ty viết tắt hoặc tiêu đề không nhắc rõ mã.
- Cần mở rộng nguồn tin và lịch crawl.
- Có thể dùng mô hình tiếng Việt để sentiment chính xác hơn.

## 6. Luồng dữ liệu Realtime DNSE và VWAP

### Mục tiêu luồng

Luồng realtime dùng DNSE WebSocket để lấy trade tick và tính VWAP theo phút/session.

Grain Gold:

```text
1 mã cổ phiếu x 1 phút giao dịch
```

### Nguồn dữ liệu

Nguồn chính:

```text
DNSE Market Data WebSocket
```

Endpoint:

```text
wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json
```

Channel hiện dùng:

```text
tick.G1.json
```

### Ingest

Đã hoàn thành connector DNSE WebSocket.

Module/script:

- `src/streaming/dnse_websocket.py`
- `scripts/run_dnse_realtime_ingest.py`

Các việc đã làm:

- Tạo auth message bằng HMAC-SHA256.
- Sửa timestamp auth theo SDK DNSE hiện tại: dùng giây, không dùng milliseconds.
- Parse trade tick thành schema nội bộ:
  - `ticker`
  - `trade_ts`
  - `price`
  - `volume`
  - `raw_json`
- Hỗ trợ `DNSE_WS_SYMBOLS=ALL`.
- Khi `ALL`, script lấy toàn bộ mã từ `dim_stock`.

### Bronze realtime

Đã có output local cho DNSE trades:

```text
data/bronze_local/dnse/trades/year=YYYY/month=MM/day=DD/data.parquet
```

Hiện tại do test ngoài phiên/cuối tuần nên DNSE auth được nhưng chưa có tick live mới.

### Gold VWAP

Đã hoàn thành bảng:

- `fact_realtime_vwap`

Module/script:

- `src/loaders/load_fact_realtime_vwap.py`
- `scripts/load_realtime_vwap_demo.py`

Các chỉ số đã tính:

- `vwap_1m`
- `session_vwap`
- `price_vs_vwap_pct`
- `price_vs_session_vwap_pct`
- `session_volume`
- `session_value`

Trạng thái hiện tại:

```text
fact_realtime_vwap: 15.310 dòng
Số mã: 1.531
Khoảng phút: 2026-06-20 09:15 -> 2026-06-20 09:24
```

Lưu ý: dữ liệu hiện tại là demo VWAP đã nạp đủ 1.531 mã để kiểm thử dashboard. DNSE live cần chạy trong giờ giao dịch để có tick thật.

### Kafka/ClickHouse Streaming

Đã có phần chuẩn bị cho streaming thật:

- Script tạo Kafka topic `dnse-trades-raw`.
- SQL tham khảo cho ClickHouse Kafka Engine.
- Materialized View tham khảo để ghi vào bảng realtime.

File liên quan:

- `scripts/create_realtime_kafka_topic.py`
- `sql/streaming/realtime_vwap_kafka_engine.sql`

Trạng thái:

- Đã có thiết kế và script tham khảo.
- Chưa vận hành realtime production liên tục qua Kafka Engine.
- Hiện demo load trực tiếp vào ClickHouse để kiểm dashboard end-to-end.

### Dashboard sử dụng

Luồng này phục vụ màn:

- Theo dõi VWAP realtime.

API frontend đang đọc:

```text
/api/realtime/vwap
/api/realtime/vwap/{ticker}/series
```

Hiện API trả đủ:

```text
Frontend VWAP API: 1.531 mã
```

### Việc còn lại

- Chạy DNSE live trong giờ giao dịch thật.
- Chuyển từ demo load sang append/incremental live load.
- Hoàn thiện DNSE -> Kafka -> ClickHouse flow.
- Ingest thêm `top_price.G1.json` nếu cần order book/bid-ask.
- Thêm trạng thái trên frontend để phân biệt demo data và live data.

## 7. Luồng Alert Engine

### Mục tiêu luồng

Alert Engine dùng để phát hiện điều kiện bất thường như:

- Giá lệch VWAP mạnh.
- Volume spike.
- Breakout/breakdown.
- RSI quá mua/quá bán.
- Tin tức tiêu cực liên quan mã cổ phiếu.

### Trạng thái hiện tại

Đã có bảng Gold:

- `fact_alert_event`

Trạng thái dữ liệu:

```text
fact_alert_event: 0 dòng
```

Điều này nghĩa là schema đã có nhưng logic alert thật chưa vận hành.

### Dashboard sử dụng

Frontend đã có màn:

- Lịch sử cảnh báo.

Nhưng dữ liệu alert hiện chưa phát sinh thật.

### Việc còn lại

- Xây bảng cấu hình rule.
- Tạo job kiểm tra điều kiện alert.
- Ghi event vào `fact_alert_event`.
- Thêm cooldown để tránh spam.
- Kết nối Telegram hoặc email notification.

## 8. Luồng API và Frontend Dashboard

### Backend API

Đã hoàn thành FastAPI backend đọc từ ClickHouse.

File chính:

- `src/api/dashboard_api.py`

Endpoint đã có:

- `/api/health`
- `/api/stocks`
- `/api/stocks/{ticker}/candles`
- `/api/realtime/vwap`
- `/api/realtime/vwap/{ticker}/series`

Trạng thái:

- API chạy tại `http://localhost:8000`.
- API health trả được latest date và latest realtime minute.
- API VWAP trả được 1.531 mã.

### Frontend

Đã hoàn thành dashboard React/Vite với các màn:

- Tổng quan thị trường.
- Chi tiết cổ phiếu.
- Tín hiệu kỹ thuật.
- Giám sát pipeline.
- Theo dõi VWAP realtime.
- Tin tức & cảm xúc.
- Lịch sử cảnh báo.

File chính:

- `frontend/app/App.tsx`
- `frontend/app/components/RealtimeVWAP.tsx`
- `frontend/app/components/MarketOverview.tsx`
- `frontend/app/components/StockDetail.tsx`
- `frontend/app/components/api.ts`

Trạng thái:

- Frontend chạy tại `http://localhost:5173`.
- Vite proxy `/api` sang backend `localhost:8000`.
- Màn VWAP đã bỏ giới hạn 200 mã và có thể hiển thị toàn bộ 1.531 mã.

### Việc còn lại

- Tối ưu UI cho danh sách lớn bằng virtualized list nếu cần.
- Thêm loading/error state rõ hơn.
- Thêm nhãn demo/live data.
- Kết nối thêm API cho news, alerts và pipeline nếu hiện còn dùng mock/snapshot.

## 9. Orchestration, kiểm thử và vận hành local

### Airflow

Đã có DAG:

- `stock_lakehouse_daily`

Vai trò:

- Orchestrate ingest.
- Transform.
- Quality check.
- Load Gold.
- Trigger các bước batch chính.

Trạng thái:

- Airflow chạy được trong Docker local.
- Có tài liệu local autostart.
- Có script start/stop local stack.

### Test

Project đã có nhiều nhóm test:

- Test cấu trúc project.
- Test Docker compose.
- Test MinIO client.
- Test ingestion.
- Test transform.
- Test quality.
- Test ClickHouse schema.
- Test Gold loader.
- Test dbt model.
- Test DNSE WebSocket auth/parser.
- Test realtime VWAP aggregation.

Test gần nhất đã chạy:

```text
11 passed
```

### Việc còn lại

- Tạo một lệnh smoke test end-to-end gọn.
- Dọn các file runtime như `__pycache__`, `.pids`, `logs` khỏi git status nếu cần.
- Chuẩn hóa hướng dẫn chạy từ máy mới.

## 10. Khó khăn đã gặp và cách xử lý

### 10.1. Khác biệt Windows và WSL

Khó khăn:

- `npm` bị trỏ sang Windows/CMD khi chạy trong WSL.
- Vite lỗi UNC path và không nhận `vite`.

Cách xử lý:

- Dùng Node local trong `.node/bin`.
- Ưu tiên chạy toàn bộ project trong WSL/Linux.
- Start frontend bằng PATH local.

### 10.2. DNSE auth bị đóng kết nối

Khó khăn:

- WebSocket đóng ngay sau auth.
- Không có lỗi JSON rõ ràng.

Nguyên nhân:

- Code cũ dùng timestamp milliseconds.
- SDK DNSE hiện dùng timestamp seconds.

Cách xử lý:

- Đối chiếu SDK DNSE.
- Sửa `create_auth_message`.
- Thêm test để đảm bảo timestamp mặc định là 10 chữ số.

### 10.3. Realtime phụ thuộc giờ giao dịch

Khó khăn:

- Ngoài phiên giao dịch hoặc cuối tuần không có tick realtime.

Cách xử lý:

- Tách demo VWAP và DNSE live.
- Dùng demo để kiểm dashboard.
- Chạy DNSE live trong phiên thật để lấy tick.

### 10.4. Ban đầu chỉ có 3 mã VWAP

Khó khăn:

- Config demo chỉ dùng `VCB,FPT,HPG`.
- Frontend có giới hạn render 200 dòng.

Cách xử lý:

- Đổi sang `DNSE_WS_SYMBOLS=ALL`.
- Sửa ingest để lấy mã từ `dim_stock`.
- Sửa demo loader để nạp 1.531 mã.
- Bỏ giới hạn render 200 mã.

### 10.5. Dữ liệu nhiều nguồn không đồng nhất

Khó khăn:

- Nguồn có thể thiếu dữ liệu, đổi schema hoặc giới hạn request.
- Entity linking tin tức có thể sai nếu tên công ty không rõ.

Cách xử lý:

- Tách Bronze/Silver/Gold để dễ debug.
- Thêm test chất lượng dữ liệu.
- Giữ raw data để có thể transform lại.

## 11. Bước tiếp theo đề xuất

### Ưu tiên 1: Chạy realtime thật trong phiên giao dịch

- Chạy DNSE live trong giờ giao dịch.
- Ghi tick thật vào Bronze.
- Load tick thật vào `fact_realtime_vwap`.
- Kiểm tra frontend VWAP cập nhật theo dữ liệu live.

### Ưu tiên 2: Hoàn thiện streaming production

- Đưa DNSE trade tick vào Kafka topic `dnse-trades-raw`.
- Apply ClickHouse Kafka Engine.
- Hoàn thiện Materialized View.
- Chuyển VWAP sang incremental/live aggregation.

### Ưu tiên 3: Hoàn thiện dashboard

- Thêm nhãn demo/live.
- Thêm freshness timestamp.
- Hoàn thiện màn alert.
- Hoàn thiện màn news sentiment nếu còn dùng snapshot/mock.
- Tối ưu render danh sách lớn.

### Ưu tiên 4: Hoàn thiện Alert Engine

- Định nghĩa alert rules.
- Ghi `fact_alert_event`.
- Thêm notification Telegram/email.
- Thêm cooldown và severity.

### Ưu tiên 5: Hardening vận hành

- Chuẩn hóa logging.
- Thêm retry/backoff.
- Thêm smoke test end-to-end.
- Hoàn thiện tài liệu chạy project từ đầu.
- Không commit `.env`, secret, log runtime hoặc pid file.

## 12. Kết luận

Hiện project đã hoàn thành phần lớn nền tảng Data Lakehouse local: ingest dữ liệu, chuẩn hóa Bronze/Silver, load Gold vào ClickHouse, có Airflow orchestration, có FastAPI backend và có React dashboard. Các luồng chính như OHLCV, company profile, market index, news sentiment và realtime VWAP đều đã có triển khai cụ thể.

Phần đã mạnh nhất hiện tại là batch analytics và dashboard local. Phần cần hoàn thiện tiếp là realtime production qua DNSE/Kafka/ClickHouse, alert engine thật, dashboard live-state và hardening vận hành.
