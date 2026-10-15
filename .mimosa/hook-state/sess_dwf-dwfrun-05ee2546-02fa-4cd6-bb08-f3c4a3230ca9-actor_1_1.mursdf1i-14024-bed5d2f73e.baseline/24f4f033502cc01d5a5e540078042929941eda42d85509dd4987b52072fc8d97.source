# SCP CIRCUIT: M13 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M13-closure.json)
"""
Free API Catalog — kho dữ liệu API free toàn cầu cho SCP.

Nguồn: repo công khai `public-apis/public-apis` trên GitHub (bản curated
cộng đồng, ~2.200 API phân theo 50+ category). Catalog được fetch về, parse
thành entries có cấu trúc và cache durable tại ``data/free_api_catalog.json``.

TẠI SAO module này tồn tại:
  Người vận hành không có ngân sách API trả phí. Internet + các API free là
  kho dữ liệu thay thế. SCP cần một catalog có thể tra cứu (search theo
  category/auth) để vòng học (top_systems_learning) và các fetcher sau này
  chọn nguồn dữ liệu free phù hợp.

Fail-closed:
  - Parser là hàm thuần (pure) — test được hermetic, không mạng.
  - refresh() thất bại → trả {"ok": False, "reason": ...} và phục vụ từ cache;
    KHÔNG bao giờ raise ra caller, KHÔNG bao giờ bịa entries.
  - Chỉ fetch đúng 1 host cố định trong ALLOWED_HOSTS (SSRF-safe by
    construction; URL không bao giờ đến từ user input).
  - Egress opt-out: SCP_TOP_SYSTEMS_EGRESS=0 → tắt hẳn mạng, chỉ dùng cache.

[2026-08-29] Local Ollama đã bị xóa khỏi SCP — mọi LLM call đi qua OpenRouter
API (xem scp/llm_gateway/client.py). Module này là mắt xích "kho dữ liệu free"
cùng cấp với gateway đó.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.data_sources.free_api_catalog")

CATALOG_SOURCE_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
ALLOWED_HOSTS = frozenset({"raw.githubusercontent.com"})
_USER_AGENT = "SCP-FreeAPICatalog/1.0 (+https://github.com/checken1994/GA-LAB)"

# Row shape: | [Name](https://url) | Description | `auth` | Yes | Yes |
_ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\((\S+?)\)\s*\|(.*?)\|\s*$")


def _egress_disabled() -> bool:
    return os.environ.get("SCP_TOP_SYSTEMS_EGRESS", "1").strip().lower() in {"0", "false", "off"}


def parse_catalog_md(text: str) -> list[dict[str, Any]]:
    """Parse the public-apis README markdown into structured entries.

    Pure function — no I/O, no network. Accepts only the canonical 5-column
    table shape (| API | Description | Auth | HTTPS | CORS |) and deliberately
    skips sponsor tables whose header is a different shape (e.g. "Call this
    API" with a Postman button column).
    """
    entries: list[dict[str, Any]] = []
    category = ""
    in_api_table = False
    seen_names: set[tuple[str, str]] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("### "):
            category = line[4:].strip()
            in_api_table = False
            continue
        # The public-apis README is inconsistently formatted: the first table
        # keeps the leading pipe ("| API | ...") but every later category table
        # drops it ("API | ..."). Accept both shapes.
        if line.startswith("| API") or line.startswith("API |"):
            in_api_table = "Auth" in line and "HTTPS" in line and "CORS" in line
            continue
        if not line.startswith("|"):
            if not line:
                in_api_table = False
            continue
        if not in_api_table:
            continue
        match = _ROW_RE.match(line)
        if not match:
            continue
        name, url, rest = match.group(1).strip(), match.group(2).strip(), match.group(3)
        cells = [cell.strip() for cell in rest.split("|")]
        while len(cells) < 4:
            cells.append("")
        description = cells[0]
        auth = cells[1].strip("`").strip()
        https = cells[2].strip()
        cors = cells[3].strip()
        key = (category, name)
        if key in seen_names:
            continue
        seen_names.add(key)
        entries.append(
            {
                "name": name,
                "url": url,
                "description": description,
                "auth": auth,
                "https": https,
                "cors": cors,
                "category": category,
            }
        )
    return entries


class FreeAPICatalog:
    """Durable, queryable catalog of the world's free public APIs."""

    schema_version = 1

    def __init__(self, data_dir: str = "data", transport: Callable[[str], bytes] | None = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.data_dir / "free_api_catalog.json"
        self._entries: list[dict[str, Any]] | None = None
        self.last_result: dict[str, Any] = {}
        # Injectable transport for hermetic tests; production uses _http_get.
        self._transport = transport

    # ------------------------------------------------------------------
    # Network (fixed allowlisted host only)
    # ------------------------------------------------------------------
    @staticmethod
    def _http_get(url: str, timeout: float = 25.0, max_bytes: int = 5_000_000) -> bytes:
        host = urllib.request.urlparse(url).hostname or ""
        if url.lower().startswith("http://") or host not in ALLOWED_HOSTS:
            raise ValueError(f"host not in catalog allowlist: {host!r}")
        if _egress_disabled():
            raise RuntimeError("egress disabled by SCP_TOP_SYSTEMS_EGRESS=0")
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})  # noqa: S310 — scheme+host allowlisted above
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw urlopen — thêm lớp
        # validate scheme + chặn private/loopback IP (defense in depth sau
        # allowlist host phía trên).
        with safe_urlopen(req, timeout=timeout) as resp:  # noqa: S310 — validated by safe_urlopen
            return resp.read(max_bytes)

    def refresh(self, force: bool = False) -> dict[str, Any]:
        """Fetch + parse + cache the catalog. Never raises (fail-closed)."""
        cached = self._load_cache()
        if cached and not force:
            age = time.time() - float(cached.get("fetched_at", 0))
            if age < float(os.environ.get("SCP_FREE_API_CATALOG_TTL_SEC", "86400")):
                self.last_result = {"ok": True, "served": "cache_fresh", "count": cached.get("count", 0)}
                return self.last_result
        try:
            raw = (self._transport or self._http_get)(CATALOG_SOURCE_URL)
            entries = parse_catalog_md(raw.decode("utf-8", errors="replace"))
            payload = {
                "schema_version": self.schema_version,
                "source": CATALOG_SOURCE_URL,
                "fetched_at": time.time(),
                "raw_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
                "count": len(entries),
                "entries": entries,
            }
            self.cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self._entries = entries
            self.last_result = {
                "ok": True,
                "served": "network",
                "count": len(entries),
                "raw_sha256": payload["raw_sha256"],
            }
            return self.last_result
        except Exception as exc:
            logger.debug(f"refresh ignored: {exc}", exc_info=True)
            self.last_result = {
                "ok": False,
                "reason": type(exc).__name__,
                "detail": str(exc)[:200],
                "served": "cache" if cached else "none",
            }
            logger.warning("[FreeAPICatalog] refresh failed (%s) — serving cache", self.last_result["reason"])
            return self.last_result

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def _load_cache(self) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (TypeError, ValueError, OSError):
            logger.debug('FreeAPICatalog._load_cache: TypeError, ValueError, OSError ignored', exc_info=True)
            return None

    def entries(self) -> list[dict[str, Any]]:
        if self._entries is None:
            cached = self._load_cache()
            self._entries = list(cached.get("entries", [])) if cached else []
        return self._entries

    def search(
        self,
        query: str = "",
        category: str | None = None,
        auth: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search the catalog. auth="No" filters APIs usable without a key."""
        tokens = [t for t in query.lower().split() if t]
        out: list[dict[str, Any]] = []
        for entry in self.entries():
            if category and entry.get("category", "").lower() != category.lower():
                continue
            if auth and entry.get("auth", "").lower() != auth.lower():
                continue
            haystack = " ".join(
                [entry.get("name", ""), entry.get("description", ""), entry.get("category", "")]
            ).lower()
            if tokens and not all(t in haystack for t in tokens):
                continue
            out.append(entry)
            if len(out) >= max(1, int(limit)):
                break
        return out

    def status(self) -> dict[str, Any]:
        cached = self._load_cache()
        return {
            "count": len(self.entries()),
            "cached": bool(cached),
            "fetched_at": cached.get("fetched_at") if cached else None,
            "source": CATALOG_SOURCE_URL,
            "last_result": self.last_result,
        }


_CATALOG: FreeAPICatalog | None = None
_CATALOG_LOCK = threading.Lock()


def get_catalog(data_dir: str = "data") -> FreeAPICatalog:
    """Thread-safe singleton catalog."""
    global _CATALOG
    if _CATALOG is None:
        with _CATALOG_LOCK:
            if _CATALOG is None:
                _CATALOG = FreeAPICatalog(data_dir=data_dir)
    return _CATALOG
