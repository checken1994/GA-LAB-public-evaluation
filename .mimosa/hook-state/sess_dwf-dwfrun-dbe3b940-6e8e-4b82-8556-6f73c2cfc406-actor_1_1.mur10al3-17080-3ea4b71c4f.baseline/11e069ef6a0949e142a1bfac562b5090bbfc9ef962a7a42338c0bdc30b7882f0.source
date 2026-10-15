"""
[OPT-11] CornellLIIDataSource — Cornell Law LII (Legal Information Institute).

DNA SCP: law domain had no dedicated primary DataSource — only the generic
LegalDataSource. Cornell LII is the authoritative community resource for
US Constitution, US Code, UCC, CFR — fills the gap for SuperGPQA's Law
discipline (constitutional questions, statute lookup, federal regulations).
Public site is crawl-friendly and exposes a search endpoint (no API key).
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.cornell_lii")

# [AUDIT-20260909 SSRF-S1] USC title number PHẢI là digits (ràng buộc chặt
# hơn regex caller để fail-closed trong builder).
_USC_TITLE_RE = re.compile(r"^\d{1,3}$")


def build_usc_title_url(title_number: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — title number PHẢI fullmatch
    ^\\d{1,3}$; input xấu → ValueError TRƯỚC KHI fetch. Host cố định
    www.law.cornell.edu."""
    num = str(title_number or "").strip()
    if not _USC_TITLE_RE.fullmatch(num):
        raise ValueError(f"invalid_usc_title:{num[:16]!r}")
    return f"https://www.law.cornell.edu/uscode/text/{num}"


def build_lii_search_url(question: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — question được urlencode
    thành query value, không thể đổi host/path. Host cố định."""
    return "https://www.law.cornell.edu/wext/search.html?" + urllib.parse.urlencode(
        {"q": str(question or "")}
    )


class CornellLIIDataSource(IDataSource):
    """Cornell Law LII — US Constitution, US Code, UCC, CFR (no key required)."""

    BASE_URL = "https://www.law.cornell.edu"
    SEARCH_URL = "https://www.law.cornell.edu/wext/search.html"

    # Direct canonical entry points (HTML pages — parsed minimally for snippets)
    CONSTITUTION_URL = "https://www.law.cornell.edu/constitution/constitution.table.html"
    UCC_URL = "https://www.law.cornell.edu/ucc/ucc.table.html"
    USC_URL = "https://www.law.cornell.edu/uscode/text/"

    def __init__(self):
        # Cornell LII is public + crawl-friendly, no API key needed
        self.enabled = True
        logger.info("[CornellLII] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "cornell_lii"

    @property
    def priority(self) -> int:
        return 15  # mid-low — legal niche; cross-check with LegalDataSource

    @property
    def ttl(self) -> int:
        return 86400  # 24h — law doesn't change fast

    def get_supported_intents(self) -> list[str]:
        return ["law", "legal", "constitution", "statute", "regulation",
                "ucc", "usc", "cfr", "federal_law", "us_law"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = [
            "constitution", "hiến pháp", "statute", "luật",
            "regulation", "quy định", "ucc", "uniform commercial code",
            "usc", "united states code", "cfr", "code of federal regulations",
            "federal law", "supreme court", "amendment", "tu chính",
            "cornell", "lii", "bill of rights",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (www.law.cornell.edu). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://www.law.cornell.edu/uscode/text/')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            q = question.lower()
            # Route to most specific resource first
            if "constitution" in q or "hiến pháp" in q or "amendment" in q or "bill of rights" in q:
                return self._fetch_url(self.CONSTITUTION_URL, "US Constitution", question)
            if "ucc" in q or "uniform commercial code" in q:
                return self._fetch_url(self.UCC_URL, "Uniform Commercial Code", question)
            # USC title lookup — extract title number if present
            m = re.search(r'\busc\s*(\d+)\b', q)
            if m:
                # [AUDIT-20260909 SSRF-S1] builder validate digits-only.
                return self._fetch_url(build_usc_title_url(m.group(1)),
                                       f"USC Title {m.group(1)}", question)
            # Generic search via LII search endpoint
            return self._search_lii(question)
        except Exception as e:
            logger.debug(f"[CornellLII] query failed: {e}", exc_info=True)
            return None

    def _fetch_url(self, url: str, label: str, question: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get — validate
            # scheme + chặn private IP trước khi fetch. Non-200 → HTTPError.
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Verifier/1.0 (educational)"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                body = r.read()
            # Return reference — LII pages are authoritative legal text
            return {
                "value": label,
                "source": "cornell_lii",
                "metadata": {
                    "url": url,
                    "question": question,
                    "verified": True,
                    "page_size": len(body),
                },
            }
        except Exception as e:
            logger.debug(f"[CornellLII] fetch {label} failed: {e}", exc_info=True)
            return None

    def _search_lii(self, question: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode question trước khi fetch.
            url = build_lii_search_url(question)
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Verifier/1.0 (educational)"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                body = r.read()
            return {
                "value": question,
                "source": "cornell_lii",
                "metadata": {
                    "url": url,
                    "search_performed": True,
                    "page_size": len(body),
                },
            }
        except Exception as e:
            logger.debug(f"[CornellLII] search failed: {e}", exc_info=True)
            return None
