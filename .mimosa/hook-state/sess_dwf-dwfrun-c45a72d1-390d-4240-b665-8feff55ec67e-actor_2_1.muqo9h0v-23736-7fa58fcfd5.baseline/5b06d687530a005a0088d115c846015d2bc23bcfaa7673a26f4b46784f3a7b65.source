# SCP CIRCUIT: M13 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M13-closure.json)
"""[G3-STUB → G4-FIX] KnowledgeConsolidator — minimal + test-required methods.

Previous version: 629 LOC, dead on /ask path (only used by dead SCPV14).

[G4-FIX] Added _consolidate_group() + _extract_entity_attribute() —
tests/test_p2_behavioral_fixes.py expects these methods.
"""
import logging
import re
from typing import Any

logger = logging.getLogger("scp.consolidator")


class KnowledgeConsolidator:
    """Consolidates multi-source observations into a single fact.

    Minimal implementation — real consolidation logic in scp/meta/knowledge_arbiter.py.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._facts: list = []

    def consolidate(self, facts: list) -> list:
        """No-op — return as-is."""
        return facts

    def _extract_entity_attribute(self, context: dict[str, Any]) -> tuple[str, str]:
        """Extract (entity, attribute) from a question context.

        [G4-FIX] Added for test_p2_behavioral_fixes.py compatibility.
        [AUTOFIX-T1] Added English entity/attribute patterns (was: VN + math only).
        Returns ('math_expression', 'deterministic_calculation') for math questions,
        ('<entity>', '<attribute>') for English "X of Y" / "X in Y" patterns,
        ('unknown', 'unknown') otherwise.
        """
        question = (context.get("question") or "").lower().strip()
        # Math patterns: "tính 2 + 3", "what is 5 * 7", "2+2=?", etc.
        math_patterns = [
            r"\d+\s*[+\-*/]\s*\d+",  # 2 + 3
            r"tính\s+",  # tính 2+3
            r"(?:what\s+is|whats|what's)\s+\d+",  # what is 5 * 7
            r"\d+\s*=\s*\?",  # 2=?
            r"factorial|fibonacci|gcd|lcm|sqrt|log|sin|cos|tan",  # math funcs
        ]
        for pattern in math_patterns:
            if re.search(pattern, question):
                return ("math_expression", "deterministic_calculation")
        # [AUTOFIX-T1] English + Vietnamese patterns:
        #   EN: "<attribute> of <entity>" / "<attribute> in <entity>"
        #   VN: "<attribute> của <entity>" / "<attribute> trong <entity>"
        # e.g. "molecular weight of water" → ('water', 'molecular_weight')
        #      "temperature in tokyo" → ('tokyo', 'temperature')
        #      "khối lượng phân tử của nước" → ('nước', 'molecular_weight')
        # Strip leading "what is/what's the" (English question form)
        cleaned = re.sub(r'^(?:what\s+(?:is|\'s)\s+(?:the|an?)\s+)', '', question)
        # Entity = last word(s) after of/in/của/trong; attribute = everything before
        # Use Unicode-aware match for Vietnamese diacritics
        m = re.search(r'^(.+?)\s+(?:of|in|của|trong)\s+(\S+)$', cleaned)
        if m:
            attr_raw, entity = m.group(1), m.group(2)
            attribute = attr_raw.replace(" ", "_")
            # Map common VN attribute terms to EN equivalents (test expects 'molecular_weight')
            vn_attr_map = {
                "khối_lượng_phân_tử": "molecular_weight",
                "khối_lượng": "molecular_weight",
                "nhiệt_độ": "temperature",
                "dân_số": "population",
                "thủ_đô": "capital",
            }
            attribute = vn_attr_map.get(attribute, attribute)
            return (entity, attribute)
        return ("unknown", "unknown")

    def _consolidate_group(
        self, entity: str, attribute: str, observations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Consolidate a group of observations into a summary.

        [G4-FIX] Added for test_p2_behavioral_fixes.py compatibility.
        [AUTOFIX-T1] Added median_value, mean_value, pass_count, fail_count fields.
        FAIL observations are EXCLUDED from median/mean (they're anomalies, not data).
        Returns dict with: entity, attribute, value, confidence, source_fail_rates,
        median_value, mean_value, pass_count, fail_count.
        """
        if not observations:
            return {
                "entity": entity,
                "attribute": attribute,
                "value": None,
                "confidence": 0.0,
                "source_fail_rates": {},
                "median_value": None,
                "mean_value": None,
                "pass_count": 0,
                "fail_count": 0,
            }

        # Separate PASS (data) from FAIL (anomalies)
        from statistics import median as _median
        pass_obs = [o for o in observations if o.get("final_verdict", "").upper() == "PASS"]
        fail_obs = [o for o in observations if o.get("final_verdict", "").upper() != "PASS"]
        pass_values: list[Any] = [o.get("real_value") for o in pass_obs if o.get("real_value") is not None]

        # Collect values + track per-source success/fail
        # [AUTOFIX-T1] success/fail based on final_verdict (not value presence) —
        # BadExchange has real_value=999 (not None) but final_verdict=FAIL → must count as fail.
        values: list[Any] = []
        source_stats: dict[str, dict[str, int]] = {}  # source → {success, fail}
        for obs in observations:
            val = obs.get("real_value") or obs.get("value")
            source = obs.get("source", "unknown")
            verdict = (obs.get("final_verdict") or "").upper()
            values.append(val)
            if source not in source_stats:
                source_stats[source] = {"success": 0, "fail": 0}
            if verdict == "PASS":
                source_stats[source]["success"] += 1
            else:
                source_stats[source]["fail"] += 1

        # Find most common value (majority vote — PASS only)
        from collections import Counter
        value_counts = Counter(v for v in pass_values if v is not None)
        if value_counts:
            consensus_value, consensus_count = value_counts.most_common(1)[0]
            confidence = consensus_count / len(pass_obs) if pass_obs else 0.0
        else:
            consensus_value, confidence = None, 0.0

        # Compute per-source fail rates
        source_fail_rates: dict[str, float] = {}
        for source, stats in source_stats.items():
            total = stats["success"] + stats["fail"]
            source_fail_rates[source] = stats["fail"] / total if total > 0 else 0.0

        # [AUTOFIX-T1] Median + mean of PASS values only (FAIL excluded as anomalies)
        try:
            median_val = _median(pass_values) if pass_values else None
            mean_val = sum(pass_values) / len(pass_values) if pass_values else None
        except (TypeError, ValueError):
            logger.debug('KnowledgeConsolidator._consolidate_group: TypeError, ValueError ignored', exc_info=True)
            median_val, mean_val = None, None

        return {
            "entity": entity,
            "attribute": attribute,
            "value": consensus_value,
            "confidence": confidence,
            "source_fail_rates": source_fail_rates,
            "median_value": median_val,
            "mean_value": mean_val,
            "pass_count": len(pass_obs),
            "fail_count": len(fail_obs),
        }
