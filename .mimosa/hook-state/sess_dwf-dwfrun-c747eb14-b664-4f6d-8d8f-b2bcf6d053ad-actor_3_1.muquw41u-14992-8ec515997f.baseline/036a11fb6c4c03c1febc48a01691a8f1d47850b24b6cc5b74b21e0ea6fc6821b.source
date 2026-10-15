"""
Mảnh ghép #11 nâng cấp — Knowledge Curation Pipeline: từ Internet vô tận
đến bộ nhớ dài hạn có chất lượng, qua 4 cổng chặt chẽ.

    CÀO (Multi-Source) → CHẤM ĐIỂM (Multi-Signal) → TRÍCH XUẤT (Concepts) → NHỚ (Dedup+Prune)

Câu hỏi của chủ hệ thống:
  Q1 "Chỉ OpenRouter? API khác chạy thế nào?" → Multi-provider failover + pre-configured free APIs
  Q2 "Cào Internet ra sao?"                    → 5 nguồn: GitHub + Wikipedia + arXiv + Hacker News + Stack Overflow
  Q3 "Tách rác khỏi thật?"                     → Multi-signal reliability score (4 tín hiệu độc lập)

Tất cả deterministic — không dùng LLM để đánh giá chất lượng dữ liệu
(đánh giá bằng LLM là tự dính ảo giác đồng thuận).
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
import urllib.request
from typing import Any

from scp.core.top_systems_learning import (
    TOPIC_LIBRARY,
    TokenBucket,
    _extract_concepts,
    inspect_untrusted,
)
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.core.curation_pipeline")

# ============================================================
# STAGE 1: MULTI-SOURCE SCRAPING — 5 nguồn free, 0 cần key
# ============================================================

SCRAPER_HOSTS = frozenset({
    "api.github.com", "en.wikipedia.org",
    "export.arxiv.org", "hn.algolia.com", "api.stackexchange.com",
})
_CURATED_BUCKET = TokenBucket(capacity=30, refill_seconds=1.0)


def scrape_arxiv(query: str, per_source: int = 3) -> list[dict[str, Any]]:
    """arXiv API — free, không key, papers nghiên cứu."""
    url = (
        "https://export.arxiv.org/api/query?search_query=all:"
        + urllib.parse.quote(query)
        + f"&max_results={per_source}&sortBy=relevance"
    )
    # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get — validate scheme
    # + chặn private IP; non-200 → HTTPError (tương đương raise_for_status).
    req = urllib.request.Request(
        url, headers={"User-Agent": "SCP-Curation/1.0"}
    )  # noqa: S310 — validated by safe_urlopen
    with safe_urlopen(req, timeout=15.0) as response:
        text = response.read(500_000).decode("utf-8", errors="replace")
    # Parse Atom XML minimally
    entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)
    out = []
    for entry in entries[:per_source]:
        title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary_m = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        link_m = re.search(r"<link[^>]*href=\"(.*?)\"", entry)
        out.append({
            "source": "arxiv",
            "kind": "paper",
            "name": (title_m.group(1).strip() if title_m else "")[:200],
            "url": (link_m.group(1) if link_m else "")[:300],
            "description": re.sub(r"\s+", " ", summary_m.group(1)).strip()[:400] if summary_m else "",
            "reputation": "high",  # arXiv = peer-reviewed + preprint chuẩn
        })
    return out


def scrape_hackernews(query: str, per_source: int = 3) -> list[dict[str, Any]]:
    """Hacker News Algolia API — free, không key, community-curated."""
    url = (
        "https://hn.algolia.com/api/v1/search?query="
        + urllib.parse.quote(query)
        + f"&tags=story&hitsPerPage={per_source}"
    )
    # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get; non-200 → HTTPError.
    req = urllib.request.Request(
        url, headers={"User-Agent": "SCP-Curation/1.0"}
    )  # noqa: S310 — validated by safe_urlopen
    with safe_urlopen(req, timeout=15.0) as response:
        data = json.loads(response.read(200_000).decode("utf-8", errors="replace"))
    out = []
    for hit in data.get("hits", [])[:per_source]:
        points = int(hit.get("points", 0))
        out.append({
            "source": "hackernews",
            "kind": "discussion",
            "name": str(hit.get("title", ""))[:200],
            "url": str(hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}")[:300],
            "description": str(hit.get("story_text") or hit.get("comment_text") or "")[:400],
            "stars": points,
            "reputation": "high" if points >= 100 else "medium" if points >= 10 else "low",
        })
    return out


def scrape_stackoverflow(query: str, per_source: int = 3) -> list[dict[str, Any]]:
    """Stack Exchange API — free, không key (300 req/day limit)."""
    url = (
        "https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance"
        + f"&q={urllib.parse.quote(query)}&site=stackoverflow&pagesize={per_source}"
        + "&filter=withbody"
    )
    # [AUDIT-20260909 SSRF-S1] safe_urlopen thay httpx.get; non-200 → HTTPError.
    req = urllib.request.Request(
        url, headers={"User-Agent": "SCP-Curation/1.0"}
    )  # noqa: S310 — validated by safe_urlopen
    with safe_urlopen(req, timeout=15.0) as response:
        data = json.loads(response.read(200_000).decode("utf-8", errors="replace"))
    out = []
    for item in data.get("items", [])[:per_source]:
        score = int(item.get("score", 0))
        is_answered = item.get("is_answered", False)
        body = re.sub(r"<[^>]+>", "", str(item.get("body_markdown") or item.get("body", "")))
        out.append({
            "source": "stackoverflow",
            "kind": "q_and_a",
            "name": str(item.get("title", ""))[:200],
            "url": str(item.get("link", ""))[:300],
            "description": body[:400],
            "stars": score,
            "reputation": "high" if is_answered and score >= 5 else "medium" if is_answered else "low",
            "answered": is_answered,
        })
    return out


# ============================================================
# STAGE 2: MULTI-SIGNAL RELIABILITY SCORING
# ============================================================

def reliability_score(record: dict[str, Any]) -> dict[str, Any]:
    """Chấm điểm độ tin cậy bằng 4 tín hiệu ĐỘC LẬP (không LLM, không mạng).

    Signal 1: SOURCE_AUTHORITY  — arXiv/StackOverflow-answered > Wikipedia > HN > GitHub-random
    Signal 2: ENGAGEMENT        — stars/points/votes (social proof, KHÔNG tuyệt đối)
    Signal 3: FRESHNESS         — dữ liệu mới hơn có giá trị cao hơn
    Signal 4: INJECTION_SCAN    — pattern-match hostile content (đã có inspect_untrusted)

    Output: composite_score 0.0-1.0 + tier (trusted/moderate/quarantined)
    """
    signals = {}

    # Signal 1: Source authority (inherent trust of the platform)
    authority_map = {
        "arxiv": 0.9, "wikipedia": 0.7, "stackoverflow": 0.7,
        "github_readme": 0.5, "github": 0.4, "hackernews": 0.4,
    }
    signals["source_authority"] = authority_map.get(record.get("source", ""), 0.3)

    # Signal 2: Engagement (social proof, normalized)
    stars = record.get("stars") or record.get("points") or 0
    signals["engagement"] = min(stars / 10_000.0, 1.0) if stars else 0.0

    # Signal 3: Freshness (newer = better, decay over 90 days)
    collected = record.get("collected_at", time.time())
    age_days = (time.time() - collected) / 86400
    signals["freshness"] = max(0.0, 1.0 - age_days / 90.0)

    # Signal 4: Injection scan (deterministic, from inspect_untrusted)
    content = record.get("description", "") + " " + " ".join(record.get("concepts", []))
    quarantined, reason = inspect_untrusted(content)
    signals["injection_clean"] = 0.0 if quarantined else 1.0

    # Composite: weighted average — injection_clean is a HARD GATE (bất kỳ
    # dấu hiệu injection nào → 0.0, không phải trung bình)
    if signals["injection_clean"] == 0.0:
        return {"composite_score": 0.0, "tier": "quarantined", "signals": signals, "quarantine_reason": reason}

    composite = (
        signals["source_authority"] * 0.35
        + signals["engagement"] * 0.20
        + signals["freshness"] * 0.15
        + signals["injection_clean"] * 0.30
    )
    tier = "trusted" if composite >= 0.7 else "moderate" if composite >= 0.4 else "weak"
    return {"composite_score": round(composite, 3), "tier": tier, "signals": signals}


# ============================================================
# STAGE 3+4: EXTRACT + MEMORY (tích hợp vào learner hiện có)
# ============================================================

def curate(learner, topic: str, per_source: int = 3) -> dict[str, Any]:
    """Full pipeline: cào 5 nguồn → chấm điểm → lọc rác → trích xuất → ghi nhớ.

    Trả về: {verdict, sources_scraped, records, trusted, quarantined, concepts}
    """
    errors = []
    all_records: list[dict[str, Any]] = []

    # Stage 1: Multi-source scraping
    sources = [
        ("github", lambda: _github_search(learner, TOPIC_LIBRARY.get(topic, {}).get("github_query", topic), per_source)),
        ("wikipedia", lambda: _wiki_search(learner, TOPIC_LIBRARY.get(topic, {}).get("wiki_query", topic), per_source)),
        ("arxiv", lambda: scrape_arxiv(topic.replace("_", " "), per_source)),
        ("hackernews", lambda: scrape_hackernews(topic.replace("_", " "), per_source)),
        ("stackoverflow", lambda: scrape_stackoverflow(topic.replace("_", " "), per_source)),
    ]
    for source_name, fetch_fn in sources:
        try:
            records = fetch_fn()
            for r in records:
                r["topic"] = topic
                r["collected_at"] = time.time()
            all_records.extend(records)
        except Exception as exc:
            logger.debug(f"curate ignored: {exc}", exc_info=True)
            errors.append(f"{source_name}: {type(exc).__name__}: {str(exc)[:100]}")

    # Stage 2: Reliability scoring + Stage 4 injection gate
    curated = []
    quarantined_count = 0
    for record in all_records:
        quality = reliability_score(record)
        record["quality"] = quality
        record["concepts"] = _extract_concepts(record.get("description", ""))
        if quality["tier"] == "quarantined":
            quarantined_count += 1
            continue  # ĐỪNG lưu — injection detected
        curated.append(record)

    # Stage 3: Concepts đã extract trong record["concepts"]

    # Stage 4: Dedup by content hash + write to ledger
    written = learner._append_ledger(curated)

    return {
        "ok": len(errors) < len(sources),
        "topic": topic,
        "sources_scraped": len(sources) - len([e for e in errors if ":" in e]),
        "records": written,
        "quarantined": quarantined_count,
        "trusted": sum(1 for c in curated if c.get("quality", {}).get("tier") == "trusted"),
        "errors": errors,
        "ledger": str(learner.ledger_path),
    }


def _github_search(learner, query: str, per_source: int) -> list[dict[str, Any]]:
    return learner._fetch_github(query, per_source)


def _wiki_search(learner, query: str, per_source: int) -> list[dict[str, Any]]:
    return learner._fetch_wikipedia(query, per_source)
