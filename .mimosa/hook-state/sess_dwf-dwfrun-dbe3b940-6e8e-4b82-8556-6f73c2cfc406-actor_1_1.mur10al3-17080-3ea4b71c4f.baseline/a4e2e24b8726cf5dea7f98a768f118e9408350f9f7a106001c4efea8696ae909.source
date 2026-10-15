"""
[Task 8-A] Frankfurter exchange rate source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_frankfurter() was 19 LOC inline. Extracted as standalone
function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import re
import urllib.request

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.frankfurter")


def query_frankfurter(target: str, question: str) -> str | None:
    """Query Frankfurter for exchange rate."""
    try:
        m = re.search(r'(\w{3})\s*(?:sang|to|→)\s*(\w{3})', question, re.IGNORECASE)
        if not m:
            return None
        base, target_cur = m.group(1).upper(), m.group(2).upper()
        url = f"https://api.frankfurter.app/latest?from={base}&to={target_cur}"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            rate = data.get("rates", {}).get(target_cur)
            if rate:
                return f"1 {base} = {rate} {target_cur}"
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.frankfurter] failed for target='{target}': {e}", exc_info=True)
        return None
