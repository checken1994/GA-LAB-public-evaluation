"""
[OPT-12] ERICDataSource — Education Resources Information Center API.

DNA SCP: education research / pedagogy claims need verifiable source.
ERIC is the world's largest education database, hosted by US Dept of Education.
API key optional — without it, rate limit is 50 req/day (vs 5000 with key).
Free key: https://eric.ed.gov/?api
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

logger = logging.getLogger("scp.data_sources.eric")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_ERIC_SEARCH_URL = "https://api.eric.ed.gov/v1rest/search"


def build_eric_search_url(search_term: str, api_key: str | None = None,
                          rows: int = 5) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — search_term + api_key được
    urlencode thành query values; host cố định api.eric.ed.gov."""
    params = {
        "search": str(search_term or ""),
        "format": "json",
        "rows": int(rows),
    }
    if api_key:
        params["api_key"] = api_key
    return _ERIC_SEARCH_URL + "?" + urllib.parse.urlencode(params)


class ERICDataSource(IDataSource):
    """ERIC API — education research, pedagogy papers."""

    BASE_URL = "https://api.eric.ed.gov/v1rest"

    def __init__(self):
        self.api_key = os.environ.get("ERIC_API_KEY", "")
        # ERIC works without key (rate-limited) — so enabled even without key
        self.enabled = True
        if not self.api_key:
            logger.info("[ERIC] enabled without key — rate-limited to 50 req/day. "
                        "Set ERIC_API_KEY for 5000 req/day.")
        else:
            logger.info("[ERIC] enabled with API key (5000 req/day)")

    @property
    def name(self) -> str:
        return "eric"

    @property
    def priority(self) -> int:
        return 15  # lower priority — education niche

    @property
    def ttl(self) -> int:
        return 3600  # 1h cache

    def get_supported_intents(self) -> list[str]:
        return ["education", "pedagogy", "research_paper", "curriculum",
                "teaching_method", "academic"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = ["education", "giáo dục", "pedagogy", "sư phạm",
                    "curriculum", "giáo trình", "teaching method", "phương pháp giảng dạy",
                    "school", "trường học", "student", "sinh viên", "học sinh",
                    "eric", "research paper", "luận văn"]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (api.eric.ed.gov). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://api.eric.ed.gov/v1rest/search?format=json')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            # ERIC query syntax: search field using `query` parameter
            # Examples: "title:reading", "author:smith", or full text search
            # For simplicity, do a full-text search on the question
            search_term = self._extract_search_term(question)
            if not search_term:
                return None
            return self._search(search_term)
        except Exception as e:
            logger.debug(f"[ERIC] query failed: {e}", exc_info=True)
            return None

    def _extract_search_term(self, question: str) -> str:
        """Extract meaningful search term from question."""
        import re
        # Strip common question words
        cleaned = re.sub(r'(?i)\b(what|who|when|where|how|why|is|are|the|a|an)\b', '', question)
        cleaned = re.sub(r'[?.,!;:\'"]', '', cleaned).strip()
        # Take up to 5 words
        words = cleaned.split()[:5]
        return ' '.join(words) if words else ""

    def _search(self, search_term: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode rồi fetch qua
            # safe_urlopen thay raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(
                build_eric_search_url(search_term, api_key=self.api_key)
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("response", {}).get("docs", [])
            if results:
                top = results[0]
                return {
                    "value": top.get("title_t", [""])[0] if isinstance(top.get("title_t"), list) else top.get("title_t", ""),
                    "source": "eric",
                    "metadata": {
                        "search_term": search_term,
                        "total_results": data.get("response", {}).get("numFound", 0),
                        "top_results": [
                            {
                                "title": (r.get("title_t", [""])[0]
                                          if isinstance(r.get("title_t"), list)
                                          else r.get("title_t", "")),
                                "author": (r.get("author_t", [""])[0]
                                           if isinstance(r.get("author_t"), list)
                                           else r.get("author_t", "")),
                                "publication_year": r.get("publicationdateyear_t", ""),
                                "eric_id": r.get("id", ""),
                            } for r in results[:3]
                        ],
                    },
                }
        except Exception as e:
            logger.debug(f"[ERIC] search '{search_term}' failed: {e}", exc_info=True)
        return None
