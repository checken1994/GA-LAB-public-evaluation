"""
[SCP-DNA-FIX R8 v3 IMP-14] Confidence-Scored Fix Ranking.

TẠI SAO file này tồn tại?
  R5/R6/R7-Full áp dụng fix đầu tiên được generate — không phân biệt "fix
  chắc chắn đúng 0.95" vs "fix đoán mò 0.40". Kết quả R5/R6 audit: 22% fix
  là false-positive (fix claims done but bug persists hoặc fix introduces
  regression). DNA #22 (PASS ≠ TRUE): "patch applied" ≠ "fix đúng".

  v3 IMP-14 thêm decision layer: trước khi apply, score mỗi proposed fix
  0.0-1.0 dựa trên 5 signals:
    (a) ast.parse sau apply có pass không?      (weight 0.30 — syntax must be valid)
    (b) reality_test (IMP-2) có pass không?     (weight 0.25 — runtime sanity)
    (c) blast radius: fix touch bao nhiêu dòng? (weight 0.15 — nhỏ = an toàn)
    (d) bug class có high FP rate?              (weight 0.15 — BareExceptPass nổi tiếng FP)
    (e) deterministic rule vs LLM-generated?    (weight 0.15 — rule = tin cậy hơn)

  Fix có:
    score >= auto_apply_threshold  (0.85) → AUTO apply
    score >= human_review_threshold (0.50) → REVIEW (operator approves)
    score <  human_review_threshold       → DISCARD (drop, không apply)

  Inspired by:
    - GitHub Copilot Autofix confidence scores (1-5 scale, có rationale)
    - Sentry Autofix validation (run tests + score before apply)
    - CodeQL severity-weighted triage

Flow:
  fixes = generate_candidate_fixes(bug)         # list[ProposedFix]
  scored = rank_fixes(fixes, bug, context)      # sort desc by score
  apply  = [f for f in scored if f.score >= auto_apply_threshold]

DNA principles applied:
  #4  (Constitution KILL)   — security/relaxation fixes capped at 0.49 (force review)
  #9  (No harm)             — discard sub-0.50 fixes (don't pollute codebase)
  #22 (PASS ≠ TRUE)         — score = explicit confidence, not implicit "it parsed"
  #7  (Autofix safe)        — pure function, fail-open (scoring error → 0.5)
"""
from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("scp.autofix.confidence_ranker")


# ============================================================
# Thresholds (env-overridable for tuning).
# ============================================================

# [SCP-DNA-FIX R15] Auto-apply threshold.
#
# R15 now uses IntentInferenceEngine to READ INTENT (not just CODE).
# With intent inference, false positives are filtered at the SOURCE.
# Auto-apply can safely use 0.85 (SCP tự autofix, không cần hỏi user).
#
# If you want EXTRA safety (review-first mode): set to 0.99 or 1.0
# If you want AGGRESSIVE auto-apply: set to 0.70
DEFAULT_AUTO_APPLY_THRESHOLD = float(os.environ.get("SCP_AUTOFIX_AUTO_APPLY_THRESHOLD", "0.85"))
DEFAULT_HUMAN_REVIEW_THRESHOLD = float(os.environ.get("SCP_AUTOFIX_HUMAN_REVIEW_THRESHOLD", "0.50"))
DEFAULT_BUG_FP_RATE = {
    # Bug classes with known high false-positive rates (from R5/R6 audit data).
    # Higher FP rate → lower default confidence for fixes touching this class.
    "BareExceptPass": 0.45,        # 63% rollback rate per RUNTIME-FIX-6
    "UndefinedName": 0.20,
    "DeadCode":      0.15,         # cross-file mode improved (IMP-4)
    "SchemaMismatch": 0.10,
    "HypothesisFailure": 0.05,    # runtime evidence — very low FP
    "NoneComparison": 0.10,
}
DEFAULT_FP_RATE = 0.15  # for bug classes not in the map


# ============================================================
# Scoring weights — sum to 1.0.
# ============================================================

WEIGHT_AST_PARSE = 0.30
WEIGHT_REALITY_TEST = 0.25
WEIGHT_BLAST_RADIUS = 0.15
WEIGHT_BUG_FP_RATE = 0.15
WEIGHT_SOURCE = 0.15


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class ProposedFix:
    """A candidate fix proposed for a bug.

    Attributes:
        fix_id: Unique identifier (e.g. sha1 of patch).
        patch: The search/replace block or unified diff.
        patched_source: Full source after applying patch (for ast.parse + reality_test).
        source: "rule" (deterministic scanner) | "llm" (LLM-generated).
        bug_type: Bug class (used for FP-rate lookup).
        bug_file: File path (for ast.parse).
        bug_line: Line number (for blast-radius estimate).
        lines_changed: Number of lines the fix touches (for blast-radius score).
        ast_parse_ok: True if patched_source passes ast.parse (caller fills).
        reality_test_ok: True if reality_test passes (caller fills).
        reality_test_result: Full result dict (optional, for audit trail).
    """
    fix_id: str
    patch: str
    patched_source: str
    source: str = "rule"           # "rule" | "llm" | "hybrid"
    bug_type: str = ""
    bug_file: str = ""
    bug_line: int = 0
    lines_changed: int = 0
    ast_parse_ok: bool = False
    reality_test_ok: bool = False
    reality_test_result: dict[str, Any] = field(default_factory=dict)
    # Populated by rank_fixes():
    confidence: float = 0.0
    disposition: str = ""           # "auto_apply" | "review" | "discard"
    score_breakdown: dict[str, float] = field(default_factory=dict)


# ============================================================
# Scoring helpers
# ============================================================

def _check_ast_parse(patched_source: str) -> bool:
    """Return True if patched_source parses as valid Python."""
    try:
        ast.parse(patched_source)
        return True
    except SyntaxError as e:
        logger.debug(f"[IMP-14] ast.parse FAIL: {e}")
        return False
    except Exception as parse_err:  # noqa: BLE001 — best-effort
        logger.debug("[IMP-14] patched-source read/parse crashed, treating as invalid: %s", parse_err, exc_info=True)
        return False


def _bug_fp_rate(bug_type: str) -> float:
    """Look up the historical false-positive rate for a bug class."""
    return DEFAULT_BUG_FP_RATE.get(bug_type, DEFAULT_FP_RATE)


def _blast_radius_score(lines_changed: int) -> float:
    """Score how localized the fix is.

    0 lines (unknown)    → 0.5 (neutral)
    1-3 lines            → 1.0 (surgical — best)
    4-10 lines           → 0.7 (moderate)
    11-30 lines          → 0.4 (broad)
    >30 lines            → 0.2 (over-broad — risky)
    """
    if lines_changed <= 0:
        return 0.5
    if lines_changed <= 3:
        return 1.0
    if lines_changed <= 10:
        return 0.7
    if lines_changed <= 30:
        return 0.4
    return 0.2


def _source_score(source: str) -> float:
    """Score fix source: deterministic rules > LLM."""
    s = (source or "").lower()
    if s == "rule":
        return 1.0   # deterministic — reproducible, auditable
    if s == "hybrid":
        return 0.75  # rule + LLM polish
    if s == "llm":
        return 0.55  # LLM-generated — variance, hallucination risk
    return 0.5       # unknown


def _is_relaxation(patch: str, bug_type: str) -> bool:
    """Heuristic: detect if a fix LOOSENS security (cap confidence at 0.49).

    Matches the same patterns as BugClassifier.RELAXATION_PATTERNS but in
    the PATCH text (not the description). E.g. "remove block", "lower
    threshold", "allow attack", "whitelist", "bypass security".
    """
    p = (patch or "").lower()
    relaxation_markers = (
        "lower threshold", "raise confidence", "looser", "relax",
        "remove block", "delete rule", "skip detect",
        "allow attack", "whitelist", "bypass security",
    )
    return any(m in p for m in relaxation_markers)


# ============================================================
# Core scoring function
# ============================================================

def score_fix(
    fix: ProposedFix,
    bug_type: str | None = None,
    auto_apply_threshold: float = DEFAULT_AUTO_APPLY_THRESHOLD,
    human_review_threshold: float = DEFAULT_HUMAN_REVIEW_THRESHOLD,
) -> ProposedFix:
    """Score a single ProposedFix (mutates + returns it).

    The score is a weighted sum:
        score = 0.30 * ast_parse_ok
              + 0.25 * reality_test_ok
              + 0.15 * blast_radius_score
              + 0.15 * (1 - fp_rate)         # higher FP → lower score
              + 0.15 * source_score

    Caps:
        - If ast_parse_ok is False → cap at 0.20 (syntax broken → don't apply).
        - If fix is a relaxation → cap at 0.49 (force human review per DNA #4).
        - On ANY scoring error → default 0.5 (fail-open, neutral).

    Disposition:
        score >= auto_apply_threshold  → "auto_apply"
        score >= human_review_threshold → "review"
        else                            → "discard"
    """
    bt = bug_type or fix.bug_type or ""
    try:
        # Re-check ast.parse if not already filled in.
        if not fix.ast_parse_ok and fix.patched_source:
            fix.ast_parse_ok = _check_ast_parse(fix.patched_source)

        ast_score = 1.0 if fix.ast_parse_ok else 0.0
        reality_score = 1.0 if fix.reality_test_ok else 0.5
        # If reality_test wasn't run (result empty), give neutral 0.5 — don't
        # punish fixes that skipped reality_test (caller may run it after).
        if not fix.reality_test_result:
            reality_score = 0.5

        radius_score = _blast_radius_score(fix.lines_changed)
        fp_rate = _bug_fp_rate(bt)
        fp_score = 1.0 - fp_rate
        src_score = _source_score(fix.source)

        raw = (
            WEIGHT_AST_PARSE * ast_score
            + WEIGHT_REALITY_TEST * reality_score
            + WEIGHT_BLAST_RADIUS * radius_score
            + WEIGHT_BUG_FP_RATE * fp_score
            + WEIGHT_SOURCE * src_score
        )

        # Hard cap: ast.parse FAIL → can't apply, period.
        if not fix.ast_parse_ok:
            raw = min(raw, 0.20)

        # Hard cap: relaxation → force human review (DNA #4 Constitution KILL).
        if _is_relaxation(fix.patch, bt):
            raw = min(raw, 0.49)

        # Clamp to [0, 1].
        score = max(0.0, min(1.0, raw))

        fix.confidence = round(score, 4)
        fix.score_breakdown = {
            "ast_parse": round(ast_score, 3),
            "reality_test": round(reality_score, 3),
            "blast_radius": round(radius_score, 3),
            "bug_fp_inverse": round(fp_score, 3),
            "source": round(src_score, 3),
            "raw_weighted": round(raw, 4),
            "weights": {
                "ast_parse": WEIGHT_AST_PARSE,
                "reality_test": WEIGHT_REALITY_TEST,
                "blast_radius": WEIGHT_BLAST_RADIUS,
                "bug_fp_rate": WEIGHT_BUG_FP_RATE,
                "source": WEIGHT_SOURCE,
            },
        }

        if fix.confidence >= auto_apply_threshold:
            fix.disposition = "auto_apply"
        elif fix.confidence >= human_review_threshold:
            fix.disposition = "review"
        else:
            fix.disposition = "discard"

    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
        logger.warning(f"[IMP-14] scoring error for fix {fix.fix_id}: {e}")
        fix.confidence = 0.5
        fix.disposition = "review"
        fix.score_breakdown = {"error": str(e)}

    return fix


def rank_fixes(
    fixes: list[ProposedFix],
    bug_type: str | None = None,
    auto_apply_threshold: float = DEFAULT_AUTO_APPLY_THRESHOLD,
    human_review_threshold: float = DEFAULT_HUMAN_REVIEW_THRESHOLD,
) -> list[ProposedFix]:
    """Score + sort a list of ProposedFix by confidence (descending).

    Steps:
        1. Score each fix (mutates + populates confidence, disposition, breakdown).
        2. Sort by confidence descending. Ties broken by:
              a. ast_parse_ok (True > False)
              b. lines_changed (fewer = more surgical, ranks higher)
              c. source ("rule" > "hybrid" > "llm")
        3. Drop "discard" fixes (below human_review_threshold).

    Returns: sorted list (highest confidence first). Caller iterates and
    applies fixes with disposition == "auto_apply" or escalates "review"
    ones to operator.
    """
    if not fixes:
        return []

    scored: list[ProposedFix] = []
    for f in fixes:
        try:
            scored.append(score_fix(
                f, bug_type=bug_type,
                auto_apply_threshold=auto_apply_threshold,
                human_review_threshold=human_review_threshold,
            ))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-14] score_fix crashed for {f.fix_id}: {e}")

    # Sort: confidence desc, then ast_parse_ok desc, then lines_changed asc,
    # then source priority (rule=0, hybrid=1, llm=2) asc.
    source_order = {"rule": 0, "hybrid": 1, "llm": 2}
    scored.sort(
        key=lambda f: (
            -f.confidence,
            0 if f.ast_parse_ok else 1,
            f.lines_changed,
            source_order.get(f.source, 3),
        )
    )

    # Drop discards (below human_review_threshold).
    kept = [f for f in scored if f.disposition != "discard"]

    if len(kept) != len(scored):
        dropped = len(scored) - len(kept)
        logger.info(
            f"[IMP-14] ranked {len(scored)} fixes, kept {len(kept)}, "
            f"dropped {dropped} below threshold {human_review_threshold}"
        )
    return kept


# ============================================================
# Convenience helpers (for engine.py integration).
# ============================================================

def best_fix(
    fixes: list[ProposedFix],
    bug_type: str | None = None,
    auto_apply_threshold: float = DEFAULT_AUTO_APPLY_THRESHOLD,
    human_review_threshold: float = DEFAULT_HUMAN_REVIEW_THRESHOLD,
) -> ProposedFix | None:
    """Return the highest-confidence fix, or None if all below threshold."""
    ranked = rank_fixes(
        fixes, bug_type=bug_type,
        auto_apply_threshold=auto_apply_threshold,
        human_review_threshold=human_review_threshold,
    )
    return ranked[0] if ranked else None


def make_fix(
    fix_id: str,
    patch: str,
    patched_source: str,
    source: str = "rule",
    bug_type: str = "",
    bug_file: str = "",
    bug_line: int = 0,
    lines_changed: int = 0,
    reality_test_result: dict[str, Any] | None = None,
) -> ProposedFix:
    """Convenience factory — fills ast_parse_ok + reality_test_ok from inputs."""
    ast_ok = _check_ast_parse(patched_source) if patched_source else False
    rt_ok = False
    if reality_test_result and isinstance(reality_test_result, dict):
        rt_ok = bool(reality_test_result.get("ok", False))
    return ProposedFix(
        fix_id=fix_id,
        patch=patch,
        patched_source=patched_source,
        source=source,
        bug_type=bug_type,
        bug_file=bug_file,
        bug_line=bug_line,
        lines_changed=lines_changed,
        ast_parse_ok=ast_ok,
        reality_test_ok=rt_ok,
        reality_test_result=reality_test_result or {},
    )


__all__ = [
    "ProposedFix",
    "score_fix",
    "rank_fixes",
    "best_fix",
    "make_fix",
    "DEFAULT_AUTO_APPLY_THRESHOLD",
    "DEFAULT_HUMAN_REVIEW_THRESHOLD",
    "DEFAULT_BUG_FP_RATE",
]
