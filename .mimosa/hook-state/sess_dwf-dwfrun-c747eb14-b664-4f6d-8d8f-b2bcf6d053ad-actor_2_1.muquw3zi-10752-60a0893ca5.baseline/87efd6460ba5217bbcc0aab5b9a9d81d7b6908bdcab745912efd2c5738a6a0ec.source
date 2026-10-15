# SCP CIRCUIT: M08 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M08-closure.json)
"""
SCP V105 — Multi-Source 24/7 Audit Fetcher

[COMPLETION-FIX] Thêm background audit fetcher:
- arXiv (cs.AI, cs.LG, cs.CL)
- HuggingFace Papers (trending)
- NewsAPI (AI headlines)
- Wikipedia (fact-check)

Chạy as background thread, không block /ask.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# [AUDIT-20260909 SSRF-S1] Thay mọi raw requests.get bằng safe_urlopen.
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.audit_fetcher")

DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))
AUDIT_DB = DATA_DIR / "audit_findings.jsonl"

# Sources config
SOURCES = {
    "arxiv": {
        "url": "http://export.arxiv.org/api/query",
        "interval": 300,  # 5 minutes
        "categories": ["cs.AI", "cs.LG", "cs.CL"],
        "enabled": True,
    },
    "huggingface": {
        "url": "https://huggingface.co/api/daily_papers",
        "interval": 3600,  # 1 hour
        "enabled": True,
    },
    "newsapi": {
        "url": "https://newsapi.org/v2/everything",
        "interval": 900,  # 15 minutes
        "query": "AI OR \"machine learning\" OR \"large language model\"",
        "enabled": bool(os.environ.get("NEWSAPI_API_KEY")),
    },
}

_last_fetch: dict[str, float] = {}
_running = False
_thread = None


# [AUDIT-20260909 SSRF-S1] Pure URL builders — input động được encode/ràng
# buộc TRƯỚC khi fetch; host luôn giữ nguyên từ SOURCES (literal cố định).
_ARXIV_CATEGORY_RE = re.compile(r"^[A-Za-z-]{2,8}(\.[A-Za-z]{2,4})?$")


def build_arxiv_category_url(category: str) -> str:
    """[AUDIT-20260909 SSRF-S1] arXiv query URL — category PHẢI khớp pattern
    (vd 'cs.AI'); input xấu → ValueError TRƯỚC KHI fetch. Host cố định."""
    cat = str(category or "")
    if not _ARXIV_CATEGORY_RE.fullmatch(cat):
        raise ValueError(f"invalid_arxiv_category:{cat[:32]!r}")
    query = urllib.parse.urlencode({
        "search_query": f"cat:{cat}",
        "start": 0,
        "max_results": 5,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    return f"{SOURCES['arxiv']['url']}?{query}"


def build_huggingface_papers_url() -> str:
    """[AUDIT-20260909 SSRF-S1] Fixed-host HuggingFace daily papers URL."""
    return SOURCES["huggingface"]["url"]


def build_newsapi_url(query: str, api_key: str, page_size: int = 5) -> str:
    """[AUDIT-20260909 SSRF-S1] NewsAPI URL — query + apiKey được urlencode
    thành query values. Host cố định newsapi.org."""
    params = {
        "q": str(query or ""),
        "apiKey": str(api_key or ""),
        "pageSize": int(page_size),
        "sortBy": "publishedAt",
    }
    return f"{SOURCES['newsapi']['url']}?{urllib.parse.urlencode(params)}"


def _fetch_arxiv() -> list[dict]:
    """Fetch latest arXiv papers."""
    findings = []
    try:
        for cat in SOURCES["arxiv"]["categories"]:
            # [AUDIT-20260909 SSRF-S1] builder validate category + urlencode.
            url = build_arxiv_category_url(cat)
            req = urllib.request.Request(url, headers={"User-Agent": "SCP-AuditFetcher/1.0"})  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=15) as resp:
                text_xml = resp.read().decode("utf-8", errors="replace")
            # Parse Atom feed (simplified)
            entries = re.findall(r'<entry>(.*?)</entry>', text_xml, re.DOTALL)
            for entry in entries[:3]:
                title_m = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary_m = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                if title_m:
                    findings.append({
                        "source": "arxiv",
                        "category": cat,
                        "title": title_m.group(1).strip(),
                        "summary": summary_m.group(1).strip()[:500] if summary_m else "",
                        "fetched_at": datetime.now().isoformat(),
                    })
    except Exception as e:
        logger.warning(f"arXiv fetch error: {e}", exc_info=True)
    return findings


def _fetch_huggingface() -> list[dict]:
    """Fetch trending HuggingFace papers."""
    findings = []
    try:
        url = build_huggingface_papers_url()
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-AuditFetcher/1.0"})  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=15) as resp:
            papers = json.loads(resp.read().decode("utf-8", errors="replace"))[:5]
        for p in papers:
            paper = p.get("paper", {})
            findings.append({
                "source": "huggingface",
                "title": paper.get("title", ""),
                "summary": paper.get("abstract", "")[:500],
                "upvotes": p.get("paper", {}).get("upvotes", 0),
                "fetched_at": datetime.now().isoformat(),
            })
    except Exception as e:
        logger.warning(f"HuggingFace fetch error: {e}", exc_info=True)
    return findings


def _fetch_newsapi() -> list[dict]:
    """Fetch AI news headlines."""
    findings = []
    api_key = os.environ.get("NEWSAPI_API_KEY")
    if not api_key:
        return findings
    try:
        # [AUDIT-20260909 SSRF-S1] builder urlencode query + apiKey (không log key).
        url = build_newsapi_url(SOURCES["newsapi"]["query"], api_key, page_size=5)
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-AuditFetcher/1.0"})  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        for article in (payload.get("articles") or [])[:5]:
            findings.append({
                "source": "newsapi",
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "published": article.get("publishedAt", ""),
                "fetched_at": datetime.now().isoformat(),
            })
    except Exception as e:
        logger.warning(f"NewsAPI fetch error: {e}", exc_info=True)
    return findings


def _save_findings(findings: list[dict]) -> None:
    """Append findings to JSONL."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(AUDIT_DB, "a", encoding="utf-8") as f:
        for finding in findings:
            f.write(json.dumps(finding, ensure_ascii=False) + "\n")


def _audit_loop() -> None:
    """Background audit loop."""
    # [FALSE-POS-FIX] F824: `global _running` removed — read-only access (while loop).
    # Assignment happens in start_audit_fetcher()/stop_audit_fetcher() which have their own global.
    logger.info("[AuditFetcher] Background thread started")
    while _running:
        try:
            now = time.time()
            # arXiv
            if SOURCES["arxiv"]["enabled"] and now - _last_fetch.get("arxiv", 0) > SOURCES["arxiv"]["interval"]:
                findings = _fetch_arxiv()
                if findings:
                    _save_findings(findings)
                    logger.info(f"[AuditFetcher] arXiv: {len(findings)} papers fetched")
                _last_fetch["arxiv"] = now

            # HuggingFace
            if SOURCES["huggingface"]["enabled"] and now - _last_fetch.get("huggingface", 0) > SOURCES["huggingface"]["interval"]:
                findings = _fetch_huggingface()
                if findings:
                    _save_findings(findings)
                    logger.info(f"[AuditFetcher] HuggingFace: {len(findings)} papers fetched")
                _last_fetch["huggingface"] = now

            # NewsAPI
            if SOURCES["newsapi"]["enabled"] and now - _last_fetch.get("newsapi", 0) > SOURCES["newsapi"]["interval"]:
                findings = _fetch_newsapi()
                if findings:
                    _save_findings(findings)
                    logger.info(f"[AuditFetcher] NewsAPI: {len(findings)} articles fetched")
                _last_fetch["newsapi"] = now

        except Exception as e:
            logger.error(f"[AuditFetcher] Loop error: {e}", exc_info=True)

        time.sleep(60)  # Check every minute


def start_audit_fetcher() -> None:
    """Start background audit fetcher thread."""
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_audit_loop, daemon=True, name="scp-audit-fetcher")
    _thread.start()
    logger.info("[AuditFetcher] Started — arXiv + HuggingFace + NewsAPI")


def stop_audit_fetcher() -> None:
    """Stop background audit fetcher."""
    global _running
    _running = False
    if _thread:
        _thread.join(timeout=5)
    logger.info("[AuditFetcher] Stopped")


def get_audit_stats() -> dict[str, Any]:
    """Get audit fetcher statistics."""
    if not AUDIT_DB.exists():
        return {"total_findings": 0, "sources": {}}

    counts: dict[str, int] = {}
    total = 0
    try:
        with open(AUDIT_DB, encoding="utf-8") as f:
            for line in f:
                try:
                    finding = json.loads(line)
                    src = finding.get("source", "unknown")
                    counts[src] = counts.get(src, 0) + 1
                    total += 1
                except json.JSONDecodeError as exc:
                    # Corrupt historical record must be visible; skipping keeps aggregation resilient.
                    logger.warning("audit_fetcher: corrupt record skipped in aggregation: %s", exc, exc_info=True)
                    continue
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)

    return {
        "total_findings": total,
        "sources": counts,
        "running": _running,
        "db_path": str(AUDIT_DB),
    }
