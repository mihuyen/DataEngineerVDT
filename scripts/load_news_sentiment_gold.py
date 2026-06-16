from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.clickhouse_client import create_client, execute, query_dataframe
from src.loaders.load_fact_news_sentiment import load_fact_news_sentiment_daily


def main() -> None:
    client = create_client()
    execute(client, "TRUNCATE TABLE IF EXISTS fact_news_sentiment_daily")
    frame = load_fact_news_sentiment_daily(client)
    counts = query_dataframe(
        client,
        "SELECT count() AS row_count, uniqExact(ticker) AS ticker_count FROM fact_news_sentiment_daily",
    )
    print("News sentiment Gold load completed")
    print(f"- loaded_rows: {frame.height}")
    print(counts.write_csv())


if __name__ == "__main__":
    main()
