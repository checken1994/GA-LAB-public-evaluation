"""
[OPT-19] UNDataDataSource — UN Data API (country statistics & demographics).

DNA SCP: SuperGPQA Political Science discipline needs verifiable country
statistics (population, GDP, trade, demographics, education, energy). WorldBank
covers economic indicators but UN Data adds trade, energy, environment,
population breakdowns. UN Data's SOAP/JSON API is free without a key —
fills the political_science stats gap.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.undata")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_UNDATA_SEARCH_URL = "https://data.un.org/ws/bs/JsonService.svc/Search"


def build_undata_search_url(query: str, max_results: int = 5) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — searchQuery được urlencode
    thành query value; host cố định data.un.org."""
    return _UNDATA_SEARCH_URL + "?" + urllib.parse.urlencode({
        "searchQuery": str(query or ""),
        "maxRes": int(max_results),
    })


class UNDataDataSource(IDataSource):
    """UN Data API — country stats, demographics, trade, energy (no key)."""

    BASE_URL = "https://data.un.org/ws/bs/JsonService.svc"

    def __init__(self):
        # UN Data API is free, no key needed
        self.enabled = True
        logger.info("[UNData] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "undata"

    @property
    def priority(self) -> int:
        return 15  # mid-low — political_science niche; cross-check WorldBank

    @property
    def ttl(self) -> int:
        return 86400  # 24h — UN stats update annually

    def get_supported_intents(self) -> list[str]:
        return ["country_stats", "demographics", "trade_stats",
                "energy_stats", "population_stats", "political_science",
                "un_data"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "country stats", "thống kê quốc gia",
            "demographics", "nhân khẩu học",
            "trade stats", "thương mại",
            "energy stats", "năng lượng",
            "population", "dân số",
            "un data", "liên hiệp quốc",
            "united nations", "un stats",
            "life expectancy", "tuổi thọ",
            "infant mortality", "tử vong trẻ sơ sinh",
            "migration", "di cư",
            "refugee", "nạn nhân",
            "gender", "giới tính",
            "literacy", "xóa mù chữ",
            "human development", "phát triển con người",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (data.un.org). Trước đây hardcode `return self.enabled`
        — constructor config, không phải live evidence (fail-open). Bất kỳ HTTP
        response nào (kể cả 4xx do thiếu key/tham số) chứng minh service
        sống; exception (egress denied, DNS, timeout) → False.

        Kết quả đi qua shared negative-result cache cross-instance
        (`shared_health_ping`): trong TTL (SCP_HEALTH_NEG_CACHE_TTL,
        default 60s) các lần gọi sau trả lại quan sát gần nhất — kể cả
        False (đó là reality gần nhất, không fake health) — mà KHÔNG
        re-ping."""
        return shared_health_ping(type(self).__name__, self._live_ping)

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật — 1 network round-trip tới URL cố định,
        không chứa key; HTTP response nào cũng = endpoint sống."""
        return reachability_ping('https://data.un.org/ws/bs/JsonService.svc/Search')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            return self._search_data(question)
        except Exception as e:
            logger.debug(f"[UNData] query failed: {e}", exc_info=True)
            return None

    def _search_data(self, query: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError → fallback giữ behavior cũ.
            try:
                req = urllib.request.Request(
                    build_undata_search_url(query),
                    headers={"User-Agent": "SCP-Verifier/1.0 (educational)"},
                )  # noqa: S310 — validated by safe_urlopen
                with safe_urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as he:
                logger.debug(f"[UNData] search returned {he.code}")
                # Fallback to UN Data public search page
                return self._fallback_search_page(query)
            results = (data.get("d") or data.get("results") or
                       data.get("SearchResults") or [])
            if not results:
                return None
            top = results[0]
            return {
                "value": top.get("IndicatorName") or top.get("Title") or "",
                "source": "undata",
                "metadata": {
                    "indicator": top.get("IndicatorName") or top.get("Title", ""),
                    "country": top.get("Country") or top.get("Area", ""),
                    "year": top.get("Year", ""),
                    "value": top.get("Value", ""),
                    "unit": top.get("Unit", ""),
                    "url": top.get("Url", ""),
                    "result_count": len(results),
                },
            }
        except Exception as e:
            logger.debug(f"[UNData] search failed: {e}", exc_info=True)
            return None

    def _fallback_search_page(self, query: str) -> dict | None:
        """Fallback: UN Data public search HTML page (no JSON API)."""
        import urllib.parse
        import urllib.request

        from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode query rồi fetch qua
            # safe_urlopen thay raw httpx.get.
            url = "https://data.un.org/Search.aspx?" + urllib.parse.urlencode(
                {"q": str(query or "")}
            )
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Verifier/1.0 (educational)"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                body = r.read()
            return {
                "value": query,
                "source": "undata",
                "metadata": {
                    "url": url,
                    "fallback": True,
                    "page_size": len(body),
                },
            }
        except Exception as e:
            logger.debug(f"[UNData] fallback search failed: {e}", exc_info=True)
            return None
