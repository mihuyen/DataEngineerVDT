# Data Contracts And Quality Rules

Tai lieu nay gom cac contract chinh de quan ly schema va chat luong du lieu cho project. Hien tai rule duoc cai dat chu yeu trong `src/quality/*_expectations.py`, `sql/ddl/*.sql`, va dbt metadata trong `dbt/models`.

## Scope

- Universe chinh: HOSE.
- Market index: `VNINDEX`, `VN30`.
- Batch pipeline: Bronze -> Silver -> Quality -> Gold ClickHouse -> Gold parquet MinIO -> Frontend export.
- Realtime DNSE: dung cho VWAP demo/live ingest, chua phai production streaming hoan chinh.

## Schema Ownership

| Layer | Source of truth | Vai tro |
| --- | --- | --- |
| Bronze | ingestion code + parquet schema thuc te | Giu du lieu raw theo source |
| Silver | transform code + quality checks | Chuan hoa cot, kieu du lieu, metadata |
| Gold | `sql/ddl/*.sql` | Schema chinh thuc trong ClickHouse |
| dbt docs | `dbt/models/sources.yml`, `dbt/models/marts/schema.yml` | Mo ta bang/cot va test doc-friendly |
| Data dictionary | `docs/data_dictionary.md` | Tai lieu nghiep vu/de bao cao |

## Global Rules

| Rule | Ap dung | Mo ta |
| --- | --- | --- |
| HOSE only | `dim_stock`, Silver company profile, Silver OHLCV universe | `exchange` phai thuoc scope cau hinh, hien la `HOSE` |
| Required columns | Tat ca Silver datasets | Thieu cot bat buoc thi quality fail |
| Non-empty identity | Ticker/index/url | Khoa nghiep vu khong null/empty |
| Valid dates | Time-series facts | Cot ngay giao dich/tin tuc khong null |
| Non-negative volume | OHLCV/index/VWAP | `volume >= 0` |
| Positive prices | OHLCV/index | `open`, `high`, `low`, `close > 0` |
| High-low consistency | OHLCV/index | `high >= low`, `high >= open/close`, `low <= open/close` |
| Uniqueness | Silver/Gold facts | Khoa nghiep vu khong trung |

## Dataset Contracts

### `silver_ohlcv`

Primary key: `ticker`, `date`

Required columns:

```text
ticker, date, open, high, low, close, volume
```

Rules:

- `ticker` not null.
- `date` not null.
- `open`, `high`, `low`, `close` > 0.
- `volume >= 0`.
- `ticker + date` unique.

### `silver_company_profile`

Primary key: `ticker`

Required columns:

```text
ticker, company_name, exchange, sector_id, sector_name, shares_outstanding
```

Rules:

- `ticker` not null.
- `company_name` not null.
- `exchange` in configured exchanges, hien tai `HOSE`.
- `sector_id` not null.
- `shares_outstanding >= 0`.
- `ticker` unique.

### `silver_market_index`

Primary key: `index_code`, `date`

Required columns:

```text
index_code, date, open, high, low, close, volume
```

Rules:

- `index_code` in `VNINDEX`, `VN30`.
- `date` not null.
- OHLC > 0.
- `volume >= 0`.
- `index_code + date` unique.

### `silver_news`

Primary key: `url`

Required columns:

```text
url, title, content, source, published_at
```

Rules:

- `url`, `title`, `source`, `published_at` not null.
- `content` length >= 50.
- `url` unique.

### Gold Facts

| Table | Primary grain | Main checks |
| --- | --- | --- |
| `fact_daily_price` | `ticker`, `trading_date` | ticker/date not null, OHLC positive, volume non-negative, ticker-date unique |
| `fact_market_index` | `index_id`, `trading_date` | index/date not null, expected index universe, index-date unique |
| `fact_news_sentiment_daily` | `ticker`, `news_date` | counts non-negative, sentiment score in expected range when enforced |
| `fact_realtime_vwap` | `ticker`, `minute_ts` | ticker/minute unique, prices and volumes non-negative |
| `fact_alert_event` | `alert_id` | alert id unique, ticker/time/condition present |

## Recommended Maintenance

- Cap nhat `sql/ddl/*.sql` khi schema Gold thay doi.
- Cap nhat `docs/data_dictionary.md` cung luc voi DDL/transform.
- Them dbt tests cho Gold facts khi muon bat loi trong CI.
- Chay quality task truoc `load_gold` trong Airflow.
- Khong sua tay parquet Gold; Gold parquet nen duoc sinh tu `scripts/export_gold_to_minio.py`.

