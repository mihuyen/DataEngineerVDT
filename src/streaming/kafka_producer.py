from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from kafka import KafkaProducer

DEFAULT_TOPIC = "dnse-trades-raw"


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
