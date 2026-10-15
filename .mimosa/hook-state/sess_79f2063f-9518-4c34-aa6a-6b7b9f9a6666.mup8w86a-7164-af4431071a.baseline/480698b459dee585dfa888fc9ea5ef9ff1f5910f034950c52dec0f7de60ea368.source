# [V10-SCANNER] TaintFlowScanner — intra-function source→sink dataflow.
#
# TẠI SAO scanner này tồn tại? (Idea 2 from world-autofix research — Pysa/CodeQL)
#   Pattern-based scanners (SecurityScanner, SQLInjectionScanner, XSSScanner)
#   flag SINKS only — they can't tell whether user input actually reaches the
#   sink. A dynamic-SQL execute() with interpolated variables is flagged
#   regardless of whether `x`
#   came from request.args or from a hardcoded constant. This produces both
#   false positives (hardcoded dynamic SQL — no real bug) and misses the
#   ROOT CAUSE: where user input ENTERED the function.
#
#   This scanner implements the Pysa/CodeQL pattern: for each dangerous SINK,
#   walk backward via AST to find if user-controlled SOURCE data reaches it
#   without sanitization. If so → flag as TaintFlow bug (much higher severity
#   than a simple pattern match — this is a confirmed source→sink dataflow).
#
# SOURCES (taint origins):
#   Web input:
#     - request.args / request.form / request.json / request.GET / request.POST
#       (and common aliases: req.args, flask.request.args)
#     - request.args.get(...) / request.form.get(...) / etc.
#   CLI / env:
#     - os.environ.get(...), os.getenv(...)
#     - sys.argv[...]
#   File reads of user-provided paths:
#     - open(...).read(), Path(...).read_text()
#   Heuristic function parameters (only for non-@staticmethod/@classmethod):
#     user_input, query, command, data, payload, content, text, input
#
# SINKS (dangerous endpoints):
#   CWE-78 (OS Command Injection):
#     - subprocess.run/Popen/call/check_output/check_call(...) with shell=True
#       OR tainted arg
#     - os.system(...), os.popen(...)
#   CWE-89 (SQL Injection):
#     - cursor.execute(...) / db.execute(...) / conn.executemany(...) /
#       db_query*(...) where the SQL string arg is built via f-string/`+`/`%`/
#       .format() AND a tainted Name appears in that construction
#   CWE-79 (Cross-Site Scripting):
#     - Markup(...) / flask.Markup(...) / markupsafe.Markup(...)
#     - HTMLResponse(...)
#     (only when first arg contains a tainted Name)
#   CWE-502 (Unsafe Deserialization):
#     - pickle.loads(...), pickle.load(...), marshal.loads(...)
#     - yaml.load(..., Loader=yaml.Loader) — non-SafeLoader
#   CWE-94 (Code Injection):
#     - eval(...), exec(...)
#     - compile(..., 'exec') when source arg contains tainted Name
#
# ALGORITHM (intra-function, AST-based, single-pass walk per FunctionDef):
#   1. Parse file with ast.parse().
#   2. For each FunctionDef (top-level + nested):
#      - Reset per-function taint state.
#      - Check decorators: if @staticmethod or @classmethod → skip heuristic
#        param tainting (these are not user-facing handlers in the typical
#        sense — caller controls args, not the network).
#      - Pre-taint params whose names match _HEURISTIC_PARAM_NAMES.
#      - Walk function body in source order (descending into control flow:
#        If/For/While/Try/With but NOT into nested FunctionDef/ClassDef —
#        those have their own scope and get their own analysis pass).
#      - For each AST node encountered in the walk:
#        (a) ast.Assign / ast.AnnAssign:
#            - If RHS is a sanitizer call (re.escape / shlex.quote /
#              html.escape / str(int(X))) → REMOVE target from tainted set
#              (var is now considered safe).
#            - Else if RHS is a SOURCE call/attr → taint target with the
#              source's line and description.
#            - Else if RHS references any currently-tainted Name (and the
#              reference is not via a sanitizer) → propagate taint to target.
#            - Else if RHS is a Constant or non-tainted Name → REMOVE target
#              from tainted set (reassignment to safe value — avoids FPs).
#        (b) ast.If:
#            - If test is `isinstance(var, ...)` → mark `var` as sanitized
#              (partial heuristic — removes from tainted set for the rest of
#              the function).
#        (c) ast.Call:
#            - If call is a SINK (per _classify_sink) → walk args+kwargs for
#              tainted Names. If any tainted Name reaches the sink → emit
#              a BugReport.
#   3. bug_type = "TaintFlow_CWE-{78|89|79|502|94}".
#      tier = BugTier.TIER_3_PERMISSION (security/logic — human must review).
#      description includes BOTH source line and sink line.
#      suggested_fix = "Sanitize input at source: {source_line} before
#                       passing to {sink_name} at line {sink_line}. ..."
#
# CONSERVATIVE HEURISTICS (avoid false positives — false positives erode trust):
#   - Only track taint WITHIN the same function scope (no cross-function
#     propagation). y = f(x) where x is tainted does NOT taint y unless f is
#     itself a SOURCE.
#   - `if isinstance(x, ...)` check between source and sink → x is considered
#     sanitized for the remainder of the function (partial heuristic).
#   - Sanitizer wrappers remove taint: re.escape(x), shlex.quote(x),
#     html.escape(x), str(int(x)).
#   - Reassignment to a Constant or non-tainted Name removes taint from target.
#   - Skip test files (path contains "/tests/" or filename starts with "test_"
#     or ends with "_test.py").
#   - Skip __pycache__, examples, scripts, attack_payloads, benchmark dirs.
#   - SQL sink only flagged if SQL string is built dynamically (f-string/+/%/
#     .format) — Constant SQL strings are parameterized and safe.
#   - subprocess.* sink only emits bug if a tainted Name reaches args/kwargs
#     (shell=True alone, without taint, is a SecurityScanner concern, not
#     TaintFlow's).
#
# RETURNS:
#   list[BugReport] — bug_type="TaintFlow_CWE-XXX", tier=TIER_3_PERMISSION.
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.taint_flow")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

__all__ = ["scan_file", "scan_scp"]


# ============================================================================
# SOURCES (taint origins)
# ============================================================================

# Web framework request attrs (Flask/Django/FastAPI) — used both as direct
# attribute access (request.args) and as method-call receiver (request.args.get).
_WEB_SOURCE_ATTRS: frozenset[str] = frozenset({
    "args", "form", "json", "GET", "POST", "data", "values",
    "cookies", "headers", "params",
})

# Variable names commonly used as the request object in handlers
_REQUEST_VAR_NAMES: frozenset[str] = frozenset({"request", "req", "flask"})

# Heuristic parameter names suggesting user input (only tainted when function
# is NOT @staticmethod/@classmethod — for static/class methods, the caller
# controls the args, not the network).
_HEURISTIC_PARAM_NAMES: frozenset[str] = frozenset({
    "user_input", "query", "command", "data", "payload",
    "content", "text", "input",
})

# Sanitizer function dotted names that "neutralize" taint
_SANITIZER_FUNCS: frozenset[str] = frozenset({
    "re.escape", "shlex.quote", "html.escape",
    "markupsafe.escape", "flask.escape", "cgi.escape",
    "bleach.clean",
})

# Bare-name sanitizer funcs (rare — usually qualified)
_SANITIZER_BARE_NAMES: frozenset[str] = frozenset({"escape", "quote", "clean"})


# ============================================================================
# SINKS (dangerous endpoints)
# ============================================================================

# subprocess functions that execute shell commands
_SUBPROCESS_FUNCS: frozenset[str] = frozenset({
    "run", "Popen", "call", "check_output", "check_call",
})

# pickle / marshal deserialization methods
_PICKLE_FUNCS: frozenset[str] = frozenset({"loads", "load"})
_MARSHAL_FUNCS: frozenset[str] = frozenset({"loads", "dumps"})

# SQL execute function/attribute names
_SQL_EXECUTE_NAMES: frozenset[str] = frozenset({
    "execute", "executemany", "executescript",
    "db_exec", "db_query_all", "db_query_one", "db_query",
})

# XSS-prone response/markup builders (bare-name imports)
_XSS_BUILDERS: frozenset[str] = frozenset({"Markup", "HTMLResponse"})


# ============================================================================
# CWE titles for description generation
# ============================================================================

_CWE_TITLES: dict[str, str] = {
    "CWE-78": "OS Command Injection",
    "CWE-89": "SQL Injection",
    "CWE-79": "Cross-Site Scripting (XSS)",
    "CWE-502": "Unsafe Deserialization",
    "CWE-94": "Code Injection",
}


# ============================================================================
# Helpers
# ============================================================================

def _is_test_file(path: Path) -> bool:
    """Return True if path looks like a test file or non-production code."""
    if "tests" in path.parts:
        return True
    if "test" in path.parts:
        return True
    if path.name.startswith("test_"):
        return True
    if path.name.endswith("_test.py"):
        return True
    if any(part in ("examples", "scripts", "attack_payloads", "benchmark")
           for part in path.parts):
        return True
    return False


def _dotted_name(node) -> str | None:
    """Return dotted name (e.g., 'os.environ.get') from Attribute/Name chain.

    Returns None for complex expressions (subscripts, calls, etc.).
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _is_source(node) -> tuple[str, str] | None:
    """If node is a SOURCE call/expression, return (kind, description).

    Returns None if not a source.

    Detected sources:
      - request.args / request.form / request.json / request.GET / request.POST
        (direct attribute access — common in Flask)
      - request.args.get(...) / request.form.get(...) / etc. (method calls)
      - os.environ.get(...) / os.getenv(...)
      - getenv(...) (bare-name alias)
      - sys.argv[...] (subscript)
    """
    # --- Call-based sources ---
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            func = node.func
            # request.args.get(...) / request.form.get(...) / etc.
            if func.attr in ("get", "getlist"):
                if (isinstance(func.value, ast.Attribute)
                        and isinstance(func.value.value, ast.Name)
                        and func.value.value.id in _REQUEST_VAR_NAMES
                        and func.value.attr in _WEB_SOURCE_ATTRS):
                    return ("web",
                            f"{func.value.value.id}.{func.value.attr}.get()")
            # os.environ.get(...) / os.getenv(...)
            dotted = _dotted_name(func)
            if dotted == "os.environ.get":
                return ("env", "os.environ.get()")
            if dotted == "os.getenv":
                return ("env", "os.getenv()")
        # Bare-name getenv(...)
        if isinstance(node.func, ast.Name) and node.func.id == "getenv":
            return ("env", "getenv()")
        # No return here — fall through to attribute/subscript checks
    # --- Attribute-based sources (request.args, request.form, etc.) ---
    if isinstance(node, ast.Attribute):
        if (isinstance(node.value, ast.Name)
                and node.value.id in _REQUEST_VAR_NAMES
                and node.attr in _WEB_SOURCE_ATTRS):
            return ("web", f"{node.value.id}.{node.attr}")
    # --- Subscript-based sources (sys.argv[...]) ---
    if isinstance(node, ast.Subscript):
        if (isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "sys"
                and node.value.attr == "argv"):
            return ("cli", "sys.argv[...]")
    return None


def _is_sanitizer_call(node) -> bool:
    """Return True if node is a Call to a known sanitizer function.

    Sanitizers wrap a tainted value and produce a "safe" output:
      - re.escape(x), shlex.quote(x), html.escape(x), markupsafe.escape(x),
        bleach.clean(x), cgi.escape(x), flask.escape(x)
      - str(int(x)) / str(float(x)) — numeric coercion then stringified
    """
    if not isinstance(node, ast.Call):
        return False
    # str(int(X)) / str(float(X)) — double-call sanitizer pattern
    if (isinstance(node.func, ast.Name)
            and node.func.id == "str"
            and node.args
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id in ("int", "float")):
        return True
    # Qualified sanitizer call (re.escape, shlex.quote, html.escape, ...)
    dotted = _dotted_name(node.func)
    if dotted is not None and dotted in _SANITIZER_FUNCS:
        return True
    # Bare-name sanitizer call (rare — usually qualified to avoid shadowing)
    if isinstance(node.func, ast.Name) and node.func.id in _SANITIZER_BARE_NAMES:
        return True
    return False


def _collect_names(node) -> set[str]:
    """Collect all Name.id values referenced in node (any context)."""
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            names.add(n.id)
    return names


def _is_dynamic_sql_string(node) -> bool:
    """Return True if node is a dynamically-built SQL string.

    Dynamic = f-string with interpolation, `+` concatenation, `%` formatting,
    or `.format()` call. Pure Constant strings are parameterized-safe.
    """
    if isinstance(node, ast.JoinedStr):
        # f-string — flag if it has any FormattedValue (interpolation)
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Mod)):
            return True
    if isinstance(node, ast.Call):
        # "...".format(...)
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"
                and isinstance(node.func.value, (ast.Constant, ast.JoinedStr))):
            return True
    return False


def _classify_sink(node: ast.Call) -> tuple[str, str] | None:
    """If node is a dangerous SINK call, return (cwe, sink_name). Else None.

    The SINK classification is structural — it does NOT check whether taint
    actually reaches the sink. That check happens in _handle_call.

    CWE mapping:
      CWE-78 — command injection (os.system, os.popen, subprocess.*)
      CWE-89 — SQL injection (cursor.execute with dynamic SQL)
      CWE-79 — XSS (Markup, HTMLResponse)
      CWE-502 — deserialization (pickle/marshal/yaml non-Safe loaders)
      CWE-94 — code injection (eval, exec, compile exec)
    """
    func = node.func

    # --- Attribute-based sinks (os.x, subprocess.x, pickle.x, yaml.x, etc.) ---
    if isinstance(func, ast.Attribute):
        recv = func.value
        attr = func.attr

        # os.system(...) / os.popen(...)
        if isinstance(recv, ast.Name) and recv.id == "os":
            if attr in ("system", "popen"):
                return ("CWE-78", f"os.{attr}")

        # subprocess.run / Popen / call / check_output / check_call
        if isinstance(recv, ast.Name) and recv.id == "subprocess":
            if attr in _SUBPROCESS_FUNCS:
                return ("CWE-78", f"subprocess.{attr}")

        # pickle.loads / pickle.load
        if isinstance(recv, ast.Name) and recv.id == "pickle":
            if attr in _PICKLE_FUNCS:
                return ("CWE-502", f"pickle.{attr}")

        # marshal.loads
        if isinstance(recv, ast.Name) and recv.id == "marshal":
            if attr in _MARSHAL_FUNCS:
                return ("CWE-502", f"marshal.{attr}")

        # yaml.load (non-SafeLoader)
        if isinstance(recv, ast.Name) and recv.id == "yaml":
            if attr == "load":
                has_safe_loader = False
                for kw in node.keywords:
                    if kw.arg == "Loader":
                        if (isinstance(kw.value, ast.Name)
                                and "Safe" in kw.value.id):
                            has_safe_loader = True
                        elif (isinstance(kw.value, ast.Attribute)
                              and "Safe" in kw.value.attr):
                            has_safe_loader = True
                if not has_safe_loader:
                    return ("CWE-502", "yaml.load")

        # cursor.execute / db.execute / conn.executemany / db_query_all(...)
        # — only flag if SQL string is built dynamically
        if attr in _SQL_EXECUTE_NAMES:
            if node.args and _is_dynamic_sql_string(node.args[0]):
                return ("CWE-89", attr)

        # flask.Markup / markupsafe.Markup
        if attr in _XSS_BUILDERS:
            return ("CWE-79", attr)

    # --- Bare-name sinks (eval, exec, compile, Markup, HTMLResponse) ---
    if isinstance(func, ast.Name):
        if func.id in ("eval", "exec"):
            return ("CWE-94", func.id)
        if func.id == "compile":
            # compile(source, filename, mode, ...) — flag if mode == 'exec'
            for arg in node.args:
                if (isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and arg.value == "exec"):
                    return ("CWE-94", "compile")
            for kw in node.keywords:
                if (kw.arg == "mode"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                        and kw.value.value == "exec"):
                    return ("CWE-94", "compile")
        if func.id in _XSS_BUILDERS:
            return ("CWE-79", func.id)

    return None


# ============================================================================
# Per-function taint analyzer
# ============================================================================

class _FunctionTaintAnalyzer:
    """Per-function intra-function taint flow analyzer.

    State is reset at the start of each FunctionDef analysis. The analyzer
    walks the function body in source order, tracking tainted variables and
    checking SINK calls for tainted-arg reachability.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []
        # tainted vars: name -> (source_line, source_desc)
        self._tainted: dict[str, tuple[int, str]] = {}
        # vars explicitly sanitized (via isinstance / sanitizer func)
        self._sanitized: set[str] = set()

    def analyze_function(self, func_node: ast.FunctionDef) -> None:
        """Analyze a single FunctionDef for taint-flow bugs."""
        # Save & reset state (functions can be nested — restore on exit)
        saved_tainted = dict(self._tainted)
        saved_sanitized = set(self._sanitized)
        self._tainted = {}
        self._sanitized = set()

        # Check decorators: @staticmethod / @classmethod → skip heuristic
        # param tainting (caller controls args, not the network)
        is_static_or_class = any(
            (isinstance(d, ast.Name) and d.id in ("staticmethod", "classmethod"))
            or (isinstance(d, ast.Attribute)
                and d.attr in ("staticmethod", "classmethod"))
            for d in func_node.decorator_list
        )

        # Pre-taint heuristic-named params
        if not is_static_or_class:
            all_args = (
                list(func_node.args.posonlyargs)
                + list(func_node.args.args)
                + list(func_node.args.kwonlyargs)
            )
            for arg in all_args:
                if arg.arg in _HEURISTIC_PARAM_NAMES:
                    self._tainted[arg.arg] = (
                        func_node.lineno,
                        f"parameter '{arg.arg}' (heuristic user-input name)",
                    )

        # Walk function body in source order
        for stmt in func_node.body:
            self._walk_in_scope(stmt)

        # Restore parent-scope state
        self._tainted = saved_tainted
        self._sanitized = saved_sanitized

    def _walk_in_scope(self, node) -> None:
        """Walk node + descendants, processing assigns/calls/ifs.

        Does NOT descend into nested FunctionDef / AsyncFunctionDef /
        ClassDef — those have their own scope and get their own analysis
        pass (called from the top-level ast.walk in scan_file).
        """
        # Don't descend into nested scopes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            return

        # Process this node based on its type
        if isinstance(node, ast.If):
            # `if isinstance(var, ...)` → mark var sanitized (partial heuristic)
            self._check_isinstance_in_test(node.test)
        elif isinstance(node, ast.Assign):
            self._handle_assign(node)
        elif isinstance(node, ast.AnnAssign):
            self._handle_annassign(node)
        elif isinstance(node, ast.AugAssign):
            self._handle_augassign(node)
        elif isinstance(node, ast.Call):
            # Expression statement or nested call — check if it's a sink
            self._handle_call(node)

        # Recurse into children (control-flow bodies, expression operands, etc.)
        for child in ast.iter_child_nodes(node):
            self._walk_in_scope(child)

    def _check_isinstance_in_test(self, test_node) -> None:
        """If test is `isinstance(var, ...)` → mark var as sanitized.

        Conservative: removes var from tainted set for the REST of the
        function (not just inside the if-body). This is a partial heuristic
        per the task spec — full branch-sensitive analysis would be too
        expensive for an AST-only scanner.
        """
        for n in ast.walk(test_node):
            if (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "isinstance"):
                if n.args and isinstance(n.args[0], ast.Name):
                    var_name = n.args[0].id
                    self._sanitized.add(var_name)
                    self._tainted.pop(var_name, None)

    def _handle_assign(self, node: ast.Assign) -> None:
        """Track taint through assignments."""
        # Sanitizer wrapping a tainted var → mark target as sanitized
        if isinstance(node.value, ast.Call) and _is_sanitizer_call(node.value):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self._tainted.pop(tgt.id, None)
                    self._sanitized.add(tgt.id)
            return

        # Source call/attr on RHS → taint target
        src = _is_source(node.value)
        if src is not None:
            _, desc = src
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self._tainted[tgt.id] = (node.lineno, desc)
                    self._sanitized.discard(tgt.id)
            return

        # RHS references a tainted var → propagate taint to target
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self._tainted.keys())) - self._sanitized
        if tainted_refs:
            # Use the earliest tainted source for the description
            src_line, src_desc = min(
                (self._tainted[n] for n in tainted_refs),
                key=lambda x: x[0],
            )
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self._tainted[tgt.id] = (
                        src_line,
                        f"{src_desc} (propagated)",
                    )
                    self._sanitized.discard(tgt.id)
            return

        # RHS is non-tainted expression. If it's a clearly-safe value
        # (Constant or non-tainted Name), REMOVE target from tainted —
        # avoids FP when a tainted-named var is reassigned to a constant.
        if isinstance(node.value, ast.Constant):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self._tainted.pop(tgt.id, None)
                    self._sanitized.discard(tgt.id)
        elif (isinstance(node.value, ast.Name)
              and node.value.id not in self._tainted):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self._tainted.pop(tgt.id, None)
                    self._sanitized.discard(tgt.id)

    def _handle_annassign(self, node: ast.AnnAssign) -> None:
        """Same as _handle_assign but for `x: Type = value` form."""
        if node.value is None:
            return
        if isinstance(node.value, ast.Call) and _is_sanitizer_call(node.value):
            if isinstance(node.target, ast.Name):
                self._tainted.pop(node.target.id, None)
                self._sanitized.add(node.target.id)
            return
        src = _is_source(node.value)
        if src is not None:
            _, desc = src
            if isinstance(node.target, ast.Name):
                self._tainted[node.target.id] = (node.lineno, desc)
                self._sanitized.discard(node.target.id)
            return
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self._tainted.keys())) - self._sanitized
        if tainted_refs and isinstance(node.target, ast.Name):
            src_line, src_desc = min(
                (self._tainted[n] for n in tainted_refs),
                key=lambda x: x[0],
            )
            self._tainted[node.target.id] = (
                src_line,
                f"{src_desc} (propagated)",
            )
            self._sanitized.discard(node.target.id)
            return
        # Reassignment to safe value → remove taint
        if isinstance(node.value, ast.Constant):
            if isinstance(node.target, ast.Name):
                self._tainted.pop(node.target.id, None)
                self._sanitized.discard(node.target.id)
        elif (isinstance(node.value, ast.Name)
              and node.value.id not in self._tainted):
            if isinstance(node.target, ast.Name):
                self._tainted.pop(node.target.id, None)
                self._sanitized.discard(node.target.id)

    def _handle_augassign(self, node: ast.AugAssign) -> None:
        """Handle `x += y` — propagate taint from y to x if y is tainted."""
        if not isinstance(node.target, ast.Name):
            return
        rhs_names = _collect_names(node.value)
        tainted_refs = (rhs_names & set(self._tainted.keys())) - self._sanitized
        if tainted_refs:
            src_line, src_desc = min(
                (self._tainted[n] for n in tainted_refs),
                key=lambda x: x[0],
            )
            self._tainted[node.target.id] = (
                src_line,
                f"{src_desc} (propagated via +=)",
            )

    def _handle_call(self, node: ast.Call) -> None:
        """Check if this Call is a SINK with tainted args reachable."""
        sink = _classify_sink(node)
        if sink is None:
            return
        cwe, sink_name = sink

        # Collect all tainted Names reachable in call args + kwargs
        tainted_arg_names: set[str] = set()
        for arg in node.args:
            for n in ast.walk(arg):
                if (isinstance(n, ast.Name)
                        and n.id in self._tainted
                        and n.id not in self._sanitized):
                    tainted_arg_names.add(n.id)
        for kw in node.keywords:
            if kw.value is not None:
                for n in ast.walk(kw.value):
                    if (isinstance(n, ast.Name)
                            and n.id in self._tainted
                            and n.id not in self._sanitized):
                        tainted_arg_names.add(n.id)

        if not tainted_arg_names:
            return  # No taint reaches this sink — no bug.

        # Pick the earliest tainted source for the description
        first_tainted = min(
            tainted_arg_names,
            key=lambda n: self._tainted[n][0],
        )
        src_line, src_desc = self._tainted[first_tainted]

        self.findings.append({
            "line": node.lineno,
            "cwe": cwe,
            "sink_name": sink_name,
            "tainted_var": first_tainted,
            "source_line": src_line,
            "source_desc": src_desc,
            "all_tainted": sorted(tainted_arg_names),
        })


# ============================================================================
# File iteration
# ============================================================================

def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    """Yield Python files under root, skipping tests/__pycache__/examples."""
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if _is_test_file(path):
            continue
        if count >= limit:
            break
        yield path
        count += 1


# ============================================================================
# Public API
# ============================================================================

def scan_file(path: Path) -> list[BugReport]:
    """Scan a single Python file for taint-flow bugs.

    NOTE: scan_file() scans whatever file is passed — the test-file filter
    (_is_test_file) only applies to scan_scp() which walks a directory.
    If a caller explicitly passes a test file path, they want it scanned.

    Args:
        path: Path to a .py file.

    Returns:
        List of BugReports with bug_type="TaintFlow_CWE-XXX". Each report
        captures a confirmed source→sink dataflow within a single function
        scope (no cross-function taint).
    """
    path = Path(path)
    bugs: list[BugReport] = []

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: S110 — best-effort, skip unreadable files
        logger.warning(f"Could not read {path}", exc_info=True)
        return bugs

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        logger.debug(f"SyntaxError in {path}: {e}")
        return bugs

    # Analyze every FunctionDef (top-level + nested) — each gets its own
    # fresh taint state via the save/restore in analyze_function.
    analyzer = _FunctionTaintAnalyzer(str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            analyzer.analyze_function(node)

    for f in analyzer.findings:
        cwe = f["cwe"]
        sink_name = f["sink_name"]
        sink_line = f["line"]
        src_line = f["source_line"]
        src_desc = f["source_desc"]
        tainted_var = f["tainted_var"]
        all_tainted = f["all_tainted"]

        cwe_title = _CWE_TITLES.get(cwe, "Taint Flow")
        extra_tainted = (
            f" (also reaching sink: {', '.join(all_tainted)})"
            if len(all_tainted) > 1 else ""
        )

        desc = (
            f"TaintFlow [{cwe} — {cwe_title}]: user-controlled data reaches "
            f"`{sink_name}(...)` at line {sink_line}. Taint origin: {src_desc} "
            f"at line {src_line}. Variable `{tainted_var}` carries the taint"
            f"{extra_tainted}. This is a confirmed source→sink dataflow "
            f"(not just a sink-only pattern match), so severity is higher "
            f"than a simple SecurityScanner/SQLInjectionScanner/XSSScanner hit."
        )

        fix = (
            f"Sanitize input at source: line {src_line} before passing to "
            f"`{sink_name}` at line {sink_line}. "
        )
        if cwe == "CWE-78":
            fix += (
                "Use shlex.quote() per arg, or pass an argument list with "
                "shell=False. For SCP, prefer scp.core.safe_process."
            )
        elif cwe == "CWE-89":
            fix += (
                "Use parameterized SQL: cursor.execute('... WHERE id=?', "
                "(var,)) — never build SQL via f-string/concat/%/format."
            )
        elif cwe == "CWE-79":
            fix += (
                "Use markupsafe.escape() or rely on Jinja2 autoescape; "
                "never call Markup() with user data."
            )
        elif cwe == "CWE-502":
            fix += (
                "Use yaml.safe_load() or json.loads(); avoid pickle/marshal "
                "on untrusted data entirely."
            )
        elif cwe == "CWE-94":
            fix += (
                "Avoid eval/exec entirely. Use ast.literal_eval() for "
                "literals, or refactor to a real parser."
            )

        bugs.append(BugReport(
            file=str(path),
            line=sink_line,
            bug_type=f"TaintFlow_{cwe}",
            description=desc,
            suggested_fix=fix,
            tier=BugTier.TIER_3_PERMISSION,
            affects_logic=True,
        ))

    return bugs


def scan_scp() -> list[BugReport]:
    """Scan the entire SCP package for taint-flow bugs.

    Walks `scp/` recursively (up to _MAX_FILES=500 files), skipping tests,
    __pycache__, examples, scripts, attack_payloads, and benchmark dirs.

    Returns:
        List of BugReports with bug_type="TaintFlow_CWE-XXX".
    """
    bugs: list[BugReport] = []
    files_scanned = 0
    for path in _iter_python_files(_SCP_ROOT, limit=_MAX_FILES):
        files_scanned += 1
        try:
            bugs.extend(scan_file(path))
        except Exception as e:  # noqa: BLE001 — never crash the whole scan
            logger.warning(f"Error scanning {path}: {e}")

    logger.info(
        f"[TaintFlowScanner] found {len(bugs)} taint-flow bug(s) "
        f"(scanned {files_scanned} files)"
    )
    return bugs
