"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V28 — Policy Applier.

Áp dụng principles (từ meta_principles) vào routing/confidence của RealityJudge.

Luồng:
    1. Load active principles từ DB
    2. Group theo domain
    3. Với mỗi question mới:
       a. Xác định domain dựa trên routing
       b. Tìm principle phù hợp (cùng domain)
       c. Adjust:
          - Confidence threshold (vd: domain có >50% FAIL → tăng threshold)
          - Source priority (vd: nếu principle nói "PubChem unreliable" → giảm priority)
          - Suggest alternative SLM
    4. Track applied_count + success_rate (feedback loop)

Closed-loop:
    lessons → principles → policies → APPLY → measure → feedback → principles
"""

import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import logging

from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db

logger = logging.getLogger("scp.policy_applier")


class PolicyApplier:
    """
    Policy Applier — áp dụng principles vào routing decisions.

    Usage:
        applier = PolicyApplier()
        adjustment = applier.get_adjustment(question, domain)
        # adjustment = {
        #     "confidence_threshold": 0.6,  # raised from 0.5
        #     "prefer_sources": ["PubChem"],
        #     "avoid_sources": [],
        #     "applied_principle_ids": [1, 5],
        # }
    """

    def __init__(self):
        init_db()
        self._cache: dict[str, list[dict]] = {}  # domain → principles
        self._cache_ts: dict[str, float] = {}
        self._CACHE_TTL = 300  # 5 minutes

    # ============================================================
    # LOAD PRINCIPLES
    # ============================================================
    def _load_principles_for_domain(self, domain: str) -> list[dict]:
        """Load principles for a domain, with TTL cache."""
        now = time.time()
        if domain in self._cache and now - self._cache_ts.get(domain, 0) < self._CACHE_TTL:
            return self._cache[domain]

        try:
            # Match by domain column OR by principle text containing domain keyword
            rows = db_query_all(
                "SELECT id, principle, domain, confidence, applied_count, success_rate "
                "FROM meta_principles "
                "WHERE domain = ? OR principle LIKE ? "
                "ORDER BY confidence DESC LIMIT 10",
                (f"{domain}_processing", f"%{domain}%")
            )
            principles = [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.warning(f"Load principles error: {e}", exc_info=True)
            principles = []

        self._cache[domain] = principles
        self._cache_ts[domain] = now
        return principles

    # ============================================================
    # EXTRACT ACTIONS FROM PRINCIPLE TEXT
    # ============================================================
    def _extract_actions(self, principle_text: str) -> dict[str, Any]:
        """
        Parse principle text → structured actions.

        [V32.1 FIX] Sửa logic threshold adjustment:
        - pass_rate CAO (>80%) → TĂNG threshold (domain ổn định, strict hơn)
        - pass_rate THẤP (<50%) → GIẢM threshold (lỏng hơn, cho cơ hội PASS)
        - fail_rate CAO (>50%) → GIẢM threshold (tránh UNKNOWN nhiều)
        """
        actions: dict[str, Any] = {
            "fail_rate": None,
            "pass_rate": None,  # nosec B105 — rate field, not a password
            "unknown_rate": None,
            "use_sources": [],
            "avoid_sources": [],
            "threshold_adjustment": 0.0,
            "raw_actions": [],
        }

        text_lower = principle_text.lower()

        # Extract rates
        m = re.search(r'fail_rate\s*=?\s*(\d+)%', text_lower)
        if m:
            actions["fail_rate"] = int(m.group(1)) / 100
        m = re.search(r'pass_rate\s*=?\s*(\d+)%', text_lower)
        if m:
            actions["pass_rate"] = int(m.group(1)) / 100
        m = re.search(r'unknown_rate\s*=?\s*(\d+)%', text_lower)
        if m:
            actions["unknown_rate"] = int(m.group(1)) / 100

        # Extract "Use X" patterns
        for m in re.finditer(r'use\s+([a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,3})', text_lower):
            src = m.group(1).strip()
            # Filter out common non-source words
            if src not in ('the', 'this', 'that', 'it', 'a', 'an'):
                actions["use_sources"].append(src)

        # Extract "Avoid X" patterns
        for m in re.finditer(r'avoid\s+([a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,3})', text_lower):
            actions["avoid_sources"].append(m.group(1).strip())

        # [SCP-DNA-FIX 4-b-004] Threshold adjustment logic — INVERTED.
        # TẠI SAO: V32.1 lowered threshold (-0.10) on weak domains (pass_rate<0.50),
        # with comment "Domain yếu → GIẢM threshold (lỏng hơn, cho cơ hội PASS)".
        # This is BACKWARDS: a weak domain (where SLMs frequently produce wrong
        # answers) should require MORE confidence to PASS, not less. Lowering the
        # threshold meant MORE wrong answers were accepted as PASS → hallucination
        # rate INCREASED. Same backwardness applied to high fail_rate and high
        # unknown_rate (both were -0.05).
        #
        # DNA #22 (PASS≠TRUE): lowering threshold on weak domains made the PASS
        # decision EASIER — the system "claimed PASS" with weaker evidence. That
        # is exactly the RELAXATION_PATTERNS anti-pattern (lower_threshold)
        # that classifier.py:93 bans in patch text — but policy_applier was doing
        # it at runtime, bypassing the classifier.
        # DNA #6: runtime threshold mutation is a trust-root modification that
        # was happening without external validation.
        #
        # Fix: INVERT signs. Weak domain → STRICTER threshold (more evidence
        # required to PASS). Was -0.10 → now +0.10. Was -0.05 → now +0.05.
        # Stable domain (pass_rate>0.80) stays at +0.05 (unchanged).
        pass_rate = actions["pass_rate"]
        fail_rate = actions["fail_rate"]
        unknown_rate = actions["unknown_rate"]

        if pass_rate is not None:
            if pass_rate > 0.80:
                # Domain ổn định → TĂNG threshold (strict hơn, không đổi)
                actions["threshold_adjustment"] = +0.05
            elif pass_rate < 0.50:
                # [SCP-DNA-FIX 4-b-004] Domain yếu → TĂNG threshold (STRICTER).
                # Was -0.10 (BACKWARDS, lowered threshold on weak domain → more
                # hallucinations accepted as PASS). Now +0.10 — weak domain
                # requires MORE confidence to PASS.
                actions["threshold_adjustment"] = +0.10
            # else: pass_rate 0.50-0.80 → không đổi
        elif fail_rate is not None and fail_rate > 0.50:
            # [SCP-DNA-FIX 4-b-004] Fail nhiều → TĂNG threshold (STRICTER).
            # Was -0.05 (BACKWARDS). Now +0.05 — high-failure domain requires
            # more confidence to PASS.
            actions["threshold_adjustment"] = +0.05
        elif unknown_rate is not None and unknown_rate > 0.50:
            # [SCP-DNA-FIX 4-b-004] Unknown nhiều → TĂNG threshold (STRICTER).
            # Was -0.05 (BACKWARDS). Now +0.05 — high-unknown domain is uncertain,
            # require more confidence to PASS.
            actions["threshold_adjustment"] = +0.05

        return actions

    # ============================================================
    # GET ADJUSTMENT
    # ============================================================
    def get_adjustment(self, question: str, domain: str,
                       base_threshold: float = 0.5) -> dict[str, Any]:
        """
        Tính adjustment cho 1 question + domain.

        Returns:
            {
                "confidence_threshold": float,    # adjusted threshold
                "prefer_sources": List[str],
                "avoid_sources": List[str],
                "applied_principle_ids": List[int],
                "applied_principles": List[Dict],  # for logging
            }
        """
        principles = self._load_principles_for_domain(domain)

        if not principles:
            return {
                "confidence_threshold": base_threshold,
                "prefer_sources": [],
                "avoid_sources": [],
                "applied_principle_ids": [],
                "applied_principles": [],
            }

        threshold = base_threshold
        prefer_sources: list[str] = []
        avoid_sources: list[str] = []
        applied_ids: list[int] = []
        applied_principles: list[dict] = []

        for p in principles:
            actions = self._extract_actions(p.get("principle", ""))
            threshold += actions["threshold_adjustment"]
            prefer_sources.extend(actions["use_sources"])
            avoid_sources.extend(actions["avoid_sources"])
            applied_ids.append(p["id"])
            applied_principles.append({
                "id": p["id"],
                "domain": p.get("domain"),
                "confidence": p.get("confidence"),
                "principle": p.get("principle", "")[:120],
            })

        # Clamp threshold
        # [V41.2] Cap at 0.65 — 0.85 was too high, caused 83% PARTIAL
        threshold = max(0.20, min(0.65, threshold))

        # Dedupe sources
        prefer_sources = list(set(prefer_sources))[:5]
        avoid_sources = list(set(avoid_sources))[:5]

        return {
            "confidence_threshold": threshold,
            "prefer_sources": prefer_sources,
            "avoid_sources": avoid_sources,
            "applied_principle_ids": applied_ids,
            "applied_principles": applied_principles,
        }

    # ============================================================
    # FEEDBACK — Update success_rate after verdict
    # ============================================================
    def record_outcome(self, principle_ids: list[int], verdict: str) -> None:
        """
        Cập nhật applied_count + success_rate cho các principle đã apply.

        Args:
            principle_ids: List of meta_principles.id
            verdict: "PASS" / "FAIL" / "UNKNOWN"
        """
        if not principle_ids:
            return

        # [V104.39 #B-success]  TẠI SAO: previously this block was
        # mis-indented INSIDE the `if not principle_ids:` body (after the return),
        # making it unreachable → `success` was never assigned → NameError at the
        # `if success is None` check below, swallowed by except → the ENTIRE
        # policy feedback loop was dead (no principle's success_rate ever updated).
        # Fix: dedent to method-body level so it runs after the guard.
        # Also: UNKNOWN/PARTIAL counted as FAIL (success=0) → domains with many
        # UNKNOWN (insufficient evidence) got success_rate → 0 → auto-delete even
        # though the principle isn't "wrong", just under-evidenced.
        # → UNKNOWN/PARTIAL = neutral (don't count toward success OR failure).
        if verdict == "PASS":
            success = 1
        elif verdict == "FAIL":
            success = 0
        else:  # UNKNOWN, PARTIAL, CONFLICT, SKIP
            success = None  # skip this principle (don't update success_rate)

        for pid in principle_ids:
            if success is None:
                continue  # [V104.39 #B-success] UNKNOWN/PARTIAL neutral — skip
            try:
                # [V104.39 #B] TẠI SAO: was no transaction → lost update under 16 workers.
                # Fix: BEGIN IMMEDIATE for atomic read-modify-write.
                from scp.core.db_manager import _db_lock
                with _db_lock:
                    db_exec("BEGIN IMMEDIATE")
                    row = db_query_one("SELECT applied_count, success_rate FROM meta_principles WHERE id = ?", (pid,))
                    if row:
                        old_count = row["applied_count"]
                        old_rate = row["success_rate"]
                        new_count = old_count + 1
                        new_rate = (old_rate * old_count + success) / new_count
                        db_exec("UPDATE meta_principles SET applied_count = ?, success_rate = ? WHERE id = ?",
                                (new_count, new_rate, pid))
                    db_exec("COMMIT")
            except Exception as e:
                try:
                    db_exec("ROLLBACK")
                except Exception as rollback_err:
                    # [G5-FIX] Was `except Exception as e:` — rebinds `e` in the
                    # function scope, so the outer `e` becomes UnboundLocalError
                    # at the next line (`logger.warning(f"... {e}")`). Rename to
                    # `rollback_err` to preserve the outer exception binding.
                    logger.warning(f"Silent except: {rollback_err}", exc_info=True)
                logger.warning(f"Update principle {pid} outcome error: {e}", exc_info=True)

    # ============================================================
    # STATS
    # ============================================================
    def get_stats(self) -> dict[str, Any]:
        """Stats về policy applier.

        [SCP-DNA-FIX 4-b-019] READ-ONLY method — does NOT mutate the policy
        KB. PRE-FIX: get_stats() called `self._auto_delete_dead_principles()`
        as a side effect — a monitoring dashboard calling get_stats() every
        minute would silently DELETE principles it considered "dead" (those
        with success_rate < 0.3 AND applied_count >= 10), corrupting the
        policy KB without operator intent.

          DNA #9 (No harm — query method silently destroys data).
          DNA #22 (PASS≠TRUE — claimed "stats" but had destructive side effect).
          DNA #11 (HITL — auto-delete bypassed human-in-the-loop intent).
          DNA #19 (Tầng kiểm toán — observation layer couldn't see deletes
          that happened as a side effect of stats queries).

        POST-FIX: get_stats() is a pure read. To prune dead principles,
        operators must call `prune_dead_principles()` explicitly (separate
        method below). The `auto_deleted` field is preserved as 0 in the
        return dict for backward-compat with any caller that reads it.
        """
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_principles")["cnt"]
            applied = db_query_one(
                "SELECT COUNT(*) as cnt FROM meta_principles WHERE applied_count > 0"
            )["cnt"]
            avg_success = db_query_one(
                "SELECT AVG(success_rate) as avg FROM meta_principles WHERE applied_count > 0"
            )["avg"] or 0

            # [SCP-DNA-FIX 4-b-019] DO NOT call _auto_delete_dead_principles()
            # from this read method. Side-effect mutation removed. The
            # `auto_deleted` field is preserved as 0 for backward-compat —
            # callers that historically checked this field will see 0
            # (no deletes performed by stats query) and not break.
            deleted = 0

            # Group by domain
            domain_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "applied": 0, "avg_success": 0})
            rows = db_query_all(
                "SELECT domain, COUNT(*) as cnt, SUM(applied_count) as applied, AVG(success_rate) as succ "
                "FROM meta_principles GROUP BY domain"
            )
            for r in rows:
                d = r["domain"] or "unknown"
                domain_stats[d] = {
                    "count": r["cnt"],
                    "applied": r["applied"] or 0,
                    "avg_success": round(r["succ"] or 0, 3),
                }

            return {
                "total_principles": total,
                "applied_principles": applied,
                "avg_success_rate": round(avg_success, 3),
                "domains": dict(domain_stats),
                "auto_deleted": deleted,
            }
        except Exception as e:
            logger.warning("Policy applier get_stats failed: %s", e, exc_info=True)
            return {"error": str(e)}

    # [SCP-DNA-FIX 4-b-019] Public explicit method for pruning dead principles.
    # Operators must call this INTENTIONALLY — it is NOT called as a side
    # effect of get_stats(). This restores HITL (DNA #11) and makes the
    # destructive operation observable + auditable.
    def prune_dead_principles(self, threshold: float = 0.3,
                              min_applied: int = 10) -> int:
        """Explicitly prune dead principles (operator-initiated).

        A principle is considered "dead" if its success_rate < `threshold`
        AND its applied_count >= `min_applied` (enough evidence to be
        confident it's not just under-tested).

        This is a DESTRUCTIVE operation — it DELETEs rows from meta_principles
        and writes a knowledge_versions audit entry for each. Call this
        explicitly when you intend to prune; do NOT call from read paths
        (get_stats, get_adjustment, etc.).

        Args:
            threshold: success_rate below this → candidate for deletion (default 0.3).
            min_applied: applied_count must be at least this (default 10) —
                principles with fewer applications are considered under-tested
                and not deleted.

        Returns:
            Number of principles deleted.
        """
        return self._auto_delete_dead_principles(threshold=threshold, min_applied=min_applied)

    def _auto_delete_dead_principles(self, threshold: float = 0.3,
                                      min_applied: int = 10) -> int:
        """ Auto-delete principles with success_rate < threshold AND applied >= min_applied.

        [SCP-DNA-FIX 4-b-019] This method is now ONLY called from
        `prune_dead_principles()` (explicit operator action). It is NOT
        called from `get_stats()` anymore — see fix comments in get_stats.
        """
        try:
            rows = db_query_all(
                "SELECT id, principle, domain, success_rate, applied_count "
                "FROM meta_principles WHERE success_rate < ? AND applied_count >= ?",
                (threshold, min_applied)
            )
            if not rows:
                return 0
            deleted_count = 0
            for r in rows:
                # Save version before delete
                db_exec("""
                    INSERT INTO knowledge_versions
                    (timestamp, entity, attribute, old_value, new_value, change_type, source, reason)
                    VALUES (?, ?, ?, ?, NULL, 'delete', 'PolicyApplier', ?)
                """, (
                    datetime.now().astimezone().isoformat(),
                    f"principle_{r['id']}", "policy",
                    r["principle"][:200],
                    f"Auto-deleted: success_rate={r['success_rate']:.2f}, applied={r['applied_count']}",
                ))
                # Delete
                db_exec("DELETE FROM meta_principles WHERE id = ?", (r["id"],))
                deleted_count += 1
                logger.info(f"Auto-dead principle #{r['id']}: success_rate={r['success_rate']:.2f}")
            return deleted_count
        except Exception as e:
            logger.warning(f"Auto-delete error: {e}", exc_info=True)
            return 0


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V28 Policy Applier")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    parser.add_argument("--test", type=str, help="Test với 1 question + domain")
    parser.add_argument("--domain", type=str, default="math", help="Domain for test")
    args = parser.parse_args()

    applier = PolicyApplier()

    if args.stats:
        stats = applier.get_stats()
        print(f"\n{'='*60}")
        print("  POLICY APPLIER STATS")
        print(f"{'='*60}")
        print(f"  Total principles:  {stats.get('total_principles', 0)}")
        print(f"  Applied principles:{stats.get('applied_principles', 0)}")
        print(f"  Avg success rate:  {stats.get('avg_success_rate', 0)}")
        print("\n  By domain:")
        for d, info in stats.get("domains", {}).items():
            print(f"    {d:30s} count={info['count']:>3} applied={info['applied']:>4} succ={info['avg_success']}")
        return

    if args.test:
        adj = applier.get_adjustment(args.test, args.domain)
        print(f"\n{'='*60}")
        print(f"  ADJUSTMENT FOR: '{args.test}'")
        print(f"  Domain: {args.domain}")
        print(f"{'='*60}")
        print(f"  Confidence threshold: {adj['confidence_threshold']:.3f}")
        print(f"  Prefer sources:       {adj['prefer_sources']}")
        print(f"  Avoid sources:        {adj['avoid_sources']}")
        print(f"  Applied principles:   {len(adj['applied_principles'])}")
        for p in adj["applied_principles"]:
            print(f"    [#{p['id']}] conf={p['confidence']:.2f} | {p['principle']}")
        return

    print("Use --stats or --test 'question'")


if __name__ == "__main__":
    main()
