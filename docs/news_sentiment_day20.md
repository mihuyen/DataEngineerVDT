# Ngày 20 - News sentiment và fact_news_sentiment_daily

## Mục tiêu

Ngày 20 tính sentiment demo cho tin tức đã được entity linking ở Ngày 19 và tổng hợp vào bảng Gold:

```text
fact_news_sentiment_daily
```

## Input

Entity links:

```text
data/gold_local/news_entity_links/year=*/month=*/data.parquet
```

Schema input chính:

- `article_id`
- `url`
- `title`
- `published_at`
- `source`
- `category`
- `ticker`
- `matched_alias`
- `match_method`
- `match_score`

## Sentiment demo

Module:

```text
src/loaders/load_fact_news_sentiment.py
```

Sentiment hiện dùng rule-based lexicon tiếng Việt:

- Từ tích cực: `tăng`, `lợi nhuận`, `tăng trưởng`, `khởi sắc`, `vượt kế hoạch`, ...
- Từ tiêu cực: `giảm`, `lỗ`, `khởi tố`, `cảnh báo`, `nợ xấu`, `rủi ro`, ...

Score:

```text
sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
```

Nếu không có từ khóa, score bằng `0`.

Label:

- `positive` nếu score > 0.05.
- `negative` nếu score < -0.05.
- `neutral` nếu còn lại.

## Output Gold

DDL:

```text
sql/ddl/fact_news_sentiment_daily.sql
```

Grain:

```text
1 ticker x 1 news_date
```

Cột:

- `ticker`
- `date_id`
- `news_date`
- `news_count`
- `source_count`
- `positive_count`
- `negative_count`
- `neutral_count`
- `avg_sentiment_score`
- `top_headline`
- `created_at`

ClickHouse:

```sql
ENGINE = MergeTree
PARTITION BY toYYYYMM(news_date)
ORDER BY (ticker, news_date)
```

## Cách chạy

Chỉ load news sentiment:

```bash
uv run python scripts/load_news_sentiment_gold.py
```

Hoặc load toàn bộ Gold:

```bash
uv run python scripts/load_gold.py
```

Nếu mới crawl tin tức:

```bash
uv run python scripts/run_news_silver.py
uv run python scripts/run_news_entity_linking.py
uv run python scripts/load_news_sentiment_gold.py
```

## Trạng thái

Ngày 20 hoàn thành ở mức sentiment demo và load `fact_news_sentiment_daily`.

Giới hạn:

- Sentiment hiện là rule-based, chưa dùng model NLP tiếng Việt.
- `top_headline` chọn headline có `match_score` cao nhất trong nhóm ticker/ngày.
- Entity linking sai hoặc thiếu sẽ ảnh hưởng trực tiếp tới fact này.
