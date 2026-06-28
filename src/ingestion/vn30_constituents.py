from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def fetch_vn30_constituents() -> list[str] | None:
    """Fetch the official VN30 constituent list from vnstock.

    Returns None when the source is unavailable so callers can fall back to a
    demo rule (top-30 HOSE tickers by shares_outstanding) instead of failing.
    """
    try:
        from vnstock import Listing

        symbols = Listing().symbols_by_group("VN30")
        tickers = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
        if not tickers:
            raise ValueError("vnstock returned an empty VN30 constituent list")
        return tickers
    except Exception as exc:
        logger.warning("Could not fetch official VN30 constituents (%s); falling back to demo rule.", exc)
        return None
