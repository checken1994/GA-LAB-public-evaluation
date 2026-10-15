"""
[SCP-DNA-FIX R8 v3 IMP-16] Fix Blast-Radius Analysis.

TẠI SAO file này tồn tại?
  IMP-14 (confidence ranker) dùng `lines_changed` làm blast-radius proxy. Nhưng
  "1 dòng thay đổi trong hàm được 50 caller gọi" nguy hiểm hơn "10 dòng thay
  đổi trong hàm leaf (0 caller)". Cần đo blast-radius THẬT:
    - Bao nhiêu function/class/module gọi target_function?
    - Bao nhiêu test cover target_function?
    - Risk level: LOW (0-2 callers) | MEDIUM (3-9) | HIGH (10-29) | CRITICAL (30+)

  Ví dụ thực tế SCP:
    - `judge.py::ingestion_decision` được 8 modules gọi → HIGH risk.
    - `conversionslm.py::_normalize_score` được 1 module gọi → LOW risk.
    - Fix ở HIGH-risk function → escalate Tier (Tier 2 → Tier 3) hoặc yêu cầu
      dry-run (IMP-9) trước khi apply.

  Inspired by:
    - CodeQL data-flow analysis (taint flow from source to sink)
    - GitHub code review "files changed" view (surfaces caller impact)
    - SonarQube "Quality Gate" on new code
    - Underhood "Dependents" graph (npm/GitHub)

Flow:
  result = compute_blast_radius(target_file, target_function, scp_root)
  if result.risk_level == "CRITICAL":
      require_dry_run = True     # use IMP-9 dry-run
  elif result.risk_level == "HIGH":
      escalate_tier_to = 3       # was Tier 2 → force Tier 3

DNA principles applied:
  #9  (No harm)         — high-risk fixes need extra verification
  #17 (Operator oversight)— CRITICAL risk requires human approval
  #7  (Autofix safe)    — fail-open: can't build graph → MEDIUM (default safe)
  #19 (Reality multi-source)— static call-graph + test-coverage = 2 sources
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.blast_radius")


# ============================================================
# Bounded walk limits (per DNA #7 — must terminate fast).
# ============================================================

MAX_NODES_PER_FILE = 5000          # cap AST walk per file
MAX_FILES_TO_SCAN = 1000            # cap total files scanned
MAX_CALLERS_RECORDED = 200         # cap callers list (avoid huge results)


# ============================================================
# Risk levels.
# ============================================================

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"

# Thresholds (caller_count → risk level).
RISK_THRESHOLDS = [
    (30, RISK_CRITICAL),
    (10, RISK_HIGH),
    (3, RISK_MEDIUM),
    (0, RISK_LOW),
]


# ============================================================
# Result dataclass.
# ============================================================

@dataclass
class BlastRadiusResult:
    """Outcome of compute_blast_radius().

    Attributes:
        target_file: Absolute path of the file containing the patched function.
        target_function: Qualified name (e.g. "ingestion_decision" or "Class.method").
        caller_count: Number of distinct call sites (across all files).
        caller_files: Distinct files that call target_function (capped at MAX_CALLERS_RECORDED).
        caller_sites: List of (file, line, qual_context) for each call site.
        test_coverage_count: Number of test files that reference target_function.
        risk_level: LOW | MEDIUM | HIGH | CRITICAL.
        reason: Human-readable summary.
        bounded: True if any cap was hit (results may be incomplete).
    """
    target_file: str = ""
    target_function: str = ""
    caller_count: int = 0
    caller_files: list[str] = field(default_factory=list)
    caller_sites: list[tuple[str, int, str]] = field(default_factory=list)
    test_coverage_count: int = 0
    test_files: list[str] = field(default_factory=list)
    risk_level: str = RISK_MEDIUM
    reason: str = ""
    bounded: bool = False


# ============================================================
# AST visitor — collects call sites of a target function.
# ============================================================

class _CallSiteCollector(ast.NodeVisitor):
    """Walks a single file's AST, records every Call that references the
    target function name.

    Matches:
        - direct name: `target_func(...)`              → Name(id=target_func)
        - attribute:   `obj.target_func(...)`          → Attribute(attr=target_func)
        - method form: `Class.target_func(...)`        → handled by Attribute
    """

    def __init__(self, target_name: str, target_short: str):
        self.target_name = target_name
        # target_short = the part after the last dot (e.g. "method" in "Class.method")
        self.target_short = target_short
        self.sites: list[tuple[int, str]] = []  # (lineno, context_str)
        self.nodes_walked = 0
        self.bounded = False

    def _record(self, lineno: int, ctx: str) -> None:
        if len(self.sites) < MAX_CALLERS_RECORDED:
            self.sites.append((lineno, ctx))
        else:
            self.bounded = True

    def _check_bounded(self) -> bool:
        self.nodes_walked += 1
        if self.nodes_walked > MAX_NODES_PER_FILE:
            self.bounded = True
            return True  # signal to stop
        return False

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: D401
        if self._check_bounded():
            return
        func = node.func
        lineno = int(getattr(node, "lineno", 0) or 0)
        # Case 1: Name(id=...) — direct call: target_func(...)
        if isinstance(func, ast.Name) and func.id == self.target_short:
            self._record(lineno, f"{func.id}()")
        # Case 2: Attribute(attr=...) — method call: obj.target_func(...)
        elif isinstance(func, ast.Attribute) and func.attr == self.target_short:
            # Best-effort: dump the value (object expression) for context.
            try:
                val_dump = ast.dump(func.value, annotate_fields=False)[:60]
            except Exception:  # noqa: BLE001
                # silent-by-design: dump probe — '?' is the documented context placeholder.
                val_dump = "?"
            self._record(lineno, f"{val_dump}.{func.attr}()")
        # Recurse into children (call args may contain nested calls).
        self.generic_visit(node)

    def visit(self, node: ast.AST) -> Any:
        if self._check_bounded():
            return
        super().visit(node)


# ============================================================
# Helpers.
# ============================================================

def _iter_python_files(root: Path, max_files: int = MAX_FILES_TO_SCAN):
    """Yield ``(path, bounded)`` pairs under root (excluding cache/venv dirs).

    [A12 H-1] Deterministic walk: sort theo path TRƯỚC khi cap (thứ tự rglob
    phụ thuộc OS) + WARNING tường minh khi truncation xảy ra. Cặp cuối
    ``(path, True)`` giữ nguyên bounded contract cho caller."""
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules",
                 ".mypy_cache", ".pytest_cache", ".ruff_cache"}
    try:
        paths = sorted(
            path for path in root.rglob("*.py")
            if not any(part in skip_dirs for part in path.parts)
        )
    except OSError as e:
        logger.debug(f"[IMP-16] rglob failed in {root}: {e}")
        return
    truncated = len(paths) > max_files
    if truncated:
        logger.warning(
            "[scanner-cap] %s: %d file .py vượt cap %d — cắt còn %d "
            "(kết quả bounded, không full coverage)",
            __name__, len(paths), max_files, max_files,
        )
    for path in paths[:max_files]:
        yield path, False
    if truncated and paths:
        yield paths[max_files], True  # bounded signal (contract cũ)


def _is_test_file(path: Path) -> bool:
    """Heuristic: True if path looks like a test file."""
    name = path.name.lower()
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    parts_lower = [p.lower() for p in path.parts]
    return "test" in parts_lower or "tests" in parts_lower


def _classify_risk(caller_count: int) -> str:
    """Map caller_count → risk level (higher = more risky)."""
    for threshold, level in RISK_THRESHOLDS:
        if caller_count >= threshold:
            return level
    return RISK_LOW


# ============================================================
# Core function: compute_blast_radius.
# ============================================================

def compute_blast_radius(
    target_file: str,
    target_function: str,
    scp_root: str | Path | None = None,
    scan_tests: bool = True,
) -> BlastRadiusResult:
    """Compute the blast radius of fixing a function.

    Args:
        target_file: Absolute path to the file containing the function.
        target_function: Qualified name — "func" (top-level) or "Class.method".
        scp_root: Root directory to scan for callers. Defaults to the SCP
                  project root (parent of autofix/).
        scan_tests: If True, also count test files that reference the function.

    Returns:
        BlastRadiusResult with caller_count, caller_files, risk_level, etc.

    Algorithm:
        1. Resolve scp_root (default: .../scp/).
        2. Walk every .py file under scp_root (capped at MAX_FILES_TO_SCAN).
        3. For each file: AST-parse, run _CallSiteCollector.
        4. Aggregate call sites (file, line, context).
        5. If scan_tests: separately count test files referencing the function
           name (cheap substring check on file content).
        6. Classify risk_level from caller_count.

    Fail-open: any error → risk_level=MEDIUM (default safe), bounded=True.
    """
    result = BlastRadiusResult(
        target_file=str(target_file),
        target_function=str(target_function),
    )

    try:
        # Resolve scp_root.
        if scp_root is None:
            # Default: parent of this file's parent's parent = .../scp/
            scp_root = Path(__file__).resolve().parent.parent.parent
        root = Path(scp_root)
        if not root.exists() or not root.is_dir():
            result.reason = f"scp_root not found: {root} — defaulting to MEDIUM"
            result.risk_level = RISK_MEDIUM
            return result

        # The "short" name is the part after the last dot.
        target_short = target_function.rsplit(".", 1)[-1]
        if not target_short:
            result.reason = "empty target_function — defaulting to MEDIUM"
            result.risk_level = RISK_MEDIUM
            return result

        caller_files_set: set[str] = set()
        test_files_set: set[str] = set()

        for path, bounded in _iter_python_files(root):
            if bounded:
                result.bounded = True
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError as read_err:
                # silent-by-design: read probe — unreadable file cannot contain
                # reachable call sites for this analysis.
                logger.debug("[IMP-16] skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            # Cheap pre-filter: skip files that don't even mention the name.
            # This avoids AST-parsing files with no chance of matching.
            if target_short not in source:
                continue

            # Try to parse + walk for call sites.
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as parse_err:
                # silent-by-design: parse probe — broken file is skipped by design.
                logger.debug("[IMP-16] skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue  # broken file — skip
            except Exception as scan_err:  # noqa: BLE001
                logger.debug("[IMP-16] skipping unreadable file %s: %s", path, scan_err, exc_info=True)
                continue

            collector = _CallSiteCollector(target_function, target_short)
            try:
                collector.visit(tree)
            except Exception as e:  # noqa: BLE001 — fail-open
                logger.debug(f"[IMP-16] visitor crashed on {path}: {e}")
                continue

            if collector.bounded:
                result.bounded = True

            for lineno, ctx in collector.sites:
                result.caller_sites.append((str(path), lineno, ctx))
                caller_files_set.add(str(path))

            # Test coverage check (cheap, only for test files).
            if scan_tests and _is_test_file(path):
                # Already confirmed target_short is in source (pre-filter).
                test_files_set.add(str(path))

        # Aggregate.
        result.caller_count = len(result.caller_sites)
        result.caller_files = sorted(caller_files_set)
        result.test_coverage_count = len(test_files_set)
        result.test_files = sorted(test_files_set)
        result.risk_level = _classify_risk(result.caller_count)

        bounded_note = " [BOUNDED — results may be incomplete]" if result.bounded else ""
        result.reason = (
            f"blast_radius for {target_function}: "
            f"{result.caller_count} call sites across {len(result.caller_files)} files, "
            f"{result.test_coverage_count} test files reference it "
            f"→ risk={result.risk_level}{bounded_note}"
        )
        logger.info(f"[IMP-16] {result.reason}")

    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
        logger.warning(f"[IMP-16] compute_blast_radius crashed (fail-open): {e}")
        result.risk_level = RISK_MEDIUM
        result.reason = f"fail-open — internal error: {e} (defaulting to MEDIUM)"
        result.bounded = True

    return result


# ============================================================
# Convenience helpers.
# ============================================================

def should_require_dry_run(result: BlastRadiusResult) -> bool:
    """Policy: HIGH and CRITICAL risk fixes should go through IMP-9 dry-run."""
    return result.risk_level in (RISK_HIGH, RISK_CRITICAL)


def should_escalate_tier(result: BlastRadiusResult, current_tier: int) -> int:
    """Policy: CRITICAL risk auto-escalates to Tier 3 (human review)."""
    if result.risk_level == RISK_CRITICAL and current_tier < 3:
        return 3
    if result.risk_level == RISK_HIGH and current_tier < 2:
        return 2
    return current_tier


def blast_radius_summary(result: BlastRadiusResult) -> dict[str, Any]:
    """JSON-serializable summary for audit log."""
    return {
        "target_file": result.target_file,
        "target_function": result.target_function,
        "caller_count": result.caller_count,
        "caller_file_count": len(result.caller_files),
        "test_coverage_count": result.test_coverage_count,
        "risk_level": result.risk_level,
        "bounded": result.bounded,
        "reason": result.reason,
    }


__all__ = [
    "BlastRadiusResult",
    "compute_blast_radius",
    "should_require_dry_run",
    "should_escalate_tier",
    "blast_radius_summary",
    "RISK_LOW",
    "RISK_MEDIUM",
    "RISK_HIGH",
    "RISK_CRITICAL",
]
