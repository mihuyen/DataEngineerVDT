from __future__ import annotations

from datetime import date, datetime, time
import json
import logging
import os
from pathlib import Path
import socket
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
from pydantic import BaseModel
import requests

from src.common.clickhouse_client import create_client
from src.common.kafka_lag import get_consumer_group_lag
from src.common.postgres_client import create_connection
from src.loaders.load_fact_realtime_vwap import build_fact_realtime_vwap


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DNSE_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze_local" / "dnse" / "trades"
QUALITY_REPORTS_DIR = PROJECT_ROOT / "quality_reports"
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
REALTIME_FRESHNESS_SECONDS = 90

AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_DAG_ID = os.getenv("AIRFLOW_DAG_ID", "stock_lakehouse_daily")
AIRFLOW_AUTH = (os.getenv("AIRFLOW_USER", "admin"), os.getenv("AIRFLOW_PASSWORD", "admin"))

# Single-user app (same convention as scripts/init_user_alerts.py's demo_user) --
# there is no login/session system, so every watchlist/alert-rule row
# belongs to this one user.
DEFAULT_USER_ID = "demo_user"

ALERT_CONDITION_COLORS = {
    "RSI_ABOVE": "#ff4d6d",
    "RSI_BELOW": "#00d97e",
    "BB_BREAK": "#8b5cf6",
    "VWAP_DEVIATION": "#a855f7",
    "PRICE_ABOVE": "#3b82f6",
    "PRICE_BELOW": "#06b6d4",
}

PIPELINE_TABLES = [
    ("fact_daily_price", "trading_date"),
    ("fact_market_index", "trading_date"),
    ("fact_news_sentiment_daily", "news_date"),
    ("fact_intraday_ohlcv", "minute_ts"),
    ("fact_realtime_vwap", "minute_ts"),
    ("fact_alert_event", "triggered_at"),
]


app = FastAPI(title="VNStock Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def ensure_watchlist_table() -> None:
    """Create watchlist if missing.

    Unlike user_alerts (created by the alert-engine container on startup),
    nothing else in the stack owns this table, so the API creates it itself
    the first time it boots.
    """
    ddl_dir = PROJECT_ROOT / "sql" / "ddl_postgres"
    try:
        with create_connection() as conn, conn.cursor() as cur:
            cur.execute((ddl_dir / "watchlist.sql").read_text(encoding="utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Could not ensure watchlist table")


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
    """Per-ticker table with the latest EOD bar as reference price, live-overlaid.

    f.close (yesterday's close, since fact_daily_price only refreshes once a
    day after the close) is exactly the "giá tham chiếu" Vietnamese price
    boards use as the day's baseline. When fact_realtime_vwap has a row for
    this ticker today, price/change/pct/volume/value are overridden with the
    live close and today's cumulative session volume/value -- mirroring how
    DNSE/SSI/VNDirect show live intraday prices against yesterday's
    reference rather than a static EOD snapshot during market hours. Falls
    back to the EOD value automatically (via ifNull) for any ticker with no
    intraday rows yet (pre-open, or DNSE/Kafka not running).
    """
    return f"""
        WITH live AS (
            SELECT
              ticker,
              -- toNullable() matters: fact_realtime_vwap's columns are not
              -- Nullable, so a plain LEFT JOIN against a non-matching ticker
              -- fills these with the column's zero default (0.0), not NULL --
              -- isNotNull(l.live_price) would then wrongly read as "live" for
              -- every ticker DNSE has no quote for today, reporting price=0.
              toNullable(argMax(close_price, minute_ts)) AS live_price,
              toNullable(argMax(session_volume, minute_ts)) AS live_volume,
              toNullable(argMax(session_value, minute_ts)) AS live_value,
              toNullable(max(minute_ts)) AS live_minute_ts
            FROM fact_realtime_vwap
            WHERE toDate(minute_ts) = today()
            GROUP BY ticker
        )
        SELECT
          f.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), f.ticker) AS name,
          ifNull(nullIf(sec.sector_name, ''), ifNull(nullIf(s.sector_id, ''), 'Khác')) AS sector,
          ifNull(nullIf(s.exchange, ''), 'NA') AS exchange,
          ifNull(l.live_price, f.close) AS price,
          if(isNotNull(l.live_price) AND f.close != 0, l.live_price - f.close, f.price_change) AS change,
          if(isNotNull(l.live_price) AND f.close != 0, (l.live_price - f.close) / f.close * 100, f.pct_change) AS pct,
          ifNull(l.live_volume, f.volume) AS volume,
          ifNull(l.live_value, f.value) AS value,
          isNotNull(l.live_price) AS isLive,
          l.live_minute_ts AS liveAsOf
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        LEFT JOIN live l ON f.ticker = l.ticker
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
            "isLive": row["isLive"],
            "liveAsOf": row["liveAsOf"],
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

    frames = []
    for path in paths:
        frame = pl.read_parquet(path)
        if "data_source" not in frame.columns:
            frame = frame.with_columns(pl.lit("DNSE").alias("data_source"))
        frames.append(frame.select(["ticker", "trade_ts", "price", "volume", "data_source"]))
    ticks = pl.concat(frames, how="diagonal_relaxed").drop_nulls(
        ["ticker", "trade_ts", "price", "volume"]
    )
    if ticks.is_empty():
        return ticks

    latest_date = ticks.select(pl.col("trade_ts").dt.date().max()).item()
    latest_ticks = ticks.filter(pl.col("trade_ts").dt.date() == latest_date)
    latest_ticks = latest_ticks.filter(pl.col("data_source").str.to_uppercase() == "DNSE")
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
            pl.col("data_source").last().alias("dataSource"),
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
                "dataSource",
            ]
        )
        .sort(pl.col("deviation").abs(), descending=True)
    )
    return [clean_row(row) for row in latest_rows.to_dicts()]


def bronze_realtime_vwap_series(
    ticker: str, base_dir: Path = DEFAULT_DNSE_BRONZE_DIR
) -> list[dict[str, Any]]:
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


def market_session_status(now: datetime | None = None) -> dict[str, Any]:
    local_now = now or datetime.now(VIETNAM_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=VIETNAM_TZ)
    else:
        local_now = local_now.astimezone(VIETNAM_TZ)

    current_time = local_now.time().replace(tzinfo=None)
    if local_now.weekday() >= 5:
        status, label = "closed", "Thị trường đã đóng cửa"
    elif current_time < time(9, 0):
        status, label = "pre_open", "Chưa mở cửa"
    elif current_time < time(11, 30):
        status, label = "live", "Đang giao dịch"
    elif current_time < time(13, 0):
        status, label = "lunch_break", "Nghỉ giữa phiên"
    elif current_time < time(15, 0):
        status, label = "live", "Đang giao dịch"
    else:
        status, label = "closed", "Thị trường đã đóng cửa"

    return {"marketStatus": status, "statusLabel": label, "marketNow": local_now.isoformat()}


def realtime_session_metadata(latest_minute: Any, source: str) -> dict[str, Any]:
    session = market_session_status()
    latest = as_datetime(latest_minute)
    now = datetime.now(VIETNAM_TZ)
    stale_seconds = None
    session_date = None
    if latest is not None:
        session_date = latest.date().isoformat()
        localized_latest = (
            latest.replace(tzinfo=VIETNAM_TZ)
            if latest.tzinfo is None
            else latest.astimezone(VIETNAM_TZ)
        )
        stale_seconds = max(0, int((now - localized_latest).total_seconds()))
    is_live = session["marketStatus"] == "live"
    is_fresh = bool(
        is_live
        and session_date == now.date().isoformat()
        and stale_seconds is not None
        and stale_seconds <= REALTIME_FRESHNESS_SECONDS
    )
    return {
        **session,
        "sessionDate": session_date,
        "staleSeconds": stale_seconds,
        "isLive": is_live,
        "isFresh": is_fresh,
        "dataMode": "REAL",
        "dataProvider": "DNSE",
        "source": source,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    latest_price_date = None
    if clickhouse_available():
        try:
            latest_price_date = scalar("SELECT max(trading_date) FROM fact_daily_price")
            latest_realtime_minute = scalar(
                "SELECT max(minute_ts) FROM fact_realtime_vwap WHERE data_source = 'DNSE'"
            )
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
        **realtime_session_metadata(latest_realtime_minute, realtime_source),
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
        filters.append(f"(upper(s.ticker) LIKE {needle} OR upper(s.company_name) LIKE {needle})")
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
          ifNull(bb_lower, low) AS bbLower,
          market_cap AS marketCap,
          value
        FROM fact_daily_price_indicators
        WHERE ticker = {quote(symbol)}
          AND ticker IN (SELECT ticker FROM dim_stock WHERE exchange = 'HOSE')
        ORDER BY trading_date DESC
        LIMIT {limit}
        """
    )[::-1]
    if not data:
        raise HTTPException(status_code=404, detail=f"No price data for ticker {symbol}")
    latest_price_date = data[-1]["date"]
    return {
        "ticker": symbol,
        "count": len(data),
        "latestPriceDate": latest_price_date,
        "dataMode": "EOD",
        "isRealtime": False,
        **market_session_status(),
        "data": data,
    }


INTRADAY_RESOLUTION_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}


@app.get("/api/stocks/{ticker}/intraday")
def get_stock_intraday(
    ticker: str,
    resolution: str = Query("5m", pattern="^(1m|5m|15m|30m|1h)$"),
    trading_date: str | None = Query(
        None, description="YYYY-MM-DD, defaults to the latest session ingested"
    ),
) -> dict[str, Any]:
    """Intraday OHLCV at a chosen timeframe, aggregated on read from the 1-minute candles.

    fact_intraday_ohlcv only ever stores the 1m grain (from DNSE's ohlc_closed.1
    channel and the Vnstock backfill) -- 5m/15m/30m/1h are computed here with
    toStartOfInterval rather than materialized as separate tables, since this
    is read-time aggregation over a single day's candles, not a heavy job.
    """
    symbol = ticker.upper()
    minutes = INTRADAY_RESOLUTION_MINUTES[resolution]

    try:
        resolved_date = trading_date or scalar(
            "SELECT max(trading_date) FROM fact_intraday_ohlcv "
            f"WHERE ticker = {quote(symbol)} AND is_final = 1"
        )
        if resolved_date is None:
            raise HTTPException(status_code=404, detail=f"No intraday data for ticker {symbol}")

        data = rows(
            f"""
            SELECT
              formatDateTime(bucket, '%Y-%m-%d %H:%i') AS time,
              argMin(open, minute_ts) AS open,
              max(high) AS high,
              min(low) AS low,
              argMax(close, minute_ts) AS close,
              sum(volume) AS volume
            FROM
            (
              SELECT
                minute_ts,
                toStartOfInterval(minute_ts, INTERVAL {minutes} MINUTE) AS bucket,
                argMax(open, (data_source = 'DNSE', ingested_at)) AS open,
                argMax(high, (data_source = 'DNSE', ingested_at)) AS high,
                argMax(low, (data_source = 'DNSE', ingested_at)) AS low,
                argMax(close, (data_source = 'DNSE', ingested_at)) AS close,
                argMax(volume, (data_source = 'DNSE', ingested_at)) AS volume
              FROM fact_intraday_ohlcv
              WHERE ticker = {quote(symbol)}
                AND trading_date = toDate({quote(str(resolved_date))})
                AND resolution = '1m'
                AND is_final = 1
              GROUP BY minute_ts
            )
            GROUP BY bucket
            ORDER BY bucket
            """
        )
        latest_minute = data[-1]["time"] if data else None
        source_rows = rows(
            f"""
            SELECT groupUniqArray(data_source) AS sources
            FROM fact_intraday_ohlcv
            WHERE ticker = {quote(symbol)}
              AND trading_date = toDate({quote(str(resolved_date))})
              AND resolution = '1m'
            """
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Intraday candle storage is unavailable"
        ) from exc

    if not data:
        raise HTTPException(status_code=404, detail=f"No intraday data for ticker {symbol}")
    sources = source_rows[0].get("sources", []) if source_rows else []
    return {
        "ticker": symbol,
        "resolution": resolution,
        "tradingDate": str(resolved_date),
        "latestMinute": latest_minute,
        "sources": sources,
        "dataMode": "INTRADAY",
        **market_session_status(),
        "count": len(data),
        "data": data,
    }


@app.get("/api/market/overview")
def get_market_overview() -> dict[str, Any]:
    if not clickhouse_available():
        raise HTTPException(status_code=503, detail="ClickHouse is unavailable")

    latest_price_date = scalar("SELECT max(trading_date) FROM fact_daily_price")
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    live_overlay = rows(
        "SELECT count(DISTINCT ticker) AS live_tickers, max(minute_ts) AS live_as_of "
        "FROM fact_realtime_vwap WHERE toDate(minute_ts) = today()"
    )
    live_ticker_count = live_overlay[0]["live_tickers"] if live_overlay else 0
    live_as_of = live_overlay[0]["live_as_of"] if live_overlay else None
    # Rank by the live-overlaid pct/value (the SELECT aliases), not the
    # EOD-only f.pct_change/f.value, so the ranking matches what the live
    # price column on screen actually shows during market hours.
    top_gainers = stock_table("pct DESC", 100)
    top_losers = stock_table("pct ASC", 100)
    top_liquidity = [
        {
            "ticker": row["ticker"],
            "name": row["name"],
            "exchange": row["exchange"],
            "volume": row["volume"],
            "value": row["value"],
            "price": row["price"],
            "isLive": row["isLive"],
            "liveAsOf": row["liveAsOf"],
        }
        for row in rows(build_stock_query("value DESC", 100))
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
        "totalValue": fmt_number(
            sum(row["total_value"] for row in market_index_rows) / 1_000_000_000, 1
        )
        + " tỷ",
        "totalVolume": fmt_number(
            sum(row["total_volume"] for row in market_index_rows) / 1_000_000, 1
        )
        + " M",
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
        # marketIndicesAll/sector aggregates are still EOD-only (a live
        # VN-Index/sector-average needs index-weighted methodology, not
        # implemented here) -- but the per-ticker tables below (top
        # gainers/losers/liquidity) are live-overlaid whenever
        # fact_realtime_vwap has a row for that ticker today.
        "dataMode": "EOD+LIVE" if live_ticker_count > 0 else "EOD",
        "isRealtime": live_ticker_count > 0,
        "liveTickerCount": live_ticker_count,
        "liveAsOf": clean(live_as_of) if live_as_of else None,
        **market_session_status(),
        "dataSnapshotMeta": {
            "generatedAt": generated_at,
            "latestPriceDate": latest_price_date,
            "label": "Phiên gần nhất đã hoàn tất",
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
            clickhouse_latest = scalar(
                "SELECT max(minute_ts) FROM fact_realtime_vwap WHERE data_source = 'DNSE'"
            )
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
                  max(f.minute_ts) AS updatedAt,
                  any(f.data_source) AS dataSource
                FROM fact_realtime_vwap f
                LEFT JOIN dim_stock s ON f.ticker = s.ticker
                LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
                WHERE s.exchange = 'HOSE'
                  AND f.data_source = 'DNSE'
                  AND f.trading_date = (
                    SELECT max(trading_date) FROM fact_realtime_vwap WHERE data_source = 'DNSE'
                  )
                GROUP BY f.ticker, name, sector, exchange
                ORDER BY abs(deviation) DESC
                """
            )
            latest_minute = clickhouse_latest
            source = "clickhouse_dnse"
        except Exception:
            pass

    if source != "clickhouse_dnse":
        data = bronze_realtime_vwap_rows()
        latest_minute = latest_bronze_realtime_minute()

    return {
        "count": len(data),
        "activeCount": len(data),
        "universeCount": bronze_universe_count() or len(data),
        "subscribedCount": bronze_universe_count() or len(data),
        "latestMinute": latest_minute,
        "source": source,
        "data": data,
        **realtime_session_metadata(latest_minute, source),
    }


@app.get("/api/realtime/vwap/{ticker}/series")
def get_realtime_vwap_series(ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
    data = []
    source = "dnse_bronze"
    if clickhouse_available():
        try:
            clickhouse_latest = scalar(
                "SELECT max(minute_ts) FROM fact_realtime_vwap WHERE data_source = 'DNSE'"
            )
            if bronze_is_newer_than(clickhouse_latest):
                raise RuntimeError("DNSE Bronze is newer than ClickHouse realtime VWAP")
            data = rows(
                f"""
                SELECT
                  formatDateTime(minute_ts, '%H:%i') AS time,
                  close_price AS price,
                  vwap_1m AS vwap,
                  session_vwap AS sessionVwap,
                  total_volume AS volume,
                  price_vs_session_vwap_pct AS deviation
                FROM fact_realtime_vwap
                WHERE ticker = {quote(symbol)}
                  AND data_source = 'DNSE'
                  AND trading_date = (
                    SELECT max(trading_date) FROM fact_realtime_vwap WHERE data_source = 'DNSE'
                  )
                  AND ticker IN (SELECT ticker FROM dim_stock WHERE exchange = 'HOSE')
                ORDER BY minute_ts
                """
            )
            source = "clickhouse_dnse"
        except Exception:
            pass

    if source != "clickhouse_dnse":
        data = bronze_realtime_vwap_series(symbol)

    if not data:
        raise HTTPException(status_code=404, detail=f"No realtime VWAP data for ticker {symbol}")
    return {"ticker": symbol, "count": len(data), "source": source, "data": data}


@app.get("/api/technical/signals")
def get_technical_signals(limit: int = Query(150, ge=10, le=2000)) -> dict[str, Any]:
    tracked_ticker_count = scalar(
        """
        SELECT countDistinct(f.ticker)
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        """,
        default=0,
    )
    raw = rows(
        f"""
        SELECT
          f.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), f.ticker) AS name,
          ifNull(f.rsi_14, 50) AS rsi,
          ifNull(f.macd, 0) AS macd,
          ifNull(f.macd_signal, 0) AS macdSignal,
          f.close AS close,
          ifNull(f.bb_upper, f.high) AS bbUpper,
          ifNull(f.bb_lower, f.low) AS bbLower,
          f.volume AS volume,
          ifNull(f.volume_sma_20, f.volume) AS volSma20,
          f.pct_change AS pct,
          f.overbought_flag AS overboughtFlag,
          f.oversold_flag AS oversoldFlag,
          f.breakout_flag AS breakoutFlag,
          f.breakdown_flag AS breakdownFlag
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
          AND (
            f.overbought_flag = 1 OR f.oversold_flag = 1 OR f.breakout_flag = 1 OR f.breakdown_flag = 1
            OR (f.macd > 0 AND f.macd > f.macd_signal)
            OR f.volume > 1.5 * ifNull(f.volume_sma_20, f.volume)
          )
        ORDER BY abs(f.pct_change) DESC
        LIMIT {limit}
        """
    )
    signals = []
    for row in raw:
        if row["breakoutFlag"]:
            signal = "breakout"
        elif row["breakdownFlag"]:
            signal = "breakdown"
        elif row["overboughtFlag"]:
            signal = "overbought"
        elif row["oversoldFlag"]:
            signal = "oversold"
        elif row["volume"] > 1.5 * (row["volSma20"] or row["volume"]):
            signal = "volume_spike"
        else:
            signal = "macd_positive"
        signals.append(
            {
                **{key: value for key, value in row.items() if not key.endswith("Flag")},
                "signal": signal,
            }
        )
    return {"trackedTickerCount": tracked_ticker_count, "count": len(signals), "data": signals}


@app.get("/api/news/sentiment")
def get_news_sentiment(days: int = Query(7, ge=1, le=60)) -> dict[str, Any]:
    by_ticker = rows(
        f"""
        SELECT
          n.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), n.ticker) AS name,
          sum(n.news_count) AS newsCount,
          max(n.source_count) AS sources,
          sum(n.positive_count) AS positive,
          sum(n.negative_count) AS negative,
          sum(n.neutral_count) AS neutral,
          avg(n.avg_sentiment_score) AS avgScore,
          argMax(n.top_headline, n.news_date) AS headline,
          formatDateTime(toDateTime(max(n.news_date)), '%Y-%m-%d') AS newsDate
        FROM fact_news_sentiment_daily n
        LEFT JOIN dim_stock s ON n.ticker = s.ticker
        WHERE n.news_date >= (SELECT max(news_date) FROM fact_news_sentiment_daily) - {days}
        GROUP BY ticker, name
        ORDER BY newsCount DESC
        """
    )
    by_date = rows(
        f"""
        SELECT
          formatDateTime(toDateTime(news_date), '%m-%d') AS date,
          sum(positive_count) AS positive,
          sum(negative_count) AS negative,
          sum(neutral_count) AS neutral
        FROM fact_news_sentiment_daily
        WHERE news_date >= (SELECT max(news_date) FROM fact_news_sentiment_daily) - {days}
        GROUP BY news_date
        ORDER BY news_date
        """
    )
    return {"count": len(by_ticker), "data": by_ticker, "byDate": by_date}


def alert_cooldown_lookup() -> dict[tuple[str, str, str], dict[str, int]]:
    """(user_id, condition_type, channel) -> {ticker_or_'ALL': cooldown_minutes}.

    fact_alert_event only stores the expanded concrete ticker (e.g. "AAA"),
    never the wildcard rule's literal ticker="ALL" in user_alerts (Postgres,
    not ClickHouse) -- so callers should fall back to the "ALL" entry when
    the concrete ticker isn't a key of its own.
    """
    try:
        with create_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, ticker, condition_type, channel, cooldown_minutes FROM user_alerts"
            )
            db_rows = cur.fetchall()
    except Exception:
        return {}
    lookup: dict[tuple[str, str, str], dict[str, int]] = {}
    for user_id, ticker, condition_type, channel, cooldown_minutes in db_rows:
        lookup.setdefault((user_id, condition_type, channel), {})[ticker] = cooldown_minutes
    return lookup


@app.get("/api/alerts")
def get_alerts(limit: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
    raw = rows(
        f"""
        SELECT
          alert_id AS id,
          formatDateTime(triggered_at, '%Y-%m-%d %H:%i') AS triggeredAt,
          user_id AS user,
          ticker AS ticker,
          condition_type AS condition,
          threshold_value AS threshold,
          actual_value AS actual,
          channel AS channel,
          delivery_status AS deliveryStatus,
          sent_at AS sentAt,
          formatDateTime(ifNull(sent_at, triggered_at), '%Y-%m-%d %H:%i') AS sentAtFormatted
        FROM fact_alert_event
        ORDER BY triggered_at DESC
        LIMIT {limit}
        """
    )
    cooldown_lookup = alert_cooldown_lookup()
    alerts = [
        {
            "id": row["id"],
            "triggeredAt": row["triggeredAt"],
            "user": row["user"],
            "ticker": row["ticker"],
            "condition": row["condition"],
            "threshold": row["threshold"],
            "actual": row["actual"],
            "channel": row["channel"],
            "status": "sent" if row["deliveryStatus"] == "sent" else "failed",
            "deliveryStatus": row["deliveryStatus"],
            "sentAt": row["sentAtFormatted"] if row["sentAt"] else None,
            "cooldown": cooldown_lookup.get(
                (row["user"], row["condition"], row["channel"]), {}
            ).get(
                row["ticker"],
                cooldown_lookup.get((row["user"], row["condition"], row["channel"]), {}).get(
                    "ALL", 0
                ),
            ),
        }
        for row in raw
    ]
    by_day = rows(
        """
        SELECT formatDateTime(triggered_at, '%m-%d') AS date, count(*) AS total
        FROM fact_alert_event
        GROUP BY date
        ORDER BY date
        """
    )
    by_condition = [
        {**row, "fill": ALERT_CONDITION_COLORS.get(row["type"], "#6b7fa3")}
        for row in rows(
            """
            SELECT condition_type AS type, count(*) AS count
            FROM fact_alert_event
            GROUP BY type
            ORDER BY count DESC
            """
        )
    ]
    return {"count": len(alerts), "data": alerts, "byDay": by_day, "byCondition": by_condition}


TASK_RECORD_TABLES = {
    "bronze_ohlcv": "fact_daily_price",
    "silver_ohlcv": "fact_daily_price",
    "bronze_market_index": "fact_market_index",
    "silver_market_index": "fact_market_index",
    "bronze_market_news": "fact_news_sentiment_daily",
    "silver_news": "fact_news_sentiment_daily",
    "check_alerts": "fact_alert_event",
}

AIRFLOW_STATE_MAP = {
    "success": "success",
    "failed": "failed",
    "upstream_failed": "failed",
    "running": "running",
    "queued": "running",
    "scheduled": "running",
}


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m{seconds}s"


def fetch_airflow_dag_status() -> list[dict[str, Any]] | None:
    """Read real task-level state for the latest DAG run from the Airflow REST API.

    Returns None (caller falls back to the ClickHouse-derived approximation)
    if Airflow is unreachable or has no runs yet — this keeps the dashboard
    usable while the scheduler/webserver is still starting up.
    """
    try:
        runs_resp = requests.get(
            f"{AIRFLOW_BASE_URL}/api/v1/dags/{AIRFLOW_DAG_ID}/dagRuns",
            params={"order_by": "-execution_date", "limit": 1},
            auth=AIRFLOW_AUTH,
            timeout=5,
        )
        runs_resp.raise_for_status()
        dag_runs = runs_resp.json().get("dag_runs", [])
        if not dag_runs:
            return None
        dag_run_id = dag_runs[0]["dag_run_id"]

        tasks_resp = requests.get(
            f"{AIRFLOW_BASE_URL}/api/v1/dags/{AIRFLOW_DAG_ID}/dagRuns/{dag_run_id}/taskInstances",
            auth=AIRFLOW_AUTH,
            timeout=5,
        )
        tasks_resp.raise_for_status()
        task_instances = tasks_resp.json().get("task_instances", [])
    except (requests.RequestException, KeyError, ValueError):
        return None

    record_counts: dict[str, int] = {}
    for table in set(TASK_RECORD_TABLES.values()):
        try:
            record_counts[table] = int(scalar(f"SELECT count(*) FROM {table}", default=0) or 0)
        except Exception:
            record_counts[table] = 0

    dag_status = []
    for task in sorted(task_instances, key=lambda t: t.get("start_date") or ""):
        airflow_state = task.get("state") or "scheduled"
        status = AIRFLOW_STATE_MAP.get(airflow_state, "failed")
        table = TASK_RECORD_TABLES.get(task["task_id"])
        dag_status.append(
            {
                "dag": task["task_id"],
                "status": status,
                "lastRun": (task.get("start_date") or "—")[:19].replace("T", " "),
                "duration": format_duration(task.get("duration")),
                "records": record_counts.get(table, 0) if table else 0,
                "tasks": 1,
                "failed": 1 if status == "failed" else 0,
            }
        )
    return dag_status or None


def load_quality_reports() -> list[dict[str, Any]]:
    if not QUALITY_REPORTS_DIR.exists():
        return []
    reports = []
    for path in sorted(QUALITY_REPORTS_DIR.glob("*_validation.json")):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return reports


@app.get("/api/pipeline/status")
def get_pipeline_status() -> dict[str, Any]:
    dag_status = fetch_airflow_dag_status()
    airflow_source = "airflow"
    if dag_status is None:
        # Airflow REST API unreachable (e.g. webserver still starting up):
        # fall back to inferring status from Gold table freshness/row counts.
        airflow_source = "clickhouse_fallback"
        dag_status = []
        for table, date_col in PIPELINE_TABLES:
            try:
                last_run = scalar(f"SELECT max({date_col}) FROM {table}")
                records = scalar(f"SELECT count(*) FROM {table}", default=0)
            except Exception:
                last_run, records = None, 0
            dag_status.append(
                {
                    "dag": table,
                    "status": "success" if records else "failed",
                    "lastRun": last_run or "—",
                    "duration": "—",
                    "records": records or 0,
                    "tasks": 1,
                    "failed": 0 if records else 1,
                }
            )

    data_quality_errors = [
        {
            "type": report.get("source_name", "unknown"),
            "table": report.get("source_name", "unknown"),
            "count": report.get("error_count", 0),
            "date": (report.get("generated_at") or "")[:10],
        }
        for report in load_quality_reports()
        if report.get("error_count", 0) > 0
    ]

    try:
        ingest_history = rows(
            """
            SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS date, count(*) AS records
            FROM fact_daily_price
            WHERE trading_date >= (SELECT max(trading_date) FROM fact_daily_price) - 14
            GROUP BY trading_date
            ORDER BY trading_date
            """
        )
    except Exception:
        ingest_history = []

    try:
        # Real consumer-group lag for ClickHouse's own Kafka engine consumer
        # (group "clickhouse-realtime-vwap"), read straight from the broker:
        # high-water-mark offset minus last committed offset, per partition.
        # The frontend chart only has one history slot per poll (it replaces
        # the array wholesale every 60s, it does not accumulate client-side),
        # so this reports one current point -- total lag right now -- rather
        # than fabricating a multi-point trend with no real history behind it.
        partition_lags = get_consumer_group_lag()
        kafka_lag = (
            [
                {
                    "time": datetime.now().strftime("%H:%M"),
                    "lag": sum(p["lag"] for p in partition_lags),
                }
            ]
            if partition_lags
            else []
        )
    except Exception:
        kafka_lag = []

    return {
        "dagStatus": dag_status,
        "dagStatusSource": airflow_source,
        "dataQualityErrors": data_quality_errors,
        "ingestHistory": ingest_history,
        "kafkaLag": kafka_lag,
    }


def latest_price_rows(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """Latest fact_daily_price snapshot for a specific set of tickers, keyed by ticker."""
    if not tickers:
        return {}
    tickers_sql = ", ".join(quote(t) for t in tickers)
    data = rows(
        f"""
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
          AND f.ticker IN ({tickers_sql})
        """
    )
    return {row["ticker"]: row for row in data}


class WatchlistAddRequest(BaseModel):
    ticker: str


@app.get("/api/watchlist")
def get_watchlist() -> dict[str, Any]:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT ticker FROM watchlist WHERE user_id = %s ORDER BY created_at DESC",
            (DEFAULT_USER_ID,),
        )
        tickers = [row[0] for row in cur.fetchall()]

    price_by_ticker = latest_price_rows(tickers)
    data = [
        {**price_by_ticker[ticker], "inWatchlist": True}
        for ticker in tickers
        if ticker in price_by_ticker
    ]
    return {"count": len(data), "data": data}


@app.post("/api/watchlist")
def add_to_watchlist(payload: WatchlistAddRequest) -> dict[str, Any]:
    ticker = payload.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO watchlist (watchlist_id, user_id, ticker)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, ticker) DO NOTHING
            """,
            (str(uuid.uuid4()), DEFAULT_USER_ID, ticker),
        )
    return {"ticker": ticker, "added": True}


@app.delete("/api/watchlist/{ticker}")
def remove_from_watchlist(ticker: str) -> dict[str, Any]:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM watchlist WHERE user_id = %s AND ticker = %s",
            (DEFAULT_USER_ID, ticker.strip().upper()),
        )
    return {"ticker": ticker.upper(), "removed": True}


# Must match src/alert_engine/rules.py's CONDITION_TYPES -- the engine raises
# ValueError on anything else, so a rule created here with an unsupported
# condition_type would silently crash that ticker's evaluation every cycle.
VALID_CONDITION_TYPES = {
    "PRICE_ABOVE",
    "PRICE_BELOW",
    "RSI_ABOVE",
    "RSI_BELOW",
    "BB_BREAK",
    "VWAP_DEVIATION",
}
VALID_CHANNELS = {"TELEGRAM", "EMAIL"}


class AlertRuleRequest(BaseModel):
    ticker: str
    conditionType: str
    thresholdValue: float
    channel: str
    cooldownMinutes: int = 60


@app.get("/api/alert-rules")
def get_alert_rules() -> dict[str, Any]:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT alert_id, ticker, condition_type, threshold_value, channel,
                   cooldown_minutes, is_active, created_at
            FROM user_alerts
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (DEFAULT_USER_ID,),
        )
        data = [
            {
                "id": str(alert_id),
                "ticker": ticker,
                "conditionType": condition_type,
                "thresholdValue": threshold_value,
                "channel": channel,
                "cooldownMinutes": cooldown_minutes,
                "isActive": is_active,
                "createdAt": created_at.isoformat(),
            }
            for alert_id, ticker, condition_type, threshold_value, channel, cooldown_minutes, is_active, created_at in cur.fetchall()
        ]
    return {"count": len(data), "data": data}


@app.post("/api/alert-rules")
def create_alert_rule(payload: AlertRuleRequest) -> dict[str, Any]:
    ticker = payload.ticker.strip().upper()
    condition_type = payload.conditionType.strip().upper()
    channel = payload.channel.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    if condition_type not in VALID_CONDITION_TYPES:
        raise HTTPException(
            status_code=400, detail=f"conditionType must be one of {sorted(VALID_CONDITION_TYPES)}"
        )
    if channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=400, detail=f"channel must be one of {sorted(VALID_CHANNELS)}"
        )
    if payload.cooldownMinutes <= 0:
        raise HTTPException(status_code=400, detail="cooldownMinutes must be positive")

    alert_id = str(uuid.uuid4())
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_alerts (alert_id, user_id, ticker, condition_type, threshold_value, channel, cooldown_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alert_id,
                DEFAULT_USER_ID,
                ticker,
                condition_type,
                payload.thresholdValue,
                channel,
                payload.cooldownMinutes,
            ),
        )
    return {"id": alert_id, "created": True}


class AlertRuleActiveRequest(BaseModel):
    isActive: bool


@app.put("/api/alert-rules/{alert_id}")
def update_alert_rule(alert_id: str, payload: AlertRuleActiveRequest) -> dict[str, Any]:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE user_alerts SET is_active = %s, updated_at = now() WHERE alert_id = %s AND user_id = %s",
            (payload.isActive, alert_id, DEFAULT_USER_ID),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"id": alert_id, "isActive": payload.isActive}


@app.delete("/api/alert-rules/{alert_id}")
def delete_alert_rule(alert_id: str) -> dict[str, Any]:
    with create_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM user_alerts WHERE alert_id = %s AND user_id = %s",
            (alert_id, DEFAULT_USER_ID),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"id": alert_id, "removed": True}
