# Ngày 18 - Gold fact_market_index

## Mục tiêu

Ngày 18 hoàn thiện bảng `fact_market_index` cho dashboard tổng quan thị trường.

Mục tiêu:

- Lưu dữ liệu chỉ số thị trường trong ClickHouse.
- Có dữ liệu cho `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX`.
- Bổ sung market breadth:
  - `advance_count`
  - `decline_count`
  - `unchanged_count`
  - `advance_decline_ratio`

## Grain

```text
1 chỉ số thị trường x 1 ngày giao dịch
```

Khóa logic:

- `index_id`
- `trading_date`

## DDL

File:

```text
sql/ddl/fact_market_index.sql
```

Thiết kế vật lý:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(trading_date)
ORDER BY (index_id, trading_date)
```

## Nguồn dữ liệu

Nguồn điểm chỉ số:

```text
data/silver_local/market_index/year=*/month=*/data.parquet
```

Nguồn breadth:

```text
data/silver_local/ohlcv/ticker=*/year=*/month=*/data.parquet
data/silver_local/company_profile/year=*/month=*/data.parquet
```

## Cách tính breadth

Mapping theo sàn:

| Exchange | Index |
| --- | --- |
| `HOSE` | `VNINDEX` |
| `HNX` | `HNXINDEX` |
| `UPCOM` | `UPCOMINDEX` |

Với `VN30`, project hiện chưa có danh sách constituents chính thức. Bản Ngày 18 dùng demo rule:

```text
Top 30 mã HOSE theo shares_outstanding
```

TODO sau này: thay demo rule bằng danh sách VN30 chính thức từ nguồn đáng tin cậy.

## Công thức

```text
advance_count = số mã có close > open
decline_count = số mã có close < open
unchanged_count = số mã có close = open
advance_decline_ratio = advance_count / decline_count
```

Nếu `decline_count = 0`, ratio được đặt bằng `advance_count`.

## Kết quả hiện tại

Sau khi load Gold:

```text
fact_market_index: 92 dòng
```

Các chỉ số có trong Gold:

- `VNINDEX`
- `VN30`
- `HNXINDEX`
- `UPCOMINDEX`

## Script

Loader:

```text
src/loaders/load_fact_market_index.py
```

Chạy:

```bash
uv run python scripts/migrate_gold_schema.py
uv run python scripts/load_gold.py
uv run python scripts/validate_gold.py
```

Test:

```bash
uv run pytest tests/test_fact_market_index_day18.py tests/test_gold_loader.py
```

## Trạng thái

Ngày 18 đã hoàn thành ở mức Gold batch table và breadth demo.

Giới hạn còn lại:

- `VN30` breadth hiện dùng demo constituents top 30 HOSE theo `shares_outstanding`.
- Cần thay bằng danh sách VN30 chính thức ở bước hoàn thiện dữ liệu.
