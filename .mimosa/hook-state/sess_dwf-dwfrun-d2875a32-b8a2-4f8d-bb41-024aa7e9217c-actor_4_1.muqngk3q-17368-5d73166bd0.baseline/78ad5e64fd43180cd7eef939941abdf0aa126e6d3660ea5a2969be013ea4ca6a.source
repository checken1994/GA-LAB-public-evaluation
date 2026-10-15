""" brain.py — re-exports KnowledgeStore + init_knowledge_db stub.

Previous version: 796 LOC with SCPV14Brain, LearningEngine, ReasoningEngine,
KnowledgeStore (SQLite-backed). All dead on /ask path — only brain/error_store.py
(ErrorStore) is wired into /ask (judge.py:315,330).

History:
- G3 (RE-06): replaced 796 LOC with a 27-LOC minimal stub KnowledgeStore class
  (in-memory dict) to preserve `from scp.brain.brain import KnowledgeStore`
  for engine.py:152.
- G3-meta (RE-06): replaced the in-memory stub with a re-export from
  error_store.py — error_store.py:339 already has a real JSONL-backed
  KnowledgeStore (claim + verified_answer + confidence + tags, max 10K rows,
  thread-safe, atomic appends). brain.py no longer ships a duplicate class.

engine.py:152 still imports `KnowledgeStore, init_knowledge_db` — both names
preserved. `init_knowledge_db` remains a no-op (JSONL store auto-creates its
file on first write via _read_jsonl → returns [] for missing path).
"""
# [G3-CONSOLIDATE RE-06] KnowledgeStore now re-exports from error_store.py
# (was duplicate stub created in G3 to preserve imports).
# - Canonical: scp/brain/error_store.py:339 (JSONL-backed, 10K cap, thread-safe)
# - Re-export:  scp/brain/brain.py (this file) — `from scp.brain.brain import KnowledgeStore`
# - 3rd "KnowledgeStore" class still exists:
#     scp/knowledge/domain_store.py:50 DomainKnowledgeStore (LIVE in /ask via judge.py)
#   That is a DIFFERENT class with a different schema (per-domain JSONL,
#   question + answer + source_tier + confidence) — not deduped here.
from scp.brain.error_store import KnowledgeStore  # noqa: F401 (re-export)


def init_knowledge_db(path: str = "") -> None:
    """No-op stub — JSONL KnowledgeStore auto-creates its file on first write.

    Kept for backward compat with engine.py:153 (`init_knowledge_db()`).
    Original (796-LOC) brain.py created SQLite tables here; the JSONL store
    in error_store.py needs no DDL — _read_jsonl returns [] for missing path.
    """
    pass
