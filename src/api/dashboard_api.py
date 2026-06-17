from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.common.clickhouse_client import create_client


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


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "latestPriceDate": scalar("SELECT max(trading_date) FROM fact_daily_price"),
        "latestRealtimeMinute": scalar("SELECT max(minute_ts) FROM fact_realtime_vwap"),
    }


@app.get("/api/stocks")
def get_stocks(
    exchange: str = Query("ALL"),
    q: str = Query(""),
    limit: int = Query(2000, ge=1, le=3000),
) -> dict[str, Any]:
    filters = []
    if exchange != "ALL":
        filters.append(f"s.exchange = {quote(exchange)}")
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
          formatDateTime(toDateTime(trading_date), '%m-%d') AS date,
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
        ORDER BY trading_date DESC
        LIMIT {limit}
        """
    )[::-1]
    if not data:
        raise HTTPException(status_code=404, detail=f"No price data for ticker {symbol}")
    return {"ticker": symbol, "count": len(data), "data": data}


@app.get("/api/realtime/vwap")
def get_realtime_vwap() -> dict[str, Any]:
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
        GROUP BY f.ticker, name, sector, exchange
        ORDER BY abs(deviation) DESC
        """
    )
    return {
        "count": len(data),
        "latestMinute": scalar("SELECT max(minute_ts) FROM fact_realtime_vwap"),
        "data": data,
    }


@app.get("/api/realtime/vwap/{ticker}/series")
def get_realtime_vwap_series(ticker: str) -> dict[str, Any]:
    symbol = ticker.upper()
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
        ORDER BY minute_ts
        """
    )
    if not data:
        raise HTTPException(status_code=404, detail=f"No realtime VWAP data for ticker {symbol}")
    return {"ticker": symbol, "count": len(data), "data": data}
