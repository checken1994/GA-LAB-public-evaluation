# [V5.9-SCANNER] LogicFlowScanner — detect fragile confidence-flow checks.
#
# TẠI SAO scanner này tồn tại?
#   Pipeline confidence flow:
#     SLM returns conf X  →  judge uses threshold Y  →  governance checks Z
#
#   Fragile pattern: `if confidence == 0.7:` — exact float equality.
#   - Float arithmetic: 0.7 + 0.1 != 0.8 (rounding errors)
#   - Calibration: SLM may return 0.7000001 after tuning → check fails silently
#   - Cross-platform: different float representations may differ in last bit
#
#   VÍ DỤ (từ audit, slms.py:980):
#     if confidence == 0.7 and val:  # LocalDB-Cached, chưa verified
#         # ... do Wikipedia verification, set confidence = 0.85
#
#   If SLM ever returns 0.6999 or 0.7001 (calibration, smoothing, etc.),
#   the entire Wikipedia verification branch is skipped silently.
#
#   Robust patterns:
#     - `if confidence >= 0.7:` — inclusive threshold (PREFERRED for "at least")
#     - `if confidence < 0.7:` — exclusive (PREFERRED for "below")
#     - `if 0.65 <= confidence <= 0.75:` — bounded range
#     - `if abs(confidence - 0.7) < 1e-6:` — explicit epsilon check
#
# LOGIC:
#   1. Walk all .py files in scp/ (skip tests, __pycache__)
#   2. AST scan for `if <varname> == <float>:` patterns where varname suggests
#      confidence (confidence, conf, _conf, _kb_sc_conf, etc.)
#   3. Report each as "LogicFlowGap" with the exact line + suggested fix
#
# RETURNS:
#   list[BugReport] — bug_type="LogicFlowGap"
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.logic_flow")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/

_MAX_FILES = 500

# Variable names that suggest confidence values
_CONF_NAME_PATTERN = re.compile(
    r"^(confidence|conf|_conf|_kb_sc_conf|_hit_conf|final_confidence|"
    r"pred_conf|pred\.confidence|verdict\.confidence|sim|score)$"
)

# Floats commonly used as thresholds (these are the "magic numbers" we want to
# detect equality checks against)
_THRESHOLD_FLOATS = {0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.92, 0.95, 1.0}


def _is_confidence_name(node) -> bool:
    """Check if an AST node represents a confidence-like variable."""
    # Direct name: `confidence`
    if isinstance(node, ast.Name):
        return bool(_CONF_NAME_PATTERN.match(node.id))
    # Attribute: `pred.confidence` or `verdict.confidence`
    if isinstance(node, ast.Attribute):
        full_name = f"{_attr_chain(node)}"
        return bool(_CONF_NAME_PATTERN.match(full_name))
    return False


def _attr_chain(node) -> str:
    """Reconstruct dotted attribute chain: `pred.confidence` from AST."""
    if isinstance(node, ast.Attribute):
        parent = _attr_chain(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_threshold_float(node) -> float | None:
    """Check if node is a Constant float that looks like a threshold."""
    if isinstance(node, ast.Constant) and isinstance(node.value, float):
        # Round to 2 decimals for matching (0.7000001 → 0.7)
        rounded = round(node.value, 4)
        if rounded in _THRESHOLD_FLOATS:
            return rounded
    return None


class _ExactFloatEqFinder(ast.NodeVisitor):
    """Find `if confidence == 0.7:` patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []

    def visit_If(self, node: ast.If):
        self._check_test(node.test, node.lineno)
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self._check_test(node.test, node.lineno)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert):
        # `assert confidence == 0.7` — also fragile
        self._check_test(node.test, node.lineno)
        self.generic_visit(node)

    def _check_test(self, test, lineno: int):
        # [V5.9-SCANNER] Walk ALL Compare nodes in the test (handles `and`/`or`
        # BoolOps where the `==` is nested inside, e.g.
        # `if confidence == 0.7 and val:` — test is BoolOp, not Compare).
        for node in ast.walk(test):
            if not isinstance(node, ast.Compare):
                continue
            if len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], ast.Eq):
                continue
            left, right = node.left, node.comparators[0]
            # Try both orderings: `Name == Constant` or `Constant == Name`
            for a, b in [(left, right), (right, left)]:
                if _is_confidence_name(a):
                    thr = _is_threshold_float(b)
                    if thr is not None:
                        var_name = (
                            _attr_chain(a) if isinstance(a, ast.Attribute) else a.id
                        )
                        # Avoid duplicate findings for the same line+var+thr
                        key = (lineno, var_name, thr)
                        if key not in {(f["line"], f["var_name"], f["threshold"])
                                       for f in self.findings}:
                            self.findings.append({
                                "line": lineno,
                                "threshold": thr,
                                "var_name": var_name,
                            })
                        return


def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.name.startswith("test_"):
            continue
        if any(part in ("examples", "scripts", "attack_payloads")
               for part in path.parts):
            continue
        if count >= limit:
            break
        yield path
        count += 1


class LogicFlowScanner:
    """Detect fragile `if confidence == X` exact-float-equality checks."""

    name: str = "LogicFlowScanner"
    bug_type: str = "LogicFlowGap"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    def scan(self) -> list[BugReport]:
        """Walk scp/ source files and find fragile confidence == X checks."""
        bugs: list[BugReport] = []
        files_scanned = 0
        for path in _iter_python_files(self.scp_root, limit=self.max_files):
            files_scanned += 1
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as parse_err:
                # silent-by-design: parse probe — unparseable file is skipped; dedicated
                # syntax-error scanners report these files.
                logger.debug("logic_flow_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue  # other scanner handles syntax errors
            except Exception as read_err:  # noqa: S112
                logger.debug("logic_flow_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue
            finder = _ExactFloatEqFinder(str(path))
            finder.visit(tree)
            for f in finder.findings:
                var_name = f["var_name"]
                thr = f["threshold"]
                lineno = f["line"]
                bugs.append(BugReport(
                    file=str(path),
                    line=lineno,
                    bug_type=self.bug_type,
                    description=(
                        f"LogicFlowGap: `if {var_name} == {thr}` at line "
                        f"{lineno} — exact float equality is fragile. "
                        f"Calibration/smoothing may return {thr}±0.0001 "
                        f"→ branch silently skipped."
                    ),
                    suggested_fix=(
                        f"Replace `== {thr}` with `>= {thr}` (if 'at least' "
                        f"semantics) or `< {thr}` (if 'below'). For 'exactly', "
                        f"use `abs({var_name} - {thr}) < 1e-6`."
                    ),
                    tier=BugTier.TIER_3_PERMISSION,  # changes verdict flow → logic
                    affects_logic=True,
                ))

        logger.info(
            f"[LogicFlowScanner] found {len(bugs)} fragile == check(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
