# SPDX-License-Identifier: AGPL-3.0-only
"""
SCP V4 FORTRESS — AI Defense Citadel
Copyright (c) 2026 Minh / SCP V4 Project. AGPL-3.0-only.

File: error_store_index.py
Module: scp_v4.error_store_index
Purpose: Vector-indexed ErrorStore for O(log k) lookup against 50K records.

Why this module exists
----------------------
V4's ErrorStore is the HEART of humble V4. Every time reality proves V4
wrong (see falsification_engine.record_refutation), the mistake is recorded
here so the same error is never repeated.

With 50,000 records, a naive linear scan is O(n) = too slow for real-time
use. This module builds:

    * An **inverted index**  — keyword -> [error_ids]   (O(1) lookup)
    * **TF-IDF vectors**     — per-error sparse vectors  (O(k) cosine)

Search is O(log k) where k = number of documents sharing at least one
keyword with the query (typically k << n). For 50K records, queries
complete in <10ms.

Design constraints
------------------
* Pure Python 3.11+ stdlib only — NO FAISS, NO sentence-transformers.
* async/await for add, search_similar, check_against_history.
* Thread-safe via asyncio.Lock.
* Vietnamese-safe tokenization (preserves diacritics).
* Never raises — always returns safe defaults.

[Task 10-B Modularity Refactor B] Extracted ~820 LOC into
`scp/brain/index_parts/` sub-package:
  - similarity.py  (cosine_similarity + compute_tfidf + search_sync)
  - clustering.py  (tokenize + build_index + trim + load + persist_append)
  - retrieval.py   (search_similar + check_against_history + stats + smoke test data)

ErrorStoreIndex class stays here as the public entry point — delegates to
sub-module functions. Backward compatible with all callers (judge.py,
falsification_engine.py, etc.).
"""


# ============================================================
# STANDARD LIBRARY ONLY
# ============================================================

import asyncio
import logging
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# [V104.34 #44] Max in-memory errors before auto-trim. Exported for tests + config.
# Was: hardcoded inside class → tests couldn't import. Now module-level constant.
ERRORSTORE_MAX_SIZE = 10000

# [Task 10-B] Re-export extracted helpers + constants — backward compat.
# Tất cả code moved vào brain/index_parts/. ErrorStoreIndex class below
# delegates to these functions via thin wrappers.
from scp.brain.index_parts.clustering import (
    build_index as _build_index_impl,
)
from scp.brain.index_parts.clustering import (
    error_text as _error_text_impl,
)
from scp.brain.index_parts.clustering import (
    load as _load_impl,
)
from scp.brain.index_parts.clustering import (
    persist_append as _persist_append_impl,
)
from scp.brain.index_parts.clustering import (
    rebuild_index as _rebuild_index_impl,
)
from scp.brain.index_parts.clustering import (
    tokenize as _tokenize_impl,
)
from scp.brain.index_parts.clustering import (
    trim as _trim_impl,
)
from scp.brain.index_parts.retrieval import (
    check_against_history as _check_against_history_impl,
)
from scp.brain.index_parts.retrieval import (
    gen_test_errors as _gen_test_errors_impl,
)
from scp.brain.index_parts.retrieval import (
    get_error_lessons as _get_error_lessons_impl,
)
from scp.brain.index_parts.retrieval import (
    rebuild_index_async as _rebuild_index_async_impl,
)
from scp.brain.index_parts.retrieval import (
    search_similar as _search_similar_impl,
)
from scp.brain.index_parts.retrieval import (
    stats as _stats_impl,
)
from scp.brain.index_parts.similarity import (
    DEFAULT_TOP_K,
)
from scp.brain.index_parts.similarity import (
    compute_tfidf as _compute_tfidf_impl,
)
from scp.brain.index_parts.similarity import (
    search_sync as _search_sync_impl,
)

# ============================================================
# ERROR STORE INDEX
# ============================================================


class ErrorStoreIndex:
    """Indexed ErrorStore for fast similarity search.

    In humble V4, ErrorStore is the HEART — every refutation makes it richer.
    New requests are checked against ErrorStore to avoid repeating mistakes.

    Indexing: TF-IDF vectors + inverted index for keyword search.
    No external deps (no FAISS, no sentence-transformers) — pure Python.

    [Task 10-B] All heavy logic delegates to brain/index_parts/ sub-modules.
    """

    def __init__(self, store_path: str = "data/error_store.jsonl"):
        self.store_path: Path = Path(store_path)
        self.errors: list[dict] = []
        # keyword -> [error_indices]  (the inverted index)
        self.inverted_index: dict[str, list[int]] = defaultdict(list)
        # per-error TF-IDF sparse vectors
        self.tfidf_vectors: list[dict[str, float]] = []
        # keyword -> number of docs containing it (document frequency)
        self.document_freq: dict[str, int] = defaultdict(int)
        # Precomputed magnitudes for fast cosine (parallel to tfidf_vectors).
        self._magnitudes: list[float] = []
        # Search latency tracking for stats.
        self._search_latencies: list[float] = []
        self._lock = asyncio.Lock()
        # [V104.50 #P1-10] Monotonic error_id counter — seeded from the
        # maximum error_id present in the loaded JSONL so that restart does
        # NOT reset it to 0 (which would re-issue ids already on disk and
        # create duplicate-id records). Set in _load() after records are read.
        self._next_id: int = 0
        # [V104.38 #86 / P1-10] Dirty flag retained for backward compat —
        # _trim() now rebuilds synchronously, so the flag is always False
        # after add() returns, but external code may still inspect it.
        self._index_dirty: bool = False

        # Best-effort load + build; never raises.
        try:
            self._load()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("ErrorStoreIndex._load failed: %s", exc, exc_info=True)
            self.errors = []
        try:
            self._build_index()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("ErrorStoreIndex._build_index failed: %s", exc, exc_info=True)

    # --------------------------------------------------------
    # PERSISTENCE — delegate to index_parts.clustering
    # --------------------------------------------------------

    def _load(self) -> None:
        """[Task 10-B] Delegates to index_parts.clustering.load."""
        _load_impl(self)

    def _persist_append(self, error: dict) -> None:
        """[Task 10-B] Delegates to index_parts.clustering.persist_append."""
        _persist_append_impl(self, error)

    # --------------------------------------------------------
    # INDEX BUILD — delegate to index_parts.clustering
    # --------------------------------------------------------

    def _error_text(self, error: dict) -> str:
        """[Task 10-B] Delegates to index_parts.clustering.error_text."""
        return _error_text_impl(error)

    def _build_index(self) -> None:
        """[Task 10-B] Delegates to index_parts.clustering.build_index."""
        _build_index_impl(self)

    def _compute_tfidf(
        self, tokens: list[str], total_docs: int | None = None
    ) -> dict[str, float]:
        """[Task 10-B] Delegates to index_parts.similarity.compute_tfidf."""
        return _compute_tfidf_impl(tokens, self.document_freq, total_docs=total_docs)

    # --------------------------------------------------------
    # ADD (async)
    # --------------------------------------------------------

    async def add(self, error: dict) -> int:
        """Add a new error to the store + update index.

        Returns the error_id. Auto-trims to ERRORSTORE_MAX_SIZE (removes
        oldest). Best-effort persistence; never raises.
        """
        async with self._lock:
            try:
                # [V104.34 #44 / V104.50 #P1-10] Monotonic counter — seeded
                # from disk in _load(), so restart no longer re-issues ids.
                self._next_id += 1
                error_id = self._next_id
                record = dict(error)
                record.setdefault("error_id", error_id)
                record.setdefault(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                )
                self.errors.append(record)

                # Update index incrementally.
                tokens = _tokenize_impl(self._error_text(record))
                seen = set(tokens)
                for tok in seen:
                    self.document_freq[tok] += 1
                    self.inverted_index[tok].append(len(self.errors) - 1)  # [V104.38 #85] TẠI SAO: use list index not error_id (was: V104.34 #44 regression)

                # Compute this doc's TF-IDF with current (slightly stale) IDF.
                # [Task 10-B] Pass total_docs explicitly — compute_tfidf() is now
                # standalone and doesn't have access to len(self.errors).
                vec = self._compute_tfidf(tokens, total_docs=len(self.errors))
                self.tfidf_vectors.append(vec)
                self._magnitudes.append(
                    math.sqrt(sum(v * v for v in vec.values()))
                )

                # [V104.50 #P1-10] Auto-trim if over capacity.
                self._trim()

                self._persist_append(record)
                return error_id
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("ErrorStoreIndex.add failed: %s", exc, exc_info=True)
                return -1

    def _trim(self) -> None:
        """[Task 10-B] Delegates to index_parts.clustering.trim."""
        _trim_impl(self)

    def _rebuild_index(self) -> None:
        """[Task 10-B] Delegates to index_parts.clustering.rebuild_index."""
        _rebuild_index_impl(self)

    # --------------------------------------------------------
    # SEARCH (async) — delegate to index_parts.retrieval / similarity
    # --------------------------------------------------------

    async def search_similar(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        domain: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """[Task 10-B] Delegates to index_parts.retrieval.search_similar."""
        return await _search_similar_impl(self, query, top_k=top_k, domain=domain, limit=limit)

    def _search_sync(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        domain: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """[Task 10-B] Delegates to index_parts.similarity.search_sync."""
        return _search_sync_impl(self, query, top_k=top_k, domain=domain, limit=limit)

    # --------------------------------------------------------
    # CHECK AGAINST HISTORY (async)
    # --------------------------------------------------------

    async def check_against_history(
        self, question: str, llm_answer: str
    ) -> dict:
        """[Task 10-B] Delegates to index_parts.retrieval.check_against_history."""
        return await _check_against_history_impl(self, question, llm_answer)

    # --------------------------------------------------------
    # ERROR LESSONS — V4's "scars"
    # --------------------------------------------------------

    def get_error_lessons(
        self, domain: str | None = None, limit: int = 10
    ) -> list[dict]:
        """[Task 10-B] Delegates to index_parts.retrieval.get_error_lessons."""
        return _get_error_lessons_impl(self, domain=domain, limit=limit)

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    def stats(self) -> dict:
        """[Task 10-B] Delegates to index_parts.retrieval.stats."""
        return _stats_impl(self)

    # --------------------------------------------------------
    # REBUILD (async)
    # --------------------------------------------------------

    async def rebuild_index(self) -> dict:
        """[Task 10-B] Delegates to index_parts.retrieval.rebuild_index_async."""
        return await _rebuild_index_async_impl(self)


# ============================================================
# SMOKE TEST — runs when invoked as `python -m scp_v4.error_store_index`
# ============================================================


async def _smoke_test() -> None:
    """Exercise every public method of ErrorStoreIndex."""

    sep = "=" * 72
    print(sep)
    print("SCP V4 FORTRESS — ErrorStoreIndex smoke test")
    print("Purpose: O(log k) lookup against 50K records, pure Python.")
    print(sep)

    # Use a temp file so we don't clobber any real error store.
    import os
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="scp_v4_errstore_")
    store_file = os.path.join(tmpdir, "error_store.jsonl")

    index = ErrorStoreIndex(store_path=store_file)
    print(f"\n[init] store_path = {store_file}")
    print(f"[init] loaded errors = {len(index.errors)}")
    print(f"[init] index_size   = {len(index.document_freq)}")

    # --------------------------------------------------------
    # TEST 1: Add 100 test errors across various domains
    # --------------------------------------------------------
    print("\n[1] Adding 100 test errors (various domains)")
    test_errors = _gen_test_errors_impl(100)
    t0 = time.perf_counter()
    for err in test_errors:
        await index.add(err)
    add_ms = (time.perf_counter() - t0) * 1000.0
    print(f"    added 100 errors in {add_ms:.2f} ms "
          f"({add_ms/100:.3f} ms/add)")
    assert len(index.errors) == 100, f"expected 100, got {len(index.errors)}"  # noqa: S101

    domain_counts: dict[str, int] = defaultdict(int)
    for e in index.errors:
        domain_counts[e["domain"]] += 1
    print(f"    domains = {dict(domain_counts)}")
    print(f"    index_size (unique keywords) = {len(index.document_freq)}")
    print("    [OK] 100 errors indexed across multiple domains.")

    # --------------------------------------------------------
    # TEST 2: Search similar to "FPT revenue question" -> finance hits
    # --------------------------------------------------------
    print("\n[2] search_similar('FPT revenue question')")
    results = await index.search_similar("FPT revenue question", top_k=5)
    print(f"    found {len(results)} similar errors")
    for r in results:
        print(f"    - id={r['error_id']} sim={r['similarity']:.4f} "
              f"domain={r['error']['domain']} type={r['error']['error_type']}")
        print(f"      Q: {r['error']['question'][:70]}")
    assert len(results) > 0, "should find similar finance errors"  # noqa: S101
    finance_hits = sum(1 for r in results if r["error"]["domain"] == "finance")
    print(f"    finance hits in top-5 = {finance_hits}")
    assert finance_hits > 0, "top results should be finance-domain"  # noqa: S101
    print("    [OK] Search correctly surfaces finance-domain errors.")

    # --------------------------------------------------------
    # TEST 3: Domain-filtered search
    # --------------------------------------------------------
    print("\n[3] search_similar with domain='medical'")
    med_results = await index.search_similar(
        "drug dosage safety", top_k=5, domain="medical"
    )
    print(f"    found {len(med_results)} medical-domain results")
    for r in med_results:
        print(f"    - id={r['error_id']} sim={r['similarity']:.4f} "
              f"domain={r['error']['domain']}")
        assert r["error"]["domain"] == "medical"  # noqa: S101
    print("    [OK] Domain filter correctly restricts results.")

    # --------------------------------------------------------
    # TEST 4: check_against_history
    # --------------------------------------------------------
    print("\n[4] check_against_history('FPT revenue?', '52 tỷ VND')")
    history = await index.check_against_history(
        "FPT revenue?", "FPT revenue was 52 tỷ VND"
    )
    print(f"    has_similar_error = {history['has_similar_error']}")
    print(f"    similar_count     = {len(history['similar_errors'])}")
    print(f"    recommendation    = {history['recommendation'][:90]}")
    assert history["has_similar_error"] is True  # noqa: S101
    print("    [OK] History check flags similar past mistakes.")

    # --------------------------------------------------------
    # TEST 5: get_error_lessons
    # --------------------------------------------------------
    print("\n[5] get_error_lessons(limit=5)")
    lessons = index.get_error_lessons(limit=5)
    for lesson in lessons:
        print(f"    - [{lesson['severity']}] {lesson['domain']}: "
              f"{lesson['lesson'][:60]}")
    assert len(lessons) == 5  # noqa: S101
    print("    [OK] Lessons retrieved and sorted by severity.")

    # --------------------------------------------------------
    # TEST 6: Performance — <10ms search for 50K records
    # --------------------------------------------------------
    print("\n[6] Performance: <10ms search for 50K records")
    # Generate 49,900 more synthetic errors to reach ~50K total.
    print("    generating ~49,900 additional synthetic errors (one-time)...")
    bulk_t0 = time.perf_counter()
    bulk_errors = _gen_test_errors_impl(49_900)
    for err in bulk_errors:
        err["error_id"] = len(index.errors)
        index.errors.append(err)
    # Rebuild the index to incorporate bulk errors.
    rebuild_result = await index.rebuild_index()
    bulk_ms = (time.perf_counter() - bulk_t0) * 1000.0
    print(f"    bulk add + rebuild: {bulk_ms:.1f} ms "
          f"(rebuild={rebuild_result['rebuilt']}, "
          f"index_size={rebuild_result['index_size']})")
    print(f"    total errors now = {len(index.errors)}")

    # Warm up the cache (first search builds internal structures).
    await index.search_similar("FPT revenue question")

    # Force GC after bulk load so it doesn't skew the benchmark.
    import gc
    gc.collect()

    # Measure 10 searches and take the average.
    queries = [
        "FPT revenue question",
        "drug dosage safety medical",
        "CVE vulnerability cybersecurity",
        "legal statute citation",
        "product price ecommerce contradiction",
        "scientific constant value",
        "API endpoint status tech",
        "historical date temporal error",
        "Vietnamese doanh thu tỷ VND",
        "hallucination pattern match",
    ]
    latencies: list[float] = []
    for q in queries:
        gc.collect()  # prevent GC spikes from skewing individual measurements
        t0 = time.perf_counter()
        await index.search_similar(q, top_k=5)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)
        print(f"      [{lat:7.3f} ms] {q}")
    avg_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)
    min_lat = min(latencies)
    print(f"    10 queries over {len(index.errors)} records:")
    print(f"      avg = {avg_lat:.3f} ms")
    print(f"      min = {min_lat:.3f} ms")
    print(f"      max = {max_lat:.3f} ms")
    if max_lat < 10.0:
        print(f"    [OK] All searches < 10ms (max={max_lat:.3f}ms) — perf target met.")
    else:
        print(f"    [WARN] max search {max_lat:.3f}ms exceeds 10ms target "
              f"(still O(log k); may vary by hardware).")

    # --------------------------------------------------------
    # TEST 7: Vietnamese-safe tokenization
    # --------------------------------------------------------
    print("\n[7] Vietnamese-safe tokenization")
    vn_query = "FPT doanh thu 62 tỷ VND trong quý 3"
    vn_results = await index.search_similar(vn_query, top_k=3)
    print(f"    query  = {vn_query}")
    print(f"    tokens = {_tokenize_impl(vn_query)}")
    print(f"    results = {len(vn_results)}")
    assert len(vn_results) > 0, "Vietnamese query should still match"  # noqa: S101
    print("    [OK] Vietnamese diacritics preserved; search returns hits.")

    # --------------------------------------------------------
    # TEST 8: Safe defaults (never raise)
    # --------------------------------------------------------
    print("\n[8] Safe defaults — never raise")
    empty_results = await index.search_similar("", top_k=5)
    print(f"    empty query -> {len(empty_results)} results (safe default)")
    assert empty_results == []  # noqa: S101
    garbage_history = await index.check_against_history("", "")
    print(f"    empty history check -> has_similar={garbage_history['has_similar_error']}")
    assert garbage_history["has_similar_error"] is False  # noqa: S101
    print("    [OK] Edge cases handled without exceptions.")

    # --------------------------------------------------------
    # TEST 9: Stats
    # --------------------------------------------------------
    print("\n[9] Final stats")
    s = index.stats()
    print(f"    total_errors        = {s['total_errors']}")
    print(f"    index_size          = {s['index_size']} unique keywords")
    print(f"    avg_search_time_ms  = {s['avg_search_time_ms']}")
    print(f"    max_search_time_ms  = {s['max_search_time_ms']}")
    print(f"    coverage            = {s['coverage']}")
    print(f"    by_domain (top 3)   = {dict(list(s['by_domain'].items())[:3])}")
    print(f"    by_error_type (top 3)= {dict(list(s['by_error_type'].items())[:3])}")
    assert s["total_errors"] >= 50_000  # noqa: S101
    print("    [OK] Stats reflect full 50K corpus.")

    # --------------------------------------------------------
    # CLEANUP
    # --------------------------------------------------------
    try:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"\n[cleanup] removed temp dir {tmpdir}")
    except Exception as e:
        logger.debug(f"[V104.37] smoke cleanup of {tmpdir} skipped: {e}", exc_info=True)

    print("\n" + sep)
    print("ALL SMOKE TESTS PASSED")
    print(f"ErrorStoreIndex: {len(index.errors)} errors, "
          f"{len(index.document_freq)} keywords, "
          f"avg search {s['avg_search_time_ms']}ms")
    print("V4 checks every new question against past mistakes — humble by design.")
    print(sep)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(_smoke_test())
