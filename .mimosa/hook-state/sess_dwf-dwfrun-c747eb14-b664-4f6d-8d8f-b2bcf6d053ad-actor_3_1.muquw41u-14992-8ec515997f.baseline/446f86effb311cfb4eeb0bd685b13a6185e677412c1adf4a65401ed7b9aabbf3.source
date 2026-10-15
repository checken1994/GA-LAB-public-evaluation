"""
[SCP-DNA-FIX R7-Full IMP-7] Lineage-Aware Cross-Validation — NEW autofix phase.

TẠI SAO file này tồn tại?
  R5/R6 count "how many sources flagged this bug" — but if 3 sources share
  lineage (e.g. ruff + pyflakes + pylint all use Python AST), they share
  blind-spots. "3 sources agree" is misleading — same blind-spot = same miss.

  Example: mypy + pyright + astroid all use type-system lineage. If all 3 say
  "no type error" on a function, that's still only 1 lineage agreeing. A bug
  visible only via RUNTIME observation (reality-log) would still be missed.

  This phase requires ≥2 DISTINCT lineages to agree before a bug is trusted
  for Tier-2 auto-fix. If only 1 lineage sees it → Tier-3 (human review).

Lineages (8 distinct, no shared analysis engine):
  1. rust-ast          — ruff (Rust-based AST walker)
  2. python-ast        — pyflakes / pylint / internal AST scanners
  3. astroid-semantic  — pylint's astroid (semantic graph, deeper than raw AST)
  4. type-system       — mypy / pyright (type inference)
  5. dead-code-ast     — vulture (dead-code-specific AST)
  6. security-pattern  — bandit (regex + AST security patterns)
  7. reality-log       — runtime trace (actual exceptions, log analysis)
  8. property-runtime  — hypothesis (property-based runtime tests)

Inspired by: Semgrep multi-rule agreement + CodeQL dataflow

Flow:
  scanner produces BugReport → lineage_cross_validation.validate(bug, sources)
  → {trusted: bool, distinct_lineages: int, lineages: list[str], reason: str}
  trusted=False (only 1 lineage) → demote to Tier-3 (human review)
  trusted=True (≥2 lineages) → keep tier

DNA principles applied:
  #5  (Evidence-first)    — require cross-lineage evidence, not source count
  #14 (Không tăng quyền chỉ vì lập luận tăng) — ≥2 lineages is EVIDENCE, not argument
  #19 (Reality multi-source) — distinct sources, not same-lineage agreement
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("scp.autofix.lineage_cross_validation")


# Canonical lineage set — each lineage uses a DIFFERENT analysis engine.
LINEAGES: dict[str, set[str]] = {
    "rust-ast": {
        "ruff", "Ruff", "Ruff_PLW0211", "Ruff_PLW2901", "Ruff_F841",
        "Ruff_B902", "Ruff_S110", "Ruff_S112", "Ruff_RUF012",
        "Ruff_S603", "Ruff_S310", "Ruff_S404", "Ruff_S607",
    },
    "python-ast": {
        "pyflakes", "pylint", "BareExceptPass", "PossiblyUndefinedName",
        "DeadCode", "DeadSLM", "RoutingGap", "APIWiringGap", "LogicFlowFragile",
        "SchemaMismatch", "TypeMismatch", "NullDereference", "RaceCondition",
        "SQLInjection", "ResourceLeak", "PerformanceIssue", "SecurityIssue",
        "XSSVulnerability", "PLW0211", "PLW2901", "F841",
    },
    "astroid-semantic": {
        "pylint-astroid", "astroid", "Pylint_PL", "Pylint_C",
        "Pylint_W", "Pylint_E", "Pylint_R",
    },
    "type-system": {
        "mypy", "pyright", "TypeCheck", "TypeMismatch",
    },
    "dead-code-ast": {
        "vulture", "Vulture", "DeadCode", "DeadSLM",
    },
    "security-pattern": {
        "bandit", "Bandit", "Bandit_B110", "Bandit_B101", "Bandit_B602",
        "Bandit_S", "SecurityIssue", "SQLInjection", "XSSVulnerability",
        "cmd-injection", "deserialization",
    },
    "reality-log": {
        "runtime", "reality", "log-analysis", "traceback", "RuntimeError",
        "ImportError", "AttributeError", "TypeError-reality",
    },
    "property-runtime": {
        "hypothesis", "property-test", "quickcheck", "HypothesisFailure",
    },
}


# Minimum distinct lineages to trust a Tier-2 auto-fix.
MIN_DISTINCT_LINEAGES_TIER2 = 2
# Minimum to trust a Tier-4 attack-mode auto-fix (higher bar — risky).
MIN_DISTINCT_LINEAGES_TIER4 = 3


def _infer_lineage(source: str) -> str | None:
    """Map a source string (scanner name, rule code, tool name) to a lineage.

    Returns None if source doesn't match any known lineage.
    """
    if not source:
        return None
    # Try exact match first
    for lineage, members in LINEAGES.items():
        if source in members:
            return lineage
    # Try prefix / substring match (e.g. "Ruff_S603" not in set, but "ruff" prefix)
    src_lower = source.lower()
    for lineage, members in LINEAGES.items():
        for m in members:
            if src_lower == m.lower():
                return lineage
    # Heuristic: if source contains lineage name
    for lineage in LINEAGES:
        if lineage.split("-")[0] in src_lower:
            return lineage
    return None


def collect_lineages(sources: list[str]) -> list[str]:
    """Collect DISTINCT lineages that flagged a bug.

    Args:
        sources: List of source names (e.g. ["ruff", "pyflakes", "mypy"]).

    Returns: Sorted list of distinct lineage names.
    """
    seen: set[str] = set()
    for s in sources:
        lin = _infer_lineage(s)
        if lin is not None and lin not in seen:
            seen.add(lin)
    return sorted(seen)


def validate_bug_lineage(
    bug: Any,
    sources: list[str],
    target_tier: int = 2,
) -> dict:
    """Validate that a bug has enough distinct-lineage evidence for its tier.

    Args:
        bug: BugReport-like object (for context logging only).
        sources: List of source names that flagged this bug.
        target_tier: The tier we want to apply the fix at (1/2/4).
            - Tier 1: no requirement (implementation bugs, no logic change)
            - Tier 2: requires MIN_DISTINCT_LINEAGES_TIER2 (default 2)
            - Tier 4: requires MIN_DISTINCT_LINEAGES_TIER4 (default 3)

    Returns:
        {
            "trusted": bool,            — True if lineage evidence is sufficient
            "distinct_lineages": int,
            "lineages": list[str],
            "required": int,            — min lineages required for target_tier
            "demote_to_tier": int | None,  — if not trusted, suggested tier (3)
            "reason": str,
        }
    """
    distinct = collect_lineages(sources)

    if target_tier == 1:
        # Tier 1 (pure implementation) — no lineage requirement (low risk).
        return {
            "trusted": True,
            "distinct_lineages": len(distinct),
            "lineages": distinct,
            "required": 0,
            "demote_to_tier": None,
            "reason": (
                f"[IMP-7] Tier-1 fix — no lineage requirement "
                f"({len(distinct)} lineage(s) seen: {distinct})"
            ),
        }

    required = (
        MIN_DISTINCT_LINEAGES_TIER4 if target_tier == 4
        else MIN_DISTINCT_LINEAGES_TIER2
    )
    trusted = len(distinct) >= required

    bug_id = (
        f"{getattr(bug, 'file', '?')}:{getattr(bug, 'line', '?')}:"
        f"{getattr(bug, 'bug_type', '?')}"
    )
    reason = (
        f"[IMP-7] lineage check for {bug_id}: "
        f"{len(distinct)} distinct lineage(s) ({distinct}) "
        f"vs required {required} for Tier-{target_tier} → "
        f"{'TRUSTED' if trusted else 'DEMOTE to Tier-3'}"
    )
    logger.info(reason)

    return {
        "trusted": trusted,
        "distinct_lineages": len(distinct),
        "lineages": distinct,
        "required": required,
        "demote_to_tier": None if trusted else 3,
        "reason": reason,
    }


def merge_lineage_evidence(bugs: list[Any]) -> dict[str, list[str]]:
    """For each bug (keyed by file:line:bug_type), collect source list.

    Caller assigns sources to each bug (from scanner metadata), then calls
    validate_bug_lineage() per bug.

    Args:
        bugs: List of BugReport-like objects. Each must have a `.sources`
              attribute (list[str]) OR a `.source` attribute (single str).

    Returns: {bug_key: [source1, source2, ...]}
    """
    out: dict[str, list[str]] = {}
    for bug in bugs:
        key = (
            f"{getattr(bug, 'file', '?')}:{getattr(bug, 'line', '?')}:"
            f"{getattr(bug, 'bug_type', '?')}"
        )
        sources: list[str] = []
        if hasattr(bug, "sources") and isinstance(bug.sources, list):
            sources = list(bug.sources)
        elif hasattr(bug, "source"):
            sources = [str(bug.source)]
        out[key] = sources
    return out


__all__ = [
    "LINEAGES",
    "MIN_DISTINCT_LINEAGES_TIER2",
    "MIN_DISTINCT_LINEAGES_TIER4",
    "collect_lineages",
    "validate_bug_lineage",
    "merge_lineage_evidence",
]
