"""
SCP V100 — Domain-Separated Knowledge Store
=============================================
Lưu tri thức tách theo domain — tránh kẹt/lỗi khi ghi.
Async write (thread pool) — không block pipeline chính.

Cấu trúc:
  data/knowledge/
    ├── math.jsonl
    ├── physics.jsonl
    ├── chemistry.jsonl
    ├── finance.jsonl
    ├── medical.jsonl
    ├── geography.jsonl
    ├── history.jsonl
    ├── weather.jsonl
    ├── general.jsonl
    └── ... (mỗi domain 1 file)

Tính năng:
  - Async write via ThreadPoolExecutor (không block judge())
  - SHA-256 integrity cho mỗi record
  - TTL per Trust Tier (auto-expire)
  - Domain-separated (không kẹt 1 domain → ảnh hưởng khác)
  - Thread-safe (threading.Lock per domain)
  - Auto-cleanup expired records (mỗi 1h)
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from scp.knowledge.trust_hierarchy import (
    KnowledgeRecord,
    compute_hash,
    get_tier,
    get_ttl,
    is_expired,
)

logger = logging.getLogger("scp.knowledge.store")


class DomainKnowledgeStore:
    """Knowledge store tách theo domain — async write, thread-safe, TTL-aware.

    Naming convention: <Purpose>Store (world standard).
    """

    def __init__(self, data_dir: str = "data/knowledge", max_workers: int = 4):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="kb-write")
        self._locks: dict[str, threading.Lock] = {}  # per-domain lock
        self._global_lock = threading.Lock()
        self._cache: dict[str, list[KnowledgeRecord]] = {}  # domain → records (in-memory)
        self._stats = {
            "total_stored": 0,
            "total_expired": 0,
            "total_reads": 0,
            "total_writes": 0,
            "write_errors": 0,
            "last_cleanup": 0,
        }
        # Pre-load all domains
        self._load_all()

    def _get_lock(self, domain: str) -> threading.Lock:
        """Get or create lock for domain."""
        with self._global_lock:
            if domain not in self._locks:
                self._locks[domain] = threading.Lock()
            return self._locks[domain]

    def _domain_file(self, domain: str) -> Path:
        """Get file path for domain."""
        safe_domain = domain.replace("/", "_").replace(" ", "_").lower()
        return self.data_dir / f"{safe_domain}.jsonl"

    def _load_all(self):
        """Load all domain files into cache."""
        for f in self.data_dir.glob("*.jsonl"):
            domain = f.stem
            self._load_domain(domain)

    def _load_domain(self, domain: str):
        """Load 1 domain file into cache."""
        f = self._domain_file(domain)
        if not f.is_file():
            return
        lock = self._get_lock(domain)
        with lock:
            records = []
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            record = KnowledgeRecord(
                                id=data["id"],
                                hash=data["hash"],
                                question=data.get("question", ""),
                                answer=data.get("answer", ""),
                                domain=data.get("domain", domain),
                                source=data.get("source", "unknown"),
                                source_url=data.get("source_url", ""),
                                source_tier=data.get("source_tier", 4),
                                collected_at=data.get("collected_at", 0),
                                source_published_at=data.get("source_published_at", 0),
                                expires_at=data.get("expires_at", 0),
                                verified_by=data.get("verified_by", []),
                                verification_count=data.get("verification_count", 0),
                                confidence=data.get("confidence", 0.5),
                                collected_by=data.get("collected_by", "on_demand"),
                                parent_id=data.get("parent_id"),
                                version=data.get("version", ""),
                            )
                            # Skip expired
                            if not is_expired(record):
                                records.append(record)
                            else:
                                self._stats["total_expired"] += 1
                        except Exception as e:
                            logger.debug(f"KB load error: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"KB load domain {domain}: {e}", exc_info=True)
            self._cache[domain] = records
            logger.info(f"KB loaded {domain}: {len(records)} records")

    def store(
        self,
        question: str,
        answer: str,
        domain: str,
        source: str,
        source_url: str = "",
        confidence: float = 0.5,
        collected_by: str = "on_demand",
        verified_by: list[str] | None = None,
        version: str = "",
    ) -> KnowledgeRecord | None:
        """Store 1 record — async write, returns immediately.

        [V109 FIX] Deduplication: check content hash before storing.
        [V109 FIX] Quality filter: skip if source_tier=4 AND confidence < 0.7.

        Args:
            question: Question that was asked
            answer: Verified answer
            domain: Knowledge domain (math, physics, finance, ...)
            source: Data source name (wikipedia, pubchem, ...)
            source_url: URL of source
            confidence: Confidence score (0-1)
            collected_by: How this was collected (on_demand, scheduled_crawl, curiosity, bypass_learning)
            verified_by: List of sources that verified this
            version: Version string for Tier 1 (Luật 2025, ...)

        Returns:
            KnowledgeRecord (stored in cache, written to disk async), or None if dedup/quality skip
        """
        now = time.time()
        tier = get_tier(source)
        ttl = get_ttl(source)

        # [V109 FIX 1] Deduplication — check content hash (question + answer, WITHOUT timestamp)
        content_hash = compute_hash(question[:500], answer[:500], source, 0)  # deterministic hash
        lock = self._get_lock(domain)
        with lock:
            existing = self._cache.get(domain, [])
            for r in existing:
                existing_hash = compute_hash(r.question, r.answer, r.source, 0)
                if existing_hash == content_hash:
                    logger.debug(f"[KB] Dedup skip: question already stored (hash={content_hash[:12]})")
                    return None  # Already stored — skip

        # [V109 FIX 2] Quality filter — don't store low-quality learned data
        if source == "scp_learned" and confidence < 0.7:
            logger.debug(f"[KB] Quality skip: scp_learned conf={confidence:.2f} < 0.7 threshold")
            return None  # Too low confidence for learned data

        # [V109 FIX 3] Don't store attack/jailbreak questions
        _attack_indicators = ["bỏ qua", "ignore previous", "forget your", "jailbreak",
                              # "dan" removed [V104.34 #47] TẠI SAO: matched "danger", "dance", "DANang" "unrestricted", "developer mode", "system prompt",
                              "reveal your", "pretend to be", "act as"]
        q_lower = question.lower()
        if any(ind in q_lower for ind in _attack_indicators):
            logger.debug("[KB] Attack skip: question contains attack indicator")
            return None  # Don't store attacks in KB

        record = KnowledgeRecord(
            id=f"kr_{uuid.uuid4().hex[:12]}",
            hash=compute_hash(question, answer, source, now),
            question=question[:500],
            answer=answer[:500],
            domain=domain,
            source=source,
            source_url=source_url,
            source_tier=int(tier),
            collected_at=now,
            source_published_at=now,
            expires_at=now + ttl if ttl > 0 else 0,
            verified_by=verified_by or [source],
            verification_count=len(verified_by) if verified_by else 1,
            confidence=confidence,
            collected_by=collected_by,
            version=version,
        )

        # Add to cache (thread-safe)
        lock = self._get_lock(domain)
        with lock:
            if domain not in self._cache:
                self._cache[domain] = []
            self._cache[domain].append(record)
            self._stats["total_stored"] += 1

        # Async write to disk (don't block)
        self._executor.submit(self._async_write, domain, record)
        self._stats["total_writes"] += 1

        return record

    def _async_write(self, domain: str, record: KnowledgeRecord):
        """Write record to disk (called from thread pool)."""
        f = self._domain_file(domain)
        lock = self._get_lock(domain)
        try:
            with lock:
                with open(f, "a", encoding="utf-8") as fp:
                    fp.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"KB write error domain={domain}: {e}", exc_info=True)
            self._stats["write_errors"] += 1

    def search(
        self,
        question: str,
        domain: str = "",
        limit: int = 5,
    ) -> list[KnowledgeRecord]:
        """Search KB for similar questions.

        Args:
            question: Question to search
            domain: Optional domain filter
            limit: Max results

        Returns:
            List of KnowledgeRecord (sorted by relevance + trust tier)
        """
        self._stats["total_reads"] += 1
        q_lower = question.lower().strip()
        results = []

        domains_to_search = [domain] if domain else list(self._cache.keys())
        for dom in domains_to_search:
            records = self._cache.get(dom, [])
            for r in records:
                if is_expired(r):
                    continue
                # [V104.35 #48] TẠI SAO: bidirectional substring matched short stored
                # questions against long queries → wrong results. Fix: use token-overlap
                # scoring (Jaccard) — only match if query and record share meaningful tokens.
                r_lower = r.question.lower()
                q_tokens = {w for w in q_lower.split() if len(w) > 2}
                r_tokens = {w for w in r_lower.split() if len(w) > 2}
                # [V104.43 #BJ] TẠI SAO: was "at least 1 overlapping token" →
                # "capital of France" → token "france" → false hit. Fix: require ≥2.
                if q_tokens and r_tokens:
                    overlap = q_tokens & r_tokens
                    if (len(overlap) >= 2) or q_lower == r_lower:
                        results.append(r)
                elif q_lower == r_lower:
                    results.append(r)

        # --- RESTORED SUBSYSTEM (Wave 3): experience/semantic_kb fallback ---
        if not results:
            try:
                from scp.experience.semantic_kb import compute_tf_idf
                # Pack all active records into dictionary for the fallback scorer
                all_active = []
                for dom in domains_to_search:
                    all_active.extend([r for r in self._cache.get(dom, []) if not is_expired(r)])
                if all_active:
                    docs = [{"content": r.question, "record": r} for r in all_active]
                    fallback_results = compute_tf_idf(question, docs)
                    results = [d["record"] for d in fallback_results]
            except ImportError:
                logger.debug('DomainKnowledgeStore.search: ImportError ignored', exc_info=True)
        # --------------------------------------------------------------------

        # Sort by trust tier (lower = better), then by confidence, then by recency
        results.sort(key=lambda r: (r.source_tier, -r.confidence, -r.collected_at))
        return results[:limit]

    def get_by_domain(self, domain: str, limit: int = 100) -> list[KnowledgeRecord]:
        """Get all records for a domain."""
        self._stats["total_reads"] += 1
        records = [r for r in self._cache.get(domain, []) if not is_expired(r)]
        return records[-limit:]

    def cleanup_expired(self) -> int:
        """Remove expired records from cache + rewrite files. Returns count removed."""
        removed = 0
        now = time.time()
        for domain in list(self._cache.keys()):
            lock = self._get_lock(domain)
            with lock:
                original = self._cache[domain]
                kept = [r for r in original if not is_expired(r, now)]
                removed += len(original) - len(kept)
                self._cache[domain] = kept
                # Rewrite file (async)
                if removed > 0:
                    self._executor.submit(self._rewrite_domain, domain, kept)

        self._stats["total_expired"] += removed
        self._stats["last_cleanup"] = now
        if removed > 0:
            logger.info(f"KB cleanup: removed {removed} expired records")
        return removed

    def _rewrite_domain(self, domain: str, records: list[KnowledgeRecord]):
        """Rewrite domain file (remove expired)."""
        f = self._domain_file(domain)
        lock = self._get_lock(domain)
        try:
            with lock:
                with Path(f).open("w", encoding="utf-8") as fp:
                    for r in records:
                        fp.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"KB rewrite error domain={domain}: {e}", exc_info=True)

    def verify_integrity(self, domain: str = "") -> dict[str, Any]:
        """Verify SHA-256 integrity of records.

        Returns:
            {domain: {total, verified, corrupted}}
        """
        results = {}
        domains = [domain] if domain else list(self._cache.keys())
        for dom in domains:
            records = self._cache.get(dom, [])
            total = len(records)
            verified = 0
            corrupted = 0
            for r in records:
                expected = compute_hash(r.question, r.answer, r.source, r.collected_at)
                if r.hash == expected:
                    verified += 1
                else:
                    corrupted += 1
                    logger.warning(f"KB corruption: domain={dom} id={r.id}")
            results[dom] = {"total": total, "verified": verified, "corrupted": corrupted}
        return results

    # ---- [SCP-DNA-FIX R13-3 BUG-010] Public tamper-detection API ----
    # R5/V100 added `verify_integrity(domain)` (record-level SHA-256) but
    # vulture found 0 callers → hashes were stored on every record but NEVER
    # compared. Attacker who edits data/knowledge/*.jsonl is NEVER detected.
    # Below are the public aggregation methods that a scheduler should call.
    #
    # TODO(parent — scp/api_server_parts/lifespan.py owner): wire this into the FastAPI
    # lifespan startup + a 24h recurring task:
    #     from scp.knowledge.domain_store import DomainKnowledgeStore
    #     store = DomainKnowledgeStore()  # or get_singleton()
    #     # On startup: register all existing domain files
    #     for f in store.data_dir.glob("*.jsonl"):
    #         store.register_file(f.name)
    #     # Verify records + file-level hashes
    #     record_results = store.verify_all_baselines()
    #     file_results = store.verify_all_file_baselines()
    #     if any(v.get("corrupted", 0) > 0 for v in record_results.values()):
    #         logger.error(f"[domain_store] RECORD CORRUPTION DETECTED: {record_results}")
    # Until the lifespan wires this in, callers can invoke the API directly.
    def verify_all_baselines(self) -> dict[str, dict[str, Any]]:
        """Verify SHA-256 integrity of records across ALL domains.

        Iterates every domain in the cache and calls `verify_integrity(dom)`
        on each. Returns an aggregate dict keyed by domain name.

        Returns:
            {domain: {"total": int, "verified": int, "corrupted": int}}.
            Empty dict if no domains have been loaded.
        """
        # Reuse verify_integrity(no-domain) which already iterates all domains;
        # we wrap it here to give the bug-spec's canonical name + log loudly
        # on corruption so a scheduler/operator sees the alert.
        results = self.verify_integrity(domain="")
        for dom, stats in results.items():
            if stats.get("corrupted", 0) > 0:
                logger.error(
                    f"[domain_store] CORRUPTION DETECTED: domain='{dom}' "
                    f"corrupted={stats['corrupted']}/{stats['total']} records"
                )
        return results

    def register_file(self, file_name: str) -> bool:
        """Register a domain .jsonl file for file-level tamper detection.

        Computes the SHA-256 of the file's raw bytes and stores it as a
        baseline. Future calls to `verify_all_file_baselines()` will compare
        against this hash. Idempotent: re-registering the same file refreshes
        the baseline (use after a planned write to avoid false alarms).

        Args:
            file_name: File name relative to data_dir (e.g., "math.jsonl"),
                OR a full path under data_dir.

        Returns:
            True if the baseline was stored; False if the file does not
            exist (in which case no baseline is recorded).
        """
        import hashlib as _hashlib

        # Normalize: accept either "math.jsonl" or "data/knowledge/math.jsonl"
        path = Path(file_name)
        if not path.is_absolute():
            # Try as relative-to-data_dir first; if not found, try as-is.
            candidate = self.data_dir / file_name
            if candidate.exists():
                path = candidate
            elif path.exists():
                pass  # use as-is
            else:
                logger.warning(
                    f"[domain_store] register_file: '{file_name}' not found "
                    f"under data_dir={self.data_dir} — no baseline stored"
                )
                return False

        try:
            h = _hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception as e:
            logger.warning(f"[domain_store] register_file: hash failed for '{file_name}': {e}", exc_info=True)
            return False

        # Use the relative name as the key for stable lookups across cwd changes.
        key = path.name
        if not hasattr(self, "_file_baselines") or self._file_baselines is None:
            self._file_baselines: dict[str, str] = {}
        self._file_baselines[key] = h
        logger.info(f"[domain_store] file baseline registered: {key} (hash={h[:12]}...)")
        return True

    def verify_all_file_baselines(self) -> dict[str, bool]:
        """Verify all registered domain files match their baseline hashes.

        Companion to `register_file()`. Iterates every file registered and
        re-computes the SHA-256, comparing against the stored baseline.

        Returns:
            Dict mapping file_name → bool (True if hash matches baseline,
            False if mismatch or file missing). Empty dict if no files
            have been registered.
        """
        import hashlib as _hashlib

        if not getattr(self, "_file_baselines", None):
            return {}

        results: dict[str, bool] = {}
        for file_name, expected_hash in list(self._file_baselines.items()):
            path = self.data_dir / file_name
            if not path.exists():
                results[file_name] = False
                logger.error(
                    f"[domain_store] TAMPER DETECTED: file '{file_name}' "
                    f"missing (was registered with hash={expected_hash[:12]}...)"
                )
                continue
            try:
                actual = _hashlib.sha256(path.read_bytes()).hexdigest()
            except Exception as e:
                results[file_name] = False
                logger.error(f"[domain_store] hash failed for '{file_name}': {e}", exc_info=True)
                continue
            ok = (actual == expected_hash)
            results[file_name] = ok
            if not ok:
                logger.error(
                    f"[domain_store] TAMPER DETECTED: file '{file_name}' "
                    f"hash mismatch (expected={expected_hash[:12]}... actual={actual[:12]}...)"
                )
        return results

    def stats(self) -> dict[str, Any]:
        """[B-S1] Extended stats cho /v100/knowledge/stats.

        Bổ sung (giữ nguyên các key cũ để backward-compatible):
          - concepts / total_records: tổng số knowledge records đang active
          - sources: đếm số record theo nguồn (provenance)
          - fresh_records / stale_records: active vs is_expired (đo lúc gọi,
            vì record có thể hết hạn sau khi load vào cache)
        """
        total = sum(len(r) for r in self._cache.values())
        sources: dict[str, int] = {}
        fresh = 0
        stale = 0
        for records in self._cache.values():
            for r in records:
                sources[r.source] = sources.get(r.source, 0) + 1
                if is_expired(r):
                    stale += 1
                else:
                    fresh += 1
        return {
            **self._stats,
            "concepts": total,
            "total_records": total,
            "domains": len(self._cache),
            "by_domain": {d: len(r) for d, r in self._cache.items()},
            "sources": sources,
            "fresh_records": fresh,
            "stale_records": stale,
        }

    def close(self):
        """Shutdown thread pool."""
        self._executor.shutdown(wait=True)


__all__ = ["DomainKnowledgeStore"]
