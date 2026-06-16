# Ngày 9 - Kiểm tra chất lượng dữ liệu OHLCV

Ngày cập nhật: 2026-06-14

## Mục tiêu

Ngày 9 tập trung kiểm tra lỗi dữ liệu OHLCV ở tầng Silver để đảm bảo bộ dữ liệu giá đáng tin cậy hơn trước khi load sang Gold.

Các nhóm lỗi cần kiểm tra:

- Giá âm hoặc bằng 0.
- Volume âm hoặc null.
- `high < low`.
- `high < open`.
- `high < close`.
- `low > open`.
- `low > close`.
- Trùng khóa `ticker + date`.
- Thiếu cột bắt buộc.
- Null ở các trường quan trọng.

## File liên quan

Module quality:

```text
src/quality/ohlcv_expectations.py
```

Script chạy quality check:

```text
scripts/run_quality_check.py
```

Test:

```text
tests/test_ohlcv_quality.py
```

Report sinh ra:

```text
quality_reports/ohlcv_silver_validation.json
```

## Cách chạy

Kiểm tra toàn bộ Silver OHLCV:

```powershell
uv run python scripts/run_quality_check.py --fail-on-error
```

Kiểm tra một vài mã cụ thể:

```powershell
uv run python scripts/run_quality_check.py --tickers VCB ACB HPG --fail-on-error
```

## Rule kiểm tra hiện tại

| Rule | Ý nghĩa |
|---|---|
| `expect_required_columns_to_exist` | Các cột bắt buộc phải tồn tại |
| `expect_ticker_to_not_be_null` | `ticker` không được null/rỗng |
| `expect_date_to_not_be_null` | `date` không được null |
| `expect_close_to_not_be_null` | `close` không được null |
| `expect_volume_to_not_be_null` | `volume` không được null |
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
| `expect_ticker_date_to_be_unique` | Không trùng `ticker + date` |

## Kết quả chạy thực tế

Lệnh đã chạy:

```powershell
uv run python scripts/run_quality_check.py --fail-on-error
```

Kết quả:

```text
success: True
record_count: 35142
error_count: 0
report_path: quality_reports/ohlcv_silver_validation.json
```

Tất cả expectation đều pass:

```text
PASS expect_required_columns_to_exist
PASS expect_ticker_to_not_be_null
PASS expect_date_to_not_be_null
PASS expect_close_to_not_be_null
PASS expect_volume_to_not_be_null
PASS expect_open_to_be_positive
PASS expect_high_to_be_positive
PASS expect_low_to_be_positive
PASS expect_close_to_be_positive
PASS expect_volume_to_be_non_negative
PASS expect_high_to_be_at_least_low
PASS expect_high_to_be_at_least_open
PASS expect_high_to_be_at_least_close
PASS expect_low_to_be_at_most_open
PASS expect_low_to_be_at_most_close
PASS expect_ticker_date_to_be_unique
```

## Kết luận

Ngày 9 đã hoàn thành cho OHLCV:

- Silver OHLCV đã được kiểm tra trên toàn bộ 35.142 dòng.
- Không phát hiện giá âm, volume âm/null, lỗi `high < low` hoặc duplicate `ticker + date`.
- Dữ liệu OHLCV Silver đủ điều kiện để tiếp tục phục vụ Gold Layer và dashboard.

## TODO sau Ngày 9

- Bổ sung quality rule tương tự cho company profile.
- Bổ sung quality rule cho market index.
- Bổ sung quality rule cho news.
- Đưa quality check vào Airflow như một quality gate bắt buộc trước khi load Gold.
