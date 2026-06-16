# Ngày 19 - Entity linking cho tin tức

## Mục tiêu

Ngày 19 gán bài viết tin tức với mã cổ phiếu (`ticker`) để chuẩn bị cho `fact_news_sentiment_daily` ở Ngày 20.

## Nguồn dữ liệu

Tin tức sạch:

```text
data/silver_local/news/year=*/month=*/data.parquet
```

Thông tin doanh nghiệp:

```text
data/silver_local/company_profile/year=*/month=*/data.parquet
```

## Cách link ticker

Module:

```text
src/transform/news_entity_linking.py
```

Logic:

- Tạo dictionary từ `dim_stock`/Silver company profile:
  - `ticker`
  - `company_name`
  - `company_name_en`
  - alias rút gọn từ tên công ty
- Ghép trên các trường bài báo:
  - `title`
  - `description`
  - `content`
  - `tags`
- Dùng regex:
  - Ticker dùng word boundary để tránh match nhầm trong từ dài.
  - Company alias dùng regex không phân biệt hoa thường.

## Output

Dataset linked:

```text
data/gold_local/news_entity_links/year=YYYY/month=MM/data.parquet
```

Schema chính:

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
- `linked_at`

## Chạy entity linking

```bash
uv run python scripts/run_news_entity_linking.py
```

## Crawl tin tức mỗi 5 phút

Hiện crawler mỗi lần lấy tối đa `max_articles_per_source`, mặc định đang là 20 bài mỗi nguồn. Nếu muốn cứ 5 phút crawl một lần, chạy:

```bash
uv run python scripts/run_news_crawl_loop.py --interval-seconds 300
```

Nếu chỉ muốn ghi local, không upload MinIO:

```bash
uv run python scripts/run_news_crawl_loop.py --interval-seconds 300 --no-upload
```

Script này chạy theo vòng:

```text
Bronze crawl -> Silver transform -> entity linking
```

Để test một vòng:

```bash
uv run python scripts/run_news_crawl_loop.py --run-once --no-upload
```

## Chống mất dữ liệu khi crawl nhiều lần

`market_news.save_parquet()` đã được chỉnh để:

- Nếu file Bronze cùng ngày đã tồn tại thì đọc file cũ.
- Append bài mới.
- Dedupe theo `url`.
- Ghi lại file `data.parquet`.

Nhờ vậy crawl 5 phút/lần không ghi đè mất các bài đã crawl trước đó trong cùng ngày.

## Giới hạn

- Entity linking hiện là rule-based, chưa dùng NLP nâng cao.
- Có thể match thiếu nếu bài viết chỉ nhắc biệt danh thương hiệu không có trong company profile.
- Có thể match nhầm với ticker quá ngắn nếu ngữ cảnh không liên quan; đã giảm rủi ro bằng regex boundary.
