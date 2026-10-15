# [V8.0-SCANNER] PerformanceScanner — detect O(n²) patterns + inefficient idioms.
#
# TẠI SAO scanner này tồn tại?
#   Code "chạy được" không có nghĩa "chạy nhanh". Một số pattern rõ ràng O(n²):
#     - Nested loops trên cùng list → O(n²)
#     - list.index(x) inside loop → O(n²) (linear search inside loop)
#     - `if x in list:` inside loop → O(n²) (linear scan; should be `set`)
#     - `s = ""; for x in items: s += str(x)` → O(n²) string concat (CPython
#       optimizes this away in simple cases but NOT when intermediate ops
#       intervene — should use "".join(items))
#
# LOGIC:
#   1. Nested same-list loops: walk For statements, track iter Name. If outer
#      For iter is `for x in items:` and inner For iter is `for y in items:`
#      (same Name) → O(n²) flag.
#   2. list.index() in loop: if For body contains `lst.index(...)` call where
#      lst is the loop iter var's source → O(n²).
#   3. `in <list>` in loop: if For body contains `if x in <Name>:` where Name
#      was bound to a list (not set) → flag.
#   4. String concat in loop: `s += "..."` inside For body where s is a str
#      (heuristic: name starts with 's', 'str', 'msg', 'text', 'result',
#      'output', 'html', 'json', 'csv') → flag.
#
# CONSERVATIVE HEURISTICS:
#   - Skip loops with small fixed iterators (range(<10), enumerate of literal)
#   - Skip test files, scripts
#   - For nested loops: only flag if BOTH iter names match exactly (same var)
#   - For list.index(): only flag if arg is the loop var
#   - For `in list`: only flag if RHS is a Name (not expr) — and we don't track
#     list-vs-set distinction without type info, so we flag all `in <Name>` as
#     "should be set" but only if loop body contains the pattern AND the Name
#     is locally assigned (not method call result)
#   - For string concat: skip if loop body has only ONE concat (CPython
#     optimizes simple cases); flag if >= 2 concats in same loop body
#
# RETURNS:
#   list[BugReport] — bug_type="PerformanceIssue"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.performance")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Variable name prefixes suggesting string accumulator
_STRING_VAR_PREFIXES = ("s", "str", "msg", "text", "result", "output",
                         "html", "json", "csv", "body", "buf", "buffer")


def _iter_name(node) -> str | None:
    """If node is a Name (or simple attr chain), return the name. Else None."""
    if isinstance(node, ast.Name):
        return node.id
    return None


def _looks_string_typed(node) -> bool:
    """Heuristic: does this AST node look like a string value?

    Used to filter out `score += 1` (int) from `s += "x"` (str).
    Conservative: only True if we're confident it's a string.
    """
    # String literal
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    # f-string
    if isinstance(node, ast.JoinedStr):
        return True
    # str() constructor call
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "str"):
        return True
    # .lower(), .upper(), .strip(), .format() — string methods
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("lower", "upper", "strip", "lstrip",
                                    "rstrip", "format", "replace", "join")):
        return True
    # Name with string-like prefix — too risky, skip
    return False


def _is_small_range(iter_node) -> bool:
    """True if iter is `range(<small_int>)` — skip O(n²) warning."""
    if (isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and iter_node.func.id == "range"):
        if iter_node.args and isinstance(iter_node.args[0], ast.Constant):
            v = iter_node.args[0].value
            if isinstance(v, int) and v <= 10:
                return True
    return False


class _PerfFinder(ast.NodeVisitor):
    """Walk function bodies, find O(n²) patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []
        # Stack of (loop_var_source_name, lineno) — for nested-loop detection
        self._loop_stack: list[tuple[str | None, int]] = []

    def visit_FunctionDef(self, node):
        saved = list(self._loop_stack)
        self._loop_stack = []
        for stmt in node.body:
            self.visit(stmt)
        self._loop_stack = saved

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_For(self, node: ast.For):
        # Detect iter source (Name only — skip complex exprs)
        iter_name = _iter_name(node.iter) if not _is_small_range(node.iter) else None
        # Check if this is a nested loop on same iter source
        if iter_name is not None:
            for outer_name, outer_line in self._loop_stack:
                if outer_name == iter_name:
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "nested_same_iter",
                        "iter": iter_name,
                        "outer_line": outer_line,
                    })
                    break  # only one finding per nested loop
        # Walk body with this loop on stack
        self._loop_stack.append((iter_name, node.lineno))
        # Walk body for inner patterns (list.index, in-list, str concat)
        self._scan_loop_body(node.body, iter_name, node.target)
        for stmt in node.body:
            self.visit(stmt)
        # Walk orelse
        for stmt in node.orelse:
            self.visit(stmt)
        self._loop_stack.pop()

    visit_AsyncFor = visit_For

    def _scan_loop_body(self, body, loop_iter_name, loop_target):
        """Scan loop body for list.index(), in-list, str concat patterns."""
        # Collect string-concat assignments per variable
        concat_count: dict[str, int] = {}
        # Get loop var name (target of for-loop) for list.index() detection
        loop_var_name = None
        if isinstance(loop_target, ast.Name):
            loop_var_name = loop_target.id
        for stmt in body:
            for sub in ast.walk(stmt):
                # list.index(loop_var) — O(n) linear search inside loop = O(n²)
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "index"
                        and isinstance(sub.func.value, ast.Name)
                        and loop_var_name is not None
                        and sub.args
                        and isinstance(sub.args[0], ast.Name)
                        and sub.args[0].id == loop_var_name):
                    self.findings.append({
                        "line": sub.lineno,
                        "kind": "list_index_in_loop",
                        "iter": sub.func.value.id,
                    })
                # `if x in <list_name>:` — should be `set`
                # Conservative: only flag if name STRONGLY suggests list (skip
                # ambiguous names like "data" which are often dicts).
                if (isinstance(sub, ast.Compare)
                        and len(sub.ops) == 1
                        and isinstance(sub.ops[0], ast.In)
                        and isinstance(sub.left, ast.Name)
                        and isinstance(sub.comparators[0], ast.Name)):
                    in_list = sub.comparators[0].id
                    name_lower = in_list.lower()
                    # Strong list indicators in name (not "data" — too generic)
                    strong_list_indicators = (
                        "_list", "list_", "items_list", "records", "rows",
                        "queue", "stack", "_arr", "arr_",
                    )
                    if any(s in name_lower for s in strong_list_indicators):
                        self.findings.append({
                            "line": sub.lineno,
                            "kind": "in_list_check",
                            "list_name": in_list,
                        })
                # String concat: s += "..."  (AugAssign with Add) where RHS is a
                # string-typed value (Constant str, JoinedStr, str() call, .lower() etc.)
                if (isinstance(sub, ast.AugAssign)
                        and isinstance(sub.op, ast.Add)
                        and isinstance(sub.target, ast.Name)
                        and _looks_string_typed(sub.value)):
                    tgt = sub.target.id
                    # Heuristic: name suggests string accumulator
                    first_word = tgt.split("_")[0].lower()
                    if (first_word in _STRING_VAR_PREFIXES
                            or any(tgt.lower().startswith(p) for p in _STRING_VAR_PREFIXES)):
                        concat_count[tgt] = concat_count.get(tgt, 0) + 1
        # Flag string concat only if >= 2 concats in same loop (CPython
        # optimizes single-concat cases)
        for var, cnt in concat_count.items():
            if cnt >= 2:
                self.findings.append({
                    "line": 0,  # will use loop line for report
                    "kind": "str_concat_in_loop",
                    "var": var,
                    "count": cnt,
                })


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


class PerformanceScanner:
    """Detect O(n²) patterns: nested same-iter loops, list.index() in loop,
    `in <list>` checks in loop, string concat in loop."""

    name: str = "PerformanceScanner"
    bug_type: str = "PerformanceIssue"

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
                logger.debug("performance_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("performance_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            finder = _PerfFinder(str(path))
            finder.visit(tree)

            # Dedupe findings (same file+line+kind may appear multiple times
            # because of nested walking patterns)
            seen: set[tuple] = set()
            for f in finder.findings:
                key = (f["kind"], f["line"], f.get("iter") or f.get("list_name") or f.get("var"))
                if key in seen:
                    continue
                seen.add(key)
                kind = f["kind"]
                if kind == "nested_same_iter":
                    desc = (
                        f"PerformanceIssue: nested loop at line {f['line']} iterates "
                        f"over same iterable `{f['iter']}` as outer loop at line "
                        f"{f['outer_line']} → O(n²) complexity. For n=1000 this is "
                        f"1,000,000 iterations; for n=10000 it's 100,000,000."
                    )
                    fix = (
                        "Restructure: (a) use dict lookup `{x: y for x, y in items}` "
                        "to make inner lookup O(1); (b) use itertools.product if both "
                        "loops are independent; (c) extract inner loop into a "
                        "helper function with early exit."
                    )
                elif kind == "list_index_in_loop":
                    desc = (
                        f"PerformanceIssue: `list.index(x)` called inside loop at line "
                        f"{f['line']} — `index()` is O(n) linear search, so total "
                        f"complexity is O(n²)."
                    )
                    fix = (
                        "Pre-compute `idx_map = {v: i for i, v in enumerate(lst)}` "
                        "OUTSIDE the loop, then use `idx_map[x]` (O(1)) inside."
                    )
                elif kind == "in_list_check":
                    desc = (
                        f"PerformanceIssue: `x in <list>` check inside loop at line "
                        f"{f['line']} on `{f['list_name']}` — list `in` is O(n), total "
                        f"complexity O(n²). Should use `set` for O(1) membership test."
                    )
                    fix = (
                        f"Convert `{f['list_name']}` to a set BEFORE the loop: "
                        f"`{f['list_name']}_set = set({f['list_name']})`, then "
                        f"`if x in {f['list_name']}_set:`. Set lookup is O(1) average."
                    )
                elif kind == "str_concat_in_loop":
                    desc = (
                        f"PerformanceIssue: string `+=` concat in loop on variable "
                        f"`{f['var']}` ({f['count']} times) — CPython may not optimize "
                        f"this when intermediate ops intervene, leading to O(n²) "
                        f"string copies."
                    )
                    fix = (
                        "Collect items into a list, then `''.join(items)` at end. "
                        "join() is O(n) total; `+=` is O(n²) when refcount > 1."
                    )
                else:
                    continue
                # For str_concat_in_loop, line=0 means "loop body" — set to first finding
                line = f["line"] if f["line"] > 0 else 1
                bugs.append(BugReport(
                    file=str(path),
                    line=line,
                    bug_type=self.bug_type,
                    description=desc,
                    suggested_fix=fix,
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                    affects_logic=False,
                ))

        logger.info(
            f"[PerformanceScanner] found {len(bugs)} perf issue(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
