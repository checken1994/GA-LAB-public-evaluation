"""
[OPT-20] GlottologDataSource — Glottolog API (languages & dialects).

DNA SCP: SuperGPQA Linguistics discipline had NO dedicated DataSource — only
the generic social.py covered languages loosely. Glottolog (Max Planck
Institute) is the authoritative reference for the world's languages: 7k+
languages, dialects, language families, endangerment status. Free, no key —
fills the linguistics gap entirely.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.glottolog")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_GLOTTOLOG_LANGUOID_URL = "https://glottolog.org/api/v1/languoid/"
_GLOTTOLOG_LANGUAGE_URL = "https://glottolog.org/api/v1/language"

# Glottocode: 4 chữ thường + 4 chữ số (vd abcd1234).
_GLOTTICODE_RE = re.compile(r"^[a-z]{4}\d{4}$")
# ISO 639-3: 3 chữ thường.
_ISO6393_RE = re.compile(r"^[a-z]{3}$")


def build_glottocode_url(glottocode: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — glottocode PHẢI fullmatch
    [a-z]{4}\\d{4}; input xấu → ValueError TRƯỚC KHI fetch (fail-closed)."""
    code = str(glottocode or "").strip()
    if not _GLOTTICODE_RE.fullmatch(code):
        raise ValueError(f"invalid_glottocode:{code[:32]!r}")
    return _GLOTTOLOG_LANGUOID_URL + code


def build_glottolog_language_url(iso639_3: str = None,
                                 query: str = None) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — iso639_3 PHẢI fullmatch
    [a-z]{3}; query được urlencode thành query value. Host cố định
    glottolog.org. Ít nhất một trong hai param phải có."""
    if iso639_3 is not None:
        iso = str(iso639_3 or "").strip()
        if not _ISO6393_RE.fullmatch(iso):
            raise ValueError(f"invalid_iso639_3:{iso[:32]!r}")
        return _GLOTTOLOG_LANGUAGE_URL + "?" + urllib.parse.urlencode(
            {"iso639_3": iso})
    if query is None:
        raise ValueError("glottolog_language_url_requires_iso_or_query")
    return _GLOTTOLOG_LANGUAGE_URL + "?" + urllib.parse.urlencode(
        {"q": str(query or "")})


class GlottologDataSource(IDataSource):
    """Glottolog API v1 — languages, dialects, language families (no key)."""

    BASE_URL = "https://glottolog.org/api/v1"

    def __init__(self):
        # Glottolog API is free, no key needed
        self.enabled = True
        logger.info("[Glottolog] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "glottolog"

    @property
    def priority(self) -> int:
        return 18  # mid-low — linguistics niche; primary source for language data

    @property
    def ttl(self) -> int:
        return 86400  # 24h — Glottolog publishes yearly editions; weekly acceptable

    def get_supported_intents(self) -> list[str]:
        return ["language", "dialect", "language_family", "linguistics",
                "endangered_language", "glottocode", "iso639"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        question = intent or ""
        q = question.lower()
        keywords = [
            "language", "ngôn ngữ",
            "dialect", "phương ngữ",
            "language family", "hệ ngôn ngữ",
            "linguistics", "ngôn ngữ học",
            "endangered", "nguy cấp",
            "glottolog", "glottocode",
            "iso639", "iso 639",
            "indoeuropean", "indo-european",
            "sino-tibetan", "hán tạng",
            "afroasiatic", "nam á",
            "niger-congo", "phi",
            "austronesian", "nam đảo",
            "vietnamese", "tiếng việt",
            "english", "mandarin", "spanish",
            "arabic", "hindi", "bengali",
        ]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (glottolog.org). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://glottolog.org/api/v1/languoid')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            import re
            # Glottocode pattern (4 lowercase letters + 4 digits)
            m = re.search(r'\b([a-z]{4}\d{4})\b', question.lower())
            if m:
                return self._fetch_glottocode(m.group(1))
            # ISO 639-3 pattern (3 lowercase letters)
            m = re.search(r'\biso[:\s-]*639[:\s-]*(\w{3})\b', question, re.IGNORECASE)
            if m:
                return self._fetch_iso639(m.group(1).lower())
            # Default — language name search
            return self._search_language(question)
        except Exception as e:
            logger.debug(f"[Glottolog] query failed: {e}", exc_info=True)
            return None

    def _fetch_glottocode(self, glottocode: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder fullmatch regex + safe_urlopen
            # thay raw httpx.get; input xấu → ValueError, non-200 → HTTPError.
            req = urllib.request.Request(
                build_glottocode_url(glottocode),
                headers={"User-Agent": "SCP-Verifier/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            return {
                "value": data.get("name", glottocode),
                "source": "glottolog",
                "metadata": {
                    "name": data.get("name", ""),
                    "glottocode": glottocode,
                    "iso639_3": data.get("iso639-3", ""),
                    "level": data.get("level", ""),
                    "family": data.get("family", ""),
                    "classification": data.get("classification", {}),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "countries": data.get("countries", []),
                    "endangerment": data.get("endangerment", {}),
                    "urls": data.get("urls", {}),
                },
            }
        except Exception as e:
            logger.debug(f"[Glottolog] glottocode {glottocode} fetch failed: {e}", exc_info=True)
            return None

    def _fetch_iso639(self, iso: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder fullmatch regex + safe_urlopen.
            req = urllib.request.Request(
                build_glottolog_language_url(iso639_3=iso),
                headers={"User-Agent": "SCP-Verifier/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results") or data if isinstance(data, list) else []
            if isinstance(results, list) and results:
                top = results[0]
                return {
                    "value": top.get("name", iso),
                    "source": "glottolog",
                    "metadata": {
                        "name": top.get("name", ""),
                        "iso639_3": iso,
                        "glottocode": top.get("id") or top.get("glottocode", ""),
                        "level": top.get("level", ""),
                    },
                }
            return None
        except Exception as e:
            logger.debug(f"[Glottolog] iso639 {iso} fetch failed: {e}", exc_info=True)
            return None

    def _search_language(self, query: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen;
            # non-200 → HTTPError.
            req = urllib.request.Request(
                build_glottolog_language_url(query=query),
                headers={"User-Agent": "SCP-Verifier/1.0"},
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results") if isinstance(data, dict) else data
            if not results or (isinstance(results, list) and not results):
                return None
            top = results[0] if isinstance(results, list) else results
            return {
                "value": top.get("name", query),
                "source": "glottolog",
                "metadata": {
                    "name": top.get("name", ""),
                    "glottocode": top.get("id") or top.get("glottocode", ""),
                    "iso639_3": top.get("iso639-3", ""),
                    "level": top.get("level", ""),
                    "family": top.get("family", ""),
                    "result_count": len(results) if isinstance(results, list) else 1,
                },
            }
        except Exception as e:
            logger.debug(f"[Glottolog] language search failed: {e}", exc_info=True)
            return None
