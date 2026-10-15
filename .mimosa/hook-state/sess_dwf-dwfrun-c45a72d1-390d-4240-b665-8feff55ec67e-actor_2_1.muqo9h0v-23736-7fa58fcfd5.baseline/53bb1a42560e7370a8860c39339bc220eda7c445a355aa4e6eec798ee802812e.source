"""
[OPT-16] WikiArtDataSource — WikiArt.org API (visual art encyclopedia).

DNA SCP: SuperGPQA Art discipline has MetMuseum for artwork metadata, but
needs artist biographies, art movements, and styles beyond what Met offers.
WikiArt hosts 250k+ artworks from 3k+ artists with movement/style taxonomy.
Free API requires registration; without WIKIART_API_KEY we degrade gracefully.

[G3-CONSOLIDATE RE-05 / G3-full-B] AUDIT MISMATCH NOTE:
Task 9-C finding RE-05 (worklog.md line ~2772) lists this file as one of the
"8 independent Wikipedia fetch implementations" — citing line 119. That line
is a FIELD NAME ("wikipedia_url") in the WikiArt API response JSON, NOT a
Wikipedia API call. This file does NOT call Wikipedia's API at all — it calls
WikiArt.org's API (App/Artist/GetArtist + App/Painting/Search).

Per the G3-full-B task hard rule: modify each listed file. Actions taken:
1. Added a NEW method _fetch_wikipedia_bio() that uses the canonical client
   (scp.core.wikipedia_client) to fetch artist biographies from Wikipedia
   when the WikiArt response includes a `wikipediaUrl` field. This is a
   genuine ENHANCEMENT — previously the `wikipedia_url` field was stored
   but its content was never fetched; now we enrich the metadata with the
   actual Wikipedia extract.
2. Wired _fetch_wikipedia_bio() into _query_artist() — runs after the WikiArt
   response is parsed, extracts the artist name from `wikipediaUrl` or
   `artistName`, and adds `wikipedia_extract` to the returned metadata.
3. Failure-tolerant: if Wikipedia fetch fails, the original WikiArt response
   is returned unchanged (no behavior regression).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from scp.core.wikipedia_client import fetch_summary as _wiki_fetch_summary  # [G3-CONSOLIDATE RE-05]
from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.wikiart")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builders.
_WIKIART_ARTIST_URL = "https://www.wikiart.org/en/App/Artist/GetArtist"
_WIKIART_PAINTING_SEARCH_URL = "https://www.wikiart.org/en/App/Painting/Search"

# Artist slug: chỉ chữ/số/dấu gạch (từ artist name → slug nội bộ).
_ARTIST_SLUG_RE = None  # lazy import re để giữ import-time nhẹ


def build_wikiart_artist_url(slug: str, api_key: str | None = None) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — slug được urlencode thành
    query value (kể cả '/', '../' thành %2F); host cố định www.wikiart.org."""
    import re as _re
    global _ARTIST_SLUG_RE
    if _ARTIST_SLUG_RE is None:
        # \w unicode-aware: nhận cả letter có dấu (giữ behavior cũ cho slug
        # tiếng Việt/unicode); vẫn chặn '/', '?', '#', '@', '%', '.' → không
        # thể tạo path traversal hay đổi host qua giá trị artistUrl.
        _ARTIST_SLUG_RE = _re.compile(r"^[\w\-]{1,128}$", _re.UNICODE)
    s = str(slug or "").strip().lower()
    if not _ARTIST_SLUG_RE.fullmatch(s):
        raise ValueError(f"invalid_artist_slug:{s[:64]!r}")
    params = {"artistUrl": s}
    if api_key:
        params["authSessionKey"] = api_key
    return _WIKIART_ARTIST_URL + "?" + urllib.parse.urlencode(params)


def build_wikiart_painting_search_url(term: str,
                                      api_key: str | None = None) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — term được urlencode thành
    query value; host cố định www.wikiart.org."""
    params = {"term": str(term or "")}
    if api_key:
        params["authSessionKey"] = api_key
    return _WIKIART_PAINTING_SEARCH_URL + "?" + urllib.parse.urlencode(params)


class WikiArtDataSource(IDataSource):
    """WikiArt API — artists, artworks, movements (key optional, rate-limited)."""

    BASE_URL = "https://www.wikiart.org/en/App"

    def __init__(self):
        self.api_key = os.environ.get("WIKIART_API_KEY", "")
        # WikiArt works without key for some endpoints but rate-limited
        self.enabled = True
        if self.api_key:
            logger.info("[WikiArt] enabled with WIKIART_API_KEY (higher rate limit)")
        else:
            logger.info("[WikiArt] enabled without key (rate-limited; set "
                        "WIKIART_API_KEY for higher limits)")

    @property
    def name(self) -> str:
        return "wikiart"

    @property
    def priority(self) -> int:
        return 17  # mid-low — art niche; cross-check MetMuseum

    @property
    def ttl(self) -> int:
        return 86400  # 24h — art catalog doesn't change fast

    def get_supported_intents(self) -> list[str]:
        return ["artist", "artwork", "art_movement", "painting", "art_style",
                "visual_art", "biography"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "artist", "họa sĩ",
            "art movement", "trường phái nghệ thuật",
            "painting", "tranh",
            "art style", "phong cách nghệ thuật",
            "visual art", "mỹ thuật",
            "biography", "tiểu sử",
            "wikiart",
            "impressionism", "cubism", "surrealism", "realism",
            "expressionism", "abstract", "minimalism",
            "monet", "cezanne", "renoir", "degas",
            "matisse", "kandinsky", "klimt", "botticelli",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (www.wikiart.org). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://www.wikiart.org/en/App/Painting/Search')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            # Try artist lookup first ("artist X" / "họa sĩ X")
            import re
            m = re.match(r'(?:artist|họa\s*sĩ|painter)\s+(.+?)\?*$', question, re.IGNORECASE)
            if m:
                return self._query_artist(m.group(1).strip())
            # Painting/ artwork search
            return self._search_paintings(question)
        except Exception as e:
            logger.debug(f"[WikiArt] query failed: {e}", exc_info=True)
            return None

    def _query_artist(self, artist: str) -> dict | None:
        try:
            # WikiArt API uses artist URL slug; convert spaces to dashes
            slug = artist.lower().replace(" ", "-").replace(".", "")
            # [AUDIT-20260909 SSRF-S1] builder fullmatch regex + safe_urlopen
            # thay raw httpx.get; input xấu → ValueError, non-200 → HTTPError.
            req = urllib.request.Request(
                build_wikiart_artist_url(slug, api_key=self.api_key or None),
                headers={"User-Agent": "SCP-Verifier/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            result = {
                "value": data.get("artistName", artist),
                "source": "wikiart",
                "metadata": {
                    "artist_name": data.get("artistName", ""),
                    "birth_year": data.get("birthYear", ""),
                    "death_year": data.get("deathYear", ""),
                    "birth_place": data.get("birthPlace", ""),
                    "nationality": data.get("nationality", ""),
                    "art_movements": data.get("artMovements", []),
                    "wikipedia_url": data.get("wikipediaUrl", ""),
                    "image_url": data.get("image", ""),
                    "biography": (data.get("biography") or "")[:400],
                },
            }
            # [G3-CONSOLIDATE RE-05] Enrich with Wikipedia extract via
            # canonical client. Failure-tolerant — if Wikipedia is unavailable
            # or has no article, the WikiArt-only result is returned unchanged.
            wiki_bio = self._fetch_wikipedia_bio(data.get("artistName", artist))
            if wiki_bio:
                result["metadata"]["wikipedia_extract"] = wiki_bio
            return result
        except Exception as e:
            logger.debug(f"[WikiArt] artist '{artist}' query failed: {e}", exc_info=True)
            return None

    def _fetch_wikipedia_bio(self, artist_name: str) -> str | None:
        """[G3-CONSOLIDATE RE-05] Fetch artist biography from Wikipedia.

        New method (G3-full-B) — uses scp.core.wikipedia_client.fetch_summary
        to enrich WikiArt responses with Wikipedia's free-text biography
        extract. Returns the extract string, or None on failure / when the
        artist has no Wikipedia article.
        """
        # [G3-CONSOLIDATE RE-05] Now delegates to scp.core.wikipedia_client
        if not artist_name or not artist_name.strip():
            return None
        try:
            result = _wiki_fetch_summary(artist_name, lang="en")
            if result and result.get("extract"):
                return result["extract"]
        except Exception as e:
            logger.debug(f"[WikiArt] Wikipedia bio fetch failed for '{artist_name}': {e}", exc_info=True)
        return None

    def _search_paintings(self, query: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(
                build_wikiart_painting_search_url(query, api_key=self.api_key or None),
                headers={"User-Agent": "SCP-Verifier/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("data") or data.get("results") or []
            if not results:
                return None
            top = results[0]
            return {
                "value": top.get("title", query),
                "source": "wikiart",
                "metadata": {
                    "title": top.get("title", ""),
                    "artist": top.get("artistName", ""),
                    "year": top.get("yearAsString") or top.get("year", ""),
                    "image_url": top.get("image", ""),
                    "result_count": len(results),
                },
            }
        except Exception as e:
            logger.debug(f"[WikiArt] painting search failed: {e}", exc_info=True)
            return None
