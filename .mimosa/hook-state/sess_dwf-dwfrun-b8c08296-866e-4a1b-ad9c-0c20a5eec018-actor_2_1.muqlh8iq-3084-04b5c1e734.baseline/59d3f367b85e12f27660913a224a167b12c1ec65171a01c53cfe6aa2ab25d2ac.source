# SCP CIRCUIT: M09 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M09-closure.json)
"""
SCP V105 — Real-world Harm Detector (Layer 3)

Auto monitor internet cho AI-related harm thực tế:
  - News: AI accidents, misuse, deepfake, autonomous failures
  - Government: AI policy changes, bans, investigations
  - Social media: viral AI misuse, public warnings
  - Academic: AI safety warnings, incident reports

Khi phát hiện → classify harm type → AdminAlerter cảnh báo.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# [AUDIT-20260909 SSRF-S1] Thay mọi raw requests.get bằng safe_urlopen.
from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.harm_detector")

DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))
HARM_DB = DATA_DIR / "ai_harm_incidents.jsonl"

# Harm categories
HARM_CATEGORIES = {
    "autonomous_hacking": ["AI hack", "AI breach", "AI attack", "autonomous cyber", "AI escape sandbox"],
    "deepfake": ["deepfake", "AI fake", "synthetic media", "voice clone"],
    "misinformation": ["AI misinformation", "AI propaganda", "AI fake news", "AI disinformation"],
    "autonomous_failure": ["AI accident", "AI failure", "autonomous vehicle", "AI crash", "AI error"],
    "privacy_violation": ["AI privacy", "AI surveillance", "AI tracking", "face recognition abuse"],
    "economic_harm": ["AI scam", "AI fraud", "AI theft", "AI financial crime"],
    "safety_incident": ["AI safety incident", "AI harm", "AI injury", "AI death"],
    "policy_action": ["AI ban", "AI regulation", "AI investigation", "AI lawsuit", "AI fine"],
}

SOURCES = {
    "newsapi": {
        "url": "https://newsapi.org/v2/everything",
        "interval": 900,
        "needs_key": True,
    },
    "reddit_ml": {
        "url": "https://www.reddit.com/r/MachineLearning/hot.json",
        "interval": 600,
        "headers": {"User-Agent": "SCP-HarmDetector/1.0"},
    },
    "reddit_safety": {
        "url": "https://www.reddit.com/r/aiSafety/hot.json",
        "interval": 600,
        "headers": {"User-Agent": "SCP-HarmDetector/1.0"},
    },
    "reddit_tech": {
        "url": "https://www.reddit.com/r/technology/hot.json",
        "interval": 900,
        "headers": {"User-Agent": "SCP-HarmDetector/1.0"},
    },
}

_last_scan: dict[str, float] = {}
_running = False
_thread = None


# [AUDIT-20260909 SSRF-S1] Pure URL builder — query + apiKey được urlencode;
# host cố định newsapi.org (literal từ SOURCES).
def build_newsapi_harm_url(query: str, api_key: str) -> str:
    """[AUDIT-20260909 SSRF-S1] NewsAPI harm-scan URL — mọi param động được
    urlencode thành query values, không thể đổi host/path."""
    params = {
        "q": str(query or ""),
        "apiKey": str(api_key or ""),
        "pageSize": 10,
        "sortBy": "publishedAt",
        "language": "en",
    }
    return f"{SOURCES['newsapi']['url']}?{urllib.parse.urlencode(params)}"


def _classify_harm(text: str) -> str | None:
    """Classify text vào harm category."""
    text_lower = text.lower()
    for _category, keywords in HARM_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                return _category
    return None


def _scan_newsapi() -> list[dict]:
    """Scan NewsAPI cho AI harm incidents."""
    incidents = []
    api_key = os.environ.get("NEWSAPI_API_KEY")
    if not api_key:
        return incidents
    try:
        for _category, keywords in HARM_CATEGORIES.items():
            query = " OR ".join(keywords[:3])
            # [AUDIT-20260909 SSRF-S1] builder urlencode (không log apiKey).
            url = build_newsapi_harm_url(query, api_key)
            req = urllib.request.Request(url, headers={"User-Agent": "SCP-HarmDetector/1.0"})  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for article in (payload.get("articles") or [])[:10]:
                title = article.get("title", "")
                desc = article.get("description", "")
                text = title + " " + desc
                harm_type = _classify_harm(text)
                if harm_type:
                    incidents.append({
                        "source": "newsapi",
                        "harm_type": harm_type,
                        "title": title,
                        "description": desc[:300] if desc else "",
                        "url": article.get("url", ""),
                        "published": article.get("publishedAt", ""),
                        "detected_at": datetime.now().isoformat(),
                    })
            time.sleep(1)  # Rate limit
    except Exception as e:
        logger.warning(f"NewsAPI harm scan error: {e}", exc_info=True)
    return incidents


def _scan_reddit(url: str, source_name: str) -> list[dict]:
    """Scan Reddit cho AI harm discussions."""
    incidents = []
    try:
        headers = SOURCES[source_name]["headers"]
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay requests.get — url là
        # literal từ SOURCES nhưng vẫn được validate scheme + private IP.
        req = urllib.request.Request(url, headers=headers)  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        for post in (payload.get("data", {}) or {}).get("children", [])[:25]:
            data = post.get("data", {})
            title = data.get("title", "")
            selftext = data.get("selftext", "")[:300]
            text = title + " " + selftext
            harm_type = _classify_harm(text)
            if harm_type:
                incidents.append({
                    "source": source_name,
                    "harm_type": harm_type,
                    "title": title,
                    "description": selftext[:200],
                    "url": f"https://reddit.com{data.get('permalink', '')}",
                    "score": data.get("score", 0),
                    "detected_at": datetime.now().isoformat(),
                })
    except Exception as e:
        logger.warning(f"Reddit {source_name} scan error: {e}", exc_info=True)
    return incidents


def _save_incidents(incidents: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(HARM_DB, "a", encoding="utf-8") as f:
        for inc in incidents:
            f.write(json.dumps(inc, ensure_ascii=False) + "\n")


def _alert_incidents(incidents: list[dict]) -> None:
    """Send real-time alert."""
    try:
        from scp.security.counter_response import AdminAlerter
        alerter = AdminAlerter()
        for inc in incidents:
            alerter.alert(
                event_type="ai_harm_detected",
                severity="CRITICAL" if inc["harm_type"] in ("safety_incident", "autonomous_hacking") else "HIGH",
                details={
                    "harm_type": inc["harm_type"],
                    "title": inc["title"][:200],
                    "url": inc.get("url", ""),
                    "source": inc["source"],
                },
            )
    except Exception as e:
        logger.warning(f"Alert failed: {e}", exc_info=True)


def _harm_loop() -> None:
    # [FALSE-POS-FIX] F824: `global _running` removed — read-only access (while loop).
    # Assignment happens in start_detector()/stop_detector() which have their own global.
    logger.info("[HarmDetector] Background thread started")
    while _running:
        try:
            now = time.time()
            all_incidents = []

            if now - _last_scan.get("newsapi", 0) > SOURCES["newsapi"]["interval"]:
                all_incidents.extend(_scan_newsapi())
                _last_scan["newsapi"] = now

            for reddit_key in ["reddit_ml", "reddit_safety", "reddit_tech"]:
                if now - _last_scan.get(reddit_key, 0) > SOURCES[reddit_key]["interval"]:
                    all_incidents.extend(_scan_reddit(SOURCES[reddit_key]["url"], reddit_key))
                    _last_scan[reddit_key] = now

            if all_incidents:
                # Deduplicate by title
                seen = set()
                unique = []
                for inc in all_incidents:
                    key = inc["title"][:100].lower()
                    if key not in seen:
                        seen.add(key)
                        unique.append(inc)
                _save_incidents(unique)
                _alert_incidents(unique)
                logger.info(f"[HarmDetector] {len(unique)} harm incidents found + alerted")

        except Exception as e:
            logger.error(f"[HarmDetector] Loop error: {e}", exc_info=True)
        time.sleep(60)


def start_detector() -> None:
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_harm_loop, daemon=True, name="scp-harm-detector")
    _thread.start()
    logger.info("[HarmDetector] Started — monitoring News + Reddit for AI harm")


def stop_detector() -> None:
    global _running
    _running = False
    if _thread:
        _thread.join(timeout=5)


def get_harm_stats() -> dict[str, Any]:
    if not HARM_DB.exists():
        return {"total_incidents": 0, "by_type": {}}
    counts: dict[str, int] = {}
    total = 0
    try:
        with open(HARM_DB, encoding="utf-8") as f:
            for line in f:
                try:
                    inc = json.loads(line)
                    ht = inc.get("harm_type", "unknown")
                    counts[ht] = counts.get(ht, 0) + 1
                    total += 1
                except Exception as exc:  # noqa: S112
                    # silent-by-design: one bad historical record must not abort type aggregation.
                    logger.debug("harm_detector: record aggregation skipped a bad record: %s", exc, exc_info=True)
                    continue
    except Exception as _e:  # noqa: S110
        logger.debug(f"[silent-except] {_e}", exc_info=True)
    return {"total_incidents": total, "by_type": counts, "running": _running}
