from datetime import datetime

import polars as pl

from src.api.dashboard_api import bronze_realtime_vwap_rows, bronze_realtime_vwap_series


def write_ticks(base_dir, rows):
    output = base_dir / "year=2026" / "month=06" / "day=26" / "data.parquet"
    output.parent.mkdir(parents=True)
    pl.DataFrame(rows).write_parquet(output)


def test_bronze_realtime_vwap_rows_returns_latest_dnse_ticks(tmp_path):
    write_ticks(
        tmp_path,
        {
            "ticker": ["VCB", "VCB", "FPT"],
            "trade_ts": [
                datetime(2026, 6, 26, 9, 15, 1),
                datetime(2026, 6, 26, 9, 15, 20),
                datetime(2026, 6, 26, 9, 16, 1),
            ],
            "price": [100.0, 110.0, 200.0],
            "volume": [10, 30, 20],
            "raw_json": ["{}", "{}", "{}"],
        },
    )

    rows = bronze_realtime_vwap_rows(tmp_path)

    assert {row["ticker"] for row in rows} == {"VCB", "FPT"}
    vcb = next(row for row in rows if row["ticker"] == "VCB")
    assert vcb["price"] == 110.0
    assert vcb["sessionVwap"] == 107.5


def test_bronze_realtime_vwap_series_returns_chart_shape(tmp_path):
    write_ticks(
        tmp_path,
        {
            "ticker": ["VCB", "VCB"],
            "trade_ts": [
                datetime(2026, 6, 26, 9, 15, 1),
                datetime(2026, 6, 26, 9, 16, 1),
            ],
            "price": [100.0, 120.0],
            "volume": [10, 30],
            "raw_json": ["{}", "{}"],
        },
    )

    series = bronze_realtime_vwap_series("VCB", tmp_path)

    assert [point["time"] for point in series] == ["09:15", "09:16"]
    assert series[-1]["price"] == 120.0
    assert series[-1]["sessionVwap"] == 115.0
