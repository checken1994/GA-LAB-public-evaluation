"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

# [G3-CONSOLIDATE P1-06] Verifier consolidation status:
# - This verifier: LIVE-UNIQUE
# - Canonical verifier: scp/core/multi_source_verifier.py::AsyncMultiSourceVerifier
# - Unique role: Crypto/currency multi-source verification — fetch_crypto_price
#   (6 exchanges: Binance/Coinbase/Kraken/Bitstamp/KuCoin/CoinGecko) +
#   fetch_currency_rate (Frankfurter + open.er-api.com). Canonical
#   AsyncMultiSourceVerifier does NOT cover crypto/currency. This module is
#   the canonical source for crypto/currency price verification.
# - Wired to /ask: INDIRECTLY — used by 4 SLMs internally:
#   conversionslm.py:295,321 (fetch_currency_rate + fetch_crypto_price),
#   misc_slms2.py:199,225, misc_slm.py:154,180,
#   numeric_data_slm.py:60,86 + adversary_verifier.py:109 (SYMBOL_MAP).
# - Provides SYMBOL_MAP (line 51) consumed by adversary_verifier for its
#   crypto adversary check (delegation pattern, see Task V4 actions).

#!/usr/bin/env python3
"""
SCP V29.1 — Crypto Multi-Source Verifier.

Vấn đề V29: CoinGecko rate-limit (429) → SCP không verify được giá crypto.

Giải pháp V29.1: Gọi đồng thời 6 sources, lấy median + verify bằng ConflictResolver.

Sources (theo độ tin cậy):
    1. Binance     (BTC/ETH/SOL/DOGE/XRP/USDT — major coins)
    2. Coinbase    (BTC/ETH + major)
    3. Kraken      (BTC/ETH + major)
    4. Bitstamp    (BTC/ETH/LTC/XRP)
    5. KuCoin      (200+ coins)
    6. CoinGecko   (fallback — thường rate-limited)

Strategy:
    - Gọi 3 sources đầu tiên song song
    - Lấy median (outlier-resistant)
    - Nếu ≥2 sources agree (±2%) → PASS với confidence cao
    - Nếu sources disagree >5% → FAIL với warning
"""

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("scp.crypto_verifier")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from scp.core.api_utils import fetch_with_retry
from scp.core.conflict_resolver import resolve_value

# Coin symbol → trading pair trên các exchanges
SYMBOL_MAP = {
    'bitcoin': {'binance': 'BTCUSDT', 'coinbase': 'BTC-USD', 'kraken': 'XBTUSD', 'bitstamp': 'btcusd', 'kucoin': 'BTC', 'coingecko': 'bitcoin'},
    'btc': {'binance': 'BTCUSDT', 'coinbase': 'BTC-USD', 'kraken': 'XBTUSD', 'bitstamp': 'btcusd', 'kucoin': 'BTC', 'coingecko': 'bitcoin'},
    'ethereum': {'binance': 'ETHUSDT', 'coinbase': 'ETH-USD', 'kraken': 'XETHUSD', 'bitstamp': 'ethusd', 'kucoin': 'ETH', 'coingecko': 'ethereum'},
    'eth': {'binance': 'ETHUSDT', 'coinbase': 'ETH-USD', 'kraken': 'XETHUSD', 'bitstamp': 'ethusd', 'kucoin': 'ETH', 'coingecko': 'ethereum'},
    'solana': {'binance': 'SOLUSDT', 'coinbase': 'SOL-USD', 'kraken': 'SOLUSD', 'bitstamp': None, 'kucoin': 'SOL', 'coingecko': 'solana'},
    'sol': {'binance': 'SOLUSDT', 'coinbase': 'SOL-USD', 'kraken': 'SOLUSD', 'bitstamp': None, 'kucoin': 'SOL', 'coingecko': 'solana'},
    'dogecoin': {'binance': 'DOGEUSDT', 'coinbase': 'DOGE-USD', 'kraken': 'XDGUSD', 'bitstamp': None, 'kucoin': 'DOGE', 'coingecko': 'dogecoin'},
    'doge': {'binance': 'DOGEUSDT', 'coinbase': 'DOGE-USD', 'kraken': 'XDGUSD', 'bitstamp': None, 'kucoin': 'DOGE', 'coingecko': 'dogecoin'},
    'ripple': {'binance': 'XRPUSDT', 'coinbase': 'XRP-USD', 'kraken': 'XXRPUSD', 'bitstamp': 'xrpusd', 'kucoin': 'XRP', 'coingecko': 'ripple'},
    'xrp': {'binance': 'XRPUSDT', 'coinbase': 'XRP-USD', 'kraken': 'XXRPUSD', 'bitstamp': 'xrpusd', 'kucoin': 'XRP', 'coingecko': 'ripple'},
    'tether': {'binance': 'USDUSDT', 'coinbase': None, 'kraken': 'USDTUSD', 'bitstamp': None, 'kucoin': 'USDT', 'coingecko': 'tether'},
    'usdt': {'binance': 'USDUSDT', 'coinbase': None, 'kraken': 'USDTUSD', 'bitstamp': None, 'kucoin': 'USDT', 'coingecko': 'tether'},
    'monero': {'binance': None, 'coinbase': None, 'kraken': 'XXMRUSD', 'bitstamp': None, 'kucoin': 'XMR', 'coingecko': 'monero'},
    'xmr': {'binance': None, 'coinbase': None, 'kraken': 'XXMRUSD', 'bitstamp': None, 'kucoin': 'XMR', 'coingecko': 'monero'},
    'cardano': {'binance': 'ADAUSDT', 'coinbase': 'ADA-USD', 'kraken': 'ADAUSD', 'bitstamp': None, 'kucoin': 'ADA', 'coingecko': 'cardano'},
    'ada': {'binance': 'ADAUSDT', 'coinbase': 'ADA-USD', 'kraken': 'ADAUSD', 'bitstamp': None, 'kucoin': 'ADA', 'coingecko': 'cardano'},
    'litecoin': {'binance': 'LTCUSDT', 'coinbase': 'LTC-USD', 'kraken': 'XLTCUSD', 'bitstamp': 'ltcusd', 'kucoin': 'LTC', 'coingecko': 'litecoin'},
    'ltc': {'binance': 'LTCUSDT', 'coinbase': 'LTC-USD', 'kraken': 'XLTCUSD', 'bitstamp': 'ltcusd', 'kucoin': 'LTC', 'coingecko': 'litecoin'},
    #  Add missing coins
    'polygon': {'binance': 'POLUSDT', 'coinbase': 'MATIC-USD', 'kraken': 'MATICUSD', 'bitstamp': None, 'kucoin': 'MATIC', 'coingecko': 'matic-network'},
    'matic': {'binance': 'POLUSDT', 'coinbase': 'MATIC-USD', 'kraken': 'MATICUSD', 'bitstamp': None, 'kucoin': 'MATIC', 'coingecko': 'matic-network'},
    'polkadot': {'binance': 'DOTUSDT', 'coinbase': 'DOT-USD', 'kraken': 'DOTUSD', 'bitstamp': None, 'kucoin': 'DOT', 'coingecko': 'polkadot'},
    'dot': {'binance': 'DOTUSDT', 'coinbase': 'DOT-USD', 'kraken': 'DOTUSD', 'bitstamp': None, 'kucoin': 'DOT', 'coingecko': 'polkadot'},
    'chainlink': {'binance': 'LINKUSDT', 'coinbase': 'LINK-USD', 'kraken': 'LINKUSD', 'bitstamp': None, 'kucoin': 'LINK', 'coingecko': 'chainlink'},
    'link': {'binance': 'LINKUSDT', 'coinbase': 'LINK-USD', 'kraken': 'LINKUSD', 'bitstamp': None, 'kucoin': 'LINK', 'coingecko': 'chainlink'},
    'binancecoin': {'binance': 'BNBUSDT', 'coinbase': 'BNB-USD', 'kraken': 'BNBUSD', 'bitstamp': None, 'kucoin': 'BNB', 'coingecko': 'binancecoin'},
    'bnb': {'binance': 'BNBUSDT', 'coinbase': 'BNB-USD', 'kraken': 'BNBUSD', 'bitstamp': None, 'kucoin': 'BNB', 'coingecko': 'binancecoin'},
    'stellar': {'binance': 'XLMUSDT', 'coinbase': 'XLM-USD', 'kraken': 'XXLMUSD', 'bitstamp': None, 'kucoin': 'XLM', 'coingecko': 'stellar'},
    'xlm': {'binance': 'XLMUSDT', 'coinbase': 'XLM-USD', 'kraken': 'XXLMUSD', 'bitstamp': None, 'kucoin': 'XLM', 'coingecko': 'stellar'},
    'cosmos': {'binance': 'ATOMUSDT', 'coinbase': 'ATOM-USD', 'kraken': 'ATOMUSD', 'bitstamp': None, 'kucoin': 'ATOM', 'coingecko': 'cosmos'},
    'atom': {'binance': 'ATOMUSDT', 'coinbase': 'ATOM-USD', 'kraken': 'ATOMUSD', 'bitstamp': None, 'kucoin': 'ATOM', 'coingecko': 'cosmos'},
}


def _fetch_binance(symbol: str) -> float | None:
    """Binance API — fastest, no rate-limit issues."""
    if not symbol:
        return None
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "price" in data:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"Binance error: {e}", exc_info=True)
    return None


def _fetch_coinbase(symbol: str) -> float | None:
    """Coinbase API."""
    if not symbol:
        return None
    try:
        url = f"https://api.coinbase.com/v2/prices/{symbol}/spot"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "data" in data:
            return float(data["data"]["amount"])
    except Exception as e:
        logger.debug(f"Coinbase error: {e}", exc_info=True)
    return None


def _fetch_kraken(symbol: str) -> float | None:
    """Kraken API."""
    if not symbol:
        return None
    try:
        url = f"https://api.kraken.com/0/public/Ticker?pair={symbol}"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "result" in data:
            # Kraken returns dynamic key
            for _k, v in data["result"].items():
                return float(v["c"][0])  # 'c' = last trade price
    except Exception as e:
        logger.debug(f"Kraken error: {e}", exc_info=True)
    return None


def _fetch_bitstamp(symbol: str) -> float | None:
    """Bitstamp API."""
    if not symbol:
        return None
    try:
        url = f"https://www.bitstamp.net/api/v2/ticker/{symbol}/"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "last" in data:
            return float(data["last"])
    except Exception as e:
        logger.debug(f"Bitstamp error: {e}", exc_info=True)
    return None


def _fetch_kucoin(symbol: str) -> float | None:
    """KuCoin API."""
    if not symbol:
        return None
    try:
        url = f"https://api.kucoin.com/api/v1/prices?base=USD&currencies={symbol}"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "data" in data and symbol in data["data"]:
            return float(data["data"][symbol])
    except Exception as e:
        logger.debug(f"KuCoin error: {e}", exc_info=True)
    return None


def _fetch_coingecko(coin_id: str) -> float | None:
    """CoinGecko API (fallback — often rate-limited)."""
    if not coin_id:
        return None
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and coin_id in data:
            return float(data[coin_id]["usd"])
    except Exception as e:
        logger.debug(f"CoinGecko error: {e}", exc_info=True)
    return None


# Source fetchers in priority order
SOURCE_FETCHERS = [
    ("Binance", _fetch_binance),
    ("Coinbase", _fetch_coinbase),
    ("Kraken", _fetch_kraken),
    ("Bitstamp", _fetch_bitstamp),
    ("KuCoin", _fetch_kucoin),
    ("CoinGecko", _fetch_coingecko),
]


@dataclass
class CryptoResult:
    """Result từ multi-source crypto fetch."""
    # [V104.31 #6] value can be None when coin unknown or all sources failed
    value: float | None
    source: str
    confidence: float
    sources_queried: list[str]
    sources_succeeded: list[str]
    sources_failed: list[str]
    all_values: list[dict]
    strategy: str
    conflict_detected: bool
    reason: str
    # [V104.31 #7] Sources that didn't return within timeout (neither success nor fail)
    sources_incomplete: list[str] = None

    def __post_init__(self):
        if self.sources_incomplete is None:
            self.sources_incomplete = []


def fetch_crypto_price(coin: str) -> CryptoResult:
    """
    Fetch crypto price từ nhiều sources, trả về consensus value.

     Parallel fetch — gọi 6 sources song song bằng threading
    thay vì sequential. Speedup ~5x.

    Args:
        coin: 'bitcoin', 'btc', 'ethereum', 'eth', 'solana', ...

    Returns:
        CryptoResult với median value + confidence
    """
    coin_lower = coin.lower()
    if coin_lower not in SYMBOL_MAP:
        # [V104.23 #3 FIX] value=None (was: 0.0 → caller treats as real price)
        return CryptoResult(
            value=None, source="none", confidence=0.0,
            sources_queried=[], sources_succeeded=[], sources_failed=[],
            all_values=[], strategy="unknown_coin",
            conflict_detected=False,
            reason=f"Unknown coin: {coin}"
        )

    symbols = SYMBOL_MAP[coin_lower]
    all_values: list[dict] = []
    succeeded: list[str] = []
    failed: list[str] = []

    #  Parallel fetch using threading
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Build list of (source_name, fetcher, symbol) tuples
    fetch_tasks = []
    for source_name, fetcher in SOURCE_FETCHERS:
        symbol = symbols.get(source_name.lower())
        if not symbol:
            continue
        fetch_tasks.append((source_name, fetcher, symbol))

    # Run all in parallel (max 6 workers)
    results_lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=min(6, len(fetch_tasks))) as executor:
        # Submit all
        future_to_source = {
            executor.submit(fetcher, symbol): (source_name, fetcher, symbol)
            for source_name, fetcher, symbol in fetch_tasks
        }
        # [V104.31 #7] Wrap in try/except TimeoutError — was: incomplete sources lost
        completed_sources: set[str] = set()
        try:
            for future in as_completed(future_to_source, timeout=15):
                source_name, fetcher, symbol = future_to_source[future]
                completed_sources.add(source_name)
                try:
                    price = future.result(timeout=10)
                    if price is not None and price > 0:
                        with results_lock:
                            all_values.append({"value": price, "source": source_name})
                            succeeded.append(source_name)
                    else:
                        with results_lock:
                            failed.append(source_name)
                except Exception as e:
                    with results_lock:
                        failed.append(source_name)
                    logger.debug(f"{source_name} fetch error: {e}", exc_info=True)
        except TimeoutError:
            all_submitted = {t[0] for t in fetch_tasks}
            incomplete = all_submitted - completed_sources
            with results_lock:
                for src in incomplete:
                    if src not in failed:
                        failed.append(src)
            logger.warning(f"[Crypto] Timeout — {len(incomplete)} sources incomplete")

    if not all_values:
        return CryptoResult(
            value=None, source="none", confidence=0.0,  # [V104.31 #6 crypto] was: 0.0
            sources_queried=list(symbols.keys()),
            sources_succeeded=[], sources_failed=failed,
            all_values=[], strategy="all_failed",
            conflict_detected=False,
            reason=f"All sources failed for {coin}"
        )

    # Use ConflictResolver để get consensus
    result = resolve_value(all_values, strategy="median")
    # Also try weighted_avg for comparison
    resolve_value(all_values, strategy="weighted_avg")

    # Pick median (more outlier-resistant)
    final_value = result.value
    final_source = f"median({','.join(succeeded[:3])})"

    # Confidence based on agreement
    # [V59 FIX] Manual stdev calculation — avoid statistics module name collision entirely
    nums = [v["value"] for v in all_values]
    if len(nums) >= 3:
        mean = sum(nums) / len(nums)
        if mean > 0:
            # Manual stdev (no import needed)
            variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
            std = variance ** 0.5
            cv = std / mean  # coefficient of variation
            if cv < 0.01:
                confidence = 0.95
            elif cv < 0.03:
                confidence = 0.85
            elif cv < 0.10:
                confidence = 0.65
            else:
                confidence = 0.40
        else:
            confidence = 0.50
    elif len(nums) == 2:
        diff_pct = abs(nums[0] - nums[1]) / max(nums)
        confidence = 0.85 if diff_pct < 0.02 else 0.50
    else:
        confidence = 0.70

    return CryptoResult(
        value=final_value,
        source=final_source,
        confidence=confidence,
        sources_queried=list(symbols.keys()),
        sources_succeeded=succeeded,
        sources_failed=failed,
        all_values=all_values,
        strategy=result.strategy,
        conflict_detected=result.conflict_detected,
        reason=f"Queried {len(succeeded)}/{len(SOURCE_FETCHERS)} sources, "
               f"values: {[v['value'] for v in all_values]}, "
               f"median={final_value:.2f}, confidence={confidence:.2f}"
    )


# ============================================================
# CURRENCY MULTI-SOURCE (Frankfurter + open.er-api)
# ============================================================
def fetch_currency_rate(from_curr: str, to_curr: str) -> dict[str, Any]:
    """
    Fetch currency exchange rate từ nhiều sources.

    Returns:
        {
            "value": float,
            "source": str,
            "confidence": float,
            "sources_succeeded": List[str],
            "all_values": List[Dict],
            "conflict_detected": bool,
            "reason": str,
        }
    """
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    all_values: list[dict] = []
    succeeded: list[str] = []

    # Source 1: Frankfurter
    try:
        url = f"https://api.frankfurter.app/latest?from={from_curr}&to={to_curr}"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "rates" in data and to_curr in data["rates"]:
            rate = float(data["rates"][to_curr])
            all_values.append({"value": rate, "source": "Frankfurter"})
            succeeded.append("Frankfurter")
    except Exception as e:
        logger.debug(f"Frankfurter error: {e}", exc_info=True)

    # Source 2: open.er-api.com
    try:
        url = f"https://open.er-api.com/v6/latest/{from_curr}"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "rates" in data and to_curr in data["rates"]:
            rate = float(data["rates"][to_curr])
            all_values.append({"value": rate, "source": "open.er-api.com"})
            succeeded.append("open.er-api.com")
    except Exception as e:
        logger.debug(f"open.er-api error: {e}", exc_info=True)

    if not all_values:
        return {
            "value": None, "source": "none", "confidence": 0.0, "ok": False,  # [V104.31 #6 crypto]
            "sources_succeeded": [], "all_values": [],
            "conflict_detected": False,
            "reason": f"All currency sources failed for {from_curr}/{to_curr}"
        }

    # Resolve
    result = resolve_value(all_values, strategy="weighted_avg")
    return {
        "value": result.value,
        "source": f"weighted({','.join(succeeded)})",
        "confidence": 0.90 if len(succeeded) >= 2 else 0.80,
        "sources_succeeded": succeeded,
        "all_values": all_values,
        "conflict_detected": result.conflict_detected,
        "reason": result.reason,
    }


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V29.1 Crypto Multi-Source Verifier")
    parser.add_argument("--coin", type=str, default="bitcoin", help="Coin to fetch (default: bitcoin)")
    parser.add_argument("--currency", type=str, help="Currency pair (e.g., USD/EUR)")
    parser.add_argument("--list", action="store_true", help="List supported coins")
    args = parser.parse_args()

    if args.list:
        print(f"\nSupported coins ({len(SYMBOL_MAP)}):")
        for coin in sorted(SYMBOL_MAP.keys()):
            print(f"  - {coin}")
        return

    if args.currency:
        parts = args.currency.split('/')
        if len(parts) != 2:
            print("  Format: USD/EUR")
            return
        result = fetch_currency_rate(parts[0], parts[1])
        print(f"\n  Currency {args.currency}:")
        print(f"    Rate: {result['value']:.4f}")
        print(f"    Source: {result['source']}")
        print(f"    Confidence: {result['confidence']:.2f}")
        print(f"    Sources: {result['sources_succeeded']}")
        print(f"    All values: {result['all_values']}")
        return

    result = fetch_crypto_price(args.coin)
    print(f"\n  Crypto: {args.coin}")
    print(f"    Price: ${result.value:,.2f}")
    print(f"    Source: {result.source}")
    print(f"    Confidence: {result.confidence:.2f}")
    print(f"    Sources succeeded: {result.sources_succeeded}")
    print(f"    Sources failed: {result.sources_failed}")
    print("    All values:")
    for v in result.all_values:
        print(f"      {v['source']:15s} ${v['value']:>12,.2f}")
    print(f"    Conflict: {result.conflict_detected}")
    print(f"    Reason: {result.reason}")


if __name__ == "__main__":
    main()
