from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime

from src.streaming.dnse_websocket import (
    DNSEWebSocketConfig,
    build_subscribe_message,
    create_auth_message,
    parse_dnse_time,
    parse_ohlc_message,
    parse_trade_message,
)
from scripts.run_dnse_realtime_ingest import (
    DEFAULT_DNSE_SYMBOLS,
    load_all_symbols_with_fallback,
    parse_symbols,
    read_symbols_from_file,
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


def test_dnse_auth_message_defaults_to_second_timestamp() -> None:
    before = int(time.time())
    message = create_auth_message(api_key="test_key", api_secret="test_secret")
    after = int(time.time())

    assert before <= message["timestamp"] <= after
    assert len(str(message["timestamp"])) == 10


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


def test_dnse_ingest_parse_symbols_supports_all_universe() -> None:
    assert parse_symbols("ALL") == ["ALL"]
    assert parse_symbols(" vcb, fpt ") == ["VCB", "FPT"]


def test_dnse_ingest_reads_ticker_file(tmp_path) -> None:
    ticker_file = tmp_path / "tickers.csv"
    ticker_file.write_text("symbol\nvcb\n fpt\nVCB\n", encoding="utf-8")

    assert read_symbols_from_file(ticker_file) == ["FPT", "VCB"]


def test_dnse_ingest_all_falls_back_without_clickhouse(monkeypatch, tmp_path) -> None:
    def fail_clickhouse() -> list[str]:
        raise RuntimeError("clickhouse down")

    def fail_vnstock() -> list[str]:
        raise RuntimeError("vnstock down")

    monkeypatch.setattr("scripts.run_dnse_realtime_ingest.load_all_symbols", fail_clickhouse)
    monkeypatch.setattr("scripts.run_dnse_realtime_ingest.load_symbols_from_vnstock", fail_vnstock)

    assert load_all_symbols_with_fallback(tmp_path / "missing.csv") == DEFAULT_DNSE_SYMBOLS


def test_dnse_ingest_all_uses_vnstock_before_builtin(monkeypatch, tmp_path) -> None:
    def fail_clickhouse() -> list[str]:
        raise RuntimeError("clickhouse down")

    monkeypatch.setattr("scripts.run_dnse_realtime_ingest.load_all_symbols", fail_clickhouse)
    monkeypatch.setattr(
        "scripts.run_dnse_realtime_ingest.load_symbols_from_vnstock",
        lambda: ["VCB", "FPT", "HPG"],
    )

    assert load_all_symbols_with_fallback(tmp_path / "missing.csv") == ["VCB", "FPT", "HPG"]


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
    assert tick.to_dict()["data_source"] == "DNSE"
    assert tick.to_dict()["raw_json"]


def test_parse_ohlc_message_returns_finalized_minute_candle() -> None:
    candle = parse_ohlc_message(
        {
            "data": {
                "symbol": "fpt",
                "resolution": "1",
                "open": 70.1,
                "high": 70.4,
                "low": 70.0,
                "close": 70.3,
                "volume": 12500,
                "time": 1782436500,
                "type": "bc",
            }
        }
    )

    assert candle is not None
    assert candle.ticker == "FPT"
    assert candle.resolution == "1m"
    assert candle.close == 70.3
    assert candle.to_dict()["is_final"] == 1
    assert candle.to_dict()["data_source"] == "DNSE"
