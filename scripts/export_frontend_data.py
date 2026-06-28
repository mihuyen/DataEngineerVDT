from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "app" / "components" / "mockData.ts"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.clickhouse_client import create_client  # noqa: E402


def rows(client: Any, sql: str) -> list[dict[str, Any]]:
    result = client.query(sql)
    return [dict(zip(result.column_names, row, strict=True)) for row in result.result_rows]


def scalar(client: Any, sql: str, default: Any = None) -> Any:
    result = client.query(sql)
    if not result.result_rows:
        return default
    return result.result_rows[0][0]


def clean(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=clean)


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        value = 0
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_signed(value: float | int | None, digits: int = 2) -> str:
    value = float(value or 0)
    sign = "+" if value >= 0 else ""
    return sign + fmt_number(value, digits)


def js_export(name: str, value: Any) -> str:
    return f"export const {name} = {as_json(value)};\n"


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
          f.value AS value,
          ifNull(f.rsi_14, 50) AS rsi,
          ifNull(f.macd, 0) AS macd,
          ifNull(f.macd_signal, 0) AS macdSignal,
          ifNull(f.bb_upper, f.close) AS bbUpper,
          ifNull(f.bb_lower, f.close) AS bbLower,
          ifNull(f.volume_sma_20, f.volume) AS volSma20,
          f.overbought_flag AS overbought,
          f.oversold_flag AS oversold,
          f.breakout_flag AS breakout,
          f.breakdown_flag AS breakdown
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        ORDER BY {order_by}
        LIMIT {limit}
    """


def load_news_link_lookup() -> dict[tuple[str, str], dict[str, Any]]:
    files = sorted((ROOT / "data" / "gold_local" / "news_entity_links").glob("year=*/month=*/data.parquet"))
    if not files:
        return {}

    frame = pl.concat([pl.read_parquet(file) for file in files], how="diagonal_relaxed")
    if frame.is_empty() or not {"ticker", "title", "url"}.issubset(frame.columns):
        return {}

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in frame.sort("published_at", descending=True).to_dicts():
        key = (str(item.get("ticker", "")), str(item.get("title", "")))
        lookup.setdefault(
            key,
            {
                "url": item.get("url") or "",
                "source": item.get("source") or "",
                "publishedAt": clean(item.get("published_at")),
            },
        )
    return lookup


def stock_table(client: Any, order_by: str, limit: int) -> list[dict[str, Any]]:
    data = rows(client, build_stock_query(order_by, limit))
    return [
        {
            "ticker": r["ticker"],
            "name": r["name"],
            "exchange": r["exchange"],
            "price": r["price"],
            "change": r["change"],
            "pct": r["pct"],
            "volume": r["volume"],
            "sector": r["sector"],
            **({"value": r["value"]} if "value DESC" in order_by else {}),
        }
        for r in data
    ]


def main() -> None:
    client = create_client()
    news_link_lookup = load_news_link_lookup()
    latest_price_date = scalar(client, "SELECT max(trading_date) FROM fact_daily_price")
    latest_news_date = scalar(client, "SELECT max(news_date) FROM fact_news_sentiment_daily")
    generated_at = datetime.now().replace(microsecond=0).isoformat()

    latest_stocks = rows(client, build_stock_query("f.value DESC", 200))
    stock_list = [
        {
            "ticker": r["ticker"],
            "name": r["name"],
            "exchange": r["exchange"],
            "sector": r["sector"],
        }
        for r in latest_stocks
    ]
    selected_tickers = [s["ticker"] for s in stock_list]
    ticker_list_sql = "'" + "','".join(selected_tickers) + "'" if selected_tickers else "''"

    top_gainers = stock_table(client, "f.pct_change DESC", 100)
    top_losers = stock_table(client, "f.pct_change ASC", 100)
    top_liquidity = [
        {
            "ticker": r["ticker"],
            "name": r["name"],
            "exchange": r["exchange"],
            "volume": r["volume"],
            "value": r["value"],
            "price": r["price"],
        }
        for r in rows(client, build_stock_query("f.value DESC", 100))
    ]

    sector_performance = rows(
        client,
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
        """,
    )
    sector_performance_by_exchange = rows(
        client,
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
        """,
    )

    market_index_rows = rows(
        client,
        """
        SELECT index_id, close_point, point_change, pct_change, total_volume, total_value,
               advance_count, decline_count, unchanged_count
        FROM fact_market_index
        WHERE trading_date = (SELECT max(trading_date) FROM fact_market_index)
          AND index_id IN ('VNINDEX', 'VN30')
        ORDER BY index_id
        """,
    )
    index_labels = {
        "VNINDEX": "VN-Index",
        "VN30": "VN30",
    }
    market_indices = [
        {
            "label": index_labels.get(r["index_id"], r["index_id"]),
            "value": fmt_number(r["close_point"], 2),
            "chg": fmt_signed(r["point_change"], 2),
            "pct": fmt_signed(r["pct_change"], 2) + "%",
            "up": r["point_change"] >= 0,
            "rawPct": r["pct_change"],
        }
        for r in market_index_rows
    ]
    preferred = ["VN-Index", "VN30"]
    preferred_all = ["VN-Index", "VN30"]
    market_indices_all = sorted(
        market_indices,
        key=lambda r: preferred_all.index(r["label"]) if r["label"] in preferred_all else 99,
    )
    market_mini = sorted(market_indices, key=lambda r: preferred.index(r["label"]) if r["label"] in preferred else 99)[:3]
    vnindex = next((r for r in market_index_rows if r["index_id"] == "VNINDEX"), market_index_rows[0] if market_index_rows else {})
    market_overview_stats = {
        "totalValue": fmt_number(sum(r["total_value"] for r in market_index_rows) / 1_000_000_000, 1) + " tỷ",
        "totalVolume": fmt_number(sum(r["total_volume"] for r in market_index_rows) / 1_000_000, 1) + " M",
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
        client,
        """
        SELECT ifNull(nullIf(s.exchange, ''), 'NA') AS exchange, countDistinct(f.ticker) AS count
        FROM fact_daily_price f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        WHERE f.trading_date = (SELECT max(trading_date) FROM fact_daily_price)
          AND s.exchange = 'HOSE'
        GROUP BY exchange
        """,
    )
    stock_counts_by_exchange = {row["exchange"]: row["count"] for row in stock_count_rows}
    stock_counts_by_exchange["ALL"] = sum(stock_counts_by_exchange.values())
    index_change_bars = [
        {"label": r["label"], "pct": r["rawPct"]} for r in market_indices
    ]

    vn_index_history = rows(
        client,
        """
        SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS time, close_point AS value
        FROM fact_market_index
        WHERE index_id = 'VNINDEX'
        ORDER BY trading_date DESC
        LIMIT 30
        """,
    )[::-1]
    index_history_by_exchange = {
        key: rows(
            client,
            f"""
            SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS time, close_point AS value
            FROM fact_market_index
            WHERE index_id = '{index_id}'
            ORDER BY trading_date DESC
            LIMIT 30
            """,
        )[::-1]
        for key, index_id in {"ALL": "VNINDEX", "HOSE": "VNINDEX"}.items()
    }

    candle_rows = rows(
        client,
        f"""
        SELECT ticker, trading_date, open, high, low, close, volume,
               ifNull(sma_20, close) AS sma20,
               ifNull(ema_12, close) AS ema12,
               ifNull(rsi_14, 50) AS rsi,
               ifNull(macd, 0) AS macd,
               ifNull(macd_signal, 0) AS macdSignal,
               ifNull(bb_upper, high) AS bbUpper,
               ifNull(bb_lower, low) AS bbLower
        FROM fact_daily_price
        WHERE ticker IN ({ticker_list_sql})
        ORDER BY ticker, trading_date
        """,
    )
    candlestick_by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in candle_rows:
        dt = row["trading_date"]
        if isinstance(dt, str):
            label = dt[5:10]
        else:
            label = dt.strftime("%m-%d")
        candlestick_by_ticker.setdefault(row["ticker"], []).append(
            {
                "date": label,
                "open": row["open"],
                "close": row["close"],
                "high": row["high"],
                "low": row["low"],
                "volume": row["volume"],
                "sma20": row["sma20"],
                "ema12": row["ema12"],
                "rsi": row["rsi"],
                "macd": row["macd"],
                "macdSignal": row["macdSignal"],
                "bbUpper": row["bbUpper"],
                "bbLower": row["bbLower"],
            }
        )

    technical_signals = []
    signal_candidates = rows(client, build_stock_query("abs(f.pct_change) DESC", 80))
    for r in signal_candidates:
        signal = None
        if r["overbought"]:
            signal = "overbought"
        elif r["oversold"]:
            signal = "oversold"
        elif r["breakout"]:
            signal = "breakout"
        elif r["breakdown"]:
            signal = "breakdown"
        elif r["macd"] > r["macdSignal"]:
            signal = "macd_positive"
        elif r["volume"] > r["volSma20"] * 1.4:
            signal = "volume_spike"
        if signal:
            technical_signals.append(
                {
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "rsi": r["rsi"],
                    "macd": r["macd"],
                    "macdSignal": r["macdSignal"],
                    "close": r["price"],
                    "bbUpper": r["bbUpper"],
                    "bbLower": r["bbLower"],
                    "volume": r["volume"],
                    "volSma20": r["volSma20"],
                    "signal": signal,
                    "pct": r["pct"],
                }
            )
        if len(technical_signals) >= 30:
            break

    table_counts = {
        t: scalar(client, f"SELECT count() FROM {t}", 0)
        for t in [
            "dim_stock",
            "dim_sector",
            "dim_index",
            "fact_daily_price",
            "fact_market_index",
            "fact_news_sentiment_daily",
            "fact_realtime_vwap",
            "fact_alert_event",
        ]
    }
    dag_status = [
        {"dag": "load_gold_daily_price", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["fact_daily_price"], "tasks": 5, "failed": 0},
        {"dag": "load_market_index_gold", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["fact_market_index"], "tasks": 3, "failed": 0},
        {"dag": "load_news_sentiment_gold", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["fact_news_sentiment_daily"], "tasks": 3, "failed": 0},
        {"dag": "load_realtime_vwap_demo", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["fact_realtime_vwap"], "tasks": 2, "failed": 0},
        {"dag": "load_dimensions", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["dim_stock"] + table_counts["dim_sector"] + table_counts["dim_index"], "tasks": 3, "failed": 0},
        {"dag": "alert_event_fact", "status": "success", "lastRun": "latest", "duration": "snapshot", "records": table_counts["fact_alert_event"], "tasks": 1, "failed": 0},
    ]
    data_quality_errors: list[dict[str, Any]] = []
    ingest_history = rows(
        client,
        """
        SELECT formatDateTime(toDateTime(trading_date), '%m-%d') AS date, count() AS records
        FROM fact_daily_price
        GROUP BY trading_date
        ORDER BY trading_date DESC
        LIMIT 7
        """,
    )[::-1]
    kafka_lag = rows(
        client,
        """
        SELECT formatDateTime(minute_ts, '%H:%M') AS time, 0 AS lag
        FROM fact_realtime_vwap
        GROUP BY minute_ts
        ORDER BY minute_ts
        LIMIT 60
        """,
    )

    vwap_data = rows(
        client,
        """
        SELECT formatDateTime(minute_ts, '%H:%M') AS time,
               close_price AS price,
               vwap_1m AS vwap,
               session_vwap AS sessionVwap,
               total_volume AS volume,
               price_vs_session_vwap_pct AS deviation
        FROM fact_realtime_vwap
        WHERE ticker = (SELECT ticker FROM fact_realtime_vwap GROUP BY ticker ORDER BY count() DESC, ticker LIMIT 1)
        ORDER BY minute_ts
        """,
    )
    vwap_deviations = rows(
        client,
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
          countIf(abs(f.price_vs_session_vwap_pct) >= 2) AS alerts
        FROM fact_realtime_vwap f
        LEFT JOIN dim_stock s ON f.ticker = s.ticker
        LEFT JOIN dim_sector sec ON s.sector_id = sec.sector_id
        GROUP BY f.ticker, name, sector, exchange
        ORDER BY abs(deviation) DESC
        """,
    )

    news_sentiment_rows = rows(
        client,
        """
        SELECT
          n.ticker AS ticker,
          ifNull(nullIf(s.company_name, ''), n.ticker) AS name,
          sum(n.news_count) AS newsCount,
          sum(n.source_count) AS sources,
          sum(n.positive_count) AS positive,
          sum(n.negative_count) AS negative,
          sum(n.neutral_count) AS neutral,
          avg(n.avg_sentiment_score) AS avgScore,
          argMax(n.top_headline, n.news_date) AS headline,
          max(n.news_date) AS newsDate
        FROM fact_news_sentiment_daily n
        LEFT JOIN dim_stock s ON n.ticker = s.ticker
        GROUP BY n.ticker, name
        ORDER BY newsCount DESC, abs(avgScore) DESC
        LIMIT 60
        """,
    )
    news_sentiment = [
        {
            **r,
            **news_link_lookup.get((r["ticker"], r["headline"]), {"url": "", "source": "", "publishedAt": ""}),
        }
        for r in news_sentiment_rows
    ]
    sentiment_by_date = rows(
        client,
        """
        SELECT formatDateTime(toDateTime(news_date), '%m-%d') AS date,
               sum(positive_count) AS positive,
               sum(negative_count) AS negative,
               sum(neutral_count) AS neutral
        FROM fact_news_sentiment_daily
        GROUP BY news_date
        ORDER BY news_date DESC
        LIMIT 14
        """,
    )[::-1]

    alert_history_rows = rows(
        client,
        """
        SELECT
          row_number() OVER (ORDER BY triggered_at DESC) AS id,
          user_id AS user,
          ticker,
          condition_type AS condition,
          threshold_value AS threshold,
          actual_value AS actual,
          channel,
          if(delivery_status = 'sent', 'sent', 'failed') AS status,
          delivery_status AS deliveryStatus,
          ifNull(formatDateTime(sent_at, '%H:%M:%S'), '') AS sentAt,
          formatDateTime(triggered_at, '%H:%M:%S') AS triggeredAt,
          30 AS cooldown
        FROM fact_alert_event
        ORDER BY triggered_at DESC
        LIMIT 100
        """,
    )
    alert_history = [
        {**r, "sentAt": r["sentAt"] or None}
        for r in alert_history_rows
    ]
    alerts_by_day = rows(
        client,
        """
        SELECT formatDateTime(triggered_at, '%m-%d') AS date, count() AS total
        FROM fact_alert_event
        GROUP BY toDate(triggered_at), date
        ORDER BY toDate(triggered_at)
        """,
    )
    fills = ["#8b5cf6", "#3b82f6", "#a855f7", "#00d97e", "#ff4d6d", "#6b7fa3"]
    alerts_by_condition = [
        {**r, "fill": fills[i % len(fills)]}
        for i, r in enumerate(
            rows(
                client,
                """
                SELECT condition_type AS type, count() AS count
                FROM fact_alert_event
                GROUP BY condition_type
                ORDER BY count DESC
                """,
            )
        )
    ]

    content = [
        "// Generated from ClickHouse by scripts/export_frontend_data.py.",
        f"export const dataSnapshotMeta = {as_json({'generatedAt': generated_at, 'latestPriceDate': clean(latest_price_date), 'latestNewsDate': clean(latest_news_date)})};\n",
        js_export("marketIndices", market_mini),
        js_export("marketIndicesAll", market_indices_all),
        js_export("marketOverviewStats", market_overview_stats),
        js_export("marketStatsByExchange", market_stats_by_exchange),
        js_export("stockCountsByExchange", stock_counts_by_exchange),
        js_export("breadthData", breadth_data),
        js_export("breadthDataByExchange", breadth_data_by_exchange),
        js_export("indexChangeBars", index_change_bars),
        js_export("vnIndexHistory", vn_index_history),
        js_export("indexHistoryByExchange", index_history_by_exchange),
        js_export("topGainers", top_gainers),
        js_export("topLosers", top_losers),
        js_export("topLiquidity", top_liquidity),
        js_export("sectorPerformance", sector_performance),
        js_export("sectorPerformanceByExchange", sector_performance_by_exchange),
        js_export("candlestickByTicker", candlestick_by_ticker),
        "export const generateCandlestickData = (ticker = \"VCB\") => candlestickByTicker[ticker] ?? candlestickByTicker[stockList[0]?.ticker] ?? [];\n",
        js_export("stockList", stock_list),
        js_export("technicalSignals", technical_signals),
        js_export("dagStatus", dag_status),
        js_export("dataQualityErrors", data_quality_errors),
        js_export("ingestHistory", ingest_history),
        js_export("kafkaLag", kafka_lag),
        js_export("vwapData", vwap_data),
        js_export("vwapDeviations", vwap_deviations),
        js_export("newsSentiment", news_sentiment),
        js_export("sentimentByDate", sentiment_by_date),
        js_export("alertHistory", alert_history),
        js_export("alertsByDay", alerts_by_day),
        js_export("alertsByCondition", alerts_by_condition),
    ]
    OUTPUT.write_text("\n".join(content), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} from ClickHouse")
    print(f"Latest fact_daily_price date: {latest_price_date}")
    print(f"Stocks: {len(stock_list)}, candles: {len(candle_rows)}, VWAP tickers: {len(vwap_deviations)}, alerts: {len(alert_history)}")


if __name__ == "__main__":
    main()
