from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.ingestion.vnstock_ohlcv import (
    DEFAULT_EXCHANGES,
    fetch_ticker_universe,
    load_config,
    read_tickers_from_file,
    run_many,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest OHLCV data to Bronze MinIO.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Danh sach ma co phieu can ingest. Neu bo trong se lay theo san.",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        help="Danh sach san can lay ma. Mac dinh chi lay HOSE.",
    )
    parser.add_argument(
        "--ticker-file",
        type=Path,
        help="File CSV co cot symbol hoac ticker de fallback khi API listing bi loi.",
    )
    parser.add_argument("--start-date", help="Ngay bat dau, dinh dang YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Ngay ket thuc, dinh dang YYYY-MM-DD.")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="So ngay gan nhat can lay neu khong truyen start-date.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Gioi han so ma de test nhanh truoc khi ingest toan thi truong.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Dung ngay khi mot ma bi loi.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=3.5,
        help="So giay nghi giua moi ticker de tranh rate limit vnstock.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bo qua ticker da co file parquet local cho ngay ingest hien tai.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_config = load_config()
    config_exchanges = source_config.get("default_exchanges", DEFAULT_EXCHANGES)
    exchanges = args.exchanges or config_exchanges
    listing_source = str(source_config.get("listing_source", "kbs"))
    end_date = date.fromisoformat(args.end_date) if args.end_date else date.today()
    start_date = (
        date.fromisoformat(args.start_date)
        if args.start_date
        else end_date - timedelta(days=args.days)
    )

    if args.tickers:
        tickers = [ticker.upper() for ticker in args.tickers]
    elif args.ticker_file:
        tickers = read_tickers_from_file(args.ticker_file)
    else:
        universe = fetch_ticker_universe(exchanges=exchanges, source=listing_source)
        tickers = universe.get_column("symbol").to_list()

    if args.limit:
        tickers = tickers[: args.limit]

    print(f"OHLCV Bronze ingest started for {len(tickers)} tickers")
    print(f"- exchanges: {', '.join(exchange.upper() for exchange in exchanges)}")
    print(f"- start_date: {start_date.isoformat()}")
    print(f"- end_date: {end_date.isoformat()}")

    result = run_many(
        tickers=tickers,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        continue_on_error=not args.fail_fast,
        request_delay_seconds=args.request_delay_seconds,
        skip_existing=args.skip_existing,
    )

    print("OHLCV Bronze ingest completed")
    print(f"- requested: {result['requested']}")
    print(f"- succeeded: {result['succeeded']}")
    print(f"- skipped: {result['skipped']}")
    print(f"- failed: {result['failed']}")

    if result["errors"]:
        print("Failed tickers:")
        for error in result["errors"]:
            print(f"- {error['ticker']}: {error['error']}")


if __name__ == "__main__":
    main()
