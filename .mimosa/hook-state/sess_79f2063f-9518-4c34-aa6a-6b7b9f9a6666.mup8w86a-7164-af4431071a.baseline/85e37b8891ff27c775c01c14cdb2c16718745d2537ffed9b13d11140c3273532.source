"""
[OPT-3] AlphaVantageDataSource — cross-check CoinGecko for finance.
DNA SCP: don't trust single source. CoinGecko alone = SPOF.
AlphaVantage provides stocks + forex + crypto (free tier: 25 calls/day).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.alphavantage")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder,
# caller không thể đổi host.
_ALPHAVANTAGE_API_URL = "https://www.alphavantage.co/query"


def build_alphavantage_url(params: dict) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — mọi param động (symbol,
    currency, apikey) được urlencode thành query values, không thể đổi
    host/path. Raises TypeError trên params không phải dict (fail-closed)."""
    if not isinstance(params, dict):
        raise TypeError("params must be a dict")
    return f"{_ALPHAVANTAGE_API_URL}?{urllib.parse.urlencode(params)}"


class AlphaVantageDataSource(IDataSource):
    """AlphaVantage API — stocks, forex, crypto (cross-check CoinGecko)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        self.enabled = bool(self.api_key and self.api_key != "demo")
        if not self.enabled:
            logger.info("[AlphaVantage] disabled — set ALPHAVANTAGE_API_KEY to enable")

    @property
    def name(self) -> str:
        return "alphavantage"

    @property
    def priority(self) -> int:
        return 10  # lower priority than CoinGecko (priority 5)

    @property
    def ttl(self) -> int:
        return 3600  # 1h cache

    def get_supported_intents(self) -> list[str]:
        return ["stock_price", "forex_rate", "crypto_price", "finance"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        # Accept both intent-based and question-based calls
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = ["stock", "cổ phiếu", "forex", "ngoại hối", "btc usd", "bitcoin price",
                    "exchange rate", "tỷ giá", "giá vàng", "gold price"]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (www.alphavantage.co). Trước đây hardcode `return self.enabled`
        — constructor config, không phải live evidence (fail-open). Không có API key → False ngay (không thể serve — fail-closed); có key
        → reachability ping. Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        if not self.enabled:
            # Không có API key → source không thể serve — fail-closed, không ping.
            return False
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            q = question.lower()
            if "stock" in q or "cổ phiếu" in q:
                symbol = self._extract_symbol(question)
                if symbol:
                    return self._query_stock(symbol)
            if "forex" in q or "ngoại hối" in q or "exchange rate" in q or "tỷ giá" in q:
                return self._query_forex(question)
            if "btc" in q or "bitcoin" in q or "crypto" in q:
                return self._query_crypto()
            return None
        except Exception as e:
            logger.debug(f"[AlphaVantage] query failed: {e}", exc_info=True)
            return None

    def _extract_symbol(self, question: str) -> str:
        import re
        m = re.search(r'\b(AAPL|GOOGL|MSFT|TSLA|AMZN|META|NVDA|NFLX|IBM|ORCL)\b', question, re.I)
        return m.group(1).upper() if m else ""

    def _query_stock(self, symbol: str) -> dict | None:
        try:
            url = build_alphavantage_url({
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key,
            })
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get; non-200
            # raise HTTPError → except dưới giữ behavior cũ (return None).
            with safe_urlopen(
                urllib.request.Request(url, headers={"User-Agent": "SCP-Verifier/1.0"}),
                timeout=10,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            quote = data.get("Global Quote", {})
            if quote:
                return {
                    "value": quote.get("05. price", ""),
                    "source": "alphavantage",
                    "metadata": {"symbol": symbol, "raw": quote},
                }
        except Exception as e:
            logger.debug(f"[AlphaVantage] stock query failed: {e}", exc_info=True)
        return None

    def _query_forex(self, question: str) -> dict | None:
        import re

        m = re.search(r'\b(USD|EUR|JPY|GBP|VND|CNY|KRW)\b', question, re.I)
        if not m:
            return None
        from_curr = m.group(1).upper()
        to_curr = "USD" if from_curr != "USD" else "EUR"
        try:
            url = build_alphavantage_url({
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_curr,
                "to_currency": to_curr,
                "apikey": self.api_key,
            })
            with safe_urlopen(
                urllib.request.Request(url, headers={"User-Agent": "SCP-Verifier/1.0"}),
                timeout=10,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            rate = data.get("Realtime Currency Exchange Rate", {})
            if rate:
                return {
                    "value": rate.get("5. Exchange Rate", ""),
                    "source": "alphavantage",
                    "metadata": {"from": from_curr, "to": to_curr},
                }
        except Exception as e:
            logger.debug(f"[AlphaVantage] forex query failed: {e}", exc_info=True)
        return None

    def _query_crypto(self) -> dict | None:
        try:
            url = build_alphavantage_url({
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": "BTC",
                "to_currency": "USD",
                "apikey": self.api_key,
            })
            with safe_urlopen(
                urllib.request.Request(url, headers={"User-Agent": "SCP-Verifier/1.0"}),
                timeout=10,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            rate = data.get("Realtime Currency Exchange Rate", {})
            if rate:
                return {
                    "value": rate.get("5. Exchange Rate", ""),
                    "source": "alphavantage",
                    "metadata": {"from": "BTC", "to": "USD"},
                }
        except Exception as e:
            logger.debug(f"[AlphaVantage] crypto query failed: {e}", exc_info=True)
        return None
