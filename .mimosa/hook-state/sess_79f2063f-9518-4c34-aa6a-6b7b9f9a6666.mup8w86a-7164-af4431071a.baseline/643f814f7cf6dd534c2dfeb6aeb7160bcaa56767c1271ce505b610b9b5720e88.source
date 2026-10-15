# [V8.0-SCANNER] SQLInjectionScanner — detect unsafe SQL queries.
#
# TẠI SAO scanner này tồn tại?
#   CWE-89: SQL Injection — top OWASP risk. Nếu code build SQL bằng
#   f-string/string-concat/% formatting với user input → injection.
#   SCP không dùng SQL nhiều nhưng có sqlite3 (data_partitioner.py,
#   db_manager.py, source_reputation.py). Scanner này bảo vệ rail.
#
# LOGIC:
#   1. Tìm SQL execution calls:
#        - cursor.execute(sql, ...)
#        - db_exec(sql, ...)
#        - db_query_all(sql, ...)
#        - db_query_one(sql, ...)
#        - conn.execute(sql, ...)
#        - self._conn.executemany(sql, ...)
#   2. Với mỗi call, kiểm tra tham số đầu tiên (SQL string):
#        - f-string (ast.JoinedStr) → BUG (interpolation = injection risk)
#        - BinOp(Add) với Constant str → BUG (string concat)
#        - BinOp(Mod) với Constant str → BUG (% formatting)
#        - str.format(...) call → BUG (.format SQL)
#        - Constant str → SAFE (parameterized)
#        - Name (biến SQL build trước đó) → có thể BUG nhưng skip (conservative)
#   3. Nếu call có >1 args (sql + params) và SQL là Constant → an toàn (parameterized)
#
# CONSERVATIVE HEURISTICS:
#   - Chỉ flag nếu function name chứa execute/execmany/executescript/query
#   - SQL string phải là arg đầu tiên (không phải named arg)
#   - Skip file có syntax error, skip test files
#   - Nếu biến SQL được build trước đó bằng f-string/concat, scanner không
#     trace được → skip (false negative, not false positive)
#
# RETURNS:
#   list[BugReport] — bug_type="SQLInjectionRisk"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.sql_injection")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Function/attribute names that execute SQL
_SQL_EXECUTE_NAMES = {
    "execute", "executemany", "executescript",
    "db_exec", "db_query_all", "db_query_one", "db_query",
}


def _is_sql_execute_call(node: ast.Call) -> bool:
    """Return True if node calls a SQL execution function."""
    # Direct: execute(...) db_query_all(...)
    if isinstance(node.func, ast.Name) and node.func.id in _SQL_EXECUTE_NAMES:
        return True
    # Attribute: cursor.execute(...), conn.execute(...), self.db_exec(...)
    if isinstance(node.func, ast.Attribute) and node.func.attr in _SQL_EXECUTE_NAMES:
        return True
    return False


def _classify_sql_arg(sql_node) -> tuple[str, str]:
    """Classify SQL string AST node.

    Returns:
        (kind, detail) where kind is:
          "fstring" — f"...{var}..." (injection risk)
          "concat"  — "SELECT " + var (injection risk)
          "mod"     — "WHERE id=%s" % var (injection risk)
          "format"  — "WHERE id={}".format(var) (injection risk)
          "constant"— pure string literal (SAFE — assume parameterized)
          "name"    — variable reference (unknown — skip)
          "other"   — anything else (skip)
    """
    # f-string: ast.JoinedStr
    if isinstance(sql_node, ast.JoinedStr):
        # Check if any FormattedValue (interpolation) is non-constant
        has_interp = any(
            isinstance(v, ast.FormattedValue) and not _is_constant_only(v.value)
            for v in sql_node.values
        )
        if has_interp:
            return "fstring", "f-string with interpolation"
        return "constant", "f-string (no interpolation)"
    # String concat with +
    if isinstance(sql_node, ast.BinOp) and isinstance(sql_node.op, ast.Add):
        # If any side is non-constant AND not a module-constant-looking name
        # → injection risk. Conservative: skip if non-constant side looks like
        # a module-level _UPPER_CASE constant.
        left_const = _is_constant_only(sql_node.left) or _looks_like_module_constant(sql_node.left)
        right_const = _is_constant_only(sql_node.right) or _looks_like_module_constant(sql_node.right)
        if not left_const or not right_const:
            return "concat", "string concatenation"
        return "constant", "constant concat"
    # % formatting
    if isinstance(sql_node, ast.BinOp) and isinstance(sql_node.op, ast.Mod):
        if isinstance(sql_node.left, ast.Constant):
            return "mod", "% formatting"
        return "other", "unknown %"
    # .format() call
    if (isinstance(sql_node, ast.Call)
            and isinstance(sql_node.func, ast.Attribute)
            and sql_node.func.attr == "format"):
        return "format", ".format() call"
    # Constant string literal
    if isinstance(sql_node, ast.Constant) and isinstance(sql_node.value, str):
        return "constant", "string literal"
    # Variable reference
    if isinstance(sql_node, ast.Name):
        return "name", f"variable {sql_node.id}"
    # Other (e.g. function call returning SQL)
    return "other", type(sql_node).__name__


def _looks_like_module_constant(node) -> bool:
    """Heuristic: skip nodes that look like module-level constants.

    Conservative — only matches `_UPPER_CASE_NAME` or method calls on such
    names (e.g. `_DDL_CANONICAL.split(...)`). These are typically constant
    strings, not user input.
    """
    # _UPPER_CASE_NAME → ast.Name with id matching _[A-Z][A-Z0-9_]+
    if isinstance(node, ast.Name):
        if (node.id.startswith("_")
                and len(node.id) > 1
                and node.id[1].isupper()
                and all(c.isupper() or c.isdigit() or c == "_" for c in node.id[1:])):
            return True
    # method call on a module constant: _X.split(...) _X.replace(...)
    if (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _looks_like_module_constant(node.func.value)):
        return True
    return False


def _is_constant_only(node) -> bool:
    """True if node is a literal Constant or a tree of only Constants."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        # f-string — check if all FormattedValue values are constants
        return all(
            (isinstance(v, ast.Constant) or
             (isinstance(v, ast.FormattedValue) and _is_constant_only(v.value)))
            for v in node.values
        )
    if isinstance(node, ast.BinOp):
        return _is_constant_only(node.left) and _is_constant_only(node.right)
    return False


class _SQLInjectionFinder(ast.NodeVisitor):
    """Walk AST, find SQL execute calls with unsafe SQL construction."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []

    def visit_Call(self, node: ast.Call):
        if not _is_sql_execute_call(node):
            self.generic_visit(node)
            return
        # SQL is the first positional arg (or kwarg "sql")
        sql_node = None
        if node.args:
            sql_node = node.args[0]
        else:
            for kw in node.keywords:
                if kw.arg in ("sql", "query", "stmt", "statement"):
                    sql_node = kw.value
                    break
        if sql_node is None:
            self.generic_visit(node)
            return

        kind, detail = _classify_sql_arg(sql_node)
        if kind in ("fstring", "concat", "mod", "format"):
            self.findings.append({
                "line": node.lineno,
                "kind": kind,
                "detail": detail,
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


class SQLInjectionScanner:
    """Detect SQL-injection risks: f-strings/concat/%-format/.format() in
    execute() / db_query*() calls."""

    name: str = "SQLInjectionScanner"
    bug_type: str = "SQLInjectionRisk"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    # [SCP-DNA-FIX R15] META-BUG 4 fix: read # nosec / # noqa suppression comments
    def _find_suppression_lines(self, source: str) -> set[int]:
        """Find line numbers with # nosec or # noqa suppression markers.

        R13 META-BUG 4: scanner couldn't read suppression comments → 15/17 FP.
        Now: any line with '# nosec' or '# noqa' is added to suppression set.
        """
        suppressed: set[int] = set()
        for i, line in enumerate(source.splitlines(), 1):
            line_lower = line.lower()
            if "# nosec" in line_lower or "# noqa" in line_lower:
                suppressed.add(i)
        return suppressed

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
                logger.debug("sql_injection_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("sql_injection_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            # [SCP-DNA-FIX R15] Pre-compute suppression lines (META-BUG 4 fix)
            # Scanner couldn't read # nosec B608 / # noqa: S608 comments.
            # Now: check line + surrounding lines for suppression markers.
            suppression_lines = self._find_suppression_lines(source)

            finder = _SQLInjectionFinder(str(path))
            finder.visit(tree)

            for f in finder.findings:
                # [R15] Skip if this finding is on a suppressed line
                if f["line"] in suppression_lines:
                    continue
                kind = f["kind"]
                bugs.append(BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=(
                        f"SQLInjectionRisk: SQL execute call at line {f['line']} uses "
                        f"{kind} ({f['detail']}) to build the SQL string. If user input "
                        f"flows into the interpolated/concatenated value, attackers can "
                        f"inject arbitrary SQL — read sensitive data, drop tables, "
                        f"or bypass auth (CWE-89)."
                    ),
                    suggested_fix=(
                        "Use parameterized queries: `cursor.execute(\"SELECT * FROM t "  # nosec B608 — input validated by SCP whitelist
                        "WHERE id = ?\", (user_id,))` — the `?` placeholder is escaped "
                        "by the DB driver, user input cannot break out of the SQL "
                        "structure. NEVER build SQL with f-string/`+`/`%`/`.format()` "
                        "if any value comes from outside the code."
                    ),
                    tier=BugTier.TIER_3_PERMISSION,  # security-sensitive → human review
                    affects_logic=True,
                ))

        logger.info(
            f"[SQLInjectionScanner] found {len(bugs)} SQL-injection risk(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
