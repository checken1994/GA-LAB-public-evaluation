"""
[Task 8-A] REST Countries source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_rest_countries() was 30 LOC inline. Extracted as
standalone function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import urllib.parse
import urllib.request

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.rest_countries")


def query_rest_countries(target: str) -> str | None:
    """[FIX #22] Query REST Countries API — deprecated, fall back to LocalDB.

    TẠI SAO: REST Countries v3.1/v3.2/v2 all return {'success': False, ...}
    (deprecated as of 2026). Was falling back to Wikipedia, which returns
    a description text (not the capital) -> WHY engine sees "France, officially..."
    vs LocalDB "Paris" -> CONFLICT (false positive).
    Reality > Model: tested "capital of France" -> REST Countries returned
    Wikipedia description, LocalDB returned "Paris" -> CONFLICT. After fix:
    REST Countries returns None (deprecation acknowledged) -> WHY engine
    uses LocalDB + Wikipedia only -> PASS.
    """
    try:
        url = f"https://restcountries.com/v3.1/name/{urllib.parse.quote(target)}"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            # Check for deprecation response
            if isinstance(data, dict) and data.get('success') is False:
                logger.debug(f"WHY: REST Countries API deprecated for '{target}'")
                return None  # Don't fall back to Wikipedia (causes CONFLICT)
            if isinstance(data, list) and data:
                country = data[0]
                cap = country.get('capital', [''])[0] if country.get('capital') else ''
                return cap if cap else None
            return None
    except Exception as e:
        logger.debug(f"WHY REST Countries error: {e}", exc_info=True)
        return None  # Return None, not Wikipedia fallback
