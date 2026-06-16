# Ngày 10 - Silver Layer cho dữ liệu doanh nghiệp

Ngày cập nhật: 2026-06-14

## Mục tiêu

Ngày 10 tập trung xử lý dữ liệu doanh nghiệp từ Bronze sang Silver để phục vụ các bảng dimension trong Gold Layer, đặc biệt là:

- `dim_stock`
- `dim_sector`

Các trường cần chuẩn hóa:

- Ticker.
- Tên công ty.
- Tên tiếng Anh.
- Sàn giao dịch.
- Ngành/loại hình doanh nghiệp.
- Shares outstanding.
- Một số trường mô tả phục vụ dashboard.

## File liên quan

Transform:

```text
src/transform/company_profile_transform.py
```

Script transform:

```text
scripts/run_company_profile_silver.py
```

Quality rule:

```text
src/quality/company_profile_expectations.py
```

Script quality:

```text
scripts/run_company_profile_quality_check.py
```

Test:

```text
tests/test_company_profile_transform.py
tests/test_company_profile_quality.py
```

Report:

```text
quality_reports/company_profile_silver_validation.json
```

## Bronze input

Listing:

```text
data/bronze_local/company_profile/dataset=listing/year=2026/month=06/day=14/data.parquet
```

Profile chi tiết:

```text
data/bronze_local/company_profile/dataset=profile/ticker=<TICKER>/year=2026/month=06/day=14/data.parquet
```

## Silver output

```text
data/silver_local/company_profile/year=2026/month=06/data.parquet
```

MinIO object:

```text
silver/company_profile/year=2026/month=06/data.parquet
```

## Schema Silver chính

| Cột | Ý nghĩa |
|---|---|
| `ticker` | Mã cổ phiếu chuẩn uppercase |
| `company_name` | Tên công ty tiếng Việt |
| `company_name_en` | Tên công ty tiếng Anh nếu có |
| `exchange` | Sàn giao dịch: HOSE, HNX, UPCOM |
| `sector_id` | Mã ngành/nhóm doanh nghiệp đã chuẩn hóa |
| `sector_name` | Tên ngành/loại hình doanh nghiệp |
| `shares_outstanding` | Số cổ phiếu đang lưu hành |
| `market_cap_latest` | Vốn hóa gần nhất, hiện fallback `0.0` nếu nguồn chưa có |
| `is_active` | Cờ active phục vụ dimension |
| `charter_capital` | Vốn điều lệ nếu nguồn cung cấp |
| `listed_volume` | Khối lượng niêm yết nếu nguồn cung cấp |
| `free_float` | Free float nếu nguồn cung cấp |
| `free_float_percentage` | Tỷ lệ free float nếu nguồn cung cấp |
| `business_model` | Mô tả hoạt động kinh doanh |
| `address` | Địa chỉ |
| `website` | Website |
| `processed_at` | Thời điểm xử lý Silver |
| `source_name` | Tên source nội bộ |

## Rule quality

| Rule | Ý nghĩa |
|---|---|
| `expect_required_columns_to_exist` | Các cột bắt buộc phải tồn tại |
| `expect_ticker_to_not_be_null` | `ticker` không null/rỗng |
| `expect_company_name_to_not_be_null` | `company_name` không null/rỗng |
| `expect_exchange_to_be_valid` | `exchange` thuộc HOSE/HNX/UPCOM/UNKNOWN |
| `expect_sector_id_to_not_be_null` | `sector_id` không null/rỗng |
| `expect_shares_outstanding_to_be_non_negative` | `shares_outstanding >= 0` |
| `expect_ticker_to_be_unique` | Mỗi ticker chỉ có một dòng |

## Kết quả chạy thực tế

Lệnh transform:

```powershell
uv run python scripts/run_company_profile_silver.py
```

Kết quả:

```text
record_count: 1531
local_path: data/silver_local/company_profile/year=2026/month=06/data.parquet
object_name: company_profile/year=2026/month=06/data.parquet
```

Lệnh quality:

```powershell
uv run python scripts/run_company_profile_quality_check.py --fail-on-error
```

Kết quả:

```text
success: True
record_count: 1531
error_count: 0
```

## Gold Layer sau khi load lại

Lệnh:

```powershell
uv run python scripts/load_gold.py
```

Kết quả:

```text
dim_stock: 1531
dim_sector: 5
fact_daily_price: 35142
fact_market_index: 92
dim_date: 4018
dim_index: 4
```

Ví dụ dữ liệu `dim_stock`:

```text
AAA | CTCP Nhựa An Phát Xanh | HOSE | CÔNG_TY_CỔ_PHẦN | 393742730
FPT | CTCP FPT | HOSE | CÔNG_TY_CỔ_PHẦN | 1703507121
VCB | Ngân hàng TMCP Ngoại thương Việt Nam | HOSE | NGÂN_HÀNG | 8355675094
```

## Lưu ý kỹ thuật

Ghi chú cập nhật: Gold schema hiện đã chuyển theo scheme nghiệp vụ của project. `dim_stock` dùng khóa logic `ticker`; `fact_daily_price` cũng liên kết bằng `ticker` và `trading_date`.

## Kết luận

Ngày 10 đã hoàn thành:

- Silver company profile đủ 1.531 mã.
- Dữ liệu đã chuẩn hóa ticker, tên công ty, sàn, sector và shares outstanding.
- Quality check pass toàn bộ với `error_count = 0`.
- Gold `dim_stock` và `dim_sector` đã dùng dữ liệu doanh nghiệp thay vì chỉ fallback ticker.
