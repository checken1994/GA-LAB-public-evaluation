"""
[Task 7-A] Crypto source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_crypto() was 15 LOC inline. Extracted as
standalone function for modularity. Backward-compatible — WhyEngine delegates.

[Z.ai-ROOT-FIX #23] TẠI SAO: audit Gà verify 5 sàn khai báo
(Binance, Coinbase, Kraken, Bitstamp, KuCoin) nhưng chỉ có nhánh
"binance"/"coingecko" → 4 sàn còn lại silent None.
Fix: tất cả 5 sàn → _query_crypto (dùng CoinGecko API làm fallback).
"""
from __future__ import annotations

import json as _json
import logging
import urllib.request

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.crypto")


def query_crypto(target: str) -> str | None:
    """Query CoinGecko for crypto price."""
    try:
        coin = target.lower().replace(" ", "-")
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            if coin in data:
                return f"price=${data[coin]['usd']}"
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.crypto] failed for target='{target}': {e}", exc_info=True)
        return None
