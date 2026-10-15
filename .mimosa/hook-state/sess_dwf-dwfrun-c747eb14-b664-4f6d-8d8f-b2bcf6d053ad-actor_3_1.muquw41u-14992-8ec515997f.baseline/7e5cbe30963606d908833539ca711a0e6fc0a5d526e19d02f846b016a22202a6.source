"""
[OPT-12] CourtListenerDataSource — CourtListener REST API v4 (case law).

DNA SCP: SuperGPQA Law discipline needs case-law verification beyond statutes.
CourtListener (Free Law Project) hosts millions of US federal/state court
opinions with a public REST API. Without a token you can still query (rate-
limited); with COURTLISTENER_TOKEN you get higher limits. Fills the case-law
gap left by Cornell LII (statutes only).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.courtlistener")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_CL_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/o/"


def build_courtlistener_search_url(query: str, page_size: int = 5) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — query được urlencode thành
    query value (không thể đổi host/path); host cố định www.courtlistener.com."""
    return _CL_SEARCH_URL + "?" + urllib.parse.urlencode({
        "search": str(query or ""),
        "page_size": int(page_size),
    })


class CourtListenerDataSource(IDataSource):
    """CourtListener API v4 — US case law (free, token optional for rate limit)."""

    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self):
        self.api_key = os.environ.get("COURTLISTENER_TOKEN", "")
        # CourtListener works without token but rate-limited — enabled either way
        self.enabled = True
        if self.api_key:
            logger.info("[CourtListener] enabled with COURTLISTENER_TOKEN (higher rate limit)")
        else:
            logger.info("[CourtListener] enabled without token (rate-limited; set "
                        "COURTLISTENER_TOKEN for higher limits)")

    @property
    def name(self) -> str:
        return "courtlistener"

    @property
    def priority(self) -> int:
        return 16  # mid-low — case-law niche; cross-check Cornell LII

    @property
    def ttl(self) -> int:
        return 3600  # 1h — case law doesn't change often but recent opinions flow

    def get_supported_intents(self) -> list[str]:
        return ["case_law", "court_case", "legal_case", "court_opinion",
                "judicial", "precedent", "ruling"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "case law", "án lệ", "court case", "vụ án",
            "court opinion", "judicial", "tư pháp",
            "precedent", "tiền lệ", "ruling", "phán quyết",
            "supreme court", "tối cao法院", "appeals court",
            "v. ", " vs. ",  # case citation patterns
            "courtlistener",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (www.courtlistener.com). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://www.courtlistener.com/api/rest/v4/')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            return self._search_opinions(question)
        except Exception as e:
            logger.debug(f"[CourtListener] query failed: {e}", exc_info=True)
            return None

    def _search_opinions(self, query: str) -> dict | None:
        try:
            headers = {"User-Agent": "SCP-Verifier/1.0 (educational)"}
            if self.api_key:
                headers["Authorization"] = f"Token {self.api_key}"
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get — validate
            # scheme + chặn private IP trước khi fetch; non-200 → HTTPError.
            req = urllib.request.Request(
                build_courtlistener_search_url(query), headers=headers
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            if not results:
                return None
            top = results[0]
            return {
                "value": top.get("caseName") or top.get("case_name", ""),
                "source": "courtlistener",
                "metadata": {
                    "case_name": top.get("caseName") or top.get("case_name", ""),
                    "date_filed": top.get("dateFiled") or top.get("date_filed", ""),
                    "court": top.get("court", ""),
                    "docket_number": top.get("docketNumber") or top.get("docket_number", ""),
                    "citation": top.get("citation", []),
                    "result_count": data.get("count", 0),
                    "absolute_url": top.get("absolute_url", ""),
                },
            }
        except Exception as e:
            logger.debug(f"[CourtListener] opinion search failed: {e}", exc_info=True)
            return None
