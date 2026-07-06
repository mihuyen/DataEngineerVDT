from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.loaders.load_fact_news_sentiment import load_nlp_sentiment_detail, select_active_model_version
from src.quality.news_sentiment_expectations import validate_news_sentiment_detail
from src.transform.news_entity_linking import load_silver_company_profile


def main() -> None:
    detail = load_nlp_sentiment_detail()
    if detail is None:
        raise FileNotFoundError("No news_sentiment_detail parquet files found")
    report = validate_news_sentiment_detail(
        select_active_model_version(detail),
        load_silver_company_profile(),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
