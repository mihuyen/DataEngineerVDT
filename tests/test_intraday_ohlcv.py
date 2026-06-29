from datetime import datetime

import polars as pl

from scripts.run_intraday_ohlcv_backfill import normalize_intraday_frame


def test_normalize_intraday_frame_builds_one_minute_schema() -> None:
    frame = normalize_intraday_frame(
        pl.DataFrame(
            {
                "time": [datetime(2026, 6, 26, 9, 15), datetime(2026, 6, 26, 9, 16)],
                "open": [70.0, 70.2],
                "high": [70.3, 70.4],
                "low": [69.9, 70.1],
                "close": [70.2, 70.3],
                "volume": [1000, 1200],
            }
        ),
        "fpt",
    )

    assert frame.height == 2
    assert frame.get_column("ticker").to_list() == ["FPT", "FPT"]
    assert frame.get_column("resolution").to_list() == ["1m", "1m"]
    assert frame.schema["minute_ts"] == pl.Datetime
