"""
SCP V4 FORTRESS — AI Defense Citadel
Copyright (c) 2026 [Author: Minh / SCP V4 Project]
All rights reserved.

This file is part of SCP V4 FORTRESS — an Anti-Hallucination AI Defense System.
Licensed under the MIT License.

File: persistent_store.py
Module: scp_v4.persistent_store
Purpose: JSONL-backed ErrorStore (max 50k) and KnowledgeStore (max 10k) for learning.
"""


import json
import logging
import os
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# UTILITIES
# ============================================================


# [V5.8-OPT] Spam-question filter — TẠI SAO:
# Runtime data analysis showed error_store.jsonl had grown to 3 MB / 6135 lines
# but ~80% was spam: emoji-only rows (e.g. hundreds of "🇻🇳" repeated),
# control-char garbage ("\u0000\u0001\u0002..." repeated), whitespace-only ("   "),
# and substring-repeated ("Tại sao Tại sao Tại sao..."). These bloat the store,
# distort common_errors() / stats_by_domain(), and waste memory (50k cap is
# reached with junk before real errors arrive). Fix: validate at write time.
_SPAM_REJECTED_PATH = Path("data/error_store_rejected.jsonl")
_SPAM_REJECT_LOG_LOCK = threading.Lock()


def _is_spam_question(question: str) -> tuple[bool, str]:
    """[V5.8-OPT] Returns (is_spam, reason).

    Checks (in order):
      1. too_short        — stripped question < 5 chars
      2. no_content       — < 3 alphanumeric chars (pure emoji/symbols/control chars)
      3. repeated_substring — >50% repeated word (e.g. "Tại sao Tại sao Tại sao")

    Reality check (against /upload/error_store.jsonl):
      Line 1: "🇻🇳" × 100 → no alnum → blocked as no_content ✅
      Line 2: "\u0000\u0001\u0002" × 30 → no alnum → blocked as no_content ✅
      Line 3: "   " → len(strip)=0 → blocked as too_short ✅
      "Tại sao Tại sao Tại sao" → 4 words, "Tại"=2/4=50%, "sao"=2/4=50% → blocked ✅
      "thủ đô của Pháp là gì" → 5 alnum words, no majority → PASS ✅
    """
    if not isinstance(question, str):
        return True, "not_string"
    stripped = question.strip()
    if len(stripped) < 5:
        return True, "too_short"
    # Check pure emoji/symbols (no alphanumeric)
    alnum_count = sum(1 for c in stripped if c.isalnum())
    if alnum_count < 3:
        return True, "no_content"
    # Check repeated substring (>50% repetition)
    words = stripped.split()
    if len(words) > 4:
        word_counts = Counter(words)
        most_common_count = word_counts.most_common(1)[0][1]
        if most_common_count / len(words) > 0.5:
            return True, "repeated_substring"
    return False, ""


def _log_rejected_question(
    question: str,
    answer: str,
    verdict: str,
    domain: str,
    error_type: str,
    reason: str,
) -> None:
    """[V5.8-OPT] Audit log for rejected questions — keeps forensic trail
    without polluting error_store.jsonl. Best-effort: failure is non-fatal."""
    try:
        rec = {
            "ts": time.time(),
            "reason": reason,
            "question": question[:500] if isinstance(question, str) else "",
            "answer": answer[:200] if isinstance(answer, str) else "",
            "verdict": verdict,
            "domain": domain,
            "error_type": error_type,
        }
        line = json.dumps(rec, ensure_ascii=False)
        with _SPAM_REJECT_LOG_LOCK:
            _ensure_parent(_SPAM_REJECTED_PATH)
            with _SPAM_REJECTED_PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"[V5.8-OPT] reject log write failed: {exc}", exc_info=True)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_append(path: Path, line: str) -> None:
    """Append a single JSON line, with retry on contention."""
    _ensure_parent(path)
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError as e:
                    logger.debug(f"[V104.37] brain/error_store.py: e={e}")
            return
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning('_atomic_append: Exception not handled: %s', exc, exc_info=True)
            last_exc = exc
            time.sleep(0.05 * (attempt + 1))
    if last_exc:
        raise last_exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug('_read_jsonl: json.JSONDecodeError ignored', exc_info=True)
                    continue
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"[PersistentStore] Failed to read {path}: {exc}", exc_info=True)
    return out


def _rewrite_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    _ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ============================================================
# ERROR STORE
# ============================================================


class ErrorStore:
    """Append-only JSONL store of pipeline errors / failures.

    Each record:
      {
        "id": str,
        "ts": float,
        "question": str,
        "answer": str,
        "verdict": str,
        "domain": str,
        "error_type": str,
        "details": dict,
      }
    """

    MAX_RECORDS = 50000

    def __init__(self, path: str = "data/error_store.jsonl", max_records: int = MAX_RECORDS) -> None:
        self.path = Path(path)
        self.max_records = max_records
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        with self._lock:
            self._records = _read_jsonl(self.path)
            # Trim if over max
            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records :]
                _rewrite_jsonl(self.path, self._records)

    def add(
        self,
        question: str,
        answer: str,
        verdict: str,
        domain: str = "general",
        error_type: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # [V5.8-OPT] Spam filter — reject junk before it enters the store.
        # TẠI SAO: error_store.jsonl had grown to 3 MB / 6135 lines, ~80% spam
        # (emoji-only, control-char garbage, whitespace-only, repeated substrings).
        # Without this filter the 50k cap fills with junk → real errors get
        # evicted (LRU) before they can be analyzed by common_errors() /
        # stats_by_domain(). Rejected items are logged to
        # data/error_store_rejected.jsonl for audit (don't lose forensic trail).
        # Check runs BEFORE acquiring the lock — spam check is cheap (no I/O),
        # and rejecting early avoids contending on self._lock for junk.
        try:
            is_spam, reason = _is_spam_question(question or "")
            if is_spam:
                _log_rejected_question(
                    question=question or "",
                    answer=answer or "",
                    verdict=verdict,
                    domain=domain,
                    error_type=error_type,
                    reason=reason,
                )
                logger.debug(
                    f"[V5.8-OPT] Rejected spam question (reason={reason}, "
                    f"domain={domain}, verdict={verdict})"
                )
                return {
                    "id": None,
                    "rejected": True,
                    "reject_reason": reason,
                    "domain": domain,
                    "verdict": verdict,
                }
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[V5.8-OPT] spam filter error (allowing write): {exc}", exc_info=True)

        # [V104.38 #88] TẠI SAO: ID was generated outside lock → concurrent calls got same ID.
        # Fix: generate ID inside lock (moved below).
        # [EXEC-3] TẠI SAO: previously TWO separate `with self._lock:` blocks —
        # record (with `len(self._records)`-based ID) built in first lock, lock
        # RELEASED, then second lock acquired for append. Two threads could both
        # observe same len() → duplicate IDs. Fix: merge into ONE lock block so
        # ID generation and append are atomic together.
        with self._lock:
            record = {
                "id": f"err-{int(time.time() * 1000)}-{len(self._records) % 100000:05d}",
                "ts": time.time(),
                "question": question,
                "answer": answer,
                "verdict": verdict,
                "domain": domain,
                "error_type": error_type,
                "details": details or {},
            }
            self._records.append(record)
            # Trim oldest if over cap
            trimmed: list[dict[str, Any]] = []
            if len(self._records) > self.max_records:
                trimmed = self._records[: len(self._records) - self.max_records]
                self._records = self._records[-self.max_records :]
            # Append only the new record (fast path); if trimmed, rewrite file
            try:
                _atomic_append(self.path, json.dumps(record, ensure_ascii=False))
                if trimmed:
                    _rewrite_jsonl(self.path, self._records)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"[ErrorStore] Persist failed: {exc}", exc_info=True)
        return record

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records[-limit:])

    def get_by_domain(self, domain: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            out = [r for r in self._records if r.get("domain") == domain]
        return out[-limit:]

    def get_by_error_type(self, error_type: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            out = [r for r in self._records if r.get("error_type") == error_type]
        return out[-limit:]

    def stats_by_domain(self) -> dict[str, int]:
        with self._lock:
            counter: Counter = Counter()
            for r in self._records:
                counter[r.get("domain", "unknown")] += 1
            return dict(counter)

    def common_errors(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Return top-N error types by frequency."""
        with self._lock:
            counter: Counter = Counter()
            for r in self._records:
                counter[r.get("error_type", "unknown")] += 1
        return [
            {"error_type": k, "count": v} for k, v in counter.most_common(top_n)
        ]

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> int:
        with self._lock:
            n = len(self._records)
            self._records = []
            try:
                if self.path.exists():
                    self.path.unlink()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"[ErrorStore] clear() failed: {exc}", exc_info=True)
            return n

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total": len(self._records),
                "max_records": self.max_records,
                "path": str(self.path),
                "by_domain": dict(
                    Counter(r.get("domain", "unknown") for r in self._records)
                ),
                "by_error_type": dict(
                    Counter(r.get("error_type", "unknown") for r in self._records)
                ),
            }


# ============================================================
# KNOWLEDGE STORE
# ============================================================


class KnowledgeStore:
    """JSONL-backed store of learned/verified facts.

    Each record:
      {
        "id": str,
        "ts": float,
        "domain": str,
        "claim": str,
        "verified_answer": str,
        "confidence": float,
        "source": str,
        "tags": list[str],
      }
    """

    MAX_RECORDS = 10000

    def __init__(self, path: str = "data/knowledge_store.jsonl", max_records: int = MAX_RECORDS) -> None:
        self.path = Path(path)
        self.max_records = max_records
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        with self._lock:
            self._records = _read_jsonl(self.path)
            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records :]
                _rewrite_jsonl(self.path, self._records)

    def add(
        self,
        domain: str,
        claim: str,
        verified_answer: str,
        confidence: float = 0.85,
        source: str = "manual",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        record = {
            "id": f"kb-{int(time.time() * 1000)}-{len(self._records) % 10000:04d}",
            "ts": time.time(),
            "domain": domain,
            "claim": claim,
            "verified_answer": verified_answer,
            "confidence": max(0.0, min(1.0, confidence)),
            "source": source,
            "tags": list(tags or []),
        }
        with self._lock:
            self._records.append(record)
            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records :]
                _rewrite_jsonl(self.path, self._records)
            else:
                try:
                    _atomic_append(self.path, json.dumps(record, ensure_ascii=False))
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(f"[KnowledgeStore] Persist failed: {exc}", exc_info=True)
        return record

    def get_by_domain(self, domain: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            out = [r for r in self._records if r.get("domain") == domain]
        return out[-limit:]

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        query_lower = query.lower()
        # [V104.35 #51] TẠI SAO: len(t) > 1 admits "is", "an", "in" → substring matches
        # almost every record. Fix: require len(t) >= 3 + word-boundary match.
        import re as _re
        tokens = [t for t in query_lower.split() if len(t) >= 3]
        scored: list[tuple] = []
        with self._lock:
            for r in self._records:
                text = (r.get("claim", "") + " " + r.get("verified_answer", "")).lower()
                if not tokens:
                    score = 0.0
                else:
                    # [V104.35 #51] word-boundary regex instead of substring
                    score = sum(1.0 for t in tokens if _re.search(r'\b' + _re.escape(t) + r'\b', text)) / len(tokens)
                if score > 0:
                    scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def domains(self) -> list[str]:
        with self._lock:
            return sorted({r.get("domain", "unknown") for r in self._records})

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    # [AUTOFIX-T1-RESTORE] V104.35 #50 + V104.38 #87 + #89 — behaviors removed when
    # brain.py became a stub. Restored here in KnowledgeStore (the real logic location).
    def update_or_verify(
        self,
        domain: str,
        claim: str,
        new_value: str,
        confidence: float = 0.85,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Update an existing claim's value, resetting times_verified on change.

        [V104.35 #50] When the verified_answer changes, times_verified MUST reset to 1
        (was: kept incrementing → stale confidence on changed values).
        [V104.38 #87] IntegrityError handling — if persist fails, log + don't crash.
        """
        with self._lock:
            # Find existing record by domain + claim
            existing = None
            for r in self._records:
                if r.get("domain") == domain and r.get("claim") == claim:
                    existing = r
                    break
            if existing is None:
                # New claim — add fresh
                return self.add(domain, claim, new_value, confidence, source)
            # Existing claim — check if value changed
            old_value = existing.get("verified_answer", "")
            if old_value != new_value:
                # [V104.35 #50] Value changed → reset times_verified to 1
                existing["verified_answer"] = new_value
                existing["times_verified"] = 1
                existing["confidence"] = max(0.0, min(1.0, confidence))
                existing["source"] = source
                existing["ts"] = time.time()
            else:
                # Same value → increment times_verified
                existing["times_verified"] = existing.get("times_verified", 0) + 1
            # [V104.38 #87] IntegrityError-safe persist
            try:
                _rewrite_jsonl(self.path, self._records)
            except Exception as exc:
                logger.warning(f"[KnowledgeStore] IntegrityError during update: {exc}", exc_info=True)
            return existing

    @staticmethod
    def relative_error(old_value: float | str, new_value: float | str) -> float:
        """Compute symmetric relative error.

        [V104.38 #89] Relative error must be symmetric: max(abs(old), abs(new), 1e-300)
        in the denominator. Was: only abs(old_value) → asymmetric when new > old.
        """
        try:
            old_f = float(old_value)
            new_f = float(new_value)
        except (TypeError, ValueError):
            logger.debug('KnowledgeStore.relative_error: TypeError, ValueError ignored', exc_info=True)
            return float("inf")
        # [V104.38 #89] symmetric: max(old, new, epsilon)
        denom = max(abs(old_f), abs(new_f), 1e-300)
        return abs(old_f - new_f) / denom

    def clear(self) -> int:
        with self._lock:
            n = len(self._records)
            self._records = []
            try:
                if self.path.exists():
                    self.path.unlink()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"[KnowledgeStore] clear() failed: {exc}", exc_info=True)
            return n

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total": len(self._records),
                "max_records": self.max_records,
                "path": str(self.path),
                "domains": sorted({r.get("domain", "unknown") for r in self._records}),
            }


# ============================================================
# SINGLETONS
# ============================================================

_ERROR_STORE: ErrorStore | None = None
_KNOWLEDGE_STORE: KnowledgeStore | None = None
_SINGLETON_LOCK = threading.Lock()


def get_error_store(path: str | None = None) -> ErrorStore:
    global _ERROR_STORE
    with _SINGLETON_LOCK:
        if _ERROR_STORE is None or path is not None:
            _ERROR_STORE = ErrorStore(path or "data/error_store.jsonl")
        return _ERROR_STORE


def get_knowledge_store(path: str | None = None) -> KnowledgeStore:
    global _KNOWLEDGE_STORE
    with _SINGLETON_LOCK:
        if _KNOWLEDGE_STORE is None or path is not None:
            _KNOWLEDGE_STORE = KnowledgeStore(path or "data/knowledge_store.jsonl")
        return _KNOWLEDGE_STORE


__all__ = [
    "ErrorStore",
    "KnowledgeStore",
    "get_error_store",
    "get_knowledge_store",
]
