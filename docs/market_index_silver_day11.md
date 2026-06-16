# Ngày 11 - Silver Layer cho chỉ số thị trường

Ngày cập nhật: 2026-06-14

## Mục tiêu

Ngày 11 xử lý dữ liệu chỉ số thị trường từ Bronze sang Silver để phục vụ `fact_market_index` trong Gold Layer.

Các trường cần chuẩn hóa:

- `index_code`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `trading_value`

## File liên quan

Transform:

```text
src/transform/market_index_transform.py
```

Script transform:

```text
scripts/run_market_index_silver.py
```

Quality rule:

```text
src/quality/market_index_expectations.py
```

Script quality:

```text
scripts/run_market_index_quality_check.py
```

Test:

```text
tests/test_market_index_transform.py
tests/test_market_index_quality.py
```

Report:

```text
quality_reports/market_index_silver_validation.json
```

## Silver output

```text
data/silver_local/market_index/year=2026/month=06/data.parquet
```

MinIO object:

```text
silver/market_index/year=2026/month=06/data.parquet
```

## Rule quality

| Rule | Ý nghĩa |
|---|---|
| `expect_required_columns_to_exist` | Các cột bắt buộc phải tồn tại |
| `expect_index_code_to_not_be_null` | `index_code` không null/rỗng |
| `expect_index_code_to_be_expected` | Chỉ nhận `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX` |
| `expect_date_to_not_be_null` | `date` không null |
| `expect_open_to_be_positive` | `open > 0` |
| `expect_high_to_be_positive` | `high > 0` |
| `expect_low_to_be_positive` | `low > 0` |
| `expect_close_to_be_positive` | `close > 0` |
| `expect_volume_to_be_non_negative` | `volume >= 0` |
| `expect_high_to_be_at_least_low` | `high >= low` |
| `expect_high_to_be_at_least_open` | `high >= open` |
| `expect_high_to_be_at_least_close` | `high >= close` |
| `expect_low_to_be_at_most_open` | `low <= open` |
| `expect_low_to_be_at_most_close` | `low <= close` |
| `expect_index_code_date_to_be_unique` | Không trùng `index_code + date` |
| `expect_expected_index_codes_to_exist` | Có đủ 4 chỉ số chính |

## Kết quả chạy thực tế

Lệnh:

```powershell
uv run python scripts/run_market_index_silver.py
uv run python scripts/run_market_index_quality_check.py --fail-on-error
```

Kết quả:

```text
record_count: 92
success: True
error_count: 0
```

## Kết luận

Ngày 11 đã hoàn thành:

- Silver market index có 92 dòng.
- Có đủ `VNINDEX`, `VN30`, `HNXINDEX`, `UPCOMINDEX`.
- Không có lỗi OHLC, volume âm, ngày null hoặc duplicate `index_code + date`.
- Dữ liệu đủ điều kiện phục vụ `fact_market_index`.
