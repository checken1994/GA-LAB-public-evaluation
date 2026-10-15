"""
[OPT-11] GutenbergDataSource — Project Gutenberg books API (Gutendex).

DNA SCP: literature / book data needs verifiable source.
Gutendex is a free, no-key API that mirrors Project Gutenberg's 70k+ books.
Supports: book titles, authors, literary works, download counts.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from scp.interfaces.data_source import IDataSource, reachability_ping, shared_health_ping
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.gutenberg")

# [AUDIT-20260909 SSRF-S1] Host cố định — literal duy nhất của builder.
_GUTENBERG_SEARCH_URL = "https://gutendex.com/books"


def build_gutenberg_search_url(term: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — search term được urlencode
    thành query value; host cố định gutendex.com."""
    return _GUTENBERG_SEARCH_URL + "?" + urllib.parse.urlencode({
        "search": str(term or ""),
    })


class GutenbergDataSource(IDataSource):
    """Gutendex API — Project Gutenberg books (no key required)."""

    BASE_URL = "https://gutendex.com"

    def __init__(self):
        self.enabled = True
        logger.info("[Gutenberg] enabled (no API key required)")

    @property
    def name(self) -> str:
        return "gutenberg"

    @property
    def priority(self) -> int:
        return 15  # lower priority — literature niche

    @property
    def ttl(self) -> int:
        return 86400  # 24h cache — book catalog doesn't change fast

    def get_supported_intents(self) -> list[str]:
        return ["book", "author", "literature", "novel", "literary_work"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if not self.enabled:
            return False
        if intent in self.get_supported_intents():
            return True
        # Question-based (legacy compat)
        question = intent or ""
        q = question.lower()
        keywords = ["book", "sách", "novel", "tiểu thuyết", "author", "tác giả",
                    "literature", "văn học", "gutenberg", "shakespeare", "dickens",
                    "tolstoy", "austen"]
        return any(k in q for k in keywords)

    def fetch(self, intent: str, entity: str, **kwargs) -> dict | None:
        """IDataSource interface — delegate to query()."""
        return self.query(entity or intent)

    def health_check(self) -> bool:
        """[V104.32] Fail-closed honest ping — reachability của endpoint mà
        fetch() thực sự dùng (gutendex.com). Trước đây hardcode `return self.enabled`
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
        return reachability_ping('https://gutendex.com/books?page=1')

    def query(self, question: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            import re
            # Try to extract author or title from question
            # "Who wrote X?" → X
            m = re.match(r'who\s+wrote\s+(.+?)\?*$', question, re.IGNORECASE)
            if m:
                return self._query_book(m.group(1).strip())
            # "Sách của X" / "books by X"
            m = re.match(r'(?:sách|books?)\s+(?:của|by)\s+(.+?)\?*$', question, re.IGNORECASE)
            if m:
                return self._query_author(m.group(1).strip())
            # "Author of X" → X
            m = re.match(r'author\s+of\s+(.+?)\?*$', question, re.IGNORECASE)
            if m:
                return self._query_book(m.group(1).strip())
            # Generic — try searching the whole question
            return self._query_book(question.strip())
        except Exception as e:
            logger.debug(f"[Gutenberg] query failed: {e}", exc_info=True)
            return None

    def _query_book(self, title: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(build_gutenberg_search_url(title))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            if results:
                book = results[0]
                return {
                    "value": book.get("title", ""),
                    "source": "gutenberg",
                    "metadata": {
                        "authors": [a.get("name", "") for a in book.get("authors", [])],
                        "download_count": book.get("download_count", 0),
                        "languages": book.get("languages", []),
                        "gutenberg_id": book.get("id", 0),
                        "formats": list(book.get("formats", {}).keys())[:3],
                    },
                }
        except Exception as e:
            logger.debug(f"[Gutenberg] book '{title}' query failed: {e}", exc_info=True)
        return None

    def _query_author(self, author: str) -> dict | None:
        try:
            # [AUDIT-20260909 SSRF-S1] builder urlencode + safe_urlopen thay
            # raw httpx.get; non-200 → HTTPError.
            req = urllib.request.Request(build_gutenberg_search_url(author))
            with safe_urlopen(req, timeout=10) as r:  # noqa: S310 — validated by safe_urlopen
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            results = data.get("results", [])
            if results:
                # Return top 3 books by this author
                top_books = results[:3]
                return {
                    "value": f"{len(results)} books found, top: {top_books[0].get('title', '')}",
                    "source": "gutenberg",
                    "metadata": {
                        "author_searched": author,
                        "book_count": data.get("count", 0),
                        "top_books": [
                            {
                                "title": b.get("title", ""),
                                "download_count": b.get("download_count", 0),
                                "gutenberg_id": b.get("id", 0),
                            } for b in top_books
                        ],
                    },
                }
        except Exception as e:
            logger.debug(f"[Gutenberg] author '{author}' query failed: {e}", exc_info=True)
        return None
