"""
[OPT-15] MetMuseumDataSource — Metropolitan Museum of Art Collection API.

DNA SCP: SuperGPQA Art discipline needs verifiable artwork metadata (artist,
period, medium, date). The generic ArtsDataSource is broad but not deep on
individual artworks. The Met's Open Access API exposes 490k+ objects with
rich metadata (no key required) — fills the artwork-lookup gap.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.metmuseum")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_MET_SEARCH_URL = "https://collectionapi.metmuseum.org/public/collection/v1/search"
_MET_OBJECT_URL = "https://collectionapi.metmuseum.org/public/collection/v1/objects"


def build_met_search_url(query: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — query được urlencode thành
    query value; host cố định collectionapi.metmuseum.org."""
    return _MET_SEARCH_URL + "?" + urllib.parse.urlencode({
        "q": str(query or ""),
        "hasImages": "true",
    })


def build_met_object_url(object_id: int) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — object_id PHẢI coerce được
    thành int dương; input xấu → ValueError TRƯỚC KHI fetch (fail-closed)."""
    oid = int(object_id)
    if oid <= 0:
        raise ValueError(f"invalid_met_object_id:{oid}")
    return f"{_MET_OBJECT_URL}/{oid}"


class MetMuseumDataSource(IDataSource):
    """Met Museum Collection API — 490k+ artworks (no key required)."""

    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

    def __init__(self):
        # Met Museum public API — no key needed
        self.enabled = True
        logger.info("[MetMuseum] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "metmuseum"

    @property
    def priority(self) -> int:
        return 15  # mid-low — art niche; cross-check ArtsDataSource

    @property
    def ttl(self) -> int:
        return 86400  # 24h — museum collection stable

    def get_supported_intents(self) -> list[str]:
        return ["art", "artwork", "painting", "sculpture", "artist",
                "art_history", "museum", "exhibition"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "art", "nghệ thuật",
            "artwork", "tác phẩm",
            "painting", "tranh",
            "sculpture", "điêu khắc",
            "artist", "họa sĩ",
            "art history", "lịch sử nghệ thuật",
            "museum", "viện bảo tàng",
            "met museum", "metropolitan",
            "met object", "object #", "object id",
            "art collection", "collection",
            "renaissance", "phục hưng",
            "impressionism", "ấn tượng",
            "baroque", "rococo",
            "monet", "van gogh", "picasso", "rembrandt",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (collectionapi.metmuseum.org). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://collectionapi.metmuseum.org/public/collection/v1/objects')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            # Try to extract an object ID first ("met #12345" or "object 12345")
            import re
            m = re.search(r'\b(?:met\s*#?|object\s*)(\d{3,8})\b', question, re.IGNORECASE)
            if m:
                return self._fetch_object(int(m.group(1)))
            # Otherwise search by keyword
            return self._search_objects(question)
        except Exception as e:
            logger.debug(f"[MetMuseum] query failed: {e}", exc_info=True)
            return None

    def _search_objects(self, query: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(build_met_search_url(query))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            object_ids = data.get("objectIDs")
            if not object_ids:
                return None
            # Fetch first object for full metadata
            return self._fetch_object(object_ids[0], total=len(object_ids))
        except Exception as e:
            logger.debug(f"[MetMuseum] search failed: {e}", exc_info=True)
            return None

    def _fetch_object(self, object_id: int, total: int = 1) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder int-coerce + safe_urlopen.
            req = urllib.request.Request(build_met_object_url(object_id))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                obj = json.loads(r.read().decode("utf-8", errors="replace"))
            return {
                "value": obj.get("title", ""),
                "source": "metmuseum",
                "metadata": {
                    "title": obj.get("title", ""),
                    "artist": obj.get("artistDisplayName", ""),
                    "artist_begin_date": obj.get("artistBeginDate", ""),
                    "artist_end_date": obj.get("artistEndDate", ""),
                    "object_date": obj.get("objectDate", ""),
                    "medium": obj.get("medium", ""),
                    "dimensions": obj.get("dimensions", ""),
                    "department": obj.get("department", ""),
                    "classification": obj.get("classification", ""),
                    "period": obj.get("period", ""),
                    "culture": obj.get("culture", ""),
                    "object_id": object_id,
                    "image_url": obj.get("primaryImageSmall", "") or obj.get("primaryImage", ""),
                    "met_url": obj.get("objectURL", ""),
                    "total_results": total,
                    "is_public_domain": obj.get("isPublicDomain", False),
                },
            }
        except Exception as e:
            logger.debug(f"[MetMuseum] fetch object {object_id} failed: {e}", exc_info=True)
            return None
