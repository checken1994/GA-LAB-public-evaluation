"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

 Real Question Fetcher — 100% câu hỏi THẬT từ 12+ nguồn web đa lĩnh vực.

[Task 9-B] Refactored: fetch_* functions extracted to core/question_fetchers/
subpackage. This file re-exports them for backward compatibility (external
code can still `from scp.core.real_question_fetcher import fetch_wikipedia_random`).

Public API:
  - RealQuestionFetcher (main class)
  - All fetch_* functions (re-exported from question_fetchers)
  - init_external_questions_db, _http_get_json, _clean, etc. (re-exported)
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# [Task 9-B] All shared helpers + fetcher functions extracted to question_fetchers/
# Re-export for backward compatibility.
from scp.core.question_fetchers._common import (
    _DB_AVAILABLE,
    _MAX_CONSECUTIVE_FAILURES,
    _SOURCE_HEALTH,
    _SOURCE_HEALTH_LOCK,
    init_external_questions_db,
)

# [hygiene F821-fix] logger định nghĩa trước khối try bên dưới: nhánh except
# ImportError gọi logger.debug — trước đây logger nằm dưới nên db_manager thiếu
# sẽ bị NameError(logger) che mất trong chính except handler.
logger = logging.getLogger(__name__)

# init_db + db helpers needed by RealQuestionFetcher class methods
try:
    from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db
except ImportError as exc:
    # silent-by-design: db helpers are optional at import; callers handle None helpers.
    logger.debug("db helpers unavailable for RealQuestionFetcher: %s", exc, exc_info=True)
    init_db = None
    db_exec = None
    db_query_all = None
    db_query_one = None

from datetime import datetime

from scp.core.question_fetchers.data_fetchers import (
    fetch_cocktaildb,
    fetch_coingecko,
    fetch_fruityvice,
    fetch_genderize,
    fetch_mealdb,
    fetch_nasa_apod,
    fetch_open_meteo,
    fetch_openfda,
    fetch_public_holidays,
    fetch_rest_countries,
    fetch_stackoverflow,
    fetch_sunrise_sunset,
    fetch_tv_maze,
)
from scp.core.question_fetchers.knowledge_fetchers import (
    fetch_arxiv_physics,
    fetch_bible_api,
    fetch_musicbrainz,
    fetch_open5e_spells,
    fetch_open_library,
    fetch_wikipedia_random,
)
from scp.core.question_fetchers.trivia_fetchers import (
    fetch_advice_slip,
    fetch_cat_facts,
    fetch_chuck_norris,
    fetch_dog_facts,
    fetch_official_joke,
    fetch_opentdb,
    fetch_pokemon,
    fetch_swapi,
    fetch_trivia_api,
)


class RealQuestionFetcher:
    """
    Fetch real-world questions from 15+ web APIs across many domains.

    Usage:
        fetcher = RealQuestionFetcher()
        fetcher.fetch_and_store(n=30)  # Fetch 30 real questions
        questions = fetcher.get_unused(limit=20)  # Get 20 unused
    """

    FETCHERS = [
        ("wikipedia_vi", fetch_wikipedia_random),
        ("wikipedia_en", fetch_wikipedia_random),
        ("opentdb", fetch_opentdb),
        ("trivia_api", fetch_trivia_api),
        ("nasa_apod", fetch_nasa_apod),
        ("advice_slip", fetch_advice_slip),
        ("chuck_norris", fetch_chuck_norris),
        ("official_joke", fetch_official_joke),
        ("dog_facts", fetch_dog_facts),
        ("cat_facts", fetch_cat_facts),
        ("pokemon", fetch_pokemon),
        ("swapi", fetch_swapi),
        ("mealdb", fetch_mealdb),
        ("cocktaildb", fetch_cocktaildb),
        ("fruityvice", fetch_fruityvice),
        ("rest_countries", fetch_rest_countries),
        ("open_library", fetch_open_library),
        ("sunrise_sunset", fetch_sunrise_sunset),
        ("public_holidays", fetch_public_holidays),
        ("open5e", fetch_open5e_spells),
        ("stackoverflow", fetch_stackoverflow),
        ("bible_api", fetch_bible_api),
        ("genderize", fetch_genderize),
        ("tv_maze", fetch_tv_maze),
        ("coingecko", fetch_coingecko),
        ("open_meteo", fetch_open_meteo),
        ("musicbrainz", fetch_musicbrainz),
        ("openfda", fetch_openfda),
        ("arxiv_physics", fetch_arxiv_physics),
    ]

    def __init__(self):
        if _DB_AVAILABLE:
            init_db()
            init_external_questions_db()

    def fetch_and_store(self, n: int = 30) -> dict[str, int]:
        """
        [V70→V71] Fetch N real questions from all sources IN PARALLEL, save to DB.
         Batch-capable sources (OpenTDB, Trivia, Fruityvice, etc.) get more questions per call.
        """
        #  Sources that can fetch MANY questions in 1 API call → give them more
        BATCH_SOURCES = {
            "opentdb": 200,        # [V93.1] 50/call × 4
            "trivia_api": 200,     # [V93.1] 50/call × 4
            "fruityvice": 100,     # [V93.1] sample 100
            "open5e": 100,         # [V93.1] sample 100
            "public_holidays": 50, # [V93.1] 50 countries
            "stackoverflow": 200,  # [V93.1] pagesize=100 × 2
            "wikipedia_vi": 200,   # [V93.1] 50 articles × 4
            "wikipedia_en": 200,   # [V93.1] 50 articles × 4
            "mealdb": 100,         # [V93.1] 100 meals
            "cocktaildb": 100,     # [V93.1] 100 cocktails
            "pokemon": 100,        # [V93.1] 100 pokemon
            "rest_countries": 100, # [V93.1] 100 countries
            "open_library": 200,   # [V93.1] 200 books
            "bible_api": 100,      # [V93.1] 100 verses
            "tv_maze": 100,        # [V93.1] 100 shows
            "swapi": 100,          # [V93.1] 100 SW entities
            "coingecko": 100,      # [V93.1] 100 crypto
            "open_meteo": 50,      # [V93.1] 50 cities
            "musicbrainz": 100,    # [V93.1] 100 artists
            "openfda": 50,         # [V93.1] 50 drug records
            "arxiv_physics": 50,   # [V93.1] 50 papers
        }

        # Default per_source for non-batch sources
        default_per_source = max(50, n // len(self.FETCHERS) * 2)  # [V93.1] balanced
        all_questions: list[dict] = []
        all_start = time.time()

        #  Filter out sources that have failed 3+ times in a row
        active_sources = []
        for source_name, fetcher_fn in self.FETCHERS:
            # [ROOT-FIX 3] Lock-protected read — _SOURCE_HEALTH is mutated by
            # ThreadPoolExecutor workers below (and by fetch_nasa_apod above).
            with _SOURCE_HEALTH_LOCK:
                fails = _SOURCE_HEALTH.get(source_name, 0)
            if fails >= _MAX_CONSECUTIVE_FAILURES:
                logger.info(f"  {source_name}: SKIPPED (failed {fails}x in a row)")
                continue
            per_source = BATCH_SOURCES.get(source_name, default_per_source)
            active_sources.append((source_name, fetcher_fn, per_source))

        #  Parallel fetch with ThreadPoolExecutor
        def _fetch_one(source_name, fetcher_fn, per_source):
            try:
                if source_name == "wikipedia_vi":
                    qs = fetcher_fn("vi", per_source)
                elif source_name == "wikipedia_en":
                    qs = fetcher_fn("en", per_source)
                else:
                    qs = fetcher_fn(per_source)
                # Reset failure counter on success
                # [ROOT-FIX 3] Lock-protected write — runs inside ThreadPoolExecutor
                # worker; without the lock, concurrent resets + increments race
                # (lost update → counter never decrements → permanent MAX_CONSECUTIVE_FAILURES block).
                with _SOURCE_HEALTH_LOCK:
                    _SOURCE_HEALTH[source_name] = 0
                return source_name, qs, None
            except Exception as e:
                logger.debug(f"_fetch_one ignored: {e}", exc_info=True)
                # Increment failure counter
                # [ROOT-FIX 3] Lock-protected read-modify-write (same reason as above).
                with _SOURCE_HEALTH_LOCK:
                    _SOURCE_HEALTH[source_name] = _SOURCE_HEALTH.get(source_name, 0) + 1
                return source_name, [], e

        # Run up to 8 fetchers in parallel
        with ThreadPoolExecutor(max_workers=32) as executor:  # [V93 BOOST] 32 parallel fetch workers
            futures = [
                executor.submit(_fetch_one, name, fn, ps)
                for name, fn, ps in active_sources
            ]
            #  Increased timeout from 30s → 120s to handle interval=2000+
            # (each source may need to make 50-100 API calls sequentially within itself)
            # Don't raise on timeout — just skip slow sources
            done_futures = []
            try:
                for future in as_completed(futures, timeout=30):  # [V88 BOOST] 20s (was 120s)
                    done_futures.append(future)
                    try:
                        source_name, qs, err = future.result(timeout=10)  #  per-future timeout
                        if err:
                            logger.warning(f"  {source_name}: FAILED - {err}")
                        else:
                            all_questions.extend(qs)
                            logger.info(f"  {source_name}: {len(qs)} fetched")
                    except Exception as e:
                        logger.warning(f"  Source future error: {e}", exc_info=True)
            except TimeoutError:
                # Some sources timed out — log and continue with what we have
                timed_out = [f for f in futures if f not in done_futures]
                logger.warning(f"   {len(timed_out)} sources timed out after 120s — continuing with {len(all_questions)} questions")
                # Cancel pending futures
                for f in timed_out:
                    f.cancel()

        fetch_elapsed = time.time() - all_start
        logger.info(f" Parallel fetch: {len(all_questions)} questions in {fetch_elapsed:.1f}s "
                    f"from {len(active_sources)}/{len(self.FETCHERS)} sources")

        # Store to DB
        stored = 0
        by_source: dict[str, int] = {}
        if _DB_AVAILABLE:
            now = datetime.now().astimezone().isoformat()
            for q in all_questions:
                try:
                    db_exec(
                        "INSERT OR IGNORE INTO external_questions "
                        "(question, ai_answer, source, source_url, domain, category, fetched_at, used) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                        (q["question"][:500], q.get("ai_answer", "")[:500],
                         q.get("source", "unknown"), q.get("source_url", ""),
                         q.get("domain", "unknown"), q.get("category", ""),
                         now)
                    )
                    row = db_query_one(
                        "SELECT id, used FROM external_questions WHERE question=?",
                        (q["question"][:500],)
                    )
                    if row and row.get("used") == 0:
                        stored += 1
                        src_name = q.get("source", "unknown")
                        by_source[src_name] = by_source.get(src_name, 0) + 1
                except Exception as e:
                    logger.debug(f"DB insert error: {e}", exc_info=True)

        logger.info(f"RealQuestionFetcher: fetched {len(all_questions)} in {fetch_elapsed:.1f}s, "
                    f"stored {stored} new | by_source={by_source}")
        return by_source

    def get_unused(self, limit: int = 10) -> list[dict]:
        """Get N unused real questions from DB, mark as used."""
        if not _DB_AVAILABLE:
            return []
        # [Mimosa residual 2026-09-30] `limit` là giá trị do caller điều khiển
        # và bị bind vào params tuple của db_query_all bên dưới. SQL đã
        # parameterized nên không có injection, nhưng giá trị này phải được
        # validate tại ranh giới trước khi chạm DB layer: ép kiểu int + clamp
        # [1, 100] để LIMIT chắc chắn là số nguyên dương có chặn trên (SQLite
        # coi LIMIT âm là "unlimited" — clamp loại bỏ footgun đó thay vì giữ
        # hành vi không giới hạn). Tham số cũng đổi tên n → limit để không
        # trùng tên với biến argv-derived `n` ở CLI main() — trước đây scanner
        # ghép chúng thành một taint "command-line argument" giả.
        limit = max(1, min(int(limit), 100))
        now = datetime.now().astimezone().isoformat()
        rows = db_query_all(
            "SELECT id, question, ai_answer, source, source_url, domain, category "
            "FROM external_questions WHERE used = 0 "
            "ORDER BY fetched_at DESC LIMIT ?",
            (limit,)
        )
        for r in rows:
            db_exec(
                "UPDATE external_questions SET used=1, used_at=? WHERE id=?",
                (now, r["id"])
            )
        return rows

    def get_stats(self) -> dict:
        """Get fetcher statistics."""
        if not _DB_AVAILABLE:
            return {"error": "DB not available"}
        total = db_query_one("SELECT COUNT(*) as cnt FROM external_questions")
        unused = db_query_one("SELECT COUNT(*) as cnt FROM external_questions WHERE used = 0")
        by_source_rows = db_query_all(
            "SELECT source, COUNT(*) as cnt FROM external_questions GROUP BY source"
        )
        by_domain_rows = db_query_all(
            "SELECT domain, COUNT(*) as cnt FROM external_questions GROUP BY domain"
        )
        return {
            "total_fetched": total["cnt"] if total else 0,
            "unused": unused["cnt"] if unused else 0,
            "by_source": {r["source"]: r["cnt"] for r in by_source_rows},
            "by_domain": {r["domain"]: r["cnt"] for r in by_domain_rows},
        }


# ============================================================
# CLI
# ============================================================
def main():
    """CLI: test fetcher."""
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"\n{'='*70}\n  V67 RealQuestionFetcher — Test {n} Questions from 24 sources\n{'='*70}\n")
    fetcher = RealQuestionFetcher()
    by_source = fetcher.fetch_and_store(n)
    print(f"\n  Stored by source: {by_source}")
    qs = fetcher.get_unused(10)
    print(f"\n  Sample {len(qs)} unused questions:")
    for i, q in enumerate(qs, 1):
        print(f"\n  [{i}] {q['source']} | {q['domain']}")
        print(f"      Q: {q['question'][:100]}")
        print(f"      A: {q.get('ai_answer', '')[:100]}")
    stats = fetcher.get_stats()
    print(f"\n  Stats: {stats}")


if __name__ == "__main__":
    main()
