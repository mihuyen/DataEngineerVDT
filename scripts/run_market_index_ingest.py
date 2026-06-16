from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.market_index import run


def main() -> None:
    """Run market index Bronze ingest for the default configured index list."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    results = run(start_date=start_date.isoformat(), end_date=end_date.isoformat())

    print("Market index Bronze ingest completed")
    for result in results:
        if result["status"] == "SUCCESS":
            print(f"- {result['index_code']}: {result['bucket']}/{result['object_name']}")
        else:
            print(f"- {result['index_code']}: FAILED ({result['error']})")


if __name__ == "__main__":
    main()
