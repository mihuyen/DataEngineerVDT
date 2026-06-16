# Ngày 15 - Gold Dimensions

## Mục tiêu

Ngày 15 thiết kế và tạo các bảng dimension trong ClickHouse theo scheme của project.

Các bảng:

- `dim_date`
- `dim_sector`
- `dim_stock`
- `dim_index`

## Kết quả hiện tại

```text
dim_date    4018 dòng
dim_sector  5 dòng
dim_stock   1531 dòng
dim_index   4 dòng
```

## dim_date

Cột:

- `date_id`
- `date`
- `year`
- `quarter`
- `month`
- `week`
- `day_of_week`
- `is_trading_day`

ClickHouse:

```sql
ENGINE = MergeTree
ORDER BY date_id
```

## dim_sector

Cột:

- `sector_id`
- `sector_name`
- `industry_group`
- `description`

ClickHouse:

```sql
ENGINE = MergeTree
ORDER BY sector_id
```

## dim_stock

Cột:

- `ticker`
- `company_name`
- `exchange`
- `sector_id`
- `listed_date`
- `status`
- `shares_outstanding`
- `free_float_rate`
- `market_cap_latest`
- `pe_latest`
- `eps_latest`
- `roe_latest`
- `roa_latest`
- `updated_at`

ClickHouse:

```sql
ENGINE = MergeTree
ORDER BY ticker
```

## dim_index

Cột:

- `index_id`
- `index_name`
- `exchange`
- `description`

Hiện có:

- `VNINDEX`
- `VN30`
- `HNXINDEX`
- `UPCOMINDEX`

ClickHouse:

```sql
ENGINE = MergeTree
ORDER BY index_id
```

## Script

Load riêng dimension:

```bash
uv run python scripts/load_dimensions.py
```

Recreate toàn bộ Gold schema theo DDL mới:

```bash
uv run python scripts/migrate_gold_schema.py
```

Load toàn bộ Gold batch hiện có:

```bash
uv run python scripts/load_gold.py
```

## Ghi chú

- `dim_stock` dùng `ticker` làm khóa logic theo scheme.
- Một số cột snapshot như `pe_latest`, `eps_latest`, `roe_latest`, `roa_latest`, `free_float_rate` hiện để `NULL` nếu Silver chưa có nguồn tương ứng.
- `listed_date` hiện để `NULL` nếu nguồn dữ liệu chưa cung cấp.
