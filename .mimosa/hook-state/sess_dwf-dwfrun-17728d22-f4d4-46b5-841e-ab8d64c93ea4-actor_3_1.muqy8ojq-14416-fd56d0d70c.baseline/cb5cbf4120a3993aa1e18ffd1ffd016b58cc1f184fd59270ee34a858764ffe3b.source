# [V11-SCANNER] SemanticIntentScanner — LLM reasoning for intent classification.
#
# TẠI SAO scanner này tồn tại? (Closes the "semantic intent" gap — Task 11-b)
#   SCP's existing scanners (ruff, bandit, mypy, taint_flow, ast_scan) detect
#   PATTERNS but cannot reason about INTENT. Many flagged patterns are
#   AMBIGUOUS — they could be either:
#     (a) INTENTIONAL — a deliberate design choice (fail-open error handling,
#         a test assertion, harmless test-data shuffling), OR
#     (b) BUG — an actual defect (forgotten logging, dead code, security hole).
#
#   Examples of ambiguous patterns:
#     - `except Exception: pass`  (BLE001 / S110)
#         INTENTIONAL if fail-open design (cache miss → empty result),
#         BUG if it silences real errors that should be logged.
#     - `random.randint(...)`  (S311)
#         INTENTIONAL if shuffling test data or seeding a non-security RNG,
#         BUG if used for tokens/session IDs (needs `secrets` module).
#     - `for x in items: ... x = ...`  (PLW2901)
#         INTENTIONAL if parse-and-normalize (assign cleaned value back),
#         BUG if accidental shadowing of loop variable.
#     - `assert False` / `1 == 1`  (B015)
#         INTENTIONAL if test fixture / unreachable sentinel,
#         BUG if dead code or forgotten conditional.
#
#   Z.ai (the human analyst) can read surrounding context (docstring, function
#   purpose, caller pattern) and reason about intent. SCP's regex/AST scanners
#   cannot. This scanner uses LLM reasoning to close that gap.
#
# ARCHITECTURE:
#   1. INPUT: BugReports from OTHER scanners (ruff, bandit, mypy, taint_flow)
#      that are flagged but AMBIGUOUS (could be intentional or bug). Filter
#      by rule-code substring match against AMBIGUOUS_RULES.
#   2. LLM CALL: For each ambiguous bug, send the LLM:
#        - Bug type + scanner description
#        - Code context (±15 lines around the bug, bug line marked with `>>>`)
#        - The enclosing function's docstring (if any)
#        - The file's module docstring (if any)
#      Ask: "Is this code INTENTIONAL or a BUG? Answer with one of
#      INTENTIONAL/BUG/UNCLEAR + 1-line reason."
#   3. CLASSIFICATION:
#        - INTENTIONAL → suppress (tier=TIER_1_AUTO_FIX, description prefixed
#          "[LLM-intent] intentional — ..."). Treated as false positive.
#        - BUG         → keep original tier, enrich description with LLM's
#          reasoning ("[LLM-intent] bug confirmed — ...").
#        - UNCLEAR     → escalate to TIER_3_PERMISSION (human review) with
#          LLM's analysis attached.
#
# LLM INTEGRATION (REUSE — do NOT duplicate):
#   - `_call_openrouter(prompt, max_tokens)` from scp.autofix.llm_fix handles
#     the OpenRouter HTTP call (API key from env, payload construction,
#     error handling, response parsing).
#   - `_check_rate_limit()` from scp.autofix.llm_fix enforces the per-hour
#     LLM call cap (100/hour as of V5.5-FIX). If exceeded → UNCLEAR.
#   - `_build_fix_prompt(bug, code_context)` is imported for reference but
#     NOT used directly — it produces SEARCH/REPLACE code-fix prompts,
#     whereas this scanner needs a classification prompt. We build our own
#     `_build_intent_prompt` instead. Both share `_call_openrouter` for the
#     actual HTTP transport.
#
# RATE LIMITING:
#   Reuses `_check_rate_limit()` from llm_fix.py. If rate-limited, the bug
#   is escalated to UNCLEAR (Tier 3 human review) rather than dropped or
#   retried — this avoids burning the LLM quota on retries while ensuring
#   a human sees the ambiguous case.
#
# CACHING:
#   `_intent_cache: dict[cache_key -> (label, reason)]` keyed by
#   `"{file}:{line}:{bug_type}"`. Repeated scans of the same bug (e.g. across
#   `--full-scan` runs within the same Python process) hit the cache instead
#   of re-querying the LLM. Cache is process-local (not persistent across
#   restarts) — this is intentional, since the LLM's judgment may improve
#   with model upgrades and we don't want stale suppressions.
#
# FAIL-OPEN BEHAVIOR (NEVER BLOCK ON LLM):
#   - No OPENROUTER_API_KEY in env → return original bug unchanged + log warning.
#   - Network error / HTTPError from OpenRouter → return original bug unchanged.
#   - Source file unreadable / unparseable → return original bug unchanged.
#   - Empty LLM response → return original bug unchanged.
#   - Unparseable LLM response → escalate to UNCLEAR (Tier 3).
#
#   Rationale: the LLM is a TRIAGE aid, not a gate. If it's unavailable, the
#   downstream pipeline (engine.process_bug) still receives the original bug
#   with its original tier — same behavior as if this scanner didn't exist.
#   This satisfies DNA SCP #7 (AutoFix safe).
#
# AMBIGUOUS RULE CODES (the ones worth LLM triage):
#   - BLE001   (blind except)         — often intentional fail-open in SCP
#   - S110     (try-except-pass)      — same
#   - S311     (random usage)         — context-dependent (security vs. test)
#   - PLW2901  (redefined loop var)   — often intentional (parse-and-normalize)
#   - B015     (constant expression)  — assert-style?
#
#   Matched by substring in bug_type (e.g. "Ruff_BLE001", "Bandit_S110",
#   "RuffSecurity_BLE001" all match). This mirrors classifier.py's
#   `_NEVER_AUTO_FIX_RULES` matching strategy.
#
# API:
#   - triage_bug(bug, source_code)  — single bug, source provided by caller
#   - triage_bugs(bugs)             — batch (reads each file once, cached)
#   - scan_scp()                    — standalone: runs other scanners + triages
#
# RETURNS:
#   list[BugReport] — ambiguous bugs possibly modified (tier changed,
#   description enriched, or suppressed). Non-ambiguous bugs passed through.
from __future__ import annotations

import ast
import logging
import os
import re
from dataclasses import replace
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.llm_fix import _call_openrouter, _check_rate_limit

logger = logging.getLogger("scp.autofix.scanners.semantic_intent")

__all__ = ["triage_bug", "triage_bugs", "scan_scp"]


# ============================================================================
# Constants
# ============================================================================

# Ambiguous bug rule codes — these are PATTERNS that could be either
# intentional design choices or actual bugs depending on context. The LLM
# triages them. Matched by substring (e.g. "BLE001" in "Ruff_BLE001").
AMBIGUOUS_RULES = frozenset({
    "BLE001",   # blind except — often intentional fail-open in SCP
    "S110",     # try-except-pass — same
    "S311",     # random usage — context-dependent (security vs. test data)
    "PLW2901",  # redefined loop var — often intentional (parse-and-normalize)
    "B015",     # constant expression — assert-style?
})

# Lines of context to extract around the bug line (±15 per task spec).
_CONTEXT_LINES = 15

# Intent classification labels (LLM is instructed to emit one of these).
_INTENTIONAL = "INTENTIONAL"
_BUG = "BUG"
_UNCLEAR = "UNCLEAR"

# Process-local LLM response cache: cache_key -> (label, reason).
# Keyed by (file, line, bug_type) per task spec — same bug re-scanned in the
# same process hits the cache instead of re-querying the LLM.
_intent_cache: dict[str, tuple[str, str]] = {}


# ============================================================================
# Helpers
# ============================================================================

def _is_ambiguous(bug_type: str) -> bool:
    """Return True if bug_type contains any ambiguous rule code.

    Substring match — mirrors classifier.py's `_NEVER_AUTO_FIX_RULES`
    strategy. e.g. "Ruff_BLE001", "Bandit_S110", "RuffSecurity_BLE001"
    all match.
    """
    return any(rule in bug_type for rule in AMBIGUOUS_RULES)


def _cache_key(bug: BugReport) -> str:
    """Build a cache key for a bug — (file, line, bug_type)."""
    return f"{bug.file}:{bug.line}:{bug.bug_type}"


def _has_api_key() -> bool:
    """Return True if any OPENROUTER_API_KEY env var is set.

    Mirrors `_call_openrouter`'s key-resolution: tries OPENROUTER_API_KEY,
    then _2, then _3. We duplicate this check here so we can fail-open
    BEFORE calling _call_openrouter (avoids a wasted function call and
    gives a clearer log message).
    """
    return any(
        os.environ.get(k)
        for k in ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3")
    )


def _extract_code_context(
    source: str, target_line: int, context_lines: int = _CONTEXT_LINES
) -> str:
    """Extract ±context_lines around target_line with `>>>` marker on bug line.

    Lines are numbered from 1 (matching BugReport.line convention). The bug
    line is prefixed with `>>> ` so the LLM can identify it; context lines
    are prefixed with 4 spaces for alignment.
    """
    lines = source.splitlines()
    start = max(0, target_line - 1 - context_lines)
    end = min(len(lines), target_line + context_lines)
    out: list[str] = []
    for i in range(start, end):
        line_no = i + 1
        marker = ">>> " if line_no == target_line else "    "
        out.append(f"{marker}{line_no:4d}: {lines[i]}")
    return "\n".join(out)


def _get_module_docstring(tree: ast.Module) -> str | None:
    """Extract module-level docstring if present (PEP 224 / 257)."""
    if tree.body and isinstance(tree.body[0], ast.Expr):
        val = tree.body[0].value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return val.value
    return None


def _find_enclosing_func(
    tree: ast.Module, target_line: int
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find the deepest FunctionDef whose body contains target_line.

    "Deepest" = the most specific enclosing function (in case of nested
    defs). We pick the FunctionDef with the highest `lineno` among all
    candidates that contain target_line — since nested functions always
    start AFTER their enclosing function, the highest-lineno enclosing
    FunctionDef is the innermost.
    """
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None) or node.lineno
            if node.lineno <= target_line <= end:
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def _get_func_docstring(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef | None,
) -> str | None:
    """Extract function docstring if present (PEP 257)."""
    if func_node and func_node.body and isinstance(func_node.body[0], ast.Expr):
        val = func_node.body[0].value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return val.value
    return None


def _build_intent_prompt(
    bug: BugReport,
    code_context: str,
    func_docstring: str | None,
    module_docstring: str | None,
) -> str:
    """Build the LLM prompt for intent classification.

    NOTE: we use a dedicated intent-classification prompt rather than
    `_build_fix_prompt` from llm_fix.py. The two tasks have fundamentally
    different output formats:
      - `_build_fix_prompt` → SEARCH/REPLACE code patch (multi-line block).
      - This scanner → single label (INTENTIONAL/BUG/UNCLEAR) + 1-line reason.
    Both share `_call_openrouter` for the actual HTTP transport — we do NOT
    duplicate the OpenRouter call logic.
    """
    description = bug.description or "(no description)"
    func_doc = func_docstring or "(none)"
    mod_doc = module_docstring or "(none)"

    return f"""You are performing a SEMANTIC INTENT classification, NOT generating a code fix.

A static scanner flagged the following code pattern as a potential bug, but the
pattern is AMBIGUOUS — it could be either:
  (a) INTENTIONAL — a deliberate design choice (e.g. fail-open error handling,
      a test assertion, harmless test-data shuffling), OR
  (b) BUG — an actual mistake (e.g. forgotten logging, dead code, security
      vulnerability).

BUG TYPE: {bug.bug_type}
SCANNER DESCRIPTION: {description}

FILE MODULE DOCSTRING:
{mod_doc}

ENCLOSING FUNCTION DOCSTRING:
{func_doc}

CODE CONTEXT (line marked with `>>>` is the flagged line):
{code_context}

Question: Is this code INTENTIONAL (deliberate design choice) or a BUG (real defect)?

Answer with EXACTLY one of these three labels on the FIRST line:
- INTENTIONAL
- BUG
- UNCLEAR

Then on the NEXT line, give a 1-line reason (max 100 chars).

Example 1 (fail-open design):
INTENTIONAL
Deliberate fail-open: exception is non-critical and logging it would create noise.

Example 2 (forgotten logging):
BUG
Empty except hides real errors that should be logged for debuggability.

Example 3 (insufficient context):
UNCLEAR
Cannot determine intent without seeing caller contract or test fixture.

Your answer:"""


# Regex matching an intent label as a whole word (case-insensitive).
# Whole-word boundary prevents matching "BUG" inside "DEBUG" or "INTENTIONAL"
# inside "INTENTIONALITY".
_LABEL_RE = re.compile(r"\b(INTENTIONAL|BUG|UNCLEAR)\b", re.IGNORECASE)


def _parse_intent_response(response: str) -> tuple[str, str]:
    """Parse the LLM response into (label, reason).

    Strategy:
      1. Strip empty lines.
      2. Scan each line for the first whole-word match of
         INTENTIONAL / BUG / UNCLEAR (case-insensitive).
      3. Once a label is found on line `i`:
           - Reason = remainder of line `i` after the label (if non-empty),
             stripped of leading ":-" separators.
           - Else reason = line `i+1` (next non-empty line).
           - Else reason = "(no reason given)".

    Returns ("UNCLEAR", reason) if no label is found — this is the safe
    fallback (escalate to human review) per the fail-open philosophy.
    """
    if not response:
        return (_UNCLEAR, "(empty LLM response)")

    lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
    if not lines:
        return (_UNCLEAR, "(empty LLM response)")

    # Find the first line containing a label as a whole word.
    label = None
    label_line_idx = -1
    label_pos = -1
    for i, ln in enumerate(lines):
        m = _LABEL_RE.search(ln)
        if m:
            label = m.group(1).upper()
            label_line_idx = i
            label_pos = m.start()
            break

    if label is None:
        return (_UNCLEAR, f"(unparseable response: {response[:80]!r})")

    # Extract reason: prefer the remainder of the label line (after the
    # label, stripped of leading separators like ":" or "-"); fall back to
    # the next non-empty line; finally fall back to a sentinel.
    label_line = lines[label_line_idx]
    remainder = label_line[label_pos + len(label):].strip(" -:").strip()

    if remainder:
        reason = remainder
    elif label_line_idx + 1 < len(lines):
        reason = lines[label_line_idx + 1]
    else:
        reason = "(no reason given)"

    if not reason:
        reason = "(no reason given)"

    # Truncate to keep BugReport.description manageable.
    if len(reason) > 200:
        reason = reason[:197] + "..."
    return (label, reason)


def _apply_classification(
    bug: BugReport, label: str, reason: str
) -> BugReport:
    """Apply the LLM classification to the BugReport.

    - INTENTIONAL → suppress (TIER_1, affects_logic=False, description
      prefixed "[LLM-intent] intentional — ..."). Treated as false positive.
    - BUG         → keep original tier, enrich description with LLM reasoning.
    - UNCLEAR     → escalate to TIER_3_PERMISSION (human review) with LLM's
      analysis attached.

    Returns a NEW BugReport (via dataclasses.replace) — never mutates the
    input. This is safer for callers that hold references to the original.
    """
    if label == _INTENTIONAL:
        return replace(
            bug,
            tier=BugTier.TIER_1_AUTO_FIX,
            affects_logic=False,
            description=(
                f"[LLM-intent] intentional — {reason}. "
                f"Suppressed as likely false positive.\n"
                f"Original: {bug.description}"
            ),
        )
    if label == _BUG:
        # Keep original tier — LLM confirms this is a real bug. Enrich
        # description with the LLM's reasoning so the human reviewer (if any)
        # can see why the scanner+LLM concluded this is a real defect.
        return replace(
            bug,
            description=(
                f"[LLM-intent] bug confirmed — {reason}.\n"
                f"Original: {bug.description}"
            ),
        )
    # UNCLEAR — escalate to human review with LLM's analysis attached.
    return replace(
        bug,
        tier=BugTier.TIER_3_PERMISSION,
        affects_logic=True,
        description=(
            f"[LLM-intent] unclear, escalated to human review — {reason}.\n"
            f"Original: {bug.description}"
        ),
    )


# ============================================================================
# Public API
# ============================================================================

def triage_bug(bug: BugReport, source_code: str) -> BugReport:
    """Triage a single ambiguous bug via LLM intent classification.

    Args:
        bug: BugReport from another scanner (ruff/bandit/mypy/taint_flow).
            Must have `.file`, `.line`, `.bug_type` populated.
        source_code: The full source code of bug.file (caller reads it once
            and passes it in, so batch callers can amortize file I/O).

    Returns:
        A (possibly modified) BugReport:
          - If bug.bug_type is NOT ambiguous → returned unchanged (pass-through).
          - If LLM says INTENTIONAL → tier=TIER_1_AUTO_FIX, description
            prefixed "[LLM-intent] intentional — ...".
          - If LLM says BUG → original tier preserved, description enriched
            with "[LLM-intent] bug confirmed — ...".
          - If LLM says UNCLEAR → tier=TIER_3_PERMISSION (human review),
            description prefixed "[LLM-intent] unclear, escalated — ...".
          - On any failure (no API key, network error, unparseable source,
            empty LLM response) → original bug returned unchanged (fail-open).

    Caching:
        Results are cached by (file, line, bug_type). Repeated calls with
        the same bug skip the LLM call and reuse the cached label.
    """
    # Pass-through if bug is not ambiguous (skip LLM call entirely).
    if not _is_ambiguous(bug.bug_type):
        return bug

    # Check cache — don't re-query the same bug.
    key = _cache_key(bug)
    if key in _intent_cache:
        label, reason = _intent_cache[key]
        logger.debug(f"[semantic_intent] cache hit for {key}: {label}")
    else:
        # Fail-open: if no API key, return original bug unchanged.
        if not _has_api_key():
            logger.warning(
                f"[semantic_intent] no OPENROUTER_API_KEY set — fail-open "
                f"(returning original bug for {bug.file}:{bug.line})"
            )
            return bug

        # Rate limit: if exceeded, escalate to UNCLEAR (human review).
        # Per task spec: "If rate limited, fall back to UNCLEAR (escalate to human)."
        if not _check_rate_limit():
            logger.warning(
                f"[semantic_intent] rate-limited — escalating "
                f"{bug.file}:{bug.line} ({bug.bug_type}) to human review"
            )
            return _apply_classification(
                bug, _UNCLEAR, "rate-limited (LLM quota exceeded)"
            )

        # Parse source, extract context + docstrings.
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.warning(
                f"[semantic_intent] source parse failed for {bug.file}: {e} "
                f"— fail-open"
            )
            return bug

        code_context = _extract_code_context(source_code, bug.line)
        module_docstring = _get_module_docstring(tree)
        func_node = _find_enclosing_func(tree, bug.line)
        func_docstring = _get_func_docstring(func_node)

        # Build prompt and call LLM via the shared OpenRouter transport.
        prompt = _build_intent_prompt(
            bug, code_context, func_docstring, module_docstring
        )
        try:
            response = _call_openrouter(prompt, max_tokens=200)
        except Exception as e:
            # Fail-open on any unexpected exception (network, JSON, etc.).
            logger.warning(
                f"[semantic_intent] LLM call raised {e!r} for "
                f"{bug.file}:{bug.line} — fail-open", exc_info=True
            )
            return bug

        if not response:
            logger.warning(
                f"[semantic_intent] LLM returned empty for "
                f"{bug.file}:{bug.line} — fail-open"
            )
            return bug

        label, reason = _parse_intent_response(response)
        _intent_cache[key] = (label, reason)
        logger.info(
            f"[semantic_intent] {bug.file}:{bug.line} ({bug.bug_type}) → "
            f"{label} ({reason})"
        )

    return _apply_classification(bug, label, reason)


def triage_bugs(bugs: list[BugReport]) -> list[BugReport]:
    """Batch-triage a list of bugs.

    For each ambiguous bug, reads the bug's source file (cached per-file so
    each file is read at most once), extracts context + docstrings, and
    calls triage_bug.

    Non-ambiguous bugs are passed through unchanged. Failed file reads
    cause the corresponding bug to be returned unchanged (fail-open).

    Args:
        bugs: List of BugReports from any scanner.

    Returns:
        List of BugReports in the same order as input. Ambiguous bugs may
        have modified tier/description; non-ambiguous bugs are identical.
    """
    if not bugs:
        return []

    # Cache source code per file (read once, reuse for all bugs in that file).
    source_cache: dict[str, str] = {}

    out: list[BugReport] = []
    triaged_count = 0
    skipped_count = 0
    for bug in bugs:
        if not _is_ambiguous(bug.bug_type):
            out.append(bug)
            skipped_count += 1
            continue

        file_path = bug.file
        if file_path not in source_cache:
            try:
                source_cache[file_path] = Path(file_path).read_text(
                    encoding="utf-8", errors="replace"
                )
            except Exception as e:
                logger.warning(
                    f"[semantic_intent] could not read {file_path}: {e} "
                    f"— fail-open (returning original bug)", exc_info=True
                )
                source_cache[file_path] = ""  # mark as unreadable

        source = source_cache[file_path]
        if not source:
            out.append(bug)
            continue

        out.append(triage_bug(bug, source))
        triaged_count += 1

    logger.info(
        f"[semantic_intent] triage_bugs: {triaged_count} ambiguous bugs "
        f"triaged, {skipped_count} non-ambiguous passed through"
    )
    return out


def scan_scp() -> list[BugReport]:
    """Run other scanners first, then triage ambiguous bugs via LLM.

    Standalone entry point — calls enterprise scanners (ruff/bandit/mypy/
    vulture/bugbear/dlint) + AST scanners (BareExceptPass, UndefinedName),
    then triages any ambiguous bugs through the LLM intent classifier.

    Returns the full bug list (ambiguous bugs possibly modified by triage,
    non-ambiguous bugs passed through unchanged). Fail-open: if any
    upstream scanner is unavailable, it is skipped (not fatal).
    """
    bugs: list[BugReport] = []

    # Run enterprise scanners (ruff/bandit/mypy/vulture/bugbear/dlint).
    try:
        from scp.autofix.enterprise_scanners import scan_scp_enterprise
        enterprise_bugs = scan_scp_enterprise()
        bugs.extend(enterprise_bugs)
        logger.debug(
            f"[semantic_intent] enterprise scanners returned "
            f"{len(enterprise_bugs)} bugs"
        )
    except Exception as e:
        logger.warning(
            f"[semantic_intent] enterprise scanners unavailable (fail-open): {e}", exc_info=True
        )

    # Run AST scanners (BareExceptPass, UndefinedName) — these produce
    # bug_type="BareExceptPass" which is NOT in AMBIGUOUS_RULES (it's a
    # custom SCP type, not a ruff BLE001 code), but we still include them
    # for completeness — non-ambiguous bugs pass through triage unchanged.
    try:
        from scp.autofix.runner_phases.ast_scan import ast_scan_scp
        ast_bugs = ast_scan_scp()
        bugs.extend(ast_bugs)
        logger.debug(
            f"[semantic_intent] AST scanners returned {len(ast_bugs)} bugs"
        )
    except Exception as e:
        logger.warning(
            f"[semantic_intent] AST scanners unavailable (fail-open): {e}", exc_info=True
        )

    # Triage ambiguous bugs via LLM.
    triaged = triage_bugs(bugs)

    ambiguous_count = sum(1 for b in bugs if _is_ambiguous(b.bug_type))
    logger.info(
        f"[semantic_intent] scan_scp: {len(bugs)} total bugs, "
        f"{ambiguous_count} ambiguous → triaged via LLM"
    )
    return triaged
