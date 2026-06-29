from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from kafka import KafkaProducer

DEFAULT_TOPIC = "dnse-trades-raw"
DEFAULT_OHLCV_TOPIC = "dnse-ohlcv-1m"


def create_producer() -> KafkaProducer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8"),
        linger_ms=50,
    )


def trade_tick_to_kafka_message(
    ticker: str,
    trade_ts: datetime,
    price: float,
    volume: int,
    data_source: str = "DNSE",
) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "trade_ts": trade_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "price": float(price),
        "volume": int(volume),
        "data_source": data_source.strip().upper(),
    }


def publish_trade_tick(
    producer: KafkaProducer,
    ticker: str,
    trade_ts: datetime,
    price: float,
    volume: int,
    topic: str = DEFAULT_TOPIC,
    data_source: str = "DNSE",
) -> None:
    message = trade_tick_to_kafka_message(ticker, trade_ts, price, volume, data_source=data_source)
    producer.send(topic, key=message["ticker"], value=message)


def ohlcv_candle_to_kafka_message(
    ticker: str,
    minute_ts: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
    data_source: str = "DNSE",
) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "minute_ts": minute_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "resolution": "1m",
        "open": float(open_price),
        "high": float(high_price),
        "low": float(low_price),
        "close": float(close_price),
        "volume": int(volume),
        "is_final": 1,
        "data_source": data_source.strip().upper(),
    }


def publish_ohlcv_candle(
    producer: KafkaProducer,
    ticker: str,
    minute_ts: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
    topic: str = DEFAULT_OHLCV_TOPIC,
    data_source: str = "DNSE",
) -> None:
    message = ohlcv_candle_to_kafka_message(
        ticker,
        minute_ts,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        data_source,
    )
    producer.send(topic, key=message["ticker"], value=message)
