# [V8.0-SCANNER] TypeContractScanner — detect type-mismatch bugs.
#
# TẠI SAO scanner này tồn tại?
#   Gà vừa dính bug: func() trả về dict nhưng code làm `if result > 0:` → TypeError.
#   Python type hints (return annotations) tuy có nhưng runtime KHÔNG enforce.
#   Scanner này cross-check return type annotations với cách caller dùng kết quả.
#
# PATTERNS DETECTED (conservative — chỉ flag clear cases):
#   1. `result = func()` → `if result > 0:`  với func() trả về dict/list/str
#      (Compare > < >= <= trên non-numeric type → TypeError runtime)
#   2. `result = func()` → `result.attr`  với func() trả về None literal
#      (NoneType has no attribute 'X')
#   3. `"foo" + 123`  hoặc `123 + "foo"`  (BinOp Add với str + int constant)
#   4. `lst["key"]`  với lst được annotate là list  (Subscript với str slice trên list)
#
# LOGIC:
#   1. Pass 1: thu thập function return annotations → {func_name: return_type_str}
#      (chỉ collect return type nếu annotation là simple Name như `dict`, `list`,
#       `int`, `str`, `bool`, `None` — bỏ qua Union, Optional, generic params)
#   2. Pass 2: với mỗi `var = func()` call trong cùng function scope:
#      - Nếu func có annotation "dict"/"list"/"str" → var bị flag nếu dùng trong
#        Compare `<`, `>`, `<=`, `>=` (numeric ops) → TypeError
#      - Nếu func annotation là `None` (literal None return) → var.attr = bug
#   3. Flag str+int constants trong BinOp(Add) trực tiếp (no flow tracking needed)
#   4. Flag `lst[<str_constant>]` nếu lst được annotate là list
#
# CONSERVATIVE HEURISTICS (avoid false positives):
#   - Chỉ track var trong cùng function scope (không cross-function)
#   - Var phải được gán từ `Call` trực tiếp (skip qua if/for/while blocks)
#   - Compare phải dùng trực tiếp var (không qua attribute access)
#   - Skip file có syntax error, skip test files
#
# RETURNS:
#   list[BugReport] — bug_type="TypeMismatch"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.type_contract")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Simple type names we track. Compound types (Optional[X], list[int], dict[str, Any])
# are skipped — too easy to mis-classify.
_SIMPLE_RETURN_TYPES = {"dict", "list", "str", "int", "float", "bool", "set", "tuple", "None"}

# Numeric Compare operators (these fail on dict/list/str)
_NUMERIC_COMPARE_OPS = (ast.Gt, ast.Lt, ast.GtE, ast.LtE)


def _annotation_to_simple_str(ann) -> str | None:
    """Convert return annotation AST → simple type string if it's a plain Name/None.

    Returns:
        "dict" for `-> dict:`, "int" for `-> int:`, "None" for `-> None:`,
        None for compound types (`-> Optional[X]`, `-> list[int]`, `-> "Foo"`, etc.)
    """
    if ann is None:
        return None
    # `-> dict:`  →  ast.Name(id="dict")
    if isinstance(ann, ast.Name):
        if ann.id in _SIMPLE_RETURN_TYPES:
            return ann.id
        return None
    # `-> None:`  →  ast.Constant(value=None)
    if isinstance(ann, ast.Constant):
        if ann.value is None:
            return "None"
        return None
    return None


class _FuncReturnCollector(ast.NodeVisitor):
    """Pass 1: collect {function_name: return_type_str} for module-level + class methods."""

    def __init__(self):
        self.func_returns: dict[str, str] = {}

    def visit_FunctionDef(self, node):
        if node.returns is not None:
            simple = _annotation_to_simple_str(node.returns)
            if simple is not None:
                self.func_returns[node.name] = simple
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class _TypeMisuseFinder(ast.NodeVisitor):
    """Pass 2: walk function bodies, find type-mismatch uses of return values."""

    def __init__(self, func_returns: dict[str, str], filepath: str):
        self.func_returns = func_returns
        self.filepath = filepath
        self.findings: list[dict] = []
        # Stack of var-name → simple-return-type for current function scope
        self._var_types: dict[str, str] = {}

    def visit_FunctionDef(self, node):
        # Save + reset scope for nested function
        saved = dict(self._var_types)
        self._var_types = {}
        self._define_args(node.args)
        for stmt in node.body:
            self.visit(stmt)
        self._var_types = saved

    visit_AsyncFunctionDef = visit_FunctionDef

    def _define_args(self, args: ast.arguments):
        """Collect arg annotations as simple types (for subscript-mismatch detection)."""
        for arg in args.posonlyargs + args.args + args.kwonlyargs:
            if arg.annotation is not None:
                simple = _annotation_to_simple_str(arg.annotation)
                if simple is not None:
                    self._var_types[arg.arg] = simple
        if args.vararg and args.vararg.annotation:
            simple = _annotation_to_simple_str(args.vararg.annotation)
            if simple is not None:
                self._var_types[args.vararg.arg] = simple
        if args.kwarg and args.kwarg.annotation:
            simple = _annotation_to_simple_str(args.kwarg.annotation)
            if simple is not None:
                self._var_types[args.kwarg.arg] = simple

    def visit_Assign(self, node):
        # Visit RHS first (so chained assignments work)
        self.visit(node.value)
        # If RHS is `func()` call with known return type, bind to targets
        if isinstance(node.value, ast.Call):
            rtype = self._call_return_type(node.value)
            if rtype is not None:
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        self._var_types[tgt.id] = rtype

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
            # If annotation overrides inferred type, use annotation
            if isinstance(node.target, ast.Name):
                ann_simple = _annotation_to_simple_str(node.annotation)
                if ann_simple is not None:
                    self._var_types[node.target.id] = ann_simple
                elif isinstance(node.value, ast.Call):
                    rtype = self._call_return_type(node.value)
                    if rtype is not None:
                        self._var_types[node.target.id] = rtype

    def _call_return_type(self, call: ast.Call) -> str | None:
        """Return simple type if `call` invokes a known-annotated function."""
        # Direct call: foo()
        if isinstance(call.func, ast.Name):
            return self.func_returns.get(call.func.id)
        # Method call: self.foo()  → skip (too noisy without class tracking)
        return None

    def visit_Compare(self, node: ast.Compare):
        # Check `var > 0`, `var < 5`, etc. — numeric compare on non-numeric var
        if len(node.ops) == 1 and isinstance(node.ops[0], _NUMERIC_COMPARE_OPS):
            if isinstance(node.left, ast.Name):
                vtype = self._var_types.get(node.left.id)
                if vtype in ("dict", "list", "str", "set"):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "numeric_compare_on_nonnumeric",
                        "var": node.left.id,
                        "vtype": vtype,
                    })
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Check `var.attr` where var was annotated as None (literal None return)
        if isinstance(node.value, ast.Name):
            vtype = self._var_types.get(node.value.id)
            if vtype == "None":
                self.findings.append({
                    "line": node.lineno,
                    "kind": "attr_on_none",
                    "var": node.value.id,
                    "attr": node.attr,
                })
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # Detect `"foo" + 123` or `123 + "foo"` (str + int constant)
        if isinstance(node.op, ast.Add):
            left, right = node.left, node.right
            if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                if isinstance(left.value, str) and isinstance(right.value, (int, float)):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "str_plus_num",
                        "left": repr(left.value),
                        "right": repr(right.value),
                    })
                elif isinstance(right.value, str) and isinstance(left.value, (int, float)):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "str_plus_num",
                        "left": repr(left.value),
                        "right": repr(right.value),
                    })
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # Detect `lst[<str_constant>]` where lst is annotated as list/set
        if isinstance(node.value, ast.Name):
            vtype = self._var_types.get(node.value.id)
            if vtype in ("list", "set", "tuple"):
                # Check if slice is a string constant
                slice_node = node.slice
                # Python 3.9+: slice is the expression directly
                if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "str_index_on_list",
                        "var": node.value.id,
                        "vtype": vtype,
                        "key": repr(slice_node.value),
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


class TypeContractScanner:
    """Detect type-contract violations: numeric compare on dict/list/str,
    attr access on None-returning function, str+int constants, str index on list."""

    name: str = "TypeContractScanner"
    bug_type: str = "TypeMismatch"

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
                logger.debug("type_contract_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("type_contract_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            # Pass 1: collect function return annotations
            collector = _FuncReturnCollector()
            collector.visit(tree)

            # Pass 2: walk function bodies to find misuse
            finder = _TypeMisuseFinder(collector.func_returns, str(path))
            finder.visit(tree)

            for f in finder.findings:
                kind = f["kind"]
                if kind == "numeric_compare_on_nonnumeric":
                    desc = (
                        f"TypeMismatch: variable `{f['var']}` has inferred type "
                        f"`{f['vtype']}` (from function return annotation) but is "
                        f"used in numeric Compare (> < >= <=) at line {f['line']} — "
                        f"this raises TypeError at runtime."
                    )
                    fix = (
                        f"Either change the function return type to numeric (int/float), "
                        f"or change the comparison to check truthiness "
                        f"`if {f['var']}:` or length `if len({f['var']}) > 0:`."
                    )
                elif kind == "attr_on_none":
                    desc = (
                        f"TypeMismatch: variable `{f['var']}` has inferred type `None` "
                        f"(function annotated `-> None`) but `.attr` accessed at line "
                        f"{f['line']} — NoneType has no attribute `{f['attr']}`."
                    )
                    fix = (
                        f"Either remove the `-> None` annotation (function actually "
                        f"returns a value), or change the function to return the right "
                        f"type, or check `if {f['var']} is not None:` before access."
                    )
                elif kind == "str_plus_num":
                    desc = (
                        f"TypeMismatch: str + numeric constant at line {f['line']} "
                        f"({f['left']} + {f['right']}) — raises TypeError."
                    )
                    fix = "Convert both operands to str (str(num)) or both to numeric."
                elif kind == "str_index_on_list":
                    desc = (
                        f"TypeMismatch: variable `{f['var']}` is typed `{f['vtype']}` "
                        f"but indexed with string key {f['key']} at line {f['line']} "
                        f"— list/set/tuple indices must be int, not str."
                    )
                    fix = (
                        f"Use int index (`{f['var']}[0]`) or change container type to "
                        f"dict (`{f['var']} = {{}}`) if string keys are intended."
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
            f"[TypeContractScanner] found {len(bugs)} type-mismatch bug(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
