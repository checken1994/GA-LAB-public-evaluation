"""
[Task 8-A] Question fetcher module — extracted from real_question_fetcher.py

TẠI SAO: real_question_fetcher.py god file. Tách fetcher functions vào module
này. Backward-compatible — real_question_fetcher.py re-exports all fetchers.
"""
from __future__ import annotations

import html
import logging
import random

from scp.core.question_fetchers._common import (
    _clean,
    _http_get_json,
    _map_opentdb_category,
)

# [hygiene F821-fix] các nhánh except trong fetcher dùng logger.debug nhưng
# module trước đây KHÔNG định nghĩa logger → NameError trong except handler
# thay vì skip item như thiết kế ("silent-by-design" per-item skip).
logger = logging.getLogger(__name__)

# [B311-fix 2026-09-30] RNG cho stochastic sampling phi mật mã: chọn Pokemon
# ngẫu nhiên và chọn endpoint/ID ngẫu nhiên khi query SWAPI. KHÔNG có mục đích
# bảo mật — đoán trước mục được chọn không gây hại. Dùng instance SystemRandom
# RIÊNG ở module level (pattern: scp/security/gcg_attack.py `_GCG_RNG`) thay
# cho global RNG để tách biệt với mọi lời random.seed() của module khác;
# range/semantics của choice()/randint() giữ nguyên (behavior-preserving).
_TRIVIA_RNG = random.SystemRandom()


def fetch_opentdb(n: int = 5) -> list[dict]:
    """Open Trivia DB — multi-category Q&A."""
    results = []
    url = f"https://opentdb.com/api.php?amount={min(n, 50)}&type=multiple"  # [V92 MAX] OpenTDB max 50/call
    data = _http_get_json(url)
    if not data or data.get("response_code") != 0:
        return results
    for item in data.get("results", []):
        try:
            question = html.unescape(item.get("question", ""))
            correct = html.unescape(item.get("correct_answer", ""))
            category = item.get("category", "")
            if not question or not correct:
                continue
            results.append({
                "question": question,
                "ai_answer": correct,
                "source": "opentdb",
                "source_url": "https://opentdb.com/",
                "domain": _map_opentdb_category(category),
                "category": category,
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("trivia_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_trivia_api(n: int = 5) -> list[dict]:
    """The Trivia API — alternative to OpenTDB."""
    results = []
    url = f"https://the-trivia-api.com/api/questions?limit={min(n, 50)}"  # [V92 MAX] cap 50/call
    data = _http_get_json(url)
    if not isinstance(data, list):
        return results
    for item in data:
        try:
            question = item.get("question", "")
            correct = item.get("correctAnswer", "")
            category = item.get("category", "")
            if not question or not correct:
                continue
            results.append({
                "question": question,
                "ai_answer": _clean(correct, 300),
                "source": "trivia_api",
                "source_url": "https://the-trivia-api.com/",
                "domain": _map_opentdb_category(category),
                "category": category,
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("trivia_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_advice_slip(n: int = 3) -> list[dict]:
    """Advice Slip API — random advice."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://api.adviceslip.com/advice")
        if not data or not data.get("slip"):
            continue
        advice = data["slip"].get("advice", "")
        if not advice:
            continue
        results.append({
            "question": "What is a piece of useful life advice?",
            "ai_answer": _clean(advice, 300),
            "source": "advice_slip",
            "source_url": "https://api.adviceslip.com/",
            "domain": "general",
            "category": "advice",
        })
    return results





def fetch_chuck_norris(n: int = 3) -> list[dict]:
    """Chuck Norris jokes."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://api.chucknorris.io/jokes/random")
        if not data:
            continue
        joke = data.get("value", "")
        if not joke:
            continue
        results.append({
            "question": "Tell me a Chuck Norris fact.",
            "ai_answer": _clean(joke, 300),
            "source": "chuck_norris",
            "source_url": data.get("url", "https://api.chucknorris.io/"),
            "domain": "entertainment",
            "category": "joke",
        })
    return results





def fetch_official_joke(n: int = 3) -> list[dict]:
    """Official Joke API — has setup + punchline."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://official-joke-api.appspot.com/random_joke")
        if not data:
            continue
        setup = data.get("setup", "")
        punchline = data.get("punchline", "")
        if not setup or not punchline:
            continue
        results.append({
            "question": f"Joke setup: {setup}",
            "ai_answer": _clean(punchline, 200),
            "source": "official_joke",
            "source_url": "https://github.com/15Dkatz/official_joke_api",
            "domain": "entertainment",
            "category": "joke",
        })
    return results





def fetch_dog_facts(n: int = 3) -> list[dict]:
    """Dog Facts API."""
    results = []
    data = _http_get_json("https://dog-api.kinduff.com/api/facts?number=" + str(n))
    if not data or not data.get("facts"):
        return results
    for fact in data["facts"]:
        results.append({
            "question": "Tell me a fact about dogs.",
            "ai_answer": _clean(fact, 300),
            "source": "dog_facts",
            "source_url": "https://dog-api.kinduff.com/",
            "domain": "biology",
            "category": "dog",
        })
    return results





def fetch_cat_facts(n: int = 3) -> list[dict]:
    """Cat Facts API."""
    results = []
    for _ in range(n):
        data = _http_get_json("https://catfact.ninja/fact")
        if not data:
            continue
        fact = data.get("fact", "")
        if not fact:
            continue
        results.append({
            "question": "Tell me a fact about cats.",
            "ai_answer": _clean(fact, 300),
            "source": "cat_facts",
            "source_url": "https://catfact.ninja/",
            "domain": "biology",
            "category": "cat",
        })
    return results


# Pokemon cache
_POKEMON_CACHE: list[dict] = []





def fetch_pokemon(n: int = 5) -> list[dict]:
    """PokeAPI — random Pokemon data."""
    global _POKEMON_CACHE
    results = []
    if not _POKEMON_CACHE:
        # Cache list of first 150 Pokemon
        data = _http_get_json("https://pokeapi.co/api/v2/pokemon?limit=150")
        if data and data.get("results"):
            _POKEMON_CACHE = data["results"]
    if not _POKEMON_CACHE:
        return results
    for _ in range(n):
        try:
            p = _TRIVIA_RNG.choice(_POKEMON_CACHE)
            name = p.get("name", "")
            if not name:
                continue
            # Fetch details
            detail = _http_get_json(p["url"])
            if not detail:
                continue
            types = [t["type"]["name"] for t in detail.get("types", [])]
            height = detail.get("height", 0)
            weight = detail.get("weight", 0)
            answer = f"Pokemon {name}: type={','.join(types)}, height={height}dm, weight={weight}hg"
            results.append({
                "question": f"What type is the Pokemon {name}?",
                "ai_answer": _clean(answer, 300),
                "source": "pokemon",
                "source_url": p["url"],
                "domain": "biology",
                "category": "pokemon",
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("trivia_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





def fetch_swapi(n: int = 3) -> list[dict]:
    """Star Wars API — people, planets, starships."""
    results = []
    endpoints = ["people", "planets", "starships", "vehicles", "species"]
    for _ in range(n):
        try:
            ep = _TRIVIA_RNG.choice(endpoints)
            # Random ID 1-30 (some return 404, that's OK)
            rid = _TRIVIA_RNG.randint(1, 30)
            data = _http_get_json(f"https://swapi.dev/api/{ep}/{rid}/")
            if not data:
                continue
            name = data.get("name", data.get("title", ""))
            if not name:
                continue
            # Build fact
            facts = []
            for k in list(data.keys())[:5]:
                if k in ("name", "title", "url", "created", "edited"):
                    continue
                v = data[k]
                if isinstance(v, (str, int, float)) and v:
                    facts.append(f"{k}={v}")
            answer = f"{name}: " + ", ".join(facts[:3])
            results.append({
                "question": f"Tell me about the Star Wars {ep[:-1] if ep.endswith('s') else ep}: {name}.",
                "ai_answer": _clean(answer, 300),
                "source": "swapi",
                "source_url": f"https://swapi.dev/api/{ep}/{rid}/",
                "domain": "entertainment",
                "category": ep,
            })
        except Exception as exc:  # noqa: S112
            # silent-by-design: per-item skip in optional external ingestion; one bad item must not kill the batch.
            logger.debug("trivia_fetchers: item fetch/parse failed; skipping (non-fatal): %s", exc, exc_info=True)
            continue
    return results





