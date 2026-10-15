"""
SCP V91 — Cross-Verification Module.

Gọi 2+ API cho mỗi câu hỏi, so sánh kết quả, chỉ trả lời khi ≥2 nguồn đồng ý.

Architecture:
    1. Primary API (domain-specific) → get answer A
    2. Adversary API (Wikipedia/DuckDuckGo/Wikidata) → get answer B
    3. If A and B agree → high confidence
    4. If A and B disagree → CONFLICT, low confidence
    5. If only A available → medium confidence
"""
# [G3-CONSOLIDATE P1-06] Verifier consolidation status:
# - This verifier: LIVE-UNIQUE
# - Canonical verifier: scp/core/multi_source_verifier.py::AsyncMultiSourceVerifier
# - Unique role: Cross-verification for GENERAL entities / trivia / books
#   via Wikipedia + Wikidata + DuckDuckGo (3-source agreement scoring with
#   entity-presence / shared-number / string-overlap strategies). Distinct
#   from canonical AsyncMultiSourceVerifier which targets weather/chemistry/
#   arbitrary claim verification via registered IDataSource objects.
# - Wired to /ask: INDIRECTLY — used by 5 SLMs internally:
#   universalslm.py:293 (cross_verify_entity), entertainmentslm.py:196,214,307
#   (cross_verify_book), generalslm.py:222 (cross_verify_entity),
#   lifestyle_slm.py:84 (cross_verify_entity), misc_slm.py:257,368,576
#   (cross_verify_book/entity).
# - Known partial duplication: _fetch_wikipedia (line 143) calls the SAME
#   Wikipedia REST endpoint as canonical
#   multi_source_verifier.fetch_wikipedia_summary (line 393 of canonical).
#   Implementations DIFFER: cross_verify._fetch_wikipedia has a fallback to
#   the MediaWiki search API if the primary REST summary returns a
#   disambiguation page; canonical fetch_wikipedia_summary does not.
#   NOT delegating because doing so would lose the disambiguation fallback.
#   See Task 2-B finding B2 #1 for details.
import logging
import re
import threading
import urllib.parse
from typing import Any

logger = logging.getLogger("scp.cross_verify")

from scp.core.api_utils import fetch_with_retry

# ============================================================
# [EGRESS-DEGRADE 2026-09-26] Static per-source allowed-host declaration.
# TẠI SAO: openlibrary/wikidata fetch ở dưới KHÔNG nằm trong allowlist compose
# pass của một số deployment (.env là owner-owned — product không được sửa),
# nên mỗi ask từng đốt một WARNING "egress denied" qua fetch_with_retry dù
# kết quả tất yếu là None. Contract fail-quiet-by-design:
#   * mỗi nguồn khai báo host tĩnh của nó ở đây;
#   * trước khi fetch, `_source_egress_open` probe chính sách egress (không
#     raise) — bị từ chối → nguồn degrade sang CACHE-ONLY (không I/O, trả
#     None; tầng cache verdict phía trên vẫn hoạt động như cũ);
#   * degradation log INFO đúng MỘT lần mỗi process, KHÔNG WARNING mỗi ask.
# Khi owner thêm host vào SCP_EGRESS_ALLOWLIST, nguồn tự mở lại (probe đọc
# policy live, không có state persists ngoài once-flag log).
# ============================================================
_CROSS_VERIFY_SOURCE_EGRESS_HOSTS = {
    "openlibrary": "https://openlibrary.org/",
    "wikidata": "https://www.wikidata.org/",
}
_EGRESS_DEGRADED_LOGGED: set[str] = set()
_EGRESS_DEGRADED_LOGGED_LOCK = threading.Lock()


def _source_egress_open(source: str) -> bool:
    """False = nguồn đã bị egress từ chối → caller dùng cache-only (no I/O)."""
    from scp.security.url_safety import egress_host_allowed

    probe_url = _CROSS_VERIFY_SOURCE_EGRESS_HOSTS.get(source)
    if not probe_url or egress_host_allowed(probe_url):
        return True
    with _EGRESS_DEGRADED_LOGGED_LOCK:
        if source not in _EGRESS_DEGRADED_LOGGED:
            _EGRESS_DEGRADED_LOGGED.add(source)
            logger.info(
                "[cross_verify] egress: %s not permitted by the active egress policy — "
                "degraded to cache-only for this process (single INFO, no per-ask WARNING)",
                source,
            )
    return False

# ============================================================
# MULTI-SOURCE LOOKUP — call 2+ APIs, compare results
# ============================================================

def cross_verify_entity(entity: str, question: str = "") -> dict[str, Any]:
    """
    Cross-verify an entity using MULTIPLE sources.

    Returns: {
        "value": best answer,
        "sources": [list of sources that agreed],
        "confidence": 0-1 (higher if more sources agree),
        "conflict": bool,
        "raw_results": [{source, value} for each API called]
    }
    """
    # [V93.11 FIX] Was: 3 sequential blocking calls, each with its own
    # timeout+retries (worst case 60-100+s per question!) — this was the
    # single biggest throughput killer for any "unknown"/fallback question,
    # stalling worker threads for 11-31s+ each and dragging down overall
    # system throughput far below target.
    # Now: run all 3 sources IN PARALLEL with a hard overall deadline.
    #
    # [V104.48 / Fix 4-a-010] TẠI SAO: previously used `with ThreadPoolExecutor()
    # as executor:` — the context-manager `__exit__` calls `shutdown(wait=True)`
    # which BLOCKS until ALL submitted futures finish, even after `as_completed`
    # raised TimeoutError. So the "6s deadline" was a lie (DNA #22 PASS≠TRUE);
    # one slow Wikipedia fetch could stall the worker thread for 30s+.
    # Fix: use an explicit pool + `shutdown(wait=False, cancel_futures=True)`
    # in `finally:` so the function returns in ~6s even if some futures are
    # still running. Cancelled/orphan futures run their fetch_with_retry which
    # is itself bounded by `timeout=5` per call — so they will not hang forever
    # either; they are simply not awaited by this function.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results: list[dict[str, Any]] = []
    fetchers = {
        "Wikipedia": _fetch_wikipedia,
        "Wikidata": _fetch_wikidata,
        "DuckDuckGo": _fetch_duckduckgo,
    }
    pool = ThreadPoolExecutor(max_workers=3)
    try:
        future_to_source = {pool.submit(fn, entity): src for src, fn in fetchers.items()}
        try:
            for future in as_completed(future_to_source, timeout=6.0):
                src = future_to_source[future]
                try:
                    val = future.result(timeout=0.1)
                    if val:
                        results.append({"source": src, "value": val})
                except Exception as e:
                    logger.debug(f"{src} fetch error: {e}", exc_info=True)
        except Exception:
            logger.debug("cross_verify_entity ignored", exc_info=True)
            # Overall 6s deadline hit — use whatever completed so far
            for future, src in future_to_source.items():
                if future.done() and not future.cancelled():
                    try:
                        val = future.result(timeout=0.1)
                        if val and not any(r["source"] == src for r in results):
                            results.append({"source": src, "value": val})
                    except Exception as e:
                        logger.debug(f"[V104.37] core/cross_verify.py: e={e}", exc_info=True)
    finally:
        # [Fix 4-a-010] CRITICAL: wait=False so __exit__/shutdown does NOT block.
        # cancel_futures=True (Py3.9+) cancels any not-yet-started futures;
        # in-progress ones are abandoned (bounded by fetch_with_retry timeout=5).
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError as exc:
            # silent-by-design: Python <3.9 fallback; wait=False below still avoids blocking.
            logger.debug("cross_verify: cancel_futures unsupported (%s), using shutdown(wait=False)", exc, exc_info=True)
            # Python <3.9 fallback: cancel_futures kwarg not supported.
            # wait=False still ensures we don't block on running futures.
            pool.shutdown(wait=False)

    if not results:
        return {"value": None, "sources": [], "confidence": 0.0, "conflict": False, "raw_results": []}

    if len(results) == 1:
        # [V91 FIX] Wikipedia alone with substantial extract → 0.70
        src = results[0]["source"]
        val = results[0]["value"]
        # [V104.35 #71] TẠI SAO: src is Title-case ("Wikipedia") but old comparisons
        # were lowercase → never matched → Wikipedia-only always got conf=0.50.
        # Fix: normalize to lowercase before comparing.
        src_lower = str(src).lower() if src else ""
        if src_lower == "wikipedia" and len(str(val)) > 50:
            conf = 0.70
        elif src_lower in ("wikipedia", "wikidata", "duckduckgo"):
            conf = 0.55
        else:
            conf = 0.50
        return {"value": val, "sources": [src],
                "confidence": conf, "conflict": False, "raw_results": results}

    # 2+ sources: check agreement
    values = [r["value"] for r in results]

    #  Step 1: Check if entity name appears in ALL source texts
    entity_lower = entity.lower()
    all_contain_entity = all(re.search(r"\b" + re.escape(entity_lower) + r"\b", str(v).lower()[:200]) for v in values)  # [V104.37 #84] TẠI SAO: substring "in" matched "running"
    if all_contain_entity:
        # All sources talk about the same entity → agreement
        # Pick the longest/most informative answer
        best_idx = max(range(len(values)), key=lambda i: len(str(values[i])))
        return {"value": values[best_idx], "sources": [r["source"] for r in results],
                "confidence": 0.75, "conflict": False, "raw_results": results}

    #  Step 2: Check if any key numbers are shared
    all_numbers = []
    for v in values:
        nums = set(re.findall(r'\d+\.?\d*', str(v)))
        all_numbers.append(nums)

    if all_numbers:
        common = all_numbers[0]
        for nums in all_numbers[1:]:
            common = common & nums
        if len(common) >= 1:
            return {"value": values[0], "sources": [r["source"] for r in results],
                    "confidence": 0.85, "conflict": False, "raw_results": results}

    #  Step 3: Check string overlap
    from difflib import SequenceMatcher
    similarities = []
    for i in range(len(values)):
        for j in range(i+1, len(values)):
            sim = SequenceMatcher(None, str(values[i]), str(values[j])).ratio()
            similarities.append(sim)

    avg_sim = sum(similarities) / len(similarities) if similarities else 0

    if avg_sim > 0.4:
        return {"value": values[0], "sources": [r["source"] for r in results],
                "confidence": 0.65, "conflict": False, "raw_results": results}
    else:
        # [V104.47 #6] TẠI SAO: was always conflict=False even when sources clearly
        # disagree. "Different aspects" is an assumption — if overlap <40%, they
        # likely contradict. Fix: set conflict=True when avg_sim < 0.3.
        _is_conflict = avg_sim < 0.3
        return {"value": values[0], "sources": [r["source"] for r in results],
                "confidence": 0.5 if not _is_conflict else 0.3,
                "conflict": _is_conflict, "raw_results": results}


def _fetch_wikipedia(entity: str) -> str | None:
    """Fetch Wikipedia summary for entity."""
    try:
        entity_clean = re.sub(r'^(?:a|an|the)\s+', '', entity, flags=re.IGNORECASE).strip()
        # [V91 FIX] Try REST API directly first
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(entity_clean.replace(' ', '_'))}"
        try:
            data = fetch_with_retry(url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
        except Exception as exc:
            # silent-by-design: REST summary is best-effort; later strategies still run.
            logger.debug("cross_verify: wikipedia REST fetch failed: %s", exc, exc_info=True)
            data = None
        if data and data.get("extract") and data.get("type") != "disambiguation":
            # Filter out "year" type responses for book lookups
            extract = data["extract"]
            if data.get("type") == "standard" or len(extract) > 50:
                return extract[:300]
        # [V91 FIX] Fallback: use MediaWiki search API to find the right page
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(entity_clean)}&format=json&srlimit=3"
        search_data = fetch_with_retry(search_url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
        if search_data and search_data.get("query", {}).get("search"):
            for item in search_data["query"]["search"][:1]:  # [V93.11] only try the top hit, was up to 3
                page_title = item["title"]
                # Skip disambiguation pages
                if "disambiguation" in item.get("snippet", "").lower():
                    continue
                # Try fetching summary for this page title
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title.replace(' ', '_'))}"
                try:
                    summary_data = fetch_with_retry(summary_url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
                    if summary_data and summary_data.get("extract") and summary_data.get("type") != "disambiguation":
                        return summary_data["extract"][:300]
                except Exception as exc:  # noqa: S112
                    # silent-by-design: one bad page title must not abort the remaining candidates.
                    logger.debug("cross_verify: page summary fetch failed, skipping: %s", exc, exc_info=True)
                    continue
    except Exception as e:
        logger.debug(f"Wikipedia fetch error: {e}", exc_info=True)
    return None


def _fetch_wikidata(entity: str) -> str | None:
    """Fetch Wikidata description for entity.

    [EGRESS-DEGRADE 2026-09-26] Khi wikidata bị egress policy từ chối, nguồn
    này chạy cache-only: không attempt fetch, trả None, INFO một lần/process
    (xem `_source_egress_open`) — không còn WARNING egress mỗi ask."""
    try:
        if not _source_egress_open("wikidata"):
            return None
        search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(entity)}&language=en&format=json&limit=1"
        data = fetch_with_retry(search_url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
        if data and data.get("search"):
            item = data["search"][0]
            desc = item.get("description", "")
            label = item.get("label", "")
            if desc:
                return f"{label}: {desc}" if label else desc
    except Exception as e:
        logger.debug(f"Wikidata fetch error: {e}", exc_info=True)
    return None


def _fetch_duckduckgo(entity: str) -> str | None:
    """Fetch DuckDuckGo Instant Answer for entity."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(entity)}&format=json&no_html=1"
        data = fetch_with_retry(url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
        if data:
            # Try AbstractText first
            if data.get("AbstractText"):
                return data["AbstractText"][:300]
            # Try Answer
            if data.get("Answer"):
                return data["Answer"][:300]
            # Try related topics
            topics = data.get("RelatedTopics", [])
            if topics and isinstance(topics, list):
                first = topics[0]
                if isinstance(first, dict) and first.get("Text"):
                    return first["Text"][:300]
    except Exception as e:
        logger.debug(f"DuckDuckGo fetch error: {e}", exc_info=True)
    return None


# ============================================================
# SPECIALIZED CROSS-VERIFY FOR TRIVIA QUESTIONS
# ============================================================

def cross_verify_trivia(question: str) -> dict[str, Any]:
    """
    Cross-verify trivia questions using OpenTDB + Trivia API + DuckDuckGo.

    OpenTDB and Trivia API have correct_answer in their response!
    """
    results = []

    # Source 1: DuckDuckGo (general search)
    ddg = _fetch_duckduckgo(question)
    if ddg:
        results.append({"source": "DuckDuckGo", "value": ddg})

    # Source 2: Wikipedia search
    wiki = _fetch_wikipedia(question.replace("What is ", "").replace("?", "").strip())
    if wiki:
        results.append({"source": "Wikipedia", "value": wiki})

    if not results:
        return {"value": None, "sources": [], "confidence": 0.0, "conflict": False, "raw_results": []}

    if len(results) == 1:
        return {"value": results[0]["value"], "sources": [results[0]["source"]],
                "confidence": 0.4, "conflict": False, "raw_results": results}

    # Check agreement
    from difflib import SequenceMatcher
    sim = SequenceMatcher(None, str(results[0]["value"]), str(results[1]["value"])).ratio()
    confidence = 0.7 if sim > 0.5 else 0.3

    return {"value": results[0]["value"], "sources": [r["source"] for r in results],
            "confidence": confidence, "conflict": sim < 0.3, "raw_results": results}


# ============================================================
# SPECIALIZED CROSS-VERIFY FOR BOOKS
# ============================================================

def cross_verify_book(title: str) -> dict[str, Any]:
    """Cross-verify book info using Open Library + Wikipedia + Wikidata."""
    results = []

    # Source 1: Open Library — sort by edition_count desc (most editions = original author)
    # [EGRESS-DEGRADE 2026-09-26] Cache-only khi openlibrary bị egress từ chối:
    # bỏ qua NGUỒN NÀY (không attempt fetch, cả title= lẫn fallback q=), INFO
    # một lần/process — không WARNING mỗi ask. Các nguồn còn lại chạy như cũ.
    if _source_egress_open("openlibrary"):
        try:
            # [V91 FIX] Pure numeric titles (like "1984") cause 500 errors on Open Library
            # Use q= parameter as fallback if title= fails
            url = f"https://openlibrary.org/search.json?title={urllib.parse.quote(title)}&limit=10&sort=edition_count_desc&fields=title,author_name,first_publish_year,edition_count"
            try:
                data = fetch_with_retry(url, {"User-Agent": "SCP-V91/1.0"}, timeout=15, max_retries=1)
            except Exception as exc:
                # silent-by-design: title= failure falls back to the documented q= query.
                logger.debug("cross_verify: openlibrary title= failed, using q= fallback: %s", exc, exc_info=True)
                # Fallback: use q= with "book" appended
                url = f"https://openlibrary.org/search.json?q={urllib.parse.quote(title)}&limit=10&fields=title,author_name,first_publish_year,edition_count"
                data = fetch_with_retry(url, {"User-Agent": "SCP-V91/1.0"}, timeout=5, max_retries=1)
            if data and data.get("docs"):
                docs = sorted(data["docs"], key=lambda d: d.get("edition_count", 0), reverse=True)
                doc = docs[0]
                authors = doc.get("author_name", [])
                author = authors[0] if authors else "Unknown"
                first_publish = doc.get("first_publish_year", "")
                book_info = f"Author: {author}"
                if first_publish:
                    book_info += f", First published: {first_publish}"
                results.append({"source": "OpenLibrary", "value": book_info})
        except Exception as e:
            logger.debug(f"Open Library error: {e}", exc_info=True)

    # Source 2: Wikipedia — search with "(book)" or "(novel)" suffix for accuracy
    wiki = _fetch_wikipedia(title + " (novel)")
    if not wiki:
        wiki = _fetch_wikipedia(title + " (book)")
    if not wiki:
        wiki = _fetch_wikipedia(title)
    if wiki:
        results.append({"source": "Wikipedia", "value": wiki})

    # Source 3: Wikidata — [V91 FIX] skip "year" results for book lookups
    wd = _fetch_wikidata(title)
    if wd and "year" not in wd.lower()[:30]:
        results.append({"source": "Wikidata", "value": wd})
    elif wd:
        # Try with "novel" suffix
        wd2 = _fetch_wikidata(title + " novel")
        if wd2:
            results.append({"source": "Wikidata", "value": wd2})

    if not results:
        return {"value": None, "sources": [], "confidence": 0.0, "conflict": False, "raw_results": []}

    if len(results) == 1:
        # [V91 FIX] OpenLibrary or Wikipedia (novel) alone → 0.70
        src = results[0]["source"]
        val = results[0]["value"]
        if src == "OpenLibrary":
            conf = 0.70
        elif src == "Wikipedia" and len(str(val)) > 50:
            conf = 0.70  # Wikipedia with substantial extract is reliable
        else:
            conf = 0.50
        return {"value": val, "sources": [src],
                "confidence": conf, "conflict": False, "raw_results": results}

    #  Extract author from Open Library result (most reliable)
    open_lib_result = next((r for r in results if r["source"] == "OpenLibrary"), None)
    if open_lib_result:
        # Open Library format: "Author: X, First published: Y"
        m = re.match(r'Author:\s+(.+?)(?:,|$)', open_lib_result["value"])
        if m:
            author = m.group(1).strip()
            # Check if author appears in other sources too
            other_text = " ".join(str(r["value"]) for r in results if r["source"] != "OpenLibrary")
            author_in_others = author.lower() in other_text.lower()
            confidence = 0.85 if author_in_others else 0.7
            return {"value": f"Author: {author}", "sources": [r["source"] for r in results],
                    "confidence": confidence, "conflict": False, "raw_results": results}

    #  If no Open Library, try to extract author from Wikipedia/Wikidata text
    import re as _re
    for r in results:
        text = str(r["value"])
        # Pattern: "novel by Jane Austen" or "written by George Orwell" or "by William Shakespeare"
        m = _re.search(r'(?:novel|play|book|work)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
        if m:
            author = m.group(1).strip()
            return {"value": f"Author: {author}", "sources": [r["source"] for r in results],
                    "confidence": 0.7, "conflict": False, "raw_results": results}
        # Pattern: "Jane Austen's novel" → extract "Jane Austen"
        m = _re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'s\s+(?:novel|book|play|work)", text)
        if m:
            author = m.group(1).strip()
            return {"value": f"Author: {author}", "sources": [r["source"] for r in results],
                    "confidence": 0.7, "conflict": False, "raw_results": results}

    return {"value": results[0]["value"], "sources": [r["source"] for r in results],
            "confidence": 0.5, "conflict": False, "raw_results": results}
