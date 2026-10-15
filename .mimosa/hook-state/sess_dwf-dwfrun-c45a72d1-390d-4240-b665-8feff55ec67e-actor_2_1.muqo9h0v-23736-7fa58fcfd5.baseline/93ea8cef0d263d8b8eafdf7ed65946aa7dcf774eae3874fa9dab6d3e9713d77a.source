"""
[OPT-15] GoogleFactCheckDataSource — Google Fact Check API integration.

DNA SCP #6 Evidence: Google Fact Check API aggregates 40k+ fact checks
from 100+ publishers (Snopes, PolitiFact, FactCheck.org, Reuters, etc.).
Free tier: 10k requests/day.

Env: GOOGLE_FACT_CHECK_API_KEY (already in .env, currently empty)
API: https://factchecktools.googleapis.com/v1alpha1/claims:search
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

logger = logging.getLogger("scp.data_sources.google_factcheck")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_GC_FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def build_google_factcheck_url(query: str, api_key: str,
                               max_age_days: int = 365) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — query + api_key được
    urlencode thành query values; host cố định factchecktools.googleapis.com."""
    return _GC_FACTCHECK_URL + "?" + urllib.parse.urlencode({
        "query": str(query or "")[:500],
        "key": api_key,
        "languageCode": "en",
        "maxAgeDays": int(max_age_days),
    })


class GoogleFactCheckDataSource(IDataSource):
    """Google Fact Check API — aggregate fact checks from 100+ publishers."""

    BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.info(
                "[GoogleFactCheck] disabled — set GOOGLE_FACT_CHECK_API_KEY to enable"
            )

    @property
    def name(self) -> str:
        return "google_factcheck"

    @property
    def priority(self) -> int:
        return 8  # high priority — authoritative fact checks

    @property
    def ttl(self) -> int:
        return 3600  # 1h cache

    def get_supported_intents(self) -> list[str]:
        return ["fact_check", "claim_verify", "news_verify", "general"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "true or false", "fact check", "is it true", "có thật",
            "đúng không", "real or fake", "verified", "kiểm chứng",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (factchecktools.googleapis.com). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://factchecktools.googleapis.com/v1alpha1/claims')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(
                build_google_factcheck_url(question, api_key=self.api_key)
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            claims = data.get("claims", [])
            if not claims:
                return None
            # Aggregate ratings from all publishers
            ratings = []
            for claim in claims[:5]:
                review = (claim.get("claimReview") or [{}])[0]
                rating = review.get("textualRating", "")
                publisher = review.get("publisher", {}).get("name", "")
                ratings.append({"rating": rating, "publisher": publisher})
            # Determine consensus
            false_count = sum(
                1 for r in ratings if "false" in r["rating"].lower()
            )
            true_count = sum(
                1 for r in ratings if "true" in r["rating"].lower()
            )
            if false_count > true_count:
                verdict = "FALSE"
            elif true_count > false_count:
                verdict = "TRUE"
            else:
                verdict = "MIXED"
            return {
                "value": verdict,
                "source": "google_factcheck",
                "metadata": {
                    "claims_found": len(claims),
                    "ratings": ratings,
                    "consensus": verdict,
                },
            }
        except Exception as e:
            logger.debug(f"[GoogleFactCheck] query failed: {e}", exc_info=True)
            return None


__all__ = ["GoogleFactCheckDataSource"]
