"""
[G3-MERGE] scp/core/real_learning_engine.py — DEPRECATED COMPATIBILITY STUB
============================================================================

This file has been merged into `scp/core/fast_learning_engine.py` (Task G3-full-A).

WHY THE MERGE:
- pre-merge: real_learning_engine.py (832 LOC) and fast_learning_engine.py (849 LOC)
  ran in PARALLEL as two background threads (see scp/api_server_parts/helpers.py:437+444).
  Both threads wrote to the SAME KB file (`data/v13.db`) → race condition
  (interleaved SQLite writes + duplicated Ollama API calls — Task 2-B finding P1-04).
- ~85% of method bodies were duplicated (`_store_kb`, `_verify_learned_fact`,
  `_audit_v91`, `_check_wikipedia`, `_init_kb`, etc.).
- Fix #8c (asymmetry -0.2 → 0.0, DNA #8 KB accumulation) was NEVER applied
  to either file (Task 2-B confirmed; re-confirmed at audit Task G3-full-A).
- Net: 2 engines → 1, race eliminated, ~830 LOC of duplication removed.

WHAT THIS STUB DOES:
- Re-exports `FastLearningEngine` as `RealLearningEngine` so that existing
  imports (`from scp.core.real_learning_engine import RealLearningEngine`)
  continue to work without code changes.
- Re-exports all module-level constants and helper functions that were
  originally defined here (SEED_QUESTIONS, COUNTRIES, DOMAINS, COMPOUNDS,
  COUNTRY_DOMAIN_HINTS,
  NEWS_SOURCES, LEARNING_INTERVAL, get_country_domain_matrix,
  get_total_combinations, start_learning_thread).
- `start_learning_thread` is now an alias for `start_fast_learning_thread`
  (idempotent — calling both names starts only ONE thread, eliminating the
  race). See fast_learning_engine.py:start_learning_thread for full rationale.

WHAT WAS LOST (intentionally):
- The V104.1 sequential 1-hour background thread. The fast engine's adaptive
  interval (1-30 min) supersedes it. On-demand sequential learning is still
  available via the `/v104/learn/all` endpoint → `FastLearningEngine.run_all_cycles()`.

NO NEW CODE SHOULD IMPORT FROM THIS FILE. Import from `scp.core.fast_learning_engine`
directly. This stub exists only to preserve backward compatibility with
existing imports in `scp/api_server.py:119`, `scp/api_server_parts/helpers.py:74`,
and `scp/api/routes/v104_routes.py:233`.
"""
from __future__ import annotations

# [G3-MERGE] Single source of truth — re-export everything callers expect.
from scp.core.fast_learning_engine import (
    # Module constants (ported from real_learning_engine during merge)
    COMPOUNDS,
    COUNTRIES,
    COUNTRY_DOMAIN_HINTS,
    DOMAINS,
    LEARNING_INTERVAL,
    NEWS_SOURCES,
    SEED_QUESTIONS,
    # Helper functions (ported)
    FastLearningEngine,
    get_country_domain_matrix,
    get_total_combinations,
    # Background thread starters — start_learning_thread is now an alias
    # for start_fast_learning_thread (idempotent, prevents race condition).
    # Both names are re-exported so callers can use either.
    start_fast_learning_thread,
)
from scp.core.fast_learning_engine import (
    start_fast_learning_thread as start_learning_thread,
)

# [G3-MERGE] Class alias — RealLearningEngine IS FastLearningEngine.
# All V104.1 methods (ollama_learning_cycle, local_learning_cycle,
# news_learning_cycle, run_all_cycles, _ask_llm, _check_wikipedia,
# _extract_facts, _fetch_rss_headlines) have been ported onto FastLearningEngine.
RealLearningEngine = FastLearningEngine

# Logger kept for backward compat (some callers may have imported it).
import logging  # noqa: E402

logger = logging.getLogger("scp.core.real_learning_engine")

__all__ = [
    # Class
    "RealLearningEngine",
    "FastLearningEngine",
    # Constants
    "COMPOUNDS",
    "COUNTRIES",
    "COUNTRY_DOMAIN_HINTS",
    "DOMAINS",
    "LEARNING_INTERVAL",
    "NEWS_SOURCES",
    "SEED_QUESTIONS",
    # Helpers
    "get_country_domain_matrix",
    "get_total_combinations",
    # Thread starters
    "start_learning_thread",
    "start_fast_learning_thread",
]
