# [V8.0-SCANNER] NullSafetyScanner — detect None-dereference risks.
#
# TẠI SAO scanner này tồn tại?
#   Python runtime raises AttributeError khi `None.attr` được access. Scanner
#   này phát hiện 2 pattern chính:
#     1. function annotation `-> Optional[X]` (hoặc `-> X | None`) — caller
#        không check `if result is None:` trước khi dùng `result.attr`.
#     2. `dict.get("key").attr` — `.get()` mặc định trả về None nếu key miss;
#        caller access `.attr` ngay sau đó → AttributeError.
#
# LOGIC:
#   Pass 1: thu thập function return annotation. Detect Optional[X] hoặc X | None.
#   Pass 2: trong mỗi function scope, nếu `var = func()` mà func có Optional
#   return type, thì `var.attr` (sau đó, không có `if var:` check trước) = bug.
#   Pass 3: regex/AST scan `dict.get("key").attr` pattern — chain call.
#
# CONSERVATIVE HEURISTICS:
#   - Optional[X] phải được parse rõ ràng (ast.Subscript với value=Name("Optional"))
#     hoặc BinOp Or với Name("None")  (PEP 604 `X | None`)
#   - Caller phải KHÔNG có `if var:` hoặc `if var is not None:` TRƯỚC dòng attr
#     access (trong cùng scope, không qua nested blocks)
#   - Chỉ track var trong cùng function scope, không cross-function
#   - dict.get() phải là method call trực tiếp trên Name hoặc Attribute chain
#
# RETURNS:
#   list[BugReport] — bug_type="NullDereference"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.null_safety")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500


def _is_optional_annotation(ann) -> bool:
    """Return True if annotation is `Optional[X]` or `X | None` (PEP 604).

    Handles:
      - ast.Subscript(value=Name('Optional'), slice=...)  →  Optional[X]
      - ast.BinOp(left=..., op=BitOr, right=Constant(None))  →  X | None
      - ast.BinOp(left=Constant(None), op=BitOr, right=...)  →  None | X
    """
    # Optional[X]
    if isinstance(ann, ast.Subscript):
        if isinstance(ann.value, ast.Name) and ann.value.id == "Optional":
            return True
    # X | None  (PEP 604)
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        for side in (ann.left, ann.right):
            if isinstance(side, ast.Constant) and side.value is None:
                return True
    return False


class _OptionalReturnCollector(ast.NodeVisitor):
    """Pass 1: collect {func_name: True} for functions returning Optional."""

    def __init__(self):
        self.optional_funcs: set[str] = set()

    def visit_FunctionDef(self, node):
        if node.returns is not None and _is_optional_annotation(node.returns):
            self.optional_funcs.add(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class _NullDerefFinder(ast.NodeVisitor):
    """Pass 2: walk function bodies, find var.attr where var may be None."""

    def __init__(self, optional_funcs: set[str], filepath: str):
        self.optional_funcs = optional_funcs
        self.filepath = filepath
        self.findings: list[dict] = []
        # var_name → True if assigned from Optional-returning function
        self._nullable_vars: dict[str, int] = {}  # name → lineno of assignment
        # Track lines where `if var:` or `if var is not None:` was seen
        self._checked_vars: set[str] = set()

    def visit_FunctionDef(self, node):
        saved_nullable = dict(self._nullable_vars)
        saved_checked = set(self._checked_vars)
        self._nullable_vars = {}
        self._checked_vars = set()
        for stmt in node.body:
            self.visit(stmt)
        self._nullable_vars = saved_nullable
        self._checked_vars = saved_checked

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        # Visit RHS first (in case RHS has its own attr access)
        self.visit(node.value)
        if isinstance(node.value, ast.Call):
            rtype_is_optional = self._call_returns_optional(node.value)
            if rtype_is_optional:
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        self._nullable_vars[tgt.id] = node.lineno

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
            if isinstance(node.target, ast.Name):
                # If annotation is Optional, var is nullable
                if node.annotation is not None and _is_optional_annotation(node.annotation):
                    self._nullable_vars[node.target.id] = node.lineno
                elif isinstance(node.value, ast.Call) and self._call_returns_optional(node.value):
                    self._nullable_vars[node.target.id] = node.lineno

    def _call_returns_optional(self, call: ast.Call) -> bool:
        """True if call invokes a known Optional-returning function."""
        if isinstance(call.func, ast.Name):
            return call.func.id in self.optional_funcs
        return False

    def visit_If(self, node: ast.If):
        # Track `if var:` or `if var is not None:` → var becomes "checked"
        # Conservative: only Name checks (not `if var.attr:`)
        for cond_node in ast.walk(node.test):
            if isinstance(cond_node, ast.Name) and cond_node.id in self._nullable_vars:
                self._checked_vars.add(cond_node.id)
            # `if var is not None:` pattern: Compare(Name, IsNot, Constant(None))
            if (isinstance(cond_node, ast.Compare)
                    and isinstance(cond_node.left, ast.Name)
                    and len(cond_node.ops) == 1
                    and isinstance(cond_node.ops[0], ast.IsNot)):
                right = cond_node.comparators[0] if cond_node.comparators else None
                if isinstance(right, ast.Constant) and right.value is None:
                    self._checked_vars.add(cond_node.left.id)
        # Visit body + orelse
        for stmt in node.body:
            self.visit(stmt)
        # In orelse, the var IS None (so .attr is bug; but skip — too noisy)
        for stmt in node.orelse:
            self.visit(stmt)

    def _already_flagged(self, lineno: int, kind: str, vname: str) -> bool:
        """Return True if we already flagged this var on this line for this kind."""
        for f in self.findings:
            if (f["line"] == lineno and f["kind"] == kind
                    and f.get("var") == vname):
                return True
        return False

    def visit_Attribute(self, node: ast.Attribute):
        # var.attr where var may be None and not checked
        if isinstance(node.value, ast.Name):
            vname = node.value.id
            if vname in self._nullable_vars and vname not in self._checked_vars:
                if not self._already_flagged(node.lineno, "optional_attr", vname):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "optional_attr",
                        "var": vname,
                        "attr": node.attr,
                        "assign_line": self._nullable_vars[vname],
                    })
        # dict.get("key").attr pattern — chain call.
        # Conservative: only flag if dict.get() has NO default (single arg)
        # AND the chained access is NOT .get/.pop/.setdefault (those handle
        # None gracefully? — actually they don't, but the common pattern
        # `d.get("k", {}).get("k2", default)` IS safe because of the default).
        # We check: dict.get() call must have exactly 1 positional arg.
        if (isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "get"):
            get_call = node.value
            # Skip if dict.get() has a default (>= 2 args)
            if len(get_call.args) <= 1 and not get_call.keywords:
                # Also skip "safe" chained attrs (common guarded patterns)
                if node.attr not in ("get", "pop", "setdefault", "items",
                                     "keys", "values", "copy"):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "dict_get_attr",
                        "attr": node.attr,
                    })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # var.method() where var may be None and not checked
        if (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)):
            vname = node.func.value.id
            if vname in self._nullable_vars and vname not in self._checked_vars:
                if not self._already_flagged(node.lineno, "optional_method", vname):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "optional_method",
                        "var": vname,
                        "method": node.func.attr,
                        "assign_line": self._nullable_vars[vname],
                    })
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # var[...] where var is Optional — None is not subscriptable → TypeError
        if isinstance(node.value, ast.Name):
            vname = node.value.id
            if vname in self._nullable_vars and vname not in self._checked_vars:
                if not self._already_flagged(node.lineno, "optional_subscript", vname):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "optional_subscript",
                        "var": vname,
                        "assign_line": self._nullable_vars[vname],
                    })
        self.generic_visit(node)


def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.name.startswith("test_"):
            continue
        if any(part in ("examples", "scripts", "attack_payloads") for part in path.parts):
            continue
        if count >= limit:
            break
        yield path
        count += 1


class NullSafetyScanner:
    """Detect None-dereference risks: Optional-return without None-check,
    dict.get('key').attr chains."""

    name: str = "NullSafetyScanner"
    bug_type: str = "NullDereference"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    def scan(self) -> list[BugReport]:
        bugs: list[BugReport] = []
        files_scanned = 0
        for path in _iter_python_files(self.scp_root, limit=self.max_files):
            files_scanned += 1
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as parse_err:
                # silent-by-design: parse probe — unparseable file is skipped by this scan by design.
                logger.debug("null_safety_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("null_safety_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            # Pass 1: collect Optional-returning functions
            opt_collector = _OptionalReturnCollector()
            opt_collector.visit(tree)

            # Pass 2: walk function bodies
            finder = _NullDerefFinder(opt_collector.optional_funcs, str(path))
            finder.visit(tree)

            for f in finder.findings:
                kind = f["kind"]
                if kind == "optional_attr":
                    desc = (
                        f"NullDereference: variable `{f['var']}` was assigned from "
                        f"Optional-returning function at line {f['assign_line']} but "
                        f"accessed `.attr` ({f['attr']}) at line {f['line']} without "
                        f"a preceding `if {f['var']} is not None:` check — raises "
                        f"AttributeError if function returned None."
                    )
                    fix = (
                        f"Add `if {f['var']} is not None:` before line {f['line']}, "
                        f"or use `getattr({f['var']}, '{f['attr']}', default)`, "
                        f"or change the function to never return None."
                    )
                elif kind == "optional_method":
                    desc = (
                        f"NullDereference: variable `{f['var']}` was assigned from "
                        f"Optional-returning function at line {f['assign_line']} but "
                        f"called `.method()` ({f['method']}) at line {f['line']} without "
                        f"a None-check — raises AttributeError if None."
                    )
                    fix = (
                        f"Add `if {f['var']} is not None:` guard before line {f['line']}."
                    )
                elif kind == "optional_subscript":
                    desc = (
                        f"NullDereference: variable `{f['var']}` was assigned from "
                        f"Optional-returning function at line {f['assign_line']} but "
                        f"subscripted `[...]` at line {f['line']} without a None-check — "
                        f"NoneType is not subscriptable, raises TypeError."
                    )
                    fix = (
                        f"Add `if {f['var']} is not None:` guard before line {f['line']}, "
                        f"or change the function to never return None."
                    )
                elif kind == "dict_get_attr":
                    desc = (
                        f"NullDereference: `dict.get(...).attr` chain at line {f['line']} — "
                        f"`dict.get()` returns None by default when key is missing, so "
                        f"`.attr` access raises AttributeError."
                    )
                    fix = (
                        "Either: (a) provide a default `dict.get(key, default_obj)`, "
                        "(b) check `value = dict.get(key); if value: value.attr`, "
                        "(c) use `dict[key]` if key is guaranteed present (raises "
                        "KeyError otherwise — more debuggable than AttributeError)."
                    )
                else:
                    continue
                bugs.append(BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=desc,
                    suggested_fix=fix,
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                    affects_logic=False,
                ))

        logger.info(
            f"[NullSafetyScanner] found {len(bugs)} None-dereference risk(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
