from __future__ import annotations

import hashlib
import hmac
from datetime import datetime

from src.streaming.dnse_websocket import (
    DNSEWebSocketConfig,
    build_subscribe_message,
    create_auth_message,
    parse_dnse_time,
    parse_trade_message,
)


def test_dnse_auth_message_uses_hmac_sha256() -> None:
    message = create_auth_message(
        api_key="test_key",
        api_secret="test_secret",
        timestamp=1234567890,
        nonce="abc123",
    )
    expected = hmac.new(
        b"test_secret",
        b"test_key:1234567890:abc123",
        hashlib.sha256,
    ).hexdigest()

    assert message["action"] == "auth"
    assert message["api_key"] == "test_key"
    assert message["signature"] == expected


def test_dnse_subscribe_message_matches_trade_channel() -> None:
    message = build_subscribe_message("tick.G1.json", ("VCB", "FPT"))

    assert message == {
        "action": "subscribe",
        "channels": [{"name": "tick.G1.json", "symbols": ["VCB", "FPT"]}],
    }


def test_dnse_config_from_env_normalizes_symbols(monkeypatch) -> None:
    monkeypatch.setenv("DNSE_API_KEY", "key")
    monkeypatch.setenv("DNSE_API_SECRET", "secret")
    monkeypatch.setenv("DNSE_WS_SYMBOLS", "vcb, fpt")

    config = DNSEWebSocketConfig.from_env()

    assert config.stream_url == "wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json"
    assert config.trade_channel == "tick.G1.json"
    assert config.quote_channel == "top_price.G1.json"
    assert config.symbols == ("VCB", "FPT")


def test_parse_dnse_time_from_seconds_and_nanos() -> None:
    parsed = parse_dnse_time({"Seconds": 1779762571, "Nanos": 101000000})

    assert isinstance(parsed, datetime)
    assert parsed.microsecond == 101000


def test_parse_trade_message_returns_vwap_ready_tick() -> None:
    tick = parse_trade_message(
        {
            "data": {
                "marketId": "STO",
                "boardId": "G1",
                "symbol": "hpg",
                "matchPrice": 24.35,
                "matchQtty": 40,
                "time": {"Seconds": 1779762571, "Nanos": 101000000},
            }
        }
    )

    assert tick is not None
    assert tick.ticker == "HPG"
    assert tick.price == 24.35
    assert tick.volume == 40
    assert tick.to_dict()["raw_json"]
