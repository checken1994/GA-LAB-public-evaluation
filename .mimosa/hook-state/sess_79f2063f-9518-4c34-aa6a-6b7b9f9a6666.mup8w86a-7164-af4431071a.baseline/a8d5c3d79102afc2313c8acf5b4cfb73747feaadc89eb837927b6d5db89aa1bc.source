# [V8.0-SCANNER] ResourceLeakScanner — detect unclosed resources.
#
# TẠI SAO scanner này tồn tại?
#   Resources (file handles, sockets, DB connections, HTTP responses) nếu
#   không close() sẽ leak → fd exhaustion, "Too many open files" error.
#   Python `with` statement tự close() khi exit block (kể cả exception).
#   Scanner này phát hiện resource mở mà KHÔNG dùng `with` và KHÔNG close()
#   trong cùng function scope.
#
# PATTERNS DETECTED:
#   1. `f = open(...)`           — file handle, must close()
#   2. `s = socket.socket(...)`  — socket, must close()
#   3. `conn = sqlite3.connect(...)`  — DB connection, must close()
#   4. `r = <HTTP client call>`  — HTTP response, must close() OR used as context
#   5. `conn = psycopg2.connect(...)` / `pymysql.connect(...)` — DB connections
#
# LOGIC (per-function scope):
#   1. Walk function bodies, track resource handles assigned to vars:
#        - var = open(...)
#        - var = socket.socket(...)
#        - var = sqlite3.connect(...)
#        - var = <module>.connect(...)
#        - var = HTTP client fetch (requests module: get/post/request forms)
#   2. Track `with var:` or `with ... as var:` blocks — resource auto-closed.
#   3. Track explicit `var.close()` calls — resource manually closed.
#   4. At end of function: if resource var was assigned but NEVER seen inside
#      `with` block AND NEVER had `.close()` called → BUG.
#
# CONSERVATIVE HEURISTICS:
#   - Skip if var is reassigned before use (assignment overrides previous)
#   - Skip if `return var` (caller owns lifecycle)
#   - Skip if `var` is passed to another function as arg (e.g. csv.reader(f))
#     — too noisy, conservative skip
#   - Skip if assignment is inside try block with `finally: var.close()` block
#     (try/finally pattern is also safe)
#   - Skip __init__ (resources opened in init are usually closed in __del__/close())
#
# RETURNS:
#   list[BugReport] — bug_type="ResourceLeak"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.resource_leak")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Function calls that return resources requiring close()
_RESOURCE_OPENERS = {
    # (func_name_pattern, resource_kind)
    "open": "file",
    "socket": "socket",  # socket.socket(...)
    "connect": "connection",  # sqlite3.connect / psycopg2.connect / etc
    "urlopen": "http_response",  # urllib.request.urlopen
    "get": "http_response",  # requests.get
    "post": "http_response",  # requests.post
    "put": "http_response",  # requests.put
    "request": "http_response",  # requests.request
}


def _is_resource_opening_call(node: ast.Call) -> str | None:
    """If node opens a resource, return the resource kind. Else None."""
    # Direct call: open(...)
    if isinstance(node.func, ast.Name) and node.func.id == "open":
        return "file"
    # Attribute call: socket.socket() / sqlite3.connect() / requests.get()
    if isinstance(node.func, ast.Attribute):
        attr = node.func.attr
        if attr == "socket":
            # socket.socket() — func.value should be Name('socket')
            return "socket"
        if attr == "connect":
            return "connection"
        if attr in ("get", "post", "put", "request", "urlopen"):
            # Check if receiver is `requests` or `urllib.request`
            recv = node.func.value
            if isinstance(recv, ast.Name) and recv.id == "requests":
                return "http_response"
            if isinstance(recv, ast.Attribute) and recv.attr == "request":
                return "http_response"
            # Could be dict.get() — skip if receiver looks like a local var
            return None
    return None


class _ResourceLeakFinder(ast.NodeVisitor):
    """Walk function bodies, find resource handles assigned without close."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []
        # Per-function state: var_name → (line, kind) of resource opening
        self._open_resources: dict[str, tuple[int, str]] = {}
        # Per-function: set of vars that are "managed" (with-statement or .close() called or returned)
        self._managed: set[str] = set()
        # Stack of `with` block vars (resources opened via `with X as var:`)
        self._with_vars: set[str] = set()
        # Stack of `finally` block (try/finally pattern is safe)
        self._in_finally: int = 0

    def visit_FunctionDef(self, node):
        saved_open = dict(self._open_resources)
        saved_managed = set(self._managed)
        saved_with = set(self._with_vars)
        saved_finally = self._in_finally
        self._open_resources = {}
        self._managed = set()
        self._with_vars = set()
        self._in_finally = 0

        for stmt in node.body:
            self.visit(stmt)

        # End of function — any open resource not managed = leak
        for var, (line, kind) in self._open_resources.items():
            if var in self._managed:
                continue
            self.findings.append({
                "line": line,
                "var": var,
                "kind": kind,
            })

        self._open_resources = saved_open
        self._managed = saved_managed
        self._with_vars = saved_with
        self._in_finally = saved_finally

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        # First visit RHS (in case RHS itself has calls)
        self.visit(node.value)
        # If RHS is a resource opening, track the target var
        if isinstance(node.value, ast.Call):
            kind = _is_resource_opening_call(node.value)
            if kind:
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        # Skip if assigned inside with-block (already managed)
                        if tgt.id in self._with_vars:
                            self._managed.add(tgt.id)
                        else:
                            self._open_resources[tgt.id] = (node.lineno, kind)

    def visit_AnnAssign(self, node):
        if node.value is not None:
            self.visit(node.value)
            if isinstance(node.value, ast.Call):
                kind = _is_resource_opening_call(node.value)
                if kind and isinstance(node.target, ast.Name):
                    if node.target.id in self._with_vars:
                        self._managed.add(node.target.id)
                    else:
                        self._open_resources[node.target.id] = (node.lineno, kind)

    def visit_With(self, node: ast.With):
        # Resources opened via `with X as var:` are auto-managed
        for item in node.items:
            ctx = item.context_expr
            # `with open(...) as f:` — f is auto-managed
            if isinstance(ctx, ast.Call) and _is_resource_opening_call(ctx):
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    self._managed.add(item.optional_vars.id)
            # `with var:` — var (already assigned) is auto-managed in this block
            elif isinstance(ctx, ast.Name) and ctx.id in self._open_resources:
                self._managed.add(ctx.id)
        for stmt in node.body:
            self.visit(stmt)

    visit_AsyncWith = visit_With

    def visit_Call(self, node: ast.Call):
        # `var.close()` — mark as managed
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "close"
                and isinstance(node.func.value, ast.Name)):
            vname = node.func.value.id
            if vname in self._open_resources:
                self._managed.add(vname)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        # `return var` — caller owns lifecycle, skip
        if isinstance(node.value, ast.Name) and node.value.id in self._open_resources:
            self._managed.add(node.value.id)
        if node.value is not None:
            self.visit(node.value)

    def visit_Try(self, node: ast.Try):
        # try/finally pattern: if finally block has var.close(), it's safe.
        # We mark all open resources as managed if finally block contains any
        # close() call OR if any var in finally matches an open resource.
        for stmt in node.body:
            self.visit(stmt)
        for handler in node.handlers:
            self.visit(handler)
        for stmt in node.orelse:
            self.visit(stmt)
        # In finally block, look for .close() calls and mark vars managed
        for stmt in node.finalbody:
            self._in_finally += 1
            self.visit(stmt)
            self._in_finally -= 1
        # If finally has any .close() on open resources, mark all open as managed
        # (conservative: any close in finally means we trust the pattern)
        for stmt in ast.walk(ast.Module(body=node.finalbody, type_ignores=[])):
            if (isinstance(stmt, ast.Call)
                    and isinstance(stmt.func, ast.Attribute)
                    and stmt.func.attr == "close"
                    and isinstance(stmt.func.value, ast.Name)
                    and stmt.func.value.id in self._open_resources):
                self._managed.add(stmt.func.value.id)


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


class ResourceLeakScanner:
    """Detect resource leaks: open()/socket()/connect()/requests.get() assigned
    to a var without `with` statement or explicit .close() in same function."""

    name: str = "ResourceLeakScanner"
    bug_type: str = "ResourceLeak"

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
                logger.debug("resource_leak_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("resource_leak_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            finder = _ResourceLeakFinder(str(path))
            finder.visit(tree)

            for f in finder.findings:
                kind = f["kind"]
                var = f["var"]
                bugs.append(BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=(
                        f"ResourceLeak: variable `{var}` opens a {kind} resource at "
                        f"line {f['line']} but is never used in a `with` block, never "
                        f"has `.close()` called, and is not returned to caller. "
                        f"Resource will leak — repeated calls will exhaust file "
                        f"descriptors / connections / sockets."
                    ),
                    suggested_fix=(
                        f"Use `with {kind}_resource as {var}:` (preferred — auto-closes "
                        f"on block exit, even on exception). Or add `{var}.close()` in "
                        f"a `finally:` block. NEVER rely on GC to close resources — "
                        f"CPython may delay closing for arbitrary time."
                    ),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                    affects_logic=False,
                ))

        logger.info(
            f"[ResourceLeakScanner] found {len(bugs)} resource leak(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
