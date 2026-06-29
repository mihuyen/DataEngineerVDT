from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import ssl
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import certifi
import polars as pl
import websockets


DEFAULT_DNSE_WS_URL = "wss://ws-openapi.dnse.com.vn"
DEFAULT_DNSE_ENCODING = "json"
DEFAULT_DNSE_BOARD_ID = "G1"
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass(frozen=True)
class DNSEWebSocketConfig:
    """Runtime config for DNSE Market Data WebSocket."""

    api_key: str
    api_secret: str
    symbols: tuple[str, ...]
    base_url: str = DEFAULT_DNSE_WS_URL
    encoding: str = DEFAULT_DNSE_ENCODING
    board_id: str = DEFAULT_DNSE_BOARD_ID

    @property
    def stream_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/v1/stream?encoding={self.encoding}"

    @property
    def trade_channel(self) -> str:
        return f"tick.{self.board_id}.{self.encoding}"

    @property
    def quote_channel(self) -> str:
        return f"top_price.{self.board_id}.{self.encoding}"

    @property
    def ohlc_closed_channel(self) -> str:
        return f"ohlc_closed.1.{self.encoding}"

    @classmethod
    def from_env(cls, symbols: list[str] | None = None) -> "DNSEWebSocketConfig":
        api_key = os.getenv("DNSE_API_KEY", "").strip()
        api_secret = os.getenv("DNSE_API_SECRET", "").strip()
        if not api_key or not api_secret:
            raise ValueError("Missing DNSE_API_KEY or DNSE_API_SECRET.")

        env_symbols = os.getenv("DNSE_WS_SYMBOLS", "VCB,FPT,HPG")
        selected_symbols = symbols or [symbol.strip() for symbol in env_symbols.split(",")]
        normalized_symbols = tuple(symbol.upper() for symbol in selected_symbols if symbol.strip())
        if not normalized_symbols:
            raise ValueError("DNSE symbols cannot be empty.")

        return cls(
            api_key=api_key,
            api_secret=api_secret,
            symbols=normalized_symbols,
            base_url=os.getenv("DNSE_WS_URL", DEFAULT_DNSE_WS_URL).strip() or DEFAULT_DNSE_WS_URL,
            encoding=os.getenv("DNSE_WS_ENCODING", DEFAULT_DNSE_ENCODING).strip()
            or DEFAULT_DNSE_ENCODING,
            board_id=os.getenv("DNSE_WS_BOARD_ID", DEFAULT_DNSE_BOARD_ID).strip()
            or DEFAULT_DNSE_BOARD_ID,
        )


@dataclass(frozen=True)
class DNSETradeTick:
    """Normalized DNSE trade tick used by the VWAP loader."""

    ticker: str
    trade_ts: datetime
    price: float
    volume: int
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "trade_ts": self.trade_ts,
            "price": self.price,
            "volume": self.volume,
            "data_source": "DNSE",
            "raw_json": json.dumps(self.raw, ensure_ascii=False, sort_keys=True),
        }


@dataclass(frozen=True)
class DNSEOhlcCandle:
    """Finalized one-minute OHLCV candle received from DNSE."""

    ticker: str
    minute_ts: datetime
    resolution: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "minute_ts": self.minute_ts,
            "resolution": self.resolution,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "is_final": 1,
            "data_source": "DNSE",
            "raw_json": json.dumps(self.raw, ensure_ascii=False, sort_keys=True),
        }


def create_auth_message(
    api_key: str,
    api_secret: str,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Create DNSE auth message using HMAC-SHA256."""
    auth_timestamp = timestamp if timestamp is not None else int(time.time())
    auth_nonce = nonce or str(int(time.time() * 1_000_000))
    message = f"{api_key}:{auth_timestamp}:{auth_nonce}"
    signature = hmac.new(
        api_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "action": "auth",
        "api_key": api_key,
        "signature": signature,
        "timestamp": auth_timestamp,
        "nonce": auth_nonce,
    }


def build_subscribe_message(channel_name: str, symbols: tuple[str, ...]) -> dict[str, Any]:
    """Build DNSE subscribe message."""
    return {
        "action": "subscribe",
        "channels": [
            {
                "name": channel_name,
                "symbols": list(symbols),
            }
        ],
    }


def build_subscribe_channels_message(
    channel_names: tuple[str, ...], symbols: tuple[str, ...]
) -> dict[str, Any]:
    """Build one subscription request for multiple DNSE channels."""
    return {
        "action": "subscribe",
        "channels": [
            {"name": channel_name, "symbols": list(symbols)} for channel_name in channel_names
        ],
    }


def parse_json_message(raw_message: str | bytes) -> dict[str, Any]:
    """Decode a DNSE JSON WebSocket message."""
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8")
    parsed = json.loads(raw_message)
    if not isinstance(parsed, dict):
        raise ValueError("DNSE message is not a JSON object.")
    return parsed


def parse_dnse_time(value: Any) -> datetime:
    """Parse DNSE time field into a naive datetime."""
    if isinstance(value, dict):
        seconds = value.get("Seconds", value.get("seconds"))
        nanos = value.get("Nanos", value.get("nanos", 0))
        if seconds is None:
            raise ValueError("DNSE time object missing Seconds.")
        return (
            datetime.fromtimestamp(float(seconds) + float(nanos or 0) / 1_000_000_000, UTC)
            .astimezone(VIETNAM_TZ)
            .replace(tzinfo=None)
        )
    if isinstance(value, int | float):
        timestamp = float(value)
        if timestamp >= 1_000_000_000_000_000:
            timestamp /= 1_000_000
        elif timestamp >= 1_000_000_000_000:
            timestamp /= 1_000
        return datetime.fromtimestamp(timestamp, UTC).astimezone(VIETNAM_TZ).replace(tzinfo=None)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            return parsed.astimezone(VIETNAM_TZ).replace(tzinfo=None)
        return parsed
    raise ValueError(f"Unsupported DNSE time value: {value!r}")


def unwrap_payload(message: dict[str, Any]) -> dict[str, Any]:
    """Return the market-data payload from plain or wrapped DNSE messages."""
    data = message.get("data")
    if isinstance(data, dict):
        return data
    payload = message.get("payload")
    if isinstance(payload, dict):
        return payload
    return message


def parse_trade_message(message: dict[str, Any]) -> DNSETradeTick | None:
    """Parse a DNSE Trade payload into the local VWAP tick schema."""
    payload = unwrap_payload(message)
    symbol = payload.get("symbol")
    price = payload.get("matchPrice")
    volume = payload.get("matchQtty")
    trade_time = payload.get("time")

    if symbol is None or price is None or volume is None or trade_time is None:
        return None

    return DNSETradeTick(
        ticker=str(symbol).upper(),
        trade_ts=parse_dnse_time(trade_time),
        price=float(price),
        volume=int(float(volume)),
        raw=payload,
    )


def parse_ohlc_message(message: dict[str, Any]) -> DNSEOhlcCandle | None:
    """Parse a finalized DNSE OHLC payload into the one-minute schema."""
    payload = unwrap_payload(message)
    required = ("symbol", "time", "open", "high", "low", "close", "volume")
    if any(payload.get(field) is None for field in required):
        return None

    resolution = str(payload.get("resolution", "1"))
    if resolution not in {"1", "1m"}:
        return None

    return DNSEOhlcCandle(
        ticker=str(payload["symbol"]).upper(),
        minute_ts=parse_dnse_time(payload["time"]),
        resolution="1m",
        open=float(payload["open"]),
        high=float(payload["high"]),
        low=float(payload["low"]),
        close=float(payload["close"]),
        volume=int(float(payload["volume"])),
        raw=payload,
    )


async def stream_market_events(
    config: DNSEWebSocketConfig,
    max_messages: int | None = None,
    timeout_seconds: float | None = None,
    include_ohlc: bool = True,
    include_trades: bool = True,
) -> AsyncIterator[DNSETradeTick | DNSEOhlcCandle]:
    """Stream trade ticks and finalized one-minute candles over one connection."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    started_at = time.monotonic()
    yielded = 0

    async with websockets.connect(
        config.stream_url,
        ssl=ssl_context,
        ping_interval=30,
        ping_timeout=30,
    ) as websocket:
        await websocket.recv()
        await websocket.send(json.dumps(create_auth_message(config.api_key, config.api_secret)))

        auth_response = parse_json_message(await websocket.recv())
        action = str(auth_response.get("action", "")).lower()
        if action not in {"auth_success", "authenticated"}:
            raise RuntimeError(f"DNSE auth failed: {auth_response}")

        channels: tuple[str, ...] = (config.trade_channel,) if include_trades else ()
        if include_ohlc:
            channels += (config.ohlc_closed_channel,)
        if not channels:
            raise ValueError("At least one DNSE market-data channel must be enabled")
        subscribe_message = build_subscribe_channels_message(channels, config.symbols)
        await websocket.send(json.dumps(subscribe_message, ensure_ascii=False))

        while max_messages is None or yielded < max_messages:
            if timeout_seconds is not None and time.monotonic() - started_at >= timeout_seconds:
                break

            receive_timeout = 5 if timeout_seconds is None else min(5, timeout_seconds)
            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=receive_timeout)
            except TimeoutError:
                await websocket.pong()
                continue

            message = parse_json_message(raw_message)
            message_action = str(message.get("action", "")).lower()
            if message_action == "ping":
                await websocket.send(json.dumps({"action": "pong"}))
                continue
            if message_action in {"subscribed", "subscribe_success", "pong"}:
                continue

            event = parse_ohlc_message(message) if include_ohlc else None
            if event is None and include_trades:
                event = parse_trade_message(message)
            if event is None:
                continue

            yielded += 1
            yield event


async def stream_trade_ticks(
    config: DNSEWebSocketConfig,
    max_messages: int | None = None,
    timeout_seconds: float | None = None,
) -> AsyncIterator[DNSETradeTick]:
    """Stream normalized trade ticks from DNSE Market Data WebSocket."""
    async for event in stream_market_events(
        config,
        max_messages=max_messages,
        timeout_seconds=timeout_seconds,
        include_ohlc=False,
        include_trades=True,
    ):
        if isinstance(event, DNSETradeTick):
            yield event


async def collect_trade_ticks(
    config: DNSEWebSocketConfig,
    max_messages: int | None = None,
    timeout_seconds: float | None = None,
) -> pl.DataFrame:
    """Collect DNSE trade ticks into a Polars DataFrame."""
    rows = []
    async for tick in stream_trade_ticks(
        config,
        max_messages=max_messages,
        timeout_seconds=timeout_seconds,
    ):
        rows.append(tick.to_dict())

    if not rows:
        return pl.DataFrame(
            schema={
                "ticker": pl.String,
                "trade_ts": pl.Datetime,
                "price": pl.Float64,
                "volume": pl.Int64,
                "raw_json": pl.String,
            }
        )
    return pl.DataFrame(rows)
