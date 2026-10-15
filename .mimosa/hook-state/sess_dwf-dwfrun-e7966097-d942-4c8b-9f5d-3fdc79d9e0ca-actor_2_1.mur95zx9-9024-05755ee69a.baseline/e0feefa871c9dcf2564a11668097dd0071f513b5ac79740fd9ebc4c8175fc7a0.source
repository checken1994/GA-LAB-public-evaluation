"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V41 — Principle Rule Engine.

Thay principles từ text mô tả → executable if-then-else rules với versioning.

Trước V41:
    principle = "Math domain: 50 samples, fail_rate=34%. Action: Use deterministic AST"
    → PolicyApplier parse text → dễ sai

Sau V41:
    principle = {
        "domain": "math",
        "version": 3,
        "condition": "verdict == FAIL AND source == 'PythonAST'",
        "action": "fallback_to_safe_math",
        "fallback_chain": ["PythonAST", "SafeMath", "Unknown"],
        "evidence": {"samples": 277, "fail_rate": 0.17, "last_updated": "2026-07-04"},
        "previous_version": 2,
    }
    → PolicyApplier apply trực tiếp, không parse text

Versioning:
    Khi principle update → UPDATE existing row (không INSERT mới)
    → 1 principle per domain, version tăng dần
"""

import json
import logging
import os
import re
import sys
from datetime import datetime

logger = logging.getLogger("scp.principle_rules")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from scp.core.db_manager import db_exec, db_query_all, db_query_one, init_db


# ============================================================
# SCHEMA — add version + rule columns to meta_principles
# ============================================================
def init_principle_rules_db():
    """Add rule columns to meta_principles."""
    try:
        # Check if columns exist
        cols = [r['name'] for r in db_query_all("PRAGMA table_info(meta_principles)")]
        if 'rule_condition' not in cols:
            db_exec("ALTER TABLE meta_principles ADD COLUMN rule_condition TEXT DEFAULT ''")
        if 'rule_action' not in cols:
            db_exec("ALTER TABLE meta_principles ADD COLUMN rule_action TEXT DEFAULT ''")
        if 'fallback_chain' not in cols:
            db_exec("ALTER TABLE meta_principles ADD COLUMN fallback_chain TEXT DEFAULT ''")
        if 'version' not in cols:
            db_exec("ALTER TABLE meta_principles ADD COLUMN version INTEGER DEFAULT 1")
        if 'previous_version' not in cols:
            db_exec("ALTER TABLE meta_principles ADD COLUMN previous_version INTEGER DEFAULT 0")
    except Exception as e:
        logger.debug(f"Schema migration error: {e}", exc_info=True)


# ============================================================
# PRINCIPLE RULE DEFINITIONS — per domain
# ============================================================

# Domain → rule template
DOMAIN_RULES: dict[str, dict] = {
    "math": {
        "condition": "verdict == 'FAIL' AND source == 'PythonAST'",
        "action": "skip_verdict",
        "fallback_chain": json.dumps(["PythonAST", "SafeMath", "Unknown"]),
        "reasoning": "Math is deterministic — if PythonAST fails, question is unparseable, not wrong",
    },
    "logic": {
        "condition": "verdict == 'FAIL' AND source == 'PythonAST'",
        "action": "skip_verdict",
        "fallback_chain": json.dumps(["PythonAST", "Unknown"]),
        "reasoning": "Logic is deterministic — failures are parse errors",
    },
    "statistics": {
        "condition": "verdict == 'FAIL' AND source == 'PythonMath'",
        "action": "skip_verdict",
        "fallback_chain": json.dumps(["PythonMath", "Unknown"]),
        "reasoning": "Statistics is deterministic",
    },
    "reality": {
        "condition": "verdict == 'FAIL' AND source == 'CODATA'",
        "action": "mark_for_review",
        "fallback_chain": json.dumps(["CODATA", "Wikipedia", "Unknown"]),
        "reasoning": "Physical constants rarely wrong — if FAIL, check AI answer extraction",
    },
    "chemistry": {
        "condition": "verdict == 'FAIL' AND source IN ('PubChem', 'Wikidata')",
        "action": "retry_with_adversary",
        "fallback_chain": json.dumps(["PubChem", "Wikidata", "Wikipedia", "Unknown"]),
        "reasoning": "Chemistry needs cross-validation — retry with different source",
    },
    "weather": {
        "condition": "confidence < 0.5 AND verdict != 'PASS'",
        "action": "enqueue_reverify",
        "fallback_chain": json.dumps(["Open-Meteo", "Archive", "wttr.in", "Unknown"]),
        "reasoning": "Weather is volatile — low confidence → re-verify later",
    },
    "finance": {
        "condition": "confidence < 0.7 AND sources_succeeded < 3",
        "action": "retry_with_more_sources",
        "fallback_chain": json.dumps(["Binance", "Coinbase", "Kraken", "Bitstamp", "KuCoin", "Unknown"]),
        "reasoning": "Crypto needs ≥3 sources for consensus",
    },
    "geography": {
        "condition": "verdict == 'UNKNOWN' AND entity NOT IN LocalDB",
        "action": "wikipedia_fallback",
        "fallback_chain": json.dumps(["LocalDB", "REST Countries", "Wikipedia", "Unknown"]),
        "reasoning": "Geography unknowns → try Wikipedia",
    },
    "history": {
        "condition": "verdict == 'UNKNOWN' AND entity NOT IN LocalDB",
        "action": "wikipedia_fallback",
        "fallback_chain": json.dumps(["LocalDB", "Wikipedia", "Unknown"]),
        "reasoning": "History unknowns → try Wikipedia",
    },
    "biology": {
        "condition": "verdict == 'UNKNOWN'",
        "action": "wikipedia_fallback",
        "fallback_chain": json.dumps(["InternalKB", "Wikipedia", "Unknown"]),
        "reasoning": "Biology unknowns → try Wikipedia",
    },
    "conversion": {
        "condition": "confidence < 0.7 AND sources_succeeded < 2",
        "action": "retry_with_more_sources",
        "fallback_chain": json.dumps(["Frankfurter", "open.er-api", "Unknown"]),
        "reasoning": "Currency needs ≥2 sources",
    },
    "unknown": {
        "condition": "verdict == 'UNKNOWN'",
        "action": "wikipedia_fallback",
        "fallback_chain": json.dumps(["Wikipedia", "Unknown"]),
        "reasoning": "Unknown domain → try Wikipedia as last resort",
    },
}


class PrincipleRuleEngine:
    """
    Principle Rule Engine — manage executable if-then-else rules.

    Key difference from V40:
        V40: principle = text description, append new rows
        V41: principle = executable rule, UPDATE existing (versioning)
    """

    def __init__(self):
        init_db()
        init_principle_rules_db()

    def get_rule(self, domain: str) -> dict | None:
        """
        Get the latest rule for a domain.

        Returns:
            {domain, version, condition, action, fallback_chain, evidence} or None
        """
        # Normalize domain
        domain_key = domain.replace("_processing", "")

        try:
            row = db_query_one(
                "SELECT * FROM meta_principles WHERE domain = ? ORDER BY version DESC LIMIT 1",
                (f"{domain_key}_processing",)
            )
            if row:
                return dict(row)
        except Exception as e:
            logger.debug(f"[V104.37] meta/principle_rules.py: e={e}", exc_info=True)

        # Fallback to static rules
        rule_template = DOMAIN_RULES.get(domain_key)
        if rule_template:
            return {
                "domain": f"{domain_key}_processing",
                "rule_condition": rule_template["condition"],
                "rule_action": rule_template["action"],
                "fallback_chain": rule_template["fallback_chain"],
                "version": 0,
                "confidence": 0.5,
            }
        return None

    def update_rule(self, domain: str, evidence: dict) -> bool:
        """
        Update or create a principle rule (versioning, not append).

        Args:
            domain: "math", "chemistry", etc.
            evidence: {samples, fail_rate, pass_rate, sources, accuracy}

        Returns:
            True if updated, False if failed
        """
        domain_key = domain.replace("_processing", "")
        domain_full = f"{domain_key}_processing"

        # Get rule template
        template = DOMAIN_RULES.get(domain_key, DOMAIN_RULES["unknown"])

        # Get current version
        existing = self.get_rule(domain_key)
        current_version = existing.get("version", 0) if existing else 0
        previous_version = current_version

        # Build principle text (for backward compat)
        samples = evidence.get("samples", 0)
        fail_rate = evidence.get("fail_rate", 0)
        pass_rate = evidence.get("pass_rate", 1 - fail_rate)
        sources = evidence.get("sources", "calibration")

        principle_text = (
            f"{domain_key} domain: {samples} samples, "
            f"fail_rate={fail_rate:.0%}, pass_rate={pass_rate:.0%}. "
            f"Sources: {sources}. "
            f"Rule: IF {template['condition']} → {template['action']}. "
            f"Fallback: {template['fallback_chain']}. "
            f"Reasoning: {template['reasoning']}"
        )

        # Confidence based on samples + fail_rate
        if pass_rate > 0.80:
            confidence = min(1.0, 0.7 + 0.005 * samples)
        elif pass_rate < 0.50:
            confidence = min(1.0, 0.3 + 0.005 * samples)
        else:
            confidence = min(1.0, 0.5 + 0.005 * samples)

        ts = datetime.now().astimezone().isoformat()

        try:
            # Check if principle exists for this domain
            if existing and existing.get("id"):
                # UPDATE existing (versioning, not append)
                db_exec("""
                    UPDATE meta_principles SET
                        principle = ?,
                        confidence = ?,
                        rule_condition = ?,
                        rule_action = ?,
                        fallback_chain = ?,
                        version = ?,
                        previous_version = ?,
                        created_at = ?,
                        applied_count = 0,
                        success_rate = ?
                    WHERE id = ?
                """, (
                    principle_text,
                    confidence,
                    template["condition"],
                    template["action"],
                    template["fallback_chain"],
                    current_version + 1,
                    previous_version,
                    ts,
                    pass_rate,
                    existing["id"],
                ))
                logger.info(f"Principle updated: {domain_full} v{current_version + 1} (was v{previous_version})")
                return True
            else:
                # INSERT new
                db_exec("""
                    INSERT INTO meta_principles
                    (principle, derived_from, domain, confidence, created_at,
                     applied_count, success_rate,
                     rule_condition, rule_action, fallback_chain,
                     version, previous_version)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 1, 0)
                """, (
                    principle_text,
                    json.dumps([f"calibration_{samples}_samples"]),
                    domain_full,
                    confidence,
                    ts,
                    pass_rate,
                    template["condition"],
                    template["action"],
                    template["fallback_chain"],
                ))
                logger.info(f"Principle created: {domain_full} v1")
                return True
        except Exception as e:
            logger.warning(f"Principle update error: {e}", exc_info=True)
            return False

    def get_action(self, domain: str, verdict: str, confidence: float,
                   source: str = "", sources_succeeded: int = 0) -> dict:
        """
        Get recommended action for a verdict based on principle rules.

        Returns:
            {action, fallback_chain, should_apply}
        """
        rule = self.get_rule(domain)
        if not rule:
            return {"action": "none", "fallback_chain": "[]", "should_apply": False}

        condition = rule.get("rule_condition", "")
        action = rule.get("rule_action", "none")
        fallback = rule.get("fallback_chain", "[]")

        # Evaluate condition
        should_apply = self._evaluate_condition(
            condition, verdict, confidence, source, sources_succeeded
        )

        return {
            "action": action,
            "fallback_chain": fallback,
            "should_apply": should_apply,
            "condition": condition,
            "version": rule.get("version", 0),
        }

    def _evaluate_condition(self, condition: str, verdict: str,
                            confidence: float, source: str,
                            sources_succeeded: int) -> bool:
        """Evaluate if-then condition."""
        if not condition:
            return False

        cond = condition.lower()
        # [SCP-DNA-FIX R14-BUG004] ROOT CAUSE FIX (not cascade).
        # 5-Whys analysis:
        #   Symptom: source IN ('chemistry', 'physics') never matched when
        #   source='Chemistry' (case mismatch). Chemistry rules unreachable.
        #   Why 1: `source not in sources_list` compared 'Chemistry' vs
        #   'chemistry' → False
        #   Why 2: V104.34 #57 fix lowercased source in the `==` branch
        #   (line 375) but FORGOT the `IN (...)` branch (line 382)
        #   Why 3: Each branch independently lowercases (or doesn't),
        #   so sibling branches can diverge
        #   Why 4: source is lowercased AD-HOC per branch instead of ONCE
        #   at function entry
        #   Why 5 (ROOT): source normalization is FRAGMENTED across branches.
        #         Each new branch must remember to lowercase → easy to forget
        #         → bug class recurs.
        # ROOT FIX: lowercase source ONCE at function entry into
        # `source_lower`. ALL branches use `source_lower`. This eliminates
        # the bug CLASS at origin — sibling branches can't reintroduce it.
        # (Cascade fix would patch line 382 with `source.lower() not in
        # sources_list` — but leaves the fragmentation, so next branch
        # added will reintroduce the bug.)
        source_lower = (source or "").lower()

        # Simple condition evaluator (not full expression parser)
        # verdict == 'FAIL'
        if "verdict == 'fail'" in cond:
            if verdict != "FAIL":
                return False

        # verdict == 'UNKNOWN'
        if "verdict == 'unknown'" in cond:
            if verdict != "UNKNOWN":
                return False

        # confidence < X
        m = re.search(r'confidence\s*<\s*([\d.]+)', cond)
        if m:
            threshold = float(m.group(1))
            if confidence >= threshold:
                return False

        # sources_succeeded < N
        m = re.search(r'sources_succeeded\s*<\s*(\d+)', cond)
        if m:
            n = int(m.group(1))
            if sources_succeeded >= n:
                return False

        # source == 'X' (check if source matches)
        m = re.search(r"source\s*==\s*'([^']+)'", cond)
        if m:
            expected_source = m.group(1)
            if source_lower != expected_source:
                return False

        # source IN (...) — check if source is in list
        m = re.search(r"source\s+in\s+\(([^)]+)\)", cond)
        if m:
            sources_list = [s.strip().strip("'\"") for s in m.group(1).split(",")]
            if source_lower not in sources_list:
                return False

        # All conditions passed
        return True

    def get_all_rules(self) -> list[dict]:
        """Get all principle rules (latest version per domain)."""
        try:
            rows = db_query_all("""
                SELECT * FROM meta_principles
                WHERE id IN (
                    SELECT MAX(id) FROM meta_principles GROUP BY domain
                )
                ORDER BY domain
            """)
            return [dict(r) for r in rows] if rows else []
        except Exception as exc:
            logger.warning("principle_rules: active rules query failed, returning empty: %s", exc, exc_info=True)
            return []

    def get_stats(self) -> dict:
        """Stats."""
        try:
            total = db_query_one("SELECT COUNT(*) as cnt FROM meta_principles")["cnt"]
            domains = db_query_one(
                "SELECT COUNT(DISTINCT domain) as cnt FROM meta_principles"
            )["cnt"]
            avg_version = db_query_one(
                "SELECT AVG(version) as avg FROM meta_principles WHERE version > 0"
            )["avg"] or 1
            return {
                "total_principles": total,
                "unique_domains": domains,
                "avg_version": round(avg_version, 1),
                "rule_templates": len(DOMAIN_RULES),
            }
        except Exception as e:
            logger.warning("Principle rules get_stats failed: %s", e, exc_info=True)
            return {"error": str(e)}


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V41 Principle Rule Engine")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--test", type=str, help="Test action for domain")
    args = parser.parse_args()

    engine = PrincipleRuleEngine()

    if args.stats:
        stats = engine.get_stats()
        print("\n  Principle Rule Stats:")
        for k, v in stats.items():
            print(f"    {k:20s} {v}")
        return

    if args.list:
        rules = engine.get_all_rules()
        print(f"\n  Principle Rules ({len(rules)}):")
        for r in rules:
            print(f"\n  [{r.get('domain', '?')}] v{r.get('version', 0)}")
            print(f"    Condition: {r.get('rule_condition', '?')}")
            print(f"    Action: {r.get('rule_action', '?')}")
            print(f"    Fallback: {r.get('fallback_chain', '?')}")
            print(f"    Confidence: {r.get('confidence', 0):.2f}")
            print(f"    Applied: {r.get('applied_count', 0)}, Success: {r.get('success_rate', 0):.2f}")
        return

    if args.test:
        action = engine.get_action(args.test, "FAIL", 0.3, "PythonAST", 1)
        print(f"\n  Action for {args.test} (FAIL, conf=0.3, source=PythonAST):")
        print(f"    Should apply: {action['should_apply']}")
        print(f"    Action: {action['action']}")
        print(f"    Fallback: {action['fallback_chain']}")
        return

    print("Use --stats, --list, or --test <domain>")


if __name__ == "__main__":
    main()
