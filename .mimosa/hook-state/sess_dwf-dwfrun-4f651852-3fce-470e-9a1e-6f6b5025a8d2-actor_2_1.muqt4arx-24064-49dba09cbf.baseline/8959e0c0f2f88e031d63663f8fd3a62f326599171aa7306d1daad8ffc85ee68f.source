"""
 ImpactPrioritization layer — cùng cấp WHY (2-layer: action + self-verify).

TẠI SAO: WHY gate (v9.0) hỏi "có nên fix bug này không?" (action layer — necessity +
falsification). _prioritize_bugs hỏi "fix bug nào TRƯỚC?" (verify/prioritize layer).
WHY + prioritize = cùng độ sâu (2 layer mỗi cái). Non-blocking: prioritize error
→ fail-open (return original order).

Priority order (CWE-based):
  CRITICAL (4): security bugs (CWE), race conditions → fix first
  HIGH     (3): type mismatch, null deref → fix second
  MEDIUM   (2): SQL injection, resource leak → fix third
  LOW      (1): dead code, performance → last

Returns NEW list sorted by priority (highest first). Original list unchanged.

Extracted from `autofix/runner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("scp.autofix.runner")


def _prioritize_bugs(bugs: list) -> list:
    """Prioritize bugs by security impact (CRITICAL > HIGH > MEDIUM > LOW).

    Args:
        bugs: List of BugReport objects (or duck-typed objects with .bug_type, .description).

    Returns:
        New list sorted by priority (highest first). Original list unchanged.
        On any error → fail-open (return original list order).
    """
    try:
        #  Bug type → impact priority mapping
        # CRITICAL: security bugs (CWE-based) + race conditions
        # HIGH: type/null safety (can crash production)
        # MEDIUM: SQL injection + resource leak (data/DoS risk)
        # LOW: dead code + performance (quality issues, not safety)
        CRITICAL_TYPES = {
            "security", "cwe", "command_injection", "deserialization",
            "race_condition", "race", "deadlock",
            "hardcoded_secret", "hardcoded_path",
        }
        HIGH_TYPES = {
            "type_mismatch", "type_contract", "null_safety", "null_deref",
            "undefined_name", "nameerror", "attribute_error",
            "type_error", "value_error",
        }
        MEDIUM_TYPES = {
            "sql_injection", "sql", "resource_leak", "file_handle_leak",
            "socket_leak", "bare_except_pass", "bare_except",
        }
        LOW_TYPES = {
            "dead_code", "dead_slm", "performance", "perf",
            "routing_gap", "api_wiring", "logic_flow", "schema_mismatch",
        }

        def _impact_score(bug) -> int:
            """Return impact score (4=CRITICAL, 3=HIGH, 2=MEDIUM, 1=LOW, 0=unknown)."""
            _bug_type = (getattr(bug, "bug_type", "") or "").lower()
            _desc = (getattr(bug, "description", "") or "").lower()
            _combined = f"{_bug_type} {_desc}"
            # CRITICAL: any keyword match
            for kw in CRITICAL_TYPES:
                if kw in _combined:
                    return 4
            # HIGH
            for kw in HIGH_TYPES:
                if kw in _combined:
                    return 3
            # MEDIUM
            for kw in MEDIUM_TYPES:
                if kw in _combined:
                    return 2
            # LOW
            for kw in LOW_TYPES:
                if kw in _combined:
                    return 1
            return 0  # unknown — lowest priority

        # Sort by impact (descending) — stable sort preserves original order within same impact
        _prioritized = sorted(bugs, key=_impact_score, reverse=True)

        # Audit log
        try:
            _impact_counts = {4: 0, 3: 0, 2: 0, 1: 0, 0: 0}
            for b in _prioritized:
                _impact_counts[_impact_score(b)] = _impact_counts.get(_impact_score(b), 0) + 1
            _audit_path = Path("data") / "v91_upgrade_audit.jsonl"
            _audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": time.time(),
                    "engine": "scanner",
                    "event": "prioritize_bugs",
                    "payload": {
                        "total": len(bugs),
                        "critical": _impact_counts.get(4, 0),
                        "high": _impact_counts.get(3, 0),
                        "medium": _impact_counts.get(2, 0),
                        "low": _impact_counts.get(1, 0),
                        "unknown": _impact_counts.get(0, 0),
                    },
                }, ensure_ascii=False) + "\n")
        except Exception as _audit_err:
            logger.debug(f" prioritize audit log error (fail-open): {_audit_err}", exc_info=True)

        logger.info(
            f" Prioritized {len(_prioritized)} bugs: "
            f"CRITICAL={_impact_counts.get(4,0)}, HIGH={_impact_counts.get(3,0)}, "
            f"MEDIUM={_impact_counts.get(2,0)}, LOW={_impact_counts.get(1,0)}, "
            f"UNKNOWN={_impact_counts.get(0,0)}"
        )
        return _prioritized

    except Exception as _prio_err:
        logger.debug(f" _prioritize_bugs error (fail-open, original order): {_prio_err}", exc_info=True)
        return list(bugs)  # fail-open — return original order
