from __future__ import annotations

from datetime import date, datetime
import json
import os
from pathlib import Path
import socket
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import polars as pl

from src.common.clickhouse_client import create_client
from src.loaders.load_fact_realtime_vwap import build_fact_realtime_vwap


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DNSE_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local" / "dnse" / "trades"


app = FastAPI(title="VNStock Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clean(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


def rows(sql: str) -> list[dict[str, Any]]:
    client = create_client()
    result = client.query(sql)
    return [
        {column: clean(value) for column, value in zip(result.column_names, row, strict=True)}
        for row in result.result_rows
    ]


def scalar(sql: str, default: Any = None) -> Any:
    result = create_client().query(sql)
    if not result.result_rows:
        return default
    return clean(result.result_rows[0][0])


def quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        value = 0
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_signed(value: float | int | None, digits: int = 2) -> str:
    value = float(value or 0)
    sign = "+" if value >= 0 else ""
    return sign + fmt_number(value, digits)


def build_stock_query(order_by: str, limit: int) -> str:
    return f"""
        SELECT
          f.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), f.ticker) AS name,
          ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
          ifNull(nullIf(s.exchange, ''), 'NA') AS exchange,
          f.close AS price,
          f.price_change AS change,
          f.pct_change AS pct,
          f.volume AS volume,
          f.value AS value
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        ORDER BY {order_by}
        LIMIT {limit}
    """


def stock_table(order_by: str, limit: int) -> list[dict[str, Any]]:
    data = rows(build_stock_query(order_by, limit))
    return [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "exchange": row["exchange"],
            "price": row["price"],
            "change": row["change"],
            "pct": row["pct"],
            "volume": row["volume"],
            "sector": row["sector"],
            **({"value": row["value"]} if "value DESC" in order_by else {}),
        }
        for row in data
    ]


def clickhouse_available(timeout: float = 0.2) -> bool:
    host = os.getenv("CLICKHOUSE_HOST", "localhost")
    port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: clean(value) for key, value in row.items()}


def latest_dnse_bronze_ticks(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> pl.DataFrame:
    """Read the newest local DNSE Bronze ticks when ClickHouse is unavailable."""
    paths = sorted(base_dir.glob("year=*/month=*/day=*/data.parquet"))
    if not paths:
        return pl.DataFrame(
            schema={
                "ticker": pl.String,
                "trade_ts": pl.Datetime,
                "price": pl.Float64,
                "volume": pl.Int64,
            }
        )

    ticks = pl.concat(
        [pl.read_parquet(path).select(["ticker", "trade_ts", "price", "volume"]) for path in paths],
        how="diagonal_relaxed",
    ).drop_nulls(["ticker", "trade_ts", "price", "volume"])
    if ticks.is_empty():
        return ticks

    latest_date = ticks.select(pl.col("trade_ts").dt.date().max()).item()
    latest_ticks = ticks.filter(pl.col("trade_ts").dt.date() == latest_date)
    metadata = latest_subscription_metadata(base_dir)
    symbols = metadata.get("symbols")
    if isinstance(symbols, list) and symbols:
        allowed_symbols = {str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}
        latest_ticks = latest_ticks.filter(pl.col("ticker").is_in(sorted(allowed_symbols)))
    market_hour_ticks = latest_ticks.filter(pl.col("trade_ts").dt.hour().is_between(9, 15))
    if not market_hour_ticks.is_empty():
        return market_hour_ticks
    return latest_ticks


def latest_subscription_metadata(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> dict[str, Any]:
    paths = sorted(base_dir.glob("year=*/month=*/day=*/subscription.json"))
    if not paths:
        return {}
    try:
        return json.loads(paths[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def bronze_realtime_vwap_frame(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> pl.DataFrame:
    ticks = latest_dnse_bronze_ticks(base_dir)
    if ticks.is_empty():
        return pl.DataFrame()
    return build_fact_realtime_vwap(ticks)


def bronze_realtime_vwap_rows(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> list[dict[str, Any]]:
    frame = bronze_realtime_vwap_frame(base_dir)
    if frame.is_empty():
        return []

    latest_rows = (
        frame.sort(["ticker", "minute_ts"])
        .group_by("ticker", maintain_order=True)
        .agg(
            pl.col("close_price").last().alias("price"),
            pl.col("session_vwap").last().alias("sessionVwap"),
            pl.col("session_vwap").last().alias("vwap"),
            pl.col("price_vs_session_vwap_pct").last().alias("deviation"),
            pl.col("session_volume").last().alias("volume"),
            pl.col("total_volume").mean().alias("volSma"),
            (pl.col("price_vs_session_vwap_pct").abs() >= 2).sum().alias("alerts"),
            pl.col("minute_ts").max().alias("updatedAt"),
        )
        .with_columns(
            pl.col("ticker").alias("name"),
            pl.lit("Realtime").alias("sector"),
            pl.lit("DNSE").alias("exchange"),
        )
        .select(
            [
                "ticker",
                "name",
                "sector",
                "exchange",
                "price",
                "sessionVwap",
                "vwap",
                "deviation",
                "volume",
                "volSma",
                "alerts",
                "updatedAt",
            ]
        )
        .sort(pl.col("deviation").abs(), descending=True)
    )
    return [clean_row(row) for row in latest_rows.to_dicts()]


def bronze_realtime_vwap_series(ticker: str, base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> list[dict[str, Any]]:
    symbol = ticker.upper()
    frame = bronze_realtime_vwap_frame(base_dir)
    if frame.is_empty():
        return []

    series = (
        frame.filter(pl.col("ticker") == symbol)
        .sort("minute_ts")
        .select(
            [
                pl.col("minute_ts").dt.strftime("%H:%M").alias("time"),
                pl.col("close_price").alias("price"),
                pl.col("vwap_1m").alias("vwap"),
                pl.col("session_vwap").alias("sessionVwap"),
                pl.col("total_volume").alias("volume"),
                pl.col("price_vs_session_vwap_pct").alias("deviation"),
            ]
        )
    )
    return [clean_row(row) for row in series.to_dicts()]


def latest_bronze_realtime_minute(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> Any:
    frame = bronze_realtime_vwap_frame(base_dir)
    if frame.is_empty():
        return None
    return clean(frame.select(pl.col("minute_ts").max()).item())


def bronze_universe_count(base_dir: Path = DEFAULT_DNSE_BRONZE_DIR) -> int | None:
    metadata = latest_subscription_metadata(base_dir)
    symbol_count = metadata.get("symbol_count")
    if isinstance(symbol_count, int):
        return symbol_count
    symbols = metadata.get("symbols")
    if isinstance(symbols, list):
        return len(symbols)
    return None


def as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return None


def bronze_is_newer_than(value: Any) -> bool:
    bronze_latest = as_datetime(latest_bronze_realtime_minute())
    clickhouse_latest = as_datetime(value)
    if bronze_latest is None:
        return False
    if clickhouse_latest is None:
        return True
    return bronze_latest > clickhouse_latest


@app.get("/api/health")
def health() -> dict[str, Any]:
    latest_price_date = None
    if clickhouse_available():
        try:
            latest_price_date = scalar("SELECT max(trading_date) FROM fact_daily_price")
            latest_realtime_minute = scalar("SELECT max(minute_ts) FROM fact_realtime_vwap")
            if bronze_is_newer_than(latest_realtime_minute):
                latest_realtime_minute = latest_bronze_realtime_minute()
                realtime_source = "dnse_bronze"
            else:
                realtime_source = "clickhouse"
        except Exception:
            latest_realtime_minute = latest_bronze_realtime_minute()
            realtime_source = "dnse_bronze"
    else:
        latest_realtime_minute = latest_bronze_realtime_minute()
        realtime_source = "dnse_bronze"

    return {
        "ok": True,
        "latestPriceDate": latest_price_date,
        "latestRealtimeMinute": latest_realtime_minute,
        "realtimeSource": realtime_source,
        "realtimeUniverseCount": bronze_universe_count(),
    }


@app.get("/api/stocks")
def get_stocks(
    exchange: str = Query("HOSE"),
    q: str = Query(""),
    limit: int = Query(2000, ge=1, le=3000),
) -> dict[str, Any]:
    filters = []
    filters.append("s.exchange = 'HOSE'")
    if q:
        needle = quote(f"%{q.upper()}%")
        filters.append(
            f"(upper(s.ticker) LIKE {needle} OR upper(s.company_name) LIKE {needle})"
        )
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    data = rows(
        f"""
        SELECT
          s.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), s.ticker) AS name,
          ifNull(nullIf(s.exchange, ''), 'NA') AS exchange,
          ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
          s.market_cap_latest AS marketCap,
          s.shares_outstanding AS sharesOutstanding,
          if(count(f.ticker) > 0, 1, 0) AS hasPriceData
        FROM dim_stock s
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        LEFT JOIN fact_daily_price f ON s.ticker = f.ticker
        {where_sql}
        GROUP BY s.ticker, name, exchange, sector, marketCap, sharesOutstanding
        ORDER BY s.ticker
        LIMIT {limit}
        """
    )
    return {"count": len(data), "data": data}


@app.get("/api/stocks/{ticker}/candles")
def get_stock_candles(
    ticker: str,
    limit: int = Query(260, ge=10, le=2000),
) -> dict[str, Any]:
    symbol = ticker.upper()
    data = rows(
        f"""
        SELECT
          formatDateTime(toDateTime(trading_date), '%Y-%m-%d') AS date,
          open,
          high,
          low,
          close,
          volume,
          ifNull(sma_20, close) AS sma20,
          ifNull(ema_12, close) AS ema12,
          ifNull(rsi_14, 50) AS rsi,
          ifNull(macd, 0) AS macd,
          ifNull(macd_signal, 0) AS macdSignal,
          ifNull(bb_upper, high) AS bbUpper,
          ifNull(bb_lower, low) AS bbLower
        FROM fact_daily_price
        WHERE ticker = {quote(symbol)}
          AND ticker IN (SELECT ticker FROM dim_stock WHERE exchange = 'HOSE')
        ORDER BY trading_date DESC
        LIMIT {limit}
        """
    )[::-1]
    if not data:
        raise HTTPException(status_code=404, detail=f"No price data for ticker {symbol}")
    return {"ticker": symbol, "count": len(data), "data": data}


@app.get("/api/market/overview")
def get_market_overview() -> dict[str, Any]:
    if not clickhouse_available():
        raise HTTPException(status_code=503, detail="ClickHouse is unavailable")

    latest_price_date = scalar("SELECT max(trading_date) FROM fact_daily_price")
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    top_gainers = stock_table("f.pct_change DESC", 100)
    top_losers = stock_table("f.pct_change ASC", 100)
    top_liquidity = [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "exchange": row["exchange"],
            "volume": row["volume"],
            "value": row["value"],
            "price": row["price"],
        }
        for row in rows(build_stock_query("f.value DESC", 100))
    ]

    sector_performance = rows(
        """
        SELECT
          ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
          avg(f.pct_change) AS pct,
          sum(f.value) AS value
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        GROUP BY sector
        ORDER BY abs(pct) DESC
        LIMIT 12
        """
    )
    sector_performance_by_exchange = rows(
        """
        SELECT
          ifNull(nullIf(s.exchange, ''), 'NA') AS exchange,
          ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
          avg(f.pct_change) AS pct,
          sum(f.value) AS value
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        GROUP BY exchange, sector
        ORDER BY exchange, abs(pct) DESC
        """
    )
    market_index_rows = rows(
        """
        SELECT index_id, close_point, point_change, pct_change, total_volume, total_value,
               advance_count, decline_count, unchanged_count
        FROM fact_market_index
        WHERE trading_date = (SELECT max(trading_date) FROM fact_market_index)
          AND index_id IN ('VNINDEX', 'VN30')
        ORDER BY index_id
        """
    )
    index_labels = {
        "VNINDEX": "VN-Index",
        "VN30": "VN30",
    }
    market_indices = [
        {
            "label": index_labels.get(row["index_id"], row["index_id"]),
            "value": fmt_number(row["close_point"], 2),
            "chg": fmt_signed(row["point_change"], 2),
            "pct": fmt_signed(row["pct_change"], 2) + "%",
            "up": row["point_change"] >= 0,
            "rawPct": row["pct_change"],
        }
        for row in market_index_rows
    ]
    preferred_all = ["VN-Index", "VN30"]
    market_indices_all = sorted(
        market_indices,
        key=lambda row: preferred_all.index(row["label"]) if row["label"] in preferred_all else 99,
    )
    vnindex = next(
        (row for row in market_index_rows if row["index_id"] == "VNINDEX"),
        market_index_rows[0] if market_index_rows else {},
    )
    market_overview_stats = {
        "totalValue": fmt_number(sum(row["total_value"] for row in market_index_rows) / 1_000_000_000, 1) + " tỷ",
        "totalVolume": fmt_number(sum(row["total_volume"] for row in market_index_rows) / 1_000_000, 1) + " M",
        "breadth": f"{vnindex.get('advance_count', 0)} / {vnindex.get('decline_count', 0)}",
        "breadthSub": f"Tăng / Giảm / Đứng: {vnindex.get('unchanged_count', 0)}",
    }
    index_exchange_map = {
        "VNINDEX": "HOSE",
        "VN30": "HOSE",
    }
    market_stats_by_exchange: dict[str, dict[str, str]] = {"ALL": market_overview_stats}
    breadth_data_by_exchange: dict[str, list[dict[str, Any]]] = {}
    for row in market_index_rows:
        key = index_exchange_map.get(row["index_id"], row["index_id"])
        if row["index_id"] == "VN30":
            continue
        market_stats_by_exchange[key] = {
            "totalValue": fmt_number(row["total_value"] / 1_000_000_000, 1) + " tỷ",
            "totalVolume": fmt_number(row["total_volume"] / 1_000_000, 1) + " M",
            "breadth": f"{row['advance_count']} / {row['decline_count']}",
            "breadthSub": f"Tăng / Giảm / Đứng: {row['unchanged_count']}",
        }
        breadth_data_by_exchange[key] = [
            {"name": "Tăng", "value": row["advance_count"], "fill": "#00d97e"},
            {"name": "Giảm", "value": row["decline_count"], "fill": "#ff4d6d"},
            {"name": "Đứng", "value": row["unchanged_count"], "fill": "#6b7fa3"},
        ]

    breadth_data = [
        {"name": "Tăng", "value": vnindex.get("advance_count", 0), "fill": "#00d97e"},
        {"name": "Giảm", "value": vnindex.get("decline_count", 0), "fill": "#ff4d6d"},
        {"name": "Đứng", "value": vnindex.get("unchanged_count", 0), "fill": "#6b7fa3"},
    ]
    breadth_data_by_exchange["ALL"] = breadth_data
    stock_count_rows = rows(
        """
        SELECT ifNull(nullIf(s.exchange, ''), 'NA') AS exchange, countDistinct(f.ticker) AS count
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        GROUP BY exchange
        """
    )
    stock_counts_by_exchange = {row["exchange"]: row["count"] for row in stock_count_rows}
    stock_counts_by_exchange["ALL"] = sum(stock_counts_by_exchange.values())
    index_change_bars = [{"label": row["label"], "pct": row["rawPct"]} for row in market_indices]
    vn_index_history = rows(
        """
        SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS time, close_point AS value
        FROM fact_market_index
        WHERE index_id = 'VNINDEX'
        ORDER BY trading_date DESC
        LIMIT 30
        """
    )[::-1]
    index_history_by_exchange = {
        key: rows(
            f"""
            SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS time, close_point AS value
            FROM fact_market_index
            WHERE index_id = {quote(index_id)}
            ORDER BY trading_date DESC
            LIMIT 30
            """
        )[::-1]
        for key, index_id in {
            "ALL": "VNINDEX",
            "HOSE": "VNINDEX",
        }.items()
    }

    return {
        "source": "clickhouse",
        "dataSnapshotMeta": {
            "generatedAt": generated_at,
            "latestPriceDate": latest_price_date,
        },
        "marketIndicesAll": market_indices_all,
        "marketOverviewStats": market_overview_stats,
        "marketStatsByExchange": market_stats_by_exchange,
        "stockCountsByExchange": stock_counts_by_exchange,
        "breadthData": breadth_data,
        "breadthDataByExchange": breadth_data_by_exchange,
        "indexChangeBars": index_change_bars,
        "vnIndexHistory": vn_index_history,
        "indexHistoryByExchange": index_history_by_exchange,
        "topGainers": top_gainers,
        "topLosers": top_losers,
        "topLiquidity": top_liquidity,
        "sectorPerformance": sector_performance,
        "sectorPerformanceByExchange": sector_performance_by_exchange,
    }


@app.get("/api/realtime/vwap")
def get_realtime_vwap() -> dict[str, Any]:
    data = []
    latest_minute = None
    source = "dnse_bronze"
    if clickhouse_available():
        try:
            clickhouse_latest = scalar("SELECT max(minute_ts) FROM fact_realtime_vwap")
            if bronze_is_newer_than(clickhouse_latest):
                raise RuntimeError("DNSE Bronze is newer than ClickHouse realtime VWAP")
            data = rows(
                """
                SELECT
                  f.ticker AS ticker,
                  ifNull(nullIf(s.company_name, ''), f.ticker) AS name,
                  ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
                  ifNull(nullIf(s.exchange, ''), 'NA') AS exchange,
                  argMax(f.close_price, f.minute_ts) AS price,
                  argMax(f.session_vwap, f.minute_ts) AS sessionVwap,
                  argMax(f.session_vwap, f.minute_ts) AS vwap,
                  argMax(f.price_vs_session_vwap_pct, f.minute_ts) AS deviation,
                  argMax(f.session_volume, f.minute_ts) AS volume,
                  avg(f.total_volume) AS volSma,
                  countIf(abs(f.price_vs_session_vwap_pct) >= 2) AS alerts,
                  max(f.minute_ts) AS updatedAt
                FROM fact_realtime_vwap f
                LEFT JOIN dim_stock s ON f.ticker = s.ticker
                LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
                WHERE s.exchange = 'HOSE'
                GROUP BY f.ticker, name, sector, exchange
                ORDER BY abs(deviation) DESC
                """
            )
            latest_minute = clickhouse_latest
            source = "clickhouse"
        except Exception:
            pass

    if source != "clickhouse":
        data = bronze_realtime_vwap_rows()
        latest_minute = latest_bronze_realtime_minute()

    return {
        "count": len(data),
        "activeCount": len(data),
        "universeCount": bronze_universe_count() or len(data),
        "latestMinute": latest_minute,
        "source": source,
        "data": data,
    }


@app.get("/api/realtime/vwap/{ticker}/series")
def get_realtime_vwap_series(ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
    data = []
    source = "dnse_bronze"
    if clickhouse_available():
        try:
            clickhouse_latest = scalar("SELECT max(minute_ts) FROM fact_realtime_vwap")
            if bronze_is_newer_than(clickhouse_latest):
                raise RuntimeError("DNSE Bronze is newer than ClickHouse realtime VWAP")
            data = rows(
                f"""
                SELECT
                  formatDateTime(minute_ts, '%H:%M') AS time,
                  close_price AS price,
                  vwap_1m AS vwap,
                  session_vwap AS sessionVwap,
                  total_volume AS volume,
                  price_vs_session_vwap_pct AS deviation
                FROM fact_realtime_vwap
                WHERE ticker = {quote(symbol)}
                  AND ticker IN (SELECT ticker FROM dim_stock WHERE exchange = 'HOSE')
                ORDER BY minute_ts
                """
            )
            source = "clickhouse"
        except Exception:
            pass

    if source != "clickhouse":
        data = bronze_realtime_vwap_series(symbol)

    if not data:
        raise HTTPException(status_code=404, detail=f"No realtime VWAP data for ticker {symbol}")
    return {"ticker": symbol, "count": len(data), "source": source, "data": data}
