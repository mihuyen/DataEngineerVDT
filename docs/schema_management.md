# Schema Management

Tai lieu nay mo ta cach project quan ly schema o quy mo do an/local lakehouse. Muc tieu la khong can dung DataHub/OpenMetadata production, nhung van co noi ro rang de tra loi: bang nao, cot nao, rule nao, ai la source of truth.

## Current Tooling

| Thanh phan | File/thu muc | Vai tro |
| --- | --- | --- |
| Source config | `configs/sources.yaml` | Quan ly nguon, scope HOSE, tan suat, path Bronze/Silver, bang Gold dich |
| Gold DDL | `sql/ddl/*.sql` | Source of truth cho schema ClickHouse Gold |
| dbt metadata | `dbt/models/sources.yml`, `dbt/models/marts/schema.yml` | Mo ta bang/cot Gold va test tai lieu hoa |
| Data dictionary | `docs/data_dictionary.md` | Tai lieu tap trung cho Bronze, Silver, Gold |
| Data contracts | `docs/data_contracts.md` | Rule schema/chat luong cho tung dataset |
| Quality checks | `src/quality/*_expectations.py` | Code validate du lieu truoc khi load Gold |
| Quality reports | `quality_reports/*.json` | Ket qua validation sau moi lan chay |

## Source Of Truth By Layer

| Layer | Schema source of truth | Ly do |
| --- | --- | --- |
| Bronze | ingestion code + schema parquet thuc te | Bronze gan source, schema co the thay doi theo provider |
| Silver | transform code + quality contract | Silver la lop chuan hoa nen can rule ro rang |
| Gold | `sql/ddl/*.sql` | Gold phuc vu API/dashboard, can schema on dinh nhat |
| Dashboard | API response + Gold tables | Frontend khong doc Bronze/Silver truc tiep |

## Change Workflow

Khi them hoac sua cot:

1. Sua ingestion/transform/loader lien quan.
2. Neu anh huong Gold, cap nhat `sql/ddl/*.sql`.
3. Cap nhat `docs/data_dictionary.md`.
4. Cap nhat `docs/data_contracts.md` neu co rule moi.
5. Cap nhat `dbt/models/sources.yml` hoac `schema.yml` neu cot/bang can hien trong dbt docs.
6. Chay quality checks va test lien quan.
7. Chay pipeline Airflow hoac script local de xac nhan row count/latest date.

## Why Not DataHub/OpenMetadata Now

Voi quy mo project hien tai, dung DataHub/OpenMetadata se hoi nang vi can them service, metadata ingestion va maintenance. Cach phu hop hon la:

```text
DDL + dbt schema.yml + data_dictionary.md + data_contracts.md + quality_reports
```

Neu mo rong production, co the day metadata tu dbt/ClickHouse/MinIO vao DataHub hoac OpenMetadata sau.

