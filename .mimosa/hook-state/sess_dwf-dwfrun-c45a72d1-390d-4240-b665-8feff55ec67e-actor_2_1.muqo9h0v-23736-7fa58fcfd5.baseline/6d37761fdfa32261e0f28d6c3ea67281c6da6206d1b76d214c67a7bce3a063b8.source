"""
[Task 8-A] Wikidata source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_wikidata() was 14 LOC inline. Extracted as standalone
function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import threading
import urllib.parse
import urllib.request

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.wikidata")


# [EGRESS-DEGRADE 2026-09-26] Static allowed-host declaration for this source.
# Khi www.wikidata.org bị egress policy từ chối (host không nằm trong allowlist
# compose pass — .env là owner-owned), nguồn này degrade sang CACHE-ONLY:
# không attempt fetch, trả None, log INFO đúng MỘT lần mỗi process thay vì
# WARNING egress mỗi ask (fail-quiet-by-design). Owner thêm host vào
# SCP_EGRESS_ALLOWLIST → nguồn tự mở lại (probe đọc policy live).
_WIKIDATA_EGRESS_PROBE_URL = "https://www.wikidata.org/"
_wikidata_cache_only_logged = False
_wikidata_cache_only_lock = threading.Lock()


def query_wikidata(target: str, question: str) -> str | None:
    """[Z.ai-FIX #23b] Query Wikidata SPARQL for chemical/physical properties.

    [EGRESS-DEGRADE 2026-09-26] Khi wikidata bị egress từ chối → cache-only
    (return None) với INFO một lần/process; không còn WARNING mỗi ask."""
    global _wikidata_cache_only_logged
    from scp.security.url_safety import egress_host_allowed

    if not egress_host_allowed(_WIKIDATA_EGRESS_PROBE_URL):
        with _wikidata_cache_only_lock:
            if not _wikidata_cache_only_logged:
                _wikidata_cache_only_logged = True
                logger.info(
                    "[why_sources.wikidata] host not permitted by the active egress policy — "
                    "degraded to cache-only for this process (single INFO, no per-ask WARNING)"
                )
        return None
    try:
        # Simple Wikidata search → get first entity → return label
        search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(target)}&language=en&format=json&limit=1"
        req = urllib.request.Request(search_url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            results = data.get("search", [])
            if results:
                return results[0].get("description", results[0].get("label", ""))
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.wikidata] failed for target='{target}': {e}", exc_info=True)
        return None
