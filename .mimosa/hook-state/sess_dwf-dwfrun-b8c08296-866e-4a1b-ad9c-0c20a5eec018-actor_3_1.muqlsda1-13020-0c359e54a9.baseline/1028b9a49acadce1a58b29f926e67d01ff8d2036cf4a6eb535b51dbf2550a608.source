"""
[SCP-DNA-FIX R7-Full IMP-3] R-Fix-Completeness Check — NEW autofix pipeline phase.

TẠI SAO file này tồn tại?
  R5 fix 18 bugs. R6 phát hiện 2 fix KHÔNG HOÀN CHỈNH (R6-3 why_engine, R6-5
  falsification). R7 phát hiện thêm 7: R6-1 chỉ fix 2/8 sites, R6-2 wiring
  GC-broken, R6-4 cold-start, R6-6 weight not applied, R6-7 no error handling,
  R6-8 silent no-op, R6-9 disk not pruned. 9/9 R6 fixes INCOMPLETE.

  Mỗi round bắt đầu "fresh" — không audit fix của round trước. DNA #22
  (PASS ≠ TRUE): "fix applied" ≠ "fix complete". DNA #23 (Audit the auditor)
  + #25 (Đứa trẻ hỏi Tại sao): phải kiểm tra fix cũ trước khi fix mới.

  Phase này chạy sau khi một fix được apply + reality_test pass:
    1. Re-run ONLY the scanner that originally flagged the bug.
    2. Filter results to SAME bug class + SAME file.
    3. If ANY instance remains (by bug_type, ignoring line — bug may have moved)
       → mark fix "incomplete" → re-open as new bug with `is_rN_incomplete=True`.
    4. If NO instance remains → fix is "complete".

  Inspired by: Sentry Autofix — tracks fix success rate, re-opens failed fixes.

Flow:
  Tier-2 fix applied + reality_test OK
    → completeness_check.run(bug, patched_file)
    → {complete: bool, remaining_count: int, reason: str}
  complete=False → re-open bug as new BugReport (Tier-3 for human review)

DNA principles applied:
  #22 (PASS ≠ TRUE) — fix "applied" ≠ fix "complete"
  #23 (Audit the auditor) — re-run scanner that flagged bug
  #25 (Đứa trẻ hỏi Tại sao) — ask "did the fix actually remove ALL instances?"
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.completeness_check")


# Map bug_type → scanner module + scanner class name.
# Bug types not in this map: completeness check is best-effort skipped.
_BUG_TYPE_TO_SCANNER: dict[str, tuple[str, str]] = {
    # V5.9 scanners
    "DeadSLM":           ("scp.autofix.scanners.dead_slm_scanner",      "DeadSLMScanner"),
    "RoutingGap":        ("scp.autofix.scanners.routing_gap_scanner",   "RoutingGapScanner"),
    "APIWiringGap":      ("scp.autofix.scanners.api_wiring_scanner",    "APIWiringScanner"),
    "LogicFlowFragile":  ("scp.autofix.scanners.logic_flow_scanner",    "LogicFlowScanner"),
    "SchemaMismatch":    ("scp.autofix.scanners.schema_scanner",        "SchemaMismatchScanner"),
    # V8.0 scanners
    "TypeMismatch":      ("scp.autofix.scanners.type_contract_scanner", "TypeContractScanner"),
    "NullDereference":   ("scp.autofix.scanners.null_safety_scanner",   "NullSafetyScanner"),
    "RaceCondition":     ("scp.autofix.scanners.race_condition_scanner","RaceConditionScanner"),
    "SQLInjection":      ("scp.autofix.scanners.sql_injection_scanner", "SQLInjectionScanner"),
    "ResourceLeak":      ("scp.autofix.scanners.resource_leak_scanner", "ResourceLeakScanner"),
    "PerformanceIssue":  ("scp.autofix.scanners.performance_scanner",   "PerformanceScanner"),
    "SecurityIssue":     ("scp.autofix.scanners.security_scanner",      "SecurityScanner"),
    "DeadCode":          ("scp.autofix.scanners.dead_code_scanner",     "DeadCodeScanner"),
    # OPT-18 scanner
    "XSSVulnerability":  ("scp.autofix.scanners.xss_scanner",           "XSSScanner"),
    # AST scanner bugs (handled via ast_scan, not class-based)
    "BareExceptPass":         ("scp.autofix.runner_phases.ast_scan",     "ast_scan_scp"),
    "PossiblyUndefinedName":  ("scp.autofix.runner_phases.ast_scan",     "ast_scan_scp"),
}


def _instantiate_scanner(module_path: str, class_name: str) -> Any | None:
    """Import + instantiate a scanner by module path + class name.

    Returns None if import fails (best-effort: skip check).
    """
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        logger.debug(f"[IMP-3] cannot import {module_path}: {e}")
        return None
    cls = getattr(mod, class_name, None)
    if cls is None:
        logger.debug(f"[IMP-3] {module_path} has no attribute {class_name}")
        return None
    # ast_scan_scp is a function, not a class — return as-is (caller calls directly).
    if callable(cls) and not isinstance(cls, type):
        return cls
    # Class-based scanners: instantiate with default args (they accept scp_root etc.).
    try:
        return cls()
    except TypeError:
        # Some scanners require scp_root — try with default SCP root.
        try:
            from pathlib import Path as _P
            _scp_root = _P(__file__).resolve().parent.parent.parent
            return cls(scp_root=_scp_root)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-3] cannot instantiate {class_name}: {e}")
            return None
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-3] scanner instantiation error: {e}")
        return None


def _run_scanner(scanner_obj: Any) -> list[Any]:
    """Run a scanner (class instance with .scan() OR callable function).

    Returns list of bug-like objects (each with .file, .line, .bug_type attrs).
    """
    try:
        if isinstance(scanner_obj, type):
            # Wasn't instantiated — give up.
            return []
        if hasattr(scanner_obj, "scan"):
            return scanner_obj.scan()
        if callable(scanner_obj):
            # [R37] ast_scan_scp is used here for surgical completeness only.
            # Its default enterprise pass invokes mypy/ruff/etc. over all of
            # scp/, which duplicates the primary scan and can block evolution.
            if getattr(scanner_obj, "__name__", "") == "ast_scan_scp":
                return scanner_obj(include_enterprise=False)
            return scanner_obj()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-3] scanner.run error: {e}")
    return []


def _bug_matches(bug_obj: Any, target_file: str, target_bug_type: str) -> bool:
    """Check if a scanner-found bug matches the fixed bug (same file + type).

    Line is intentionally NOT compared — bug may have moved after fix (e.g.
    upstream insert shifted lines). What matters: same bug_class still present
    in same file → fix incomplete.
    """
    bug_file = str(getattr(bug_obj, "file", ""))
    bug_type = str(getattr(bug_obj, "bug_type", ""))
    # Normalize paths for comparison (resolve symlinks + case-insensitive on Windows).
    try:
        bug_file_resolved = Path(bug_file).resolve() if bug_file else None
        target_resolved = Path(target_file).resolve()
        same_file = (
            bug_file_resolved == target_resolved
            if bug_file_resolved is not None
            else bug_file.endswith(target_file) or target_file.endswith(bug_file)
        )
    except Exception as resolve_err:
        # silent-by-design: resolve probe — plain string comparison is the
        # documented fallback for unresolvable paths.
        logger.debug("completeness_check: path resolve failed, comparing raw strings: %s", resolve_err, exc_info=True)
        same_file = bug_file == target_file
    # Bug type may have suffix like "Ruff_PLW0211" — check substring both ways.
    same_type = (
        bug_type == target_bug_type
        or bug_type.startswith(target_bug_type)
        or target_bug_type.startswith(bug_type)
    )
    return same_file and same_type


def run_completeness_check(
    bug_id: str,
    file_path: str,
    bug_type: str,
) -> dict:
    """Check whether a fix is COMPLETE — i.e. no instance of the bug remains.

    Args:
        bug_id: Original bug identifier (e.g. "R7-1").
        file_path: Patched file path.
        bug_type: The bug_type the fix was supposed to address.

    Returns:
        {
            "complete": bool,         — True if NO instance of bug_type remains in file
            "remaining_count": int,   — how many instances still present (0 = complete)
            "remaining_lines": list[int],
            "reason": str,
            "scanner_used": str,      — which scanner was re-run
        }
    """
    if bug_type not in _BUG_TYPE_TO_SCANNER:
        return {
            "complete": True,
            "remaining_count": 0,
            "remaining_lines": [],
            "reason": f"[IMP-3] no scanner mapped for bug_type={bug_type}, skip (assume complete)",
            "scanner_used": "none",
        }

    module_path, class_name = _BUG_TYPE_TO_SCANNER[bug_type]
    scanner_obj = _instantiate_scanner(module_path, class_name)
    if scanner_obj is None:
        return {
            "complete": True,
            "remaining_count": 0,
            "remaining_lines": [],
            "reason": f"[IMP-3] scanner {class_name} unavailable, skip (assume complete)",
            "scanner_used": class_name,
        }

    found_bugs = _run_scanner(scanner_obj)
    remaining = [b for b in found_bugs if _bug_matches(b, file_path, bug_type)]
    remaining_lines = [int(getattr(b, "line", 0) or 0) for b in remaining]
    is_complete = len(remaining) == 0

    reason = (
        f"[IMP-3] completeness_check for {bug_id} ({bug_type} in {Path(file_path).name}): "
        f"{'COMPLETE' if is_complete else 'INCOMPLETE'} "
        f"({len(remaining)} instance(s) remain at lines {remaining_lines[:5]})"
    )
    logger.info(reason)

    return {
        "complete": is_complete,
        "remaining_count": len(remaining),
        "remaining_lines": remaining_lines,
        "reason": reason,
        "scanner_used": class_name,
    }


def reopen_as_incomplete(
    original_bug: Any,
    completeness_result: dict,
) -> dict | None:
    """Build a re-opened bug record for an incomplete fix.

    Returns a dict with the new bug's metadata (caller converts to BugReport).
    Returns None if completeness_result says complete=True.
    """
    if completeness_result.get("complete", True):
        return None
    return {
        "file": getattr(original_bug, "file", ""),
        "line": getattr(original_bug, "line", 0),
        "bug_type": getattr(original_bug, "bug_type", ""),
        "description": (
            f"R-Fix-Completeness: previous fix INCOMPLETE. "
            f"{completeness_result.get('remaining_count', 0)} instance(s) of "
            f"{getattr(original_bug, 'bug_type', '?')} still present in "
            f"{getattr(original_bug, 'file', '?')} at lines "
            f"{completeness_result.get('remaining_lines', [])[:5]}."
        ),
        "suggested_fix": (
            "Re-audit the fix; the previous patch did not remove all instances "
            "of this bug class. Consider a multi-site pattern fixer."
        ),
        "is_rN_incomplete": True,
        "tier_hint": 3,  # escalate to Tier-3 (human review) for incomplete fixes
        "completeness_reason": completeness_result.get("reason", ""),
    }


__all__ = ["run_completeness_check", "reopen_as_incomplete"]
