# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""
[Task 8-A] Open-Meteo weather source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_open_meteo() was 25 LOC inline. Extracted as standalone
function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import os
import urllib.request
from urllib.parse import quote as _url_quote

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.open_meteo")


def query_open_meteo(target: str, question: str) -> str | None:
    """Query Open-Meteo for weather."""
    try:
        # [M12-FIX PF-5] Endpoint seam (same trust level as OPENAI_BASE_URL):
        # SCP_WHY_OPENMETEO_BASE redirects BOTH the geocoding and forecast
        # hosts (defaults unchanged: geocoding-api.open-meteo.com and
        # api.open-meteo.com). When overridden, loopback/private targets are
        # explicitly allowed; default path keeps SSRF protection.
        _base_override = os.environ.get("SCP_WHY_OPENMETEO_BASE")
        _geo_base = _base_override or "https://geocoding-api.open-meteo.com"
        _wx_base = _base_override or "https://api.open-meteo.com"
        _allow_internal = bool(_base_override)
        # Geocode city name
        # [M12-FIX PF-7] target was interpolated RAW into the URL: any
        # multi-word target ("new york", "hồ chí minh", regex-extracted
        # "singapore là 27 độ c") raised
        # ValueError("URL can't contain control characters") inside urllib and
        # the handler swallowed it -> the weather source returned None for
        # EVERY multi-word target. Encode the query parameter like wikipedia.py
        # does with urlencode.
        geo_url = f"{_geo_base}/v1/search?name={_url_quote(target)}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8, allow_internal=_allow_internal) as resp:
            geo = _json.loads(resp.read().decode('utf-8'))
            results = geo.get("results", [])
            if not results:
                return None
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
        # Get weather
        weather_url = f"{_wx_base}/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        req = urllib.request.Request(weather_url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8, allow_internal=_allow_internal) as resp:
            w = _json.loads(resp.read().decode('utf-8'))
            temp = w.get("current", {}).get("temperature_2m", "")
            return f"temperature={temp}°C"
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.open_meteo] failed for target='{target}': {e}", exc_info=True)
        return None
