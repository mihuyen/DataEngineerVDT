# Architecture

## Kiến trúc Medallion — 3 luồng độc lập, không dùng chung 1 pipeline

Hệ thống dùng kiến trúc Bronze/Silver/Gold để tách trách nhiệm giữa lưu trữ thô, làm sạch dữ liệu và phục vụ phân tích. Điểm khác biệt trong thiết kế: **không dùng một pipeline chung cho mọi loại dữ liệu**, mà tách thành 3 luồng chạy song song — batch, tin tức, thời gian thực — vì mỗi loại có tần suất, khối lượng và yêu cầu độ trễ khác nhau hoàn toàn.

## Bronze Layer

Bronze lưu dữ liệu gần nguyên trạng, chỉ thêm nguồn, thời điểm thu thập và khóa truy vết — chưa lọc nội dung. Partition theo `year/month/day` (ngày *thu thập*, không phải ngày giao dịch) để trả lời được câu hỏi "chu kỳ nào đã lấy dữ liệu này", đồng thời tránh tạo hàng trăm file nhỏ mỗi ngày (toàn bộ 404 mã của 1 ngày gộp vào 1 file). Giữ nguyên gốc để có thể chạy lại Silver bất kỳ lúc nào mà không cần gọi lại API nguồn (vốn có rate limit).

## Silver Layer

Silver chuẩn hóa lược đồ, ép kiểu, loại bản ghi sai miền giá trị và khử trùng theo khóa nghiệp vụ — logic khác nhau tùy loại dữ liệu (OHLCV vs tin tức). Polars xử lý transform. **Không dùng thư viện Great Expectations thật** — quality rule tự viết bằng Polars theo phong cách tương tự (kiểm tra Completeness/Validity/Uniqueness). Partition theo `year/month` — thô hơn Bronze, vì Gold Loader luôn quét toàn bộ file Silver để gộp/khử trùng, không lọc theo ngày cụ thể (giữ Bronze theo ngày là vì khớp nhịp ingest, không phải vì Silver cần vậy).

Silver có **Quality Gate** thật sự — chặn, không cho công bố sang Gold nếu fail (không phải chỉ log cảnh báo).

## Gold Layer

Gold là lớp phục vụ analytics trong ClickHouse, tổ chức theo star schema. 3 luồng nạp Gold theo 3 cơ chế khác nhau (Python Gold Loader → dbt cho Batch; News Gold Loader cho Tin tức; ClickHouse tự ghi qua Kafka Engine cho Realtime) — chi tiết tại `gold_layer.md`. Kiểm soát chất lượng tích hợp xuyên suốt (không phải 1 cổng chặn riêng): schema check ở Bronze, Quality Gate ở Silver, kiểm tra công thức chỉ báo trước khi ghi Gold, và Reconciliation đối soát liên tầng sau khi ghi — xem chi tiết `data_contracts.md`.

## Ba luồng xử lý

### Luồng Batch — DAG Airflow, 18:00 T2–T6

Ingest song song → Bronze → Silver Transform → Quality Gate → Gold Loader → ClickHouse/MinIO → Reconciliation → 5 nhánh song song (dbt, export MinIO, Alert Engine, backup, backfill nến).

### Luồng Tin tức — DAG riêng, mỗi 5 phút, 24/7

Crawl 3 nguồn báo → Bronze → Silver Transform → News Quality Gate → Entity Linking (gán ticker HOSE) → PhoBERT (phân tích cảm xúc) → Sentiment Quality Gate → News Gold Loader → ClickHouse → Reconciliation. Nếu dịch vụ PhoBERT gặp sự cố phải chạy fallback luật đơn giản, pipeline từ chối công bố kết quả đó.

### Luồng Realtime — bỏ qua Silver hoàn toàn

DNSE WebSocket → 2 kênh độc lập:
- **Trade tick**: chuẩn hóa → Kafka → ClickHouse (Kafka Engine + Materialized View) → gộp theo phút (`AggregatingMergeTree`) → VWAP.
- **Nến 1 phút**: chuẩn hóa → ghi thẳng `fact_intraday_ohlcv` (`ReplacingMergeTree`, tự ghi đè khi có nến hiệu chỉnh).

2 nhánh đối chiếu chéo khối lượng để phát hiện rớt kết nối WebSocket, không nằm trong Reconciliation của Batch.

**Vì sao Realtime không qua Silver**: dữ liệu đến liên tục từng lệnh khớp, dừng lại xử lý theo lô ở tầng trung gian sẽ phá vỡ tính real-time — nên ClickHouse tự biến đổi ngay khi dữ liệu tới, thay vì qua tầng xử lý code riêng như 2 luồng kia.

**Materialized View vs VIEW thường**: Kafka Engine table chỉ đọc được 1 lần (giống dòng nước chảy qua) — Materialized View là cách duy nhất "bắt" và lưu lại dữ liệu đó vĩnh viễn. Riêng VWAP lũy kế cả phiên dùng VIEW thường (không phải MV), vì cần cộng dồn không giới hạn số phút trước đó — việc này không thể tự động duy trì kiểu "ghi sẵn mỗi khi có dòng mới".

## Vai trò công nghệ

- **MinIO**: object storage tương thích S3, lưu Bronze/Silver/Gold dạng Parquet.
- **Polars**: xử lý transform batch, viết quality rule.
- **ClickHouse**: OLAP database phục vụ Gold — dạng cột, PARTITION BY + ORDER BY tối ưu truy vấn theo mã, có sẵn Kafka Engine cho luồng Realtime.
- **dbt**: tính chỉ báo kỹ thuật bằng SQL window function (SMA/RSI/Bollinger) và kiểm tra công thức (`dbt test`) trên ClickHouse.
- **Airflow**: điều phối 2 DAG (batch, tin tức); gửi cảnh báo qua callback khi task lỗi/DAG hoàn tất.
- **Kafka**: message broker cho luồng trade tick Realtime.
- **PostgreSQL**: cấu hình ứng dụng thay đổi thường xuyên — `watchlist`, `user_alerts` — dữ liệu người dùng tự tạo, không tái sinh được nên luôn nằm trong backup.
- **Hugging Face Transformers**: serving model PhoBERT tự fine-tune, chạy suy luận cục bộ (không gọi API ngoài lúc runtime).
- **FastAPI + React**: lớp phục vụ, đọc ClickHouse (dữ liệu thị trường) và PostgreSQL (watchlist/rule).
- **Grafana**: giám sát vận hành — đọc độc lập từ ClickHouse/Postgres, không phụ thuộc Airflow còn sống hay không (lưới an toàn cuối cùng khi Airflow tự nó gặp sự cố).

## Cảnh báo — 3 nguồn độc lập, hội tụ về 1 kênh Telegram

- **Alert Engine** — cảnh báo nghiệp vụ theo rule người dùng (14 loại điều kiện), đọc chỉ báo từ `fact_daily_price_indicators` (đã qua dbt test).
- **Airflow** — callback khi task hết retry hoặc DAG hoàn tất; phát hiện nhanh, chi tiết đến từng task, nhưng chết cùng lúc nếu Scheduler crash.
- **Grafana** — giám sát hạ tầng, đọc độc lập; chậm hơn nhưng vẫn phát hiện được khi Airflow tự nó gặp sự cố nghiêm trọng.

Xem chi tiết tại README.md phần "Cảnh báo" và "Giám sát vận hành".
