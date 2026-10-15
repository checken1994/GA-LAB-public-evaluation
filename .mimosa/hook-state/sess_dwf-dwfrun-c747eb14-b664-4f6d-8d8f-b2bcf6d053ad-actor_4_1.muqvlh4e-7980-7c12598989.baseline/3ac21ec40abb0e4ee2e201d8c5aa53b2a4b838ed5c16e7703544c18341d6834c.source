"""
[Task 8-A] Question fetcher module — extracted from real_question_fetcher.py

TẠI SAO: real_question_fetcher.py god file. Tách fetcher functions vào module
này. Backward-compatible — real_question_fetcher.py re-exports all fetchers.
"""
from __future__ import annotations

import logging
import random
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from scp.core.question_fetchers._common import (
    _SESSION,
    _clean,
    _extract_specific_fact,
    _guess_domain,
    _http_get_json,
)
from scp.security.url_safety import enforce_egress_policy, validate_url  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [Mimosa B311-fix 2026-09-30] Các fetcher chọn ngẫu nhiên N mục từ danh sách
# ứng viên (book OLID, arXiv entries, spells, câu Kinh Thánh, artist) để tạo
# câu hỏi kiến thức — sampling phi mật mã: không token, không secret, không
# ID/nonce cần unguessable; đoán trước mục được chọn không gây hại. Dùng
# instance Random RIÊNG (SystemRandom, seed từ os.urandom) thay cho global
# RNG để (1) tách biệt với mọi lời random.seed() của module khác và (2)
# làm rõ ràng tại call site rằng đây là nguồn ngẫu nhiên độc lập, phi bảo mật.
_FETCHERS_RNG = random.SystemRandom()

def fetch_wikipedia_random(lang: str = "vi", n: int = 5) -> list[dict]:
    """
     Fetch N random Wikipedia articles IN PARALLEL.
    Extract specific facts instead of "Tell me about X" questions.
    """
    results = []
    base = f"https://{lang}.wikipedia.org/api/rest_v1/page/random/summary"

    def _fetch_one_wiki(_):
        """Fetch 1 random Wikipedia article."""
        data = _http_get_json(base)
        if not data or data.get("type") in ("not_found", "disambiguation"):
            return None
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        if not title or not extract or len(extract) < 30:
            return None
        url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        #  Try to extract specific fact
        fact = _extract_specific_fact(title, extract, lang)
        if fact:
            question, real_value = fact
            return {
                "question": question,
                "ai_answer": real_value,  # Now a SPECIFIC value, not whole extract
                "source": f"wikipedia_{lang}",
                "source_url": url,
                "domain": _guess_domain(title + " " + extract),
                "category": data.get("type", "standard"),
            }
        else:
            #  Fallback: ask for short description (1 sentence)
            first_sent = extract.split('.')[0] + '.'
            if len(first_sent) > 30 and len(first_sent) < 300:
                if lang == "vi":
                    question = f"Mô tả ngắn về {title} là gì?"
                else:
                    question = f"What is a short description of {title}?"
                return {
                    "question": question,
                    "ai_answer": _clean(first_sent, 200),
                    "source": f"wikipedia_{lang}",
                    "source_url": url,
                    "domain": _guess_domain(title + " " + extract),
                    "category": data.get("type", "standard"),
                }
        return None

    #  Parallel fetch N articles
    with ThreadPoolExecutor(max_workers=min(n, 5)) as executor:
        futures = [executor.submit(_fetch_one_wiki, i) for i in range(n)]
        for future in as_completed(futures, timeout=30):
            try:
                r = future.result(timeout=20)
                if r:
                    results.append(r)
            except Exception as exc:  # noqa: S112
                # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
                logger.debug("knowledge_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
                continue

    return results





def fetch_open_library(n: int = 3) -> list[dict]:
    """Open Library — random book info."""
    results = []
    # Random OLID works
    olids = ["OL45804W", "OL27448W", "OL17358748W", "OL81630W", "OL14935973W",
             "OL17091839W", "OL82587W", "OL5735363W", "OL17186083W", "OL15478934W"]
    sample = _FETCHERS_RNG.sample(olids, min(n, len(olids)))
    for olid in sample:
        try:
            data = _http_get_json(f"https://openlibrary.org/works/{olid}.json")
            if not data:
                continue
            title = data.get("title", "")
            desc_obj = data.get("description", {})
            if isinstance(desc_obj, dict):
                desc = desc_obj.get("value", "")
            else:
                desc = str(desc_obj or "")
            if not title:
                continue
            results.append({
                "question": f"Tell me about the book: {title}.",
                "ai_answer": _clean(desc or title, 400),
                "source": "open_library",
                "source_url": f"https://openlibrary.org/works/{olid}",
                "domain": "arts",
                "category": "book",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("knowledge_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_arxiv_physics(n: int = 3) -> list[dict]:
    """arXiv — physics papers (physics)."""
    try:
        from defusedxml import ElementTree as ET  # noqa: B314
        url = "https://export.arxiv.org/api/query?search_query=cat:physics*&max_results=100&sortBy=submittedDate&sortOrder=descending"
        # [AUDIT-20260909 SSRF-S1] validate_url trước _SESSION.get — chặn
        # scheme lạ + private/loopback IP; fail → ValueError → trả [].
        # [AUDIT-R2 F-03] enforce_egress_policy chạy TRƯỚC _SESSION.get —
        # cùng thứ tự với _http_get_json (V-EE-1): trước đây nhánh này chỉ chạy
        # validate_url (SSRF) rồi gọi thẳng _SESSION.get, nên fetch arxiv thành
        # công dưới SCP_EGRESS_MODE=deny (probe runtime đã bắt). EgressDeniedError
        # là ValueError subclass → rơi vào except dưới → trả [] (contract
        # "fetcher fail-closed []" giữ nguyên, không fetch attempt nào xảy ra).
        enforce_egress_policy(url)
        validate_url(url)
        resp = _SESSION.get(url, timeout=10, headers={"User-Agent": "SCP-V91/1.0"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
        # arXiv uses default Atom namespace
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        sample = _FETCHERS_RNG.sample(entries, min(n, len(entries)))
        results = []
        for entry in sample:
            title = entry.find("{http://www.w3.org/2005/Atom}title")
            title_text = title.text.strip().replace("\n", " ") if title is not None else "?"
            summary = entry.find("{http://www.w3.org/2005/Atom}summary")
            summary_text = summary.text.strip()[:200] if summary is not None else ""
            results.append({
                "question": f"What is this physics research about: {title_text[:60]}?",
                "ai_answer": summary_text,
                "source": "arxiv_physics",
                "source_url": "https://arxiv.org/list/physics",
                "domain": "physics",
                "category": "research",
            })
        return results
    except Exception as e:
        logger.debug(f"arXiv physics error: {e}", exc_info=True)
        return []





def fetch_open5e_spells(n: int = 3) -> list[dict]:
    """Open5e — D&D spells (fantasy/arts)."""
    results = []
    data = _http_get_json("https://api.open5e.com/v1/spells/?limit=200")
    if not data or not data.get("results"):
        return results
    sample = _FETCHERS_RNG.sample(data["results"], min(n, len(data["results"])))
    for spell in sample:
        try:
            name = spell.get("name", "")
            desc = spell.get("desc", "")
            if not name or not desc:
                continue
            results.append({
                "question": f"What does the D&D spell '{name}' do?",
                "ai_answer": _clean(desc, 400),
                "source": "open5e",
                "source_url": "https://open5e.com/",
                "domain": "arts",
                "category": "spell",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("knowledge_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_bible_api(n: int = 2) -> list[dict]:
    """Bible API — random verses (history/literature)."""
    results = []
    refs = ["John 3:16", "Genesis 1:1", "Psalm 23:1", "Matthew 5:3", "Proverbs 1:7",
            "Romans 8:28", "Isaiah 53:5", "Revelation 21:4", "Exodus 20:3", "Philippians 4:13"]
    sample = _FETCHERS_RNG.sample(refs, min(n, len(refs)))
    for ref in sample:
        try:
            data = _http_get_json(f"https://bible-api.com/{urllib.parse.quote(ref)}?translation=kjv")
            if not data:
                continue
            text = data.get("text", "").strip()
            reference = data.get("reference", "")
            if not text:
                continue
            results.append({
                "question": f"What does the Bible say in {reference}?",
                "ai_answer": _clean(text, 400),
                "source": "bible_api",
                "source_url": "https://bible-api.com/",
                "domain": "history",
                "category": "religion",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("knowledge_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_musicbrainz(n: int = 5) -> list[dict]:
    """MusicBrainz — random artists (music)."""
    try:
        data = _http_get_json(
            "https://musicbrainz.org/ws/2/artist/?query=*&fmt=json&limit=200",
            timeout=10,
            headers={"User-Agent": "SCP-V91/1.0 (research)"}
        )
        if not data or "artists" not in data:
            return []
        artists = data["artists"]
        sample = _FETCHERS_RNG.sample(artists, min(n, len(artists)))
        results = []
        for artist in sample:
            name = artist.get("name", "?")
            country = artist.get("country", "Unknown")
            results.append({
                "question": f"Tell me about the music artist: {name}",
                "ai_answer": f"Artist: {name}, Country: {country}",
                "source": "musicbrainz",
                "source_url": "https://musicbrainz.org/",
                "domain": "music",
                "category": "artist",
            })
        return results
    except Exception as e:
        logger.debug(f"MusicBrainz error: {e}", exc_info=True)
        return []





