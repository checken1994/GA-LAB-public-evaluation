"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 LiveKnowledgeFetcher — RAG via 4 APIs (Wikipedia + Wikidata + arXiv + DuckDuckGo).

Giải quyết vấn đề "bỏ đó nằm im": Khi local DB không có câu trả lời, fetch online.

Flow:
  1. Tìm trong cache DB (knowledge_cache table)
  2. Nếu không có, gọi APIs theo priority của domain
  3. Cross-check ≥2 sources (nếu có nhiều sources)
  4. Cache kết quả với TTL
  5. Return result + metadata (sources, confidence, fetched_at)
"""
import hashlib
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any

from defusedxml import ElementTree as ET  # nosec B314 — defusedxml hardens XXE

# [AUDIT-20260909 SSRF-S1] Thay mọi raw requests.get bằng safe_urlopen
# (scheme allowlist + chặn private/loopback IP) — cùng pattern misc_slms2.py.
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.live_knowledge")

# [G3-CONSOLIDATE RE-10 / G3-full-B] sys.path.insert(0, SCRIPT_DIR) REMOVED
# (also removed `import os` + `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`
# — both were ONLY used by the sys.path hack).
# Why: it prepended scp/data_sources/ to sys.path, which shadowed the stdlib
# `statistics` module (scp/data_sources/statistics.py has no `mean()`). This
# broke `import statistics` in scp/security/response_monitor.py and caused 6
# test errors in tests/test_response_monitor.py when run after any test that
# imports RealityJudge. The hack was unnecessary — all imports in this file
# are absolute (`from scp.X.Y import ...`) or stdlib. Removing it eliminates
# the test-isolation bug documented in worklog.md Task 9-C finding C4 + Top
# test-suite integrity issues #10 (line ~1558).
# VERIFICATION: tests/test_response_monitor.py now passes 15/15 (was 9/15).

from scp.core.db_manager import db_exec, db_query_one, init_db

# [G3-CONSOLIDATE RE-05] Canonical Wikipedia client — replaces inline
# fetch_wikipedia() HTTP code below. Other modules should also import from
# here instead of re-implementing. See scp/core/wikipedia_client.py.
from scp.core.wikipedia_client import search_then_summary as _wiki_search_then_summary

# ============================================================
# CACHE TABLE
# ============================================================
CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS live_knowledge_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL UNIQUE,
    query_text TEXT,
    domain TEXT,
    value TEXT,
    source TEXT,
    sources_succeeded TEXT,
    confidence REAL,
    fetched_at TEXT,
    expires_at TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_lkc_hash ON live_knowledge_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_lkc_domain ON live_knowledge_cache(domain);
CREATE INDEX IF NOT EXISTS idx_lkc_expires ON live_knowledge_cache(expires_at);
"""


def _init_cache_db():
    try:
        init_db()
        for stmt in CACHE_SCHEMA.strip().split(';'):
            stmt = stmt.strip()
            if stmt:
                db_exec(stmt)
    except Exception as e:
        logger.warning(f"init_cache_db: {e}", exc_info=True)


def _hash_query(query: str, domain: str = "") -> str:
    return hashlib.sha256(f"{domain}:{query.lower().strip()}".encode()).hexdigest()[:16]


# ============================================================
# API FETCHERS
# ============================================================
# [AUDIT-20260909 SSRF-S1] URL builders — pure, testable. Input động
# (query) bị encode TRƯỚC khi fetch; host luôn là literal cố định.
def build_wikidata_url(query: str, language: str = "vi") -> str:
    """Wikidata entity-lookup URL — query được urlencode → không thể đổi
    host/path. Host cố định https://www.wikidata.org."""
    return (
        "https://www.wikidata.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "wbsearchentities",
            "search": str(query or ""),
            "language": language,
            "format": "json",
            "limit": 1,
        })
    )


def build_arxiv_url(query: str, max_results: int = 3) -> str:
    """arXiv API URL — query được quote(safe='') → '/', '..', '?', '&'
    không thể thoát khỏi MỘT path/query segment. Host cố định export.arxiv.org."""
    quoted = urllib.parse.quote(str(query or ""), safe="")
    return (
        f"http://export.arxiv.org/api/query"
        f"?search_query=all:{quoted}&start=0&max_results={int(max_results)}"
    )


def build_duckduckgo_url(query: str) -> str:
    """DuckDuckGo Instant Answer URL — query được urlencode. Host cố định."""
    return "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
        "q": str(query or ""),
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    })


def _safe_get_bytes(url: str, timeout: float = 8) -> bytes:
    """[AUDIT-20260909 SSRF-S1] Fetch qua safe_urlopen, trả về raw bytes.
    Non-200 → urllib raise HTTPError → caller's except trả None (giữ nguyên
    behavior `status_code != 200 → None` của code cũ)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "SCP-LiveKnowledge/1.0"}
    )  # noqa: S310 — scheme/host validated by safe_urlopen
    with safe_urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_wikipedia(query: str, lang: str = "vi") -> dict[str, Any] | None:
    """Fetch từ Wikipedia REST API.

    [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
    (search_then_summary). Same return shape, same vi→en fallback behavior.
    The previous inline implementation (2 raw HTTP GET calls) was
    removed in [AUDIT-20260909 SSRF-S1] — the live path goes through the
    canonical client so all Wikipedia calls share one rate-limit + cache.
    """
    # [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
    try:
        result = _wiki_search_then_summary(query, lang=lang)
        if result and result.get("extract"):
            return {
                "value": result["extract"],
                "source": f"Wikipedia ({lang})",
                "metadata": {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "method": "wikipedia",
                    "lang": lang,
                },
            }
        # vi→en fallback (preserved from original implementation)
        if lang != "en":
            return fetch_wikipedia(query, lang="en")
        return None
    except Exception as e:
        logger.debug(f"Wikipedia fetch error: {e}", exc_info=True)
        return None
    # --- PREVIOUS IMPLEMENTATION removed [AUDIT-20260909 SSRF-S1]: it
    # contained raw HTTP GET snippets flagged as SSRF debt; the live
    # path is _wiki_search_then_summary above (canonical, rate-limited). ---


def fetch_wikidata(query: str) -> dict[str, Any] | None:
    """Fetch từ Wikidata (entity lookup)."""
    try:
        data = json.loads(
            _safe_get_bytes(build_wikidata_url(query, language="vi"), timeout=8)
        )
        results = data.get("search", [])
        if not results:
            # Try English
            data = json.loads(
                _safe_get_bytes(build_wikidata_url(query, language="en"), timeout=8)
            )
            results = data.get("search", [])
            if not results:
                return None
        r = results[0]
        return {
            "value": r.get("description", r.get("label", "")),
            "source": "Wikidata",
            "metadata": {
                "id": r.get("id", ""),
                "label": r.get("label", ""),
                "description": r.get("description", ""),
                "method": "wikidata",
            }
        }
    except Exception as e:
        logger.debug(f"Wikidata fetch error: {e}", exc_info=True)
        return None


def fetch_arxiv(query: str, max_results: int = 3) -> dict[str, Any] | None:
    """Fetch từ arXiv API (academic papers)."""
    try:
        body = _safe_get_bytes(build_arxiv_url(query, max_results), timeout=10)
        root = ET.fromstring(body)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if not entries:
            return None
        first = entries[0]
        title = first.find("atom:title", ns).text.strip().replace("\n", " ") if first.find("atom:title", ns) is not None else ""
        summary = first.find("atom:summary", ns).text.strip().replace("\n", " ")[:500] if first.find("atom:summary", ns) is not None else ""
        return {
            "value": f"{title}. {summary}",
            "source": "arXiv",
            "metadata": {
                "title": title,
                "summary": summary,
                "total_results": len(entries),
                "method": "arxiv",
            }
        }
    except Exception as e:
        logger.debug(f"arXiv fetch error: {e}", exc_info=True)
        return None


def fetch_duckduckgo(query: str) -> dict[str, Any] | None:
    """Fetch từ DuckDuckGo Instant Answer API."""
    try:
        data = json.loads(
            _safe_get_bytes(build_duckduckgo_url(query), timeout=8)
        )
        # Try AbstractText first
        if data.get("AbstractText"):
            return {
                "value": data["AbstractText"],
                "source": data.get("AbstractSource", "DuckDuckGo"),
                "metadata": {
                    "url": data.get("AbstractURL", ""),
                    "heading": data.get("Heading", ""),
                    "method": "duckduckgo",
                }
            }
        # Try Answer
        if data.get("Answer"):
            return {
                "value": data["Answer"],
                "source": "DuckDuckGo Answer",
                "metadata": {"method": "duckduckgo_answer"}
            }
        # Try RelatedTopics
        related = data.get("RelatedTopics", [])
        if related and isinstance(related, list) and len(related) > 0:
            first = related[0]
            if isinstance(first, dict) and first.get("Text"):
                return {
                    "value": first["Text"],
                    "source": "DuckDuckGo Related",
                    "metadata": {
                        "url": first.get("FirstURL", ""),
                        "method": "duckduckgo_related",
                    }
                }
        return None
    except Exception as e:
        logger.debug(f"DuckDuckGo fetch error: {e}", exc_info=True)
        return None


# ============================================================
# API ROUTER
# ============================================================
def _fetch_unconfigured_source(query: str, source_name: str = "") -> dict[str, Any] | None:
    """Stub for authoritative sources whose real API isn't integrated yet.

    [FIX-CRIT-46 BUG 8] TẠI SAO: medlineplus / mayoclinic / fda / who were
    aliased to fetch_wikipedia. When the medical domain's preferred_apis
    included 'medlineplus', the fetcher silently returned a Wikipedia extract
    and labeled the result as cross-checked with 'medlineplus'. That is a
    fabrication: Wikipedia is NOT MedlinePlus/FDA/WHO, and the medical
    cross-check badge was misleading — a clinician trusting the "medlineplus
    cross-checked" badge could rely on a Wikipedia summary for a drug dose.
    Constitution: "abstain rather than fabricate". Fix: return None (abstain)
    so the caller knows this authoritative source is unavailable and does
    NOT silently substitute Wikipedia for it. The fallback_order in
    fetch_with_priority still tries wikipedia/wikidata/duckduckgo/arxiv, but
    those will be labeled with their real source names — no fake badge.
    """
    logger.debug(
        f"[live_knowledge] {source_name or 'source'} API not configured — "
        f"abstaining (returning None instead of substituting Wikipedia)"
    )
    return None


API_MAP = {
    "wikipedia": fetch_wikipedia,
    "wikidata": fetch_wikidata,
    "arxiv": fetch_arxiv,
    "duckduckgo": fetch_duckduckgo,
    # [FIX-CRIT-46 BUG 8] TẠI SAO: medlineplus / mayoclinic / fda / who were
    # aliased to fetch_wikipedia → medical cross-check badge was fabricated
    # (Wikipedia extract labeled as cross-checked with authoritative medical
    # source). Fix: each returns None (abstain) via _fetch_unconfigured_source
    # so the caller knows the real source is unavailable and does NOT silently
    # substitute Wikipedia. If/when the real APIs are integrated, replace the
    # lambda with the real fetcher.
    "medlineplus": lambda q: _fetch_unconfigured_source(q, "medlineplus"),
    "mayoclinic": lambda q: _fetch_unconfigured_source(q, "mayoclinic"),
    "fda": lambda q: _fetch_unconfigured_source(q, "fda"),
    "who": lambda q: _fetch_unconfigured_source(q, "who"),
    # (kept as Wikipedia fallbacks — these are not medical-safety-critical
    # sources and have separate DataSource verifiers where authoritative
    # data is needed: PubChemVerifier, RESTCountriesDataSource, etc.)
    "pubchem": fetch_wikipedia,      # chemistry (PubChem has separate verifier)
    "restcountries": fetch_wikipedia,  # geography (REST Countries has separate DS)
    "openstreetmap": fetch_wikipedia,  # cartography
}


# ============================================================
# VALUE EXTRACTION (for cross-check)
# ============================================================
# [FIX-CRIT-46 BUG 9] TẠI SAO: cross-check was comparing PROSE overlap
# (word set intersection) between two source extracts. Two sources can
# AGREE on the value but use different prose ("speed of light is 299,792
# km/s" vs "light travels at approximately 299,792 kilometers per second")
# → marked as CONFLICT (0.45). Two sources can CONFLICT on the value but
# share boilerplate prose ("speed of light is 300,000 km/s" vs "speed of
# light is 299,792 km/s") → marked as AGREE (0.85). Both directions wrong.
# Fix: extract the key fact (numeric value + unit) from each source FIRST,
# then compare value sets — intersection → agree, disjoint → conflict.
# Only fall back to prose overlap when no numeric values can be extracted
# from at least one source.
_VALUE_NUM_RE = re.compile(
    r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*'
    r'(km/s|m/s|kmh|km/h|mph|knot|mach|'
    r'm²|km²|ha|acre|'
    r'°c|°f|celsius|fahrenheit|'
    r'mg/dl|mg/l|µg|ug|mg|ml|kg|g|µl|ul|l|liter|litre|'
    r'cm|mm|km|mét|m|inch|foot|ft|yard|mile|'
    r'iu|ppm|ppb|%|‰|'
    r'bpm|mmhg|hz|khz|mhz|ghz|'
    r'w|kw|mw|wh|kwh|mwh|j|kj|mj|cal|kcal|btu|v|a|ma|'
    r'pa|kpa|mpa|bar|psi|atm|'
    r'năm|years?|days?|ngày|giờ|hours?|phút|minutes?|giây|seconds?)?',
    re.IGNORECASE,
)

# Vietnamese unit normalization → canonical lowercase ASCII form.
_UNIT_NORMALIZE = {
    'mét': 'm', 'năm': 'year', 'ngày': 'day', 'giờ': 'hour',
    'phút': 'minute', 'giây': 'second',
    'years': 'year', 'days': 'day', 'hours': 'hour',
    'minutes': 'minute', 'seconds': 'second',
    'celsius': '°c', 'fahrenheit': '°f',
    'litre': 'l', 'liter': 'l',
    'feet': 'ft',
}


def _extract_key_values(text: str) -> set[str]:
    """Extract normalized numeric values (with optional units) from text.

    Returns a set of canonical "number+unit" strings — e.g.
    {"299792km/s", "3.0e8m/s"} for "The speed of light is 299,792 km/s
    (approximately 3.0e8 m/s)." Used by cross-check to compare the actual
    FACTS two sources report, rather than their prose overlap.
    """
    if not text:
        return set()
    values: set[str] = set()
    for m in _VALUE_NUM_RE.finditer(text):
        # Strip thousand separators (commas) but keep decimal points.
        num_raw = m.group(1)
        # Heuristic: if there are 2+ commas, they're thousand separators.
        # If exactly one comma and 3 digits after, it's also a thousand sep.
        if ',' in num_raw:
            parts = num_raw.split(',')
            if all(len(p) == 3 for p in parts[1:]):
                num_raw = ''.join(parts)
            elif len(parts) == 2 and len(parts[1]) != 3:
                # comma as decimal separator (European format)
                num_raw = parts[0] + '.' + parts[1]
            else:
                num_raw = num_raw.replace(',', '')
        unit = (m.group(2) or '').lower().strip()
        unit = _UNIT_NORMALIZE.get(unit, unit)
        values.add(f"{num_raw}{unit}")
    return values


def fetch_with_priority(query: str, domain: str = "") -> tuple[dict[str, Any] | None, list[str]]:
    """
    Fetch với domain-specific priority. Trả về (result, sources_tried).

    Logic:
      1. Lấy preferred_apis từ domain_registry
      2. Try mỗi API theo thứ tự
      3. Nếu có ≥1 kết quả, return
      4. Cuối cùng fallback to Wikipedia + DuckDuckGo
    """
    from scp.data_sources.domain_registry import get_domain

    sources_tried: list[str] = []
    results: list[tuple[str, dict[str, Any]]] = []

    # Get priority APIs for domain
    priority_apis: list[str] = []
    if domain:
        meta = get_domain(domain)
        if meta:
            priority_apis = meta.get("preferred_apis", [])

    # [V89 FIX] Put arxiv LAST — it returns science papers for ANY query
    # arxiv is only useful for physics/astronomy/technology/math domains
    # For medical/sports/legal/arts etc, arxiv returns irrelevant papers
    science_domains = {"physics", "astronomy", "technology", "math", "chemistry", "reality"}
    fallback_order = ["wikipedia", "wikidata", "duckduckgo", "arxiv"]
    if domain in science_domains:
        fallback_order = ["wikipedia", "arxiv", "wikidata", "duckduckgo"]

    all_apis = priority_apis + [a for a in fallback_order if a not in priority_apis and a in API_MAP]

    for api_name in all_apis:
        fetcher = API_MAP.get(api_name)
        if not fetcher:
            continue
        sources_tried.append(api_name)
        try:
            r = fetcher(query)
            if r and r.get("value"):
                results.append((api_name, r))
                # If we have 2+ sources, that's enough
                if len(results) >= 2:
                    break
        except Exception as e:
            logger.debug(f"API {api_name} error: {e}", exc_info=True)
            continue

    if not results:
        return None, sources_tried

    # Return primary result (first one), but cross-check if multiple
    primary_api, primary_result = results[0]
    if len(results) >= 2:
        primary_result["metadata"]["cross_checked_with"] = [r[0] for r in results[1:]]
        # [V104.43 #BO] TẠI SAO: was always confidence=0.85 regardless of value match.
        # Two sources can CONTRADICT and still get 0.85 "cross-checked" badge.
        # Fix: compare primary value with each secondary source — if disagreement,
        # lower confidence instead of boosting.
        #
        # [FIX-CRIT-46 BUG 9] TẠI SAO: the V104.43 #BO fix compared PROSE
        # overlap (word set intersection) — two sources agreeing on the value
        # but using different prose got marked CONFLICT (0.45); two sources
        # conflicting on the value but sharing boilerplate prose got marked
        # AGREE (0.85). Fix: extract the key fact (numeric value + unit) from
        # each source FIRST via _extract_key_values(). If both sources yield
        # extractable values, compare value SETS — intersection → agree,
        # disjoint → conflict. Only fall back to prose overlap when at least
        # one source has no extractable numeric values (pure prose, no
        # numbers — e.g. biographical text).
        _primary_val = str(primary_result.get("value", "")).strip().lower()[:500]
        _primary_vals = _extract_key_values(_primary_val)
        _agree = True
        _cross_check_method = "value_extraction"
        for _api, _res in results[1:]:
            _sec_val = str(_res.get("value", "")).strip().lower()[:500]
            _sec_vals = _extract_key_values(_sec_val)
            if _primary_vals and _sec_vals:
                # Both sources have extractable numeric values — compare the
                # actual FACTS, not the prose. Disjoint value sets → conflict.
                if _primary_vals.isdisjoint(_sec_vals):
                    _agree = False
                    break
                # else: at least one common value → continue checking the rest
            elif _primary_val and _sec_val and _primary_val != _sec_val:
                # Fallback: at least one source has no numeric values →
                # compare prose overlap (the original V104.43 #BO behavior).
                _cross_check_method = "prose_overlap_fallback"
                _p_words = set(_primary_val.split())
                _s_words = set(_sec_val.split())
                if _p_words and _s_words:
                    _overlap = len(_p_words & _s_words) / max(len(_p_words | _s_words), 1)
                    if _overlap < 0.6:
                        _agree = False
                        break
        if _agree:
            primary_result["confidence"] = 0.85  # genuinely cross-checked
            primary_result["metadata"]["cross_check_method"] = _cross_check_method
        else:
            primary_result["confidence"] = 0.45  # [V104.43 #BO] sources disagree
            primary_result["metadata"]["cross_check_conflict"] = True
            primary_result["metadata"]["cross_check_method"] = _cross_check_method
    else:
        primary_result["confidence"] = 0.65  # single source
    return primary_result, sources_tried


# ============================================================
# CACHED FETCH
# ============================================================
def fetch_live(query: str, domain: str = "",
               force_refresh: bool = False) -> dict[str, Any] | None:
    """
    Fetch knowledge with caching.

    Args:
        query: Question text
        domain: Domain id (for priority API routing)
        force_refresh: Bypass cache

    Returns:
        {
            "value": str,
            "source": str,
            "confidence": float,
            "metadata": {...},
            "from_cache": bool,
            "fetched_at": str,
        }
    """
    _init_cache_db()
    if not query or len(query.strip()) < 3:
        return None

    qhash = _hash_query(query, domain)

    # Check cache first (if not force_refresh)
    if not force_refresh:
        try:
            cached = db_query_one(
                "SELECT * FROM live_knowledge_cache WHERE query_hash=? AND expires_at > ?",
                (qhash, datetime.now().isoformat())
            )
            if cached:
                # Parse stored data
                try:
                    metadata = json.loads(cached.get("metadata", "{}"))
                    sources_succeeded = json.loads(cached.get("sources_succeeded", "[]"))
                except Exception:
                    logger.warning('fetch_live: Exception not handled', exc_info=True)
                    metadata = {}
                    sources_succeeded = []
                return {
                    "value": cached.get("value", ""),
                    "source": cached.get("source", ""),
                    "confidence": cached.get("confidence", 0.5),
                    "metadata": {**metadata, "from_cache": True,
                                 "sources_succeeded": sources_succeeded},
                    "from_cache": True,
                    "fetched_at": cached.get("fetched_at", ""),
                }
        except Exception as e:
            logger.debug(f"Cache lookup error: {e}", exc_info=True)

    # Fetch online
    result, sources_tried = fetch_with_priority(query, domain)
    if not result:
        return None

    # Determine TTL
    from scp.data_sources.domain_registry import get_domain
    ttl_seconds = 604800  # default 1 week
    if domain:
        meta = get_domain(domain)
        if meta:
            ttl_seconds = meta.get("ttl_seconds", 604800)

    now = datetime.now()
    expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
    fetched_at = now.isoformat()

    # Cache it
    try:
        # Get sources_succeeded list
        sources_succeeded_list = []
        if result.get("metadata", {}).get("cross_checked_with"):
            sources_succeeded_list = [result["source"]] + result["metadata"]["cross_checked_with"]
        else:
            sources_succeeded_list = [result["source"]]

        db_exec(
            "INSERT OR REPLACE INTO live_knowledge_cache "
            "(query_hash, query_text, domain, value, source, sources_succeeded, "
            "confidence, fetched_at, expires_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (qhash, query[:500], domain, result["value"][:5000],
             result["source"], json.dumps(sources_succeeded_list),
             result.get("confidence", 0.5),
             fetched_at, expires_at,
             json.dumps(result.get("metadata", {})))  # [DNA-FIX] removed default=str — metadata is read back via json.loads (line 543)
        )
    except Exception as e:
        logger.warning(f"Cache store error: {e}", exc_info=True)

    return {
        **result,
        "from_cache": False,
        "fetched_at": fetched_at,
        "metadata": {
            **result.get("metadata", {}),
            "sources_tried": sources_tried,
        }
    }


def clear_expired_cache() -> int:
    """Xóa cache entries đã expire. Trả về số entries đã xóa."""
    _init_cache_db()
    try:
        now = datetime.now().isoformat()
        from scp.core.db_manager import db_query_all
        expired = db_query_all(
            "SELECT id FROM live_knowledge_cache WHERE expires_at < ?",
            (now,)
        ) or []
        if expired:
            db_exec("DELETE FROM live_knowledge_cache WHERE expires_at < ?", (now,))
        return len(expired)
    except Exception as e:
        logger.warning(f"clear_expired_cache error: {e}", exc_info=True)
        return 0


def get_cache_stats() -> dict[str, Any]:
    """Thống kê cache."""
    _init_cache_db()
    try:
        from scp.core.db_manager import db_query_all
        total_row = db_query_one("SELECT COUNT(*) as cnt FROM live_knowledge_cache") or {}
        total = total_row.get("cnt", 0)
        # By domain
        rows = db_query_all(
            "SELECT domain, COUNT(*) as cnt FROM live_knowledge_cache GROUP BY domain"
        ) or []
        by_domain = {r["domain"] or "unknown": r["cnt"] for r in rows}
        # By source
        rows = db_query_all(
            "SELECT source, COUNT(*) as cnt FROM live_knowledge_cache GROUP BY source"
        ) or []
        by_source = {r["source"] or "unknown": r["cnt"] for r in rows}
        return {
            "total_cached": total,
            "by_domain": by_domain,
            "by_source": by_source,
        }
    except Exception as e:
        logger.debug(f"get_cache_stats ignored: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V46 LiveKnowledgeFetcher")
    parser.add_argument("query", nargs="?", help="Query để test")
    parser.add_argument("--domain", type=str, default="", help="Domain id")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache")
    parser.add_argument("--stats", action="store_true", help="Show cache stats")
    args = parser.parse_args()

    if args.stats:
        stats = get_cache_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    if not args.query:
        print("Usage: python -m scp.data_sources.live_knowledge 'query' [--domain X]")
        return

    print("\n   LiveKnowledgeFetcher")
    print(f"  Query:  {args.query}")
    print(f"  Domain: {args.domain or 'auto'}")
    print(f"  Refresh: {args.refresh}")
    print()

    result = fetch_live(args.query, domain=args.domain, force_refresh=args.refresh)
    if not result:
        print("  ❌ No result from any source")
        return
    print(f"  Value:     {result.get('value', '')[:300]}")
    print(f"  Source:    {result.get('source', '')}")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  From cache: {result.get('from_cache', False)}")
    print(f"  Fetched at: {result.get('fetched_at', '')}")
    print(f"  Metadata:  {json.dumps(result.get('metadata', {}), indent=2, ensure_ascii=False)[:500]}")


if __name__ == "__main__":
    main()
