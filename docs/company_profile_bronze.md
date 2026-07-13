# Bronze Layer - Company Profile

Tầng Bronze cho `company_profile` lưu thông tin thô/tổng quan doanh nghiệp niêm yết theo danh sách mã thuộc `HOSE`.

## Nguồn dữ liệu

- Provider: `vnstock`
- Listing source: `kbs`
- Profile source: `kbs`
- Universe mặc định: toàn bộ cổ phiếu trên `HOSE`

## Schema tối thiểu

Cột bắt buộc:

- `symbol`

Các cột thường có từ provider:

- `exchange`
- `business_model`
- `founded_date`
- `charter_capital`
- `number_of_employees`
- `listing_date`
- `company_type`
- `address`
- `phone`
- `email`
- `website`
- `history`
- `outstanding_shares`
- `as_of_date`
- `source`
- `ingested_at`

## Partition strategy

Bucket:

```text
bronze
```

Object path:

```text
company_profile/
└── dataset=listing/
    └── year=2026/
        └── month=06/
            └── day=14/
                └── data.parquet
```

`dataset=listing` lưu danh mục nhanh cho toàn bộ universe. `dataset=profile` lưu profile chi tiết từng mã khi chạy enrichment.

Profile chi tiết được lưu theo từng ticker để có thể resume khi gặp rate limit:

```text
company_profile/
└── dataset=profile/
    └── ticker=VCB/
        └── year=2026/
            └── month=06/
                └── day=14/
                    └── data.parquet
```

## Cách chạy

Chạy nhanh toàn bộ danh mục doanh nghiệp `HOSE` từ listing source:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode listing
```

Chạy thử 10 mã ở chế độ listing:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode listing --limit 10
```

Chạy profile chi tiết cho một số mã cụ thể:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode profile --tickers VCB ACB FPT
```

Chạy profile chi tiết cho toàn bộ universe sẽ gọi API từng mã, nên thời gian lâu hơn và có thể bị provider giới hạn:

```powershell
uv run python scripts/run_company_profile_ingest.py --mode profile --exchanges HOSE --request-delay-seconds 5 --skip-existing
```

Nếu API listing lỗi, có thể truyền file CSV có cột `symbol` hoặc `ticker`:

```powershell
uv run python scripts/run_company_profile_ingest.py --ticker-file configs/tickers.csv
```

## Ghi chú vận hành

- Script tiếp tục chạy khi một mã lỗi và in danh sách lỗi cuối cùng.
- Dữ liệu Bronze chưa làm sạch nghiệp vụ, chưa map sang `dim_stock`.
- Silver/Gold cho company profile sẽ xử lý sau.
