# Silver Layer

Silver là tầng chuẩn hóa lược đồ, khóa nghiệp vụ và kiểm tra chất lượng — nơi thực sự có logic nghiệp vụ, khác với Bronze (gần như giữ nguyên gốc). Bao phủ: OHLCV, hồ sơ doanh nghiệp, chỉ số thị trường, tin tức.

## Mục đích

- Đọc Bronze bằng Polars, ép kiểu, chuẩn hóa mã viết hoa.
- Loại bản ghi sai miền giá trị (giá âm, `high < low`...).
- Khử trùng theo khóa nghiệp vụ (giữ bản ghi cuối nếu trùng).
- Chuẩn hóa URL, làm sạch nội dung văn bản (riêng tin tức).
- Chạy **Quality Gate** — cổng chặn thật sự, fail thì không công bố sang Gold.
- Ghi Parquet sạch xuống Silver.

## Partition — gộp thô hơn Bronze, gộp toàn bộ mã vào 1 file/tháng

```text
silver/ohlcv/year=2026/month=07/data.parquet
```

Không tách theo `ticker`, chỉ theo `year/month` (thô hơn Bronze — vốn theo `year/month/day`). Lý do không phải vì dữ liệu giảm nhiều (Quality Gate chỉ loại rất ít bản ghi lỗi), mà vì **Gold Loader luôn quét toàn bộ file Silver để gộp và khử trùng, không lọc theo ngày cụ thể** — nếu vẫn giữ partition theo ngày như Bronze sẽ tạo hàng trăm file nhỏ mỗi tháng, tốn chi phí I/O mà không mang lại lợi ích gì. Bronze giữ theo ngày vì khớp nhịp ingest hàng ngày, cần replay đúng 1 ngày khi sửa lỗi.

Grain theo từng loại dữ liệu:

| Dataset | Grain | Khóa khử trùng |
|---|---|---|
| OHLCV | `ticker + date` | |
| Chỉ số thị trường | `index_code + date` | |
| Hồ sơ doanh nghiệp | `ticker + snapshot` | |
| Tin tức | 1 dòng / URL bài viết | `url` (→ `article_id`) |

## Transform rules — khác nhau tùy loại dữ liệu

**OHLCV/chỉ số:**
- Chuẩn hóa tên cột lowercase snake_case, alias `time`/`trading_date` → `date`, `vol` → `volume`.
- Ép kiểu: `date: Date`, `open/high/low/close: Float64`, `volume: Int64`.
- Loại bản ghi: `volume < 0`, `open/high/low/close <= 0`, `high < low`.
- Khử trùng theo `ticker + date`, giữ bản ghi cuối.

**Tin tức:**
- Chuẩn hóa nguồn báo, tiêu đề, nội dung, `published_at`.
- Tạo `article_id` từ hash URL.
- Loại HTML tag còn sót, khoảng trắng thừa.
- Khử trùng theo `url`.

Thêm metadata chung: `ticker`/`article_id`, `ingested_at`, `processed_at`, `source_name`.

## Quality Gate — Validate, gắn với 6 chiều DAMA-DMBOK

Bộ validation: `src/quality/ohlcv_expectations.py` (OHLCV), `src/quality/news_expectations.py` (tin tức). **Không dùng thư viện Great Expectations thật** — quality rule tự viết bằng Polars theo phong cách tương tự, có `gx_version="n/a"` để đánh dấu.

| Kiểm tra | OHLCV | Tin tức | Chiều DAMA |
|---|---|---|---|
| Không rỗng | `ticker + date` | `url`, `published_at` | Completeness |
| Miền giá trị | `open/high/low/close > 0`, `volume >= 0`, `high >= low` | Đủ nội dung, đúng định dạng | Validity |
| Không trùng | `ticker + date` | `url` | Uniqueness |

**Nếu fail → KHÔNG công bố sang Gold.** Cần lưu ý thứ tự đúng: Silver được ghi ra đĩa xong trước, Quality Gate chạy sau đó để đọc lại và xác nhận — không phải "validate trước rồi mới ghi Silver". Nếu fail, dữ liệu Silver vẫn tồn tại trên đĩa, chỉ là không được phép đi tiếp sang Gold.

## Luồng

```text
Bronze parquet → Polars transform → Ghi Silver parquet
                                   → Quality Gate (đọc lại Silver vừa ghi)
                                   → quality_reports/*.json
```

## Cách chạy

```bash
uv run python scripts/run_silver_transform.py
uv run python scripts/run_quality_check.py       # OHLCV
uv run python scripts/run_news_quality_check.py  # Tin tức
uv run pytest
```

Bình thường chạy tự động trong DAG (Batch: sau ingest; Tin tức: mỗi 5 phút), không cần chạy tay trừ khi debug.
