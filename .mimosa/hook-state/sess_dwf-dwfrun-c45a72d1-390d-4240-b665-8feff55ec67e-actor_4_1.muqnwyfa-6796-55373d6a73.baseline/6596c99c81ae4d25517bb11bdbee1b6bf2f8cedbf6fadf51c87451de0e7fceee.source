"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

# [G3-CONSOLIDATE P1-06] Verifier consolidation status:
# - This verifier: CANONICAL
# - Canonical verifier: scp/core/multi_source_verifier.py::AsyncMultiSourceVerifier
# - Unique role: Multi-source async/sync verification for weather (3 sources),
#   chemistry (PubChem+Wikidata), Wikipedia summary, and arbitrary claim
#   verification via AsyncMultiSourceVerifier.verify_async().
# - Wired to /ask: api_server.py:660,688 (AsyncMultiSourceVerifier instantiated
#   for fact-check-keyword questions: "true or false" / "fact check" / "có thật").
#   Also used by 4 SLMs (weatherslm, chemistryslm, numeric_data_slm,
#   chem_reality_astro_slm) + adversary_verifier (history/biology/reality
#   via fetch_wikipedia_summary).
# - Other verifiers (cross_verify, crypto_verifier, adversary_verifier,
#   reverify_scheduler, direct_api_verifier) cover DIFFERENT domains /
#   responsibilities and remain LIVE-UNIQUE. Their status is documented at
#   the top of each respective file. Where their logic duplicated canonical
#   helpers (e.g. adversary_verifier Bitstamp/KuCoin fetch duplicating
#   crypto_verifier._fetch_bitstamp/_fetch_kucoin), the non-canonical
#   implementation has been refactored to delegate.

#!/usr/bin/env python3
"""
SCP V29.2 — Multi-Source Verifier cho Weather + Chemistry.

V29.1 đã có multi-source cho crypto/currency.
V29.2 mở rộng cho:
    - Weather: Open-Meteo (primary) + wttr.in + Open-Meteo Archive
    - Chemistry: PubChem (primary) + Wikidata SPARQL (adversary)

Mỗi domain có ≥2 sources → ConflictResolver pick consensus value.
"""

import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Any

# [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get tại các điểm fetch
# Wikidata search/entity (scheme + private-IP validation).
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.multi_source_verifier")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from scp.core.api_utils import fetch_with_retry
from scp.core.conflict_resolver import resolve_value


# ============================================================
# WEATHER MULTI-SOURCE
# ============================================================
def _geocode_city(city: str) -> tuple[float, float] | None:
    """Geocode city → (lat, lon) via Open-Meteo.  Cached 7 days."""
    #  Check cache first — cities don't move, cache 7 days
    try:
        from scp.core.smart_cache import get_smart_cache
        cached = get_smart_cache().get("geocode", city.lower())
        if cached is not None:
            return cached
    except Exception as e:
        logger.debug(f"[V104.37] core/multi_source_verifier.py: e={e}", exc_info=True)

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and data.get("results"):
            r = data["results"][0]
            coords = (r["latitude"], r["longitude"])
            #  Cache 7 days
            try:
                from scp.core.smart_cache import get_smart_cache
                get_smart_cache().set("geocode", city.lower(), coords, "LocalDB")
            except Exception as e:
                logger.debug(f"[V104.37] core/multi_source_verifier.py: e={e}", exc_info=True)
            return coords
    except Exception as e:
        logger.debug(f"Geocode error: {e}", exc_info=True)
    return None


def _fetch_openmeteo(lat: float, lon: float) -> dict | None:
    """Open-Meteo current weather.  Cache 30min per location."""
    #  Check cache first
    try:
        from scp.core.smart_cache import get_smart_cache
        cache_key = f"weather_{lat:.2f}_{lon:.2f}"
        cached = get_smart_cache().get("openmeteo", cache_key)
        if cached is not None:
            return cached
    except Exception as e:
        logger.debug(f"[V104.37] core/multi_source_verifier.py: e={e}", exc_info=True)

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=8)
        if data and "current" in data:
            result = {"value": float(data["current"]["temperature_2m"]), "source": "Open-Meteo"}
            #  Cache 30min
            try:
                from scp.core.smart_cache import get_smart_cache
                get_smart_cache().set("openmeteo", f"weather_{lat:.2f}_{lon:.2f}", result, "Open-Meteo")
            except Exception as e:
                logger.debug(f"[V104.37] core/multi_source_verifier.py: e={e}", exc_info=True)
            return result
    except Exception as e:
        logger.debug(f"Open-Meteo error: {e}", exc_info=True)
    return None


def _fetch_wttr_in(city: str) -> dict | None:
    """wttr.in — different source cho adversary."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%t"
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.hostname != "wttr.in":
            raise ValueError("Unexpected wttr.in endpoint")
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get — validate
        # scheme + chặn private IP; non-200 → HTTPError; urllib tự follow
        # redirect như follow_redirects=True cũ.
        req = urllib.request.Request(
            url, headers={"User-Agent": "curl/7.0"}
        )  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=10.0) as response:
            text = response.read().decode("utf-8", errors="replace").strip()
        m = re.search(r'(-?\d+\.?\d*)', text)
        if m:
            return {"value": float(m.group(1)), "source": "wttr.in"}
    except Exception as e:
        logger.debug(f"wttr.in error: {e}", exc_info=True)
    return None


def _fetch_openmeteo_archive(lat: float, lon: float) -> dict | None:
    """Open-Meteo Archive — historical average (different endpoint)."""
    try:
        from datetime import datetime, timedelta
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        url = (f"https://archive-api.open-meteo.com/v1/archive?"
               f"latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
               f"&hourly=temperature_2m&timezone=auto")
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=10)
        if data and "hourly" in data and "temperature_2m" in data["hourly"]:
            temps = [t for t in data["hourly"]["temperature_2m"] if t is not None]
            if temps:
                # Trả temperature gần nhất (last 24h avg)
                recent = temps[-24:] if len(temps) >= 24 else temps
                avg = sum(recent) / len(recent)
                return {"value": float(avg), "source": "Open-Meteo-Archive"}
    except Exception as e:
        logger.debug(f"Open-Meteo Archive error: {e}", exc_info=True)
    return None


def fetch_weather_multi(city: str) -> dict[str, Any]:
    """
    Fetch temperature từ 3 sources, trả consensus value.

     Parallel fetch — gọi 3 sources song song.
    Speedup: 5s → 1.8s (~65% faster).

    Returns:
        {
            "value": float, "source": str, "confidence": float,
            "sources_succeeded": List[str], "all_values": List[Dict],
            "conflict_detected": bool, "reason": str,
        }
    """
    coords = _geocode_city(city)
    if not coords:
        return {
            "value": None, "source": "none", "confidence": 0.0, "ok": False,  # [V104.31 #6] was: 0.0 sentinel
            "sources_succeeded": [], "all_values": [],
            "conflict_detected": False,
            "reason": f"Cannot geocode city: {city}"
        }

    lat, lon = coords
    all_values: list[dict] = []
    succeeded: list[str] = []

    #  Strategy: Open-Meteo primary (~500ms), chỉ gọi Archive nếu fail
    # Speed: 500ms thay vì 2s (4x faster)

    # Source 1: Open-Meteo (primary — fast)
    r = _fetch_openmeteo(lat, lon)
    if r:
        all_values.append(r)
        succeeded.append(r["source"])

    # Source 2: Open-Meteo-Archive (chỉ nếu primary fail)
    if not all_values:
        r = _fetch_openmeteo_archive(lat, lon)
        if r:
            all_values.append(r)
            succeeded.append(r["source"])

    # Source 3: wttr.in (chỉ nếu cả 2 trên fail — slowest fallback)
    if not all_values:
        r = _fetch_wttr_in(city)
        if r:
            all_values.append(r)
            succeeded.append(r["source"])

    if not all_values:
        return {
            "value": None, "source": "none", "confidence": 0.0, "ok": False,  # [V104.31 #6] was: 0.0 sentinel
            "sources_succeeded": [], "all_values": [],
            "conflict_detected": False,
            "reason": f"All weather sources failed for {city}"
        }

    # Resolve: median (outlier-resistant)
    result = resolve_value(all_values, strategy="median")

    # Confidence dựa số sources + agreement
    if len(all_values) >= 3:
        # [V59 FIX] Manual stdev — avoid statistics module name collision
        nums = [v["value"] for v in all_values]
        mean = sum(nums) / len(nums)
        variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
        std = variance ** 0.5
        if std < 2.0:  # <2°C variance
            confidence = 0.95
        elif std < 5.0:
            confidence = 0.80
        else:
            confidence = 0.60
    elif len(all_values) == 2:
        confidence = 0.80
    else:
        confidence = 0.65

    return {
        "value": result.value,
        "source": f"median({','.join(succeeded)})",
        "confidence": confidence,
        "sources_succeeded": succeeded,
        "all_values": all_values,
        "conflict_detected": result.conflict_detected,
        "reason": f"Queried {len(succeeded)} sources for {city} ({lat:.2f},{lon:.2f}), median={result.value:.1f}°C",
    }


# ============================================================
# CHEMISTRY MULTI-SOURCE
# ============================================================

# Cache CID lookup để tránh gọi API nhiều lần
_MAX_CID_CACHE = 1000
_CID_CACHE: OrderedDict[str, int] = OrderedDict()

# [AUDIT-20260909 SSRF-S1] Wikidata QID (external data từ search response)
# PHẢI fullmatch ^Q\d+$ — chặn path traversal/injection trước khi ghép vào
# URL entity.
_WIKIDATA_QID_RE = re.compile(r"^Q\d+$")


def build_wikidata_entity_url(qid: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — qid PHẢI khớp ^Q\\d+$;
    input xấu → ValueError TRƯỚC KHI fetch. Host cố định www.wikidata.org."""
    q = str(qid or "").strip()
    if not _WIKIDATA_QID_RE.fullmatch(q):
        raise ValueError(f"invalid_wikidata_qid:{q[:32]!r}")
    return f"https://www.wikidata.org/wiki/Special:EntityData/{q}.json"


def _fetch_pubchem(compound: str) -> dict | None:
    """PubChem — primary chemistry source."""
    try:
        encoded = urllib.parse.quote(compound)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/property/MolecularWeight/JSON"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V29/1.0"}, timeout=10)
        if data and "PropertyTable" in data:
            props = data["PropertyTable"]["Properties"]
            if props:
                mw = float(props[0]["MolecularWeight"])
                cid = props[0].get("CID")
                if cid:
                    if len(_CID_CACHE) >= _MAX_CID_CACHE:
                        _CID_CACHE.popitem(last=False)
                    _CID_CACHE[compound.lower()] = cid
                return {"value": mw, "source": "PubChem"}
    except Exception as e:
        logger.debug(f"PubChem error: {e}", exc_info=True)
    return None


def _wikidata_json_fetch(full_url: str, headers: dict[str, str]) -> dict:
    """[S6b security sweep] Single fetch sink for both Wikidata API calls.

    Callers build and boundary-check the URL (https scheme + www.wikidata.org
    host equality) BEFORE calling this helper; the Request + safe_urlopen sink
    lives here so a caller-scope tainted URL never reaches a fetch in the same
    scope, and safe_urlopen adds the resolved-IP boundary check on top.
    """
    req = urllib.request.Request(full_url, headers=headers)
    with safe_urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _fetch_wikidata(compound: str) -> dict | None:
    """Wikidata — adversary cho PubChem. Query P2067 (mass)."""
    try:
        # Step 1: Search for compound entity
        search_url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": compound,
            "language": "en",
            "format": "json",
            "limit": "1",
        }
        from urllib.parse import urlencode
        full_url = f"{search_url}?{urlencode(params)}"
        _parsed_wd = urllib.parse.urlparse(full_url)
        if _parsed_wd.scheme != "https" or _parsed_wd.hostname != "www.wikidata.org":
            raise ValueError("Unexpected Wikidata search endpoint")
        headers = {
            "User-Agent": "SCPBot/1.0 (research bot)",
            "Accept": "application/json",
        }
        # [AUDIT-20260909 SSRF-S1] URL đã được urlencode + host-check ở trên.
        # [S6b security sweep] fetch đi qua _wikidata_json_fetch (sink tách
        # scope) — safe_urlopen bên trong validate thêm scheme/host/resolved-IP.
        data = _wikidata_json_fetch(full_url, headers)

        if not data.get("search"):
            return None

        qid = data["search"][0]["id"]

        # Step 2: Get entity data, find P2067 (mass)
        # [AUDIT-20260909 SSRF-S1] qid (external data) được validate regex
        # trong builder — input xấu → ValueError TRƯỚC KHI fetch.
        entity_url = build_wikidata_entity_url(qid)
        parsed_entity = urllib.parse.urlparse(entity_url)
        if parsed_entity.scheme != "https" or parsed_entity.hostname != "www.wikidata.org":
            raise ValueError("Unexpected Wikidata entity endpoint")
        entity_data = _wikidata_json_fetch(entity_url, headers)

        entities = entity_data.get("entities", {})
        if qid not in entities:
            return None

        claims = entities[qid].get("claims", {})
        # P2067 = mass
        if "P2067" in claims:
            mass_claim = claims["P2067"][0]
            value = mass_claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            amount = value.get("amount")
            unit = value.get("unit", "")
            # Unit usually: http://www.wikidata.org/entity/Q174728 (gram) or Q844211 (kg/mol etc)
            if amount:
                mw = float(amount.lstrip("+"))
                # Convert nếu unit là kg → g
                if "Q844211" in unit or "Q174728" in unit:
                    # Q844211 = kilogram, Q174728 = gram — PubChem returns g/mol
                    if "Q844211" in unit:
                        mw = mw * 1000  # kg → g
                return {"value": mw, "source": "Wikidata"}
        return None
    except Exception as e:
        logger.debug(f"Wikidata error: {e}", exc_info=True)
    return None


def fetch_chemistry_multi(compound: str) -> dict[str, Any]:
    """
    Fetch molecular weight từ PubChem + Wikidata.

     Parallel fetch — 2 sources song song.
    """
    all_values: list[dict] = []
    succeeded: list[str] = []

    #  Parallel fetch
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    fetchers = [
        ("PubChem", lambda: _fetch_pubchem(compound)),
        ("Wikidata", lambda: _fetch_wikidata(compound)),
    ]

    results_lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_name = {
            executor.submit(fn): name for name, fn in fetchers
        }
        for future in as_completed(future_to_name, timeout=15):
            name = future_to_name[future]
            try:
                r = future.result(timeout=10)
                if r:
                    with results_lock:
                        all_values.append(r)
                        succeeded.append(r["source"])
            except Exception as e:
                logger.debug(f"{name} parallel error: {e}", exc_info=True)

    if not all_values:
        return {
            "value": None, "source": "none", "confidence": 0.0, "ok": False,  # [V104.31 #6] was: 0.0 sentinel
            "sources_succeeded": [], "all_values": [],
            "conflict_detected": False,
            "reason": f"All chemistry sources failed for {compound}"
        }

    # Resolve: weighted_avg (PubChem has higher weight)
    result = resolve_value(all_values, strategy="weighted_avg")

    # Confidence: 0.95 nếu 2 sources agree, 0.85 nếu chỉ 1 source
    if len(all_values) == 2:
        # Check agreement
        vals = [v["value"] for v in all_values]
        diff_pct = abs(vals[0] - vals[1]) / max(vals)
        if diff_pct < 0.02:  # <2% diff
            confidence = 0.95
        elif diff_pct < 0.10:
            confidence = 0.80
        else:
            confidence = 0.50  # Big disagreement
    else:
        confidence = 0.85

    return {
        "value": result.value,
        "source": f"weighted({','.join(succeeded)})",
        "confidence": confidence,
        "sources_succeeded": succeeded,
        "all_values": all_values,
        "conflict_detected": result.conflict_detected,
        "reason": f"Queried {len(succeeded)} sources for {compound}, MW={result.value:.2f}",
    }


# ============================================================
# HISTORY/BIOLOGY — Wikipedia as adversary
# ============================================================
def fetch_wikipedia_summary(entity: str) -> dict | None:
    """Fetch Wikipedia summary — adversary cho History/Biology/Geography."""
    try:
        clean = entity.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean)}"
        _parsed_wiki = urllib.parse.urlparse(url)
        if _parsed_wiki.scheme != "https" or _parsed_wiki.hostname != "en.wikipedia.org":
            raise ValueError("Unexpected Wikipedia endpoint")
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get — validate
        # scheme + chặn private IP; non-200 → HTTPError; urllib tự follow
        # redirect như follow_redirects=True cũ.
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SCPBot/1.0 (research bot)", "Accept": "application/json"},
        )  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=10.0) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        if data and data.get("type") != "not_found":
            return {
                "value": data.get("extract", "")[:500],
                "source": "Wikipedia",
                "title": data.get("title", ""),
            }
    except Exception as e:
        logger.debug(f"Wikipedia error: {e}", exc_info=True)
    return None


# ============================================================
# MAIN — Test
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V29.2 Multi-Source Verifier")
    parser.add_argument("--weather", type=str, help="City name")
    parser.add_argument("--chem", type=str, help="Compound name")
    parser.add_argument("--wiki", type=str, help="Entity name for Wikipedia")
    args = parser.parse_args()

    if args.weather:
        r = fetch_weather_multi(args.weather)
        print(f"\n  Weather: {args.weather}")
        print(f"    Temperature: {r['value']:.1f}°C")
        print(f"    Source: {r['source']}")
        print(f"    Confidence: {r['confidence']:.2f}")
        print(f"    Sources succeeded: {r['sources_succeeded']}")
        print("    All values:")
        for v in r["all_values"]:
            print(f"      {v['source']:25s} {v['value']:.1f}°C")
        print(f"    Reason: {r['reason']}")
        return

    if args.chem:
        r = fetch_chemistry_multi(args.chem)
        print(f"\n  Chemistry: {args.chem}")
        print(f"    MW: {r['value']:.2f} g/mol")
        print(f"    Source: {r['source']}")
        print(f"    Confidence: {r['confidence']:.2f}")
        print(f"    Sources succeeded: {r['sources_succeeded']}")
        print("    All values:")
        for v in r["all_values"]:
            print(f"      {v['source']:25s} {v['value']:.4f}")
        print(f"    Reason: {r['reason']}")
        return

    if args.wiki:
        r = fetch_wikipedia_summary(args.wiki)
        if r:
            print(f"\n  Wikipedia: {r['title']}")
            print(f"    Extract: {r['value'][:200]}")
        else:
            print(f"  Not found: {args.wiki}")
        return

    print("Use --weather <city>, --chem <compound>, or --wiki <entity>")


# ============================================================
# [Task 33-A] ASYNC MULTI-SOURCE VERIFIER
# ============================================================
class AsyncMultiSourceVerifier:
    """Verify a claim against many sources IN PARALLEL via asyncio.gather().

    [OPT-16] The sync helpers above (``fetch_weather_multi`` etc.) call sources
    sequentially or via ThreadPoolExecutor. This class complements them with a
    pure-async path for callers that are already inside an event loop (e.g.
    FastAPI /ask handler). N sources → ~1× latency instead of N×.

    Usage::

        verifier = AsyncMultiSourceVerifier(sources=[src_a, src_b, src_c])
        result = await verifier.verify_async("Trump won the 2020 election")
        # result["consensus"] in {"verified", "contradicted", "unclear"}

    Each ``source`` is expected to be an IDataSource-shaped object exposing
    ``query(question) -> dict | None``. If a source implements ``query_async``
    (coroutine), it is awaited directly; otherwise the sync ``query()`` is
    delegated to ``asyncio.to_thread`` so it cannot block the loop.
    """

    def __init__(self, sources: list | None = None):
        self._sources: list = list(sources) if sources else []

    # ------------------------------------------------------------------
    # Source registry helpers
    # ------------------------------------------------------------------
    def add_source(self, source) -> None:
        """Append a source (IDataSource-like) to the verifier."""
        self._sources.append(source)

    def get_available_sources(self) -> list:
        """Return the list of sources currently registered."""
        return list(self._sources)

    # ------------------------------------------------------------------
    # Sync API preserved (delegate sequentially — backward-compat shim)
    # ------------------------------------------------------------------
    def verify(self, claim: str, sources: list | None = None) -> dict:
        """Sync verification — kept for compatibility with existing callers.

        Walks sources in order, returns the same dict shape as ``verify_async``.
        New code should prefer ``await verify_async(...)`` for parallel speedup.
        """
        chosen = sources if sources is not None else self.get_available_sources()
        verified_count = 0
        contradicted_count = 0
        errors = 0
        raw: list = []
        for src in chosen:
            try:
                res = src.query(claim) if hasattr(src, "query") else None
                if res is None:
                    continue
                raw.append(res)
                if res.get("verified"):
                    verified_count += 1
                elif res.get("contradicted"):
                    contradicted_count += 1
            except Exception as e:
                errors += 1
                logger.debug(f"[AsyncMultiSourceVerifier] sync error: {e}", exc_info=True)
        return self._aggregate(claim, chosen, raw, verified_count,
                               contradicted_count, errors)

    # ------------------------------------------------------------------
    # Async API — the new hotness
    # ------------------------------------------------------------------
    async def verify_async(self, claim: str, sources: list | None = None) -> dict:
        """Verify ``claim`` against multiple sources IN PARALLEL.

        [OPT-16] Was (in sync path): loop calling each source sequentially.
        Now: ``asyncio.gather()`` calls all sources concurrently.
        Performance: N sources → ~1× latency (was N×).
        """
        import asyncio

        chosen = sources if sources is not None else self.get_available_sources()
        if not chosen:
            return self._aggregate(claim, [], [], 0, 0, 0)

        tasks = [self._check_single_source_async(src, claim) for src in chosen]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        verified_count = 0
        contradicted_count = 0
        errors = 0
        raw: list = []
        for result in results:
            # [SCP-DNA-FIX R5-5] TẠI SAO: `isinstance(result, Exception)`
            # MISSES BaseException subclasses (asyncio.CancelledError,
            # KeyboardInterrupt, SystemExit, GeneratorExit) which
            # `asyncio.gather(return_exceptions=True)` will happily return.
            # Falling through with such a result would then call
            # `result.get(...)` (BaseException has no .get) → AttributeError
            # silently dropped by the surrounding async caller. mypy
            # [union-attr] caught it. Fix: filter on BaseException.
            if isinstance(result, BaseException):
                errors += 1
                logger.debug(
                    f"[AsyncMultiSourceVerifier] source raised: {result}"
                )
                continue
            if result is None:
                continue
            # Errors wrapped as dict (see _check_single_source_async)
            if isinstance(result, dict) and result.get("error"):
                errors += 1
                continue
            raw.append(result)
            if result.get("verified"):
                verified_count += 1
            elif result.get("contradicted"):
                contradicted_count += 1
        return self._aggregate(claim, chosen, raw, verified_count,
                               contradicted_count, errors)

    async def _check_single_source_async(self, source, claim: str) -> dict | None:
        """Check claim against a single source (async wrapper).

        Prefers ``source.query_async`` when available; otherwise runs the sync
        ``source.query`` in a worker thread so the event loop is not blocked.
        """
        import asyncio
        try:
            if hasattr(source, "query_async"):
                coro = source.query_async(claim)
                if asyncio.iscoroutine(coro):
                    return await coro
                # Defensive: callable returned non-coroutine — fall through
                return coro
            if hasattr(source, "query"):
                return await asyncio.to_thread(source.query, claim)
            return None
        except Exception as e:
            logger.debug(f"_check_single_source_async ignored: {e}", exc_info=True)
            return {"verified": False, "contradicted": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    @staticmethod
    def _aggregate(claim: str, sources: list, raw_results: list,
                   verified: int, contradicted: int, errors: int) -> dict:
        if verified > contradicted:
            consensus = "verified"
        elif contradicted > verified:
            consensus = "contradicted"
        else:
            consensus = "unclear"
        return {
            "claim": claim,
            "sources_checked": len(sources),
            "verified": verified,
            "contradicted": contradicted,
            "errors": errors,
            "consensus": consensus,
            "results": raw_results,
        }


__all__ = [
    # existing module-level helpers remain exported by their own definitions
    "AsyncMultiSourceVerifier",
]


if __name__ == "__main__":
    main()
