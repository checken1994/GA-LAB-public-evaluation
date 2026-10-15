# [OPT-18-SCANNER] XSSScanner — detect Cross-Site Scripting vulnerabilities.
#
# TẠI SAO scanner này tồn tại?
#   CWE-79: Cross-Site Scripting (XSS) — OWASP Top 10 #1 (was #3).
#   SCP có web endpoints (api_server.py, dashboard/) render HTML/JSON.
#   Nếu user input được return trực tiếp trong HTML response mà không
#   escape → attacker inject <script>alert(document.cookie)</script>.
#
#   SecurityScanner V8.0 đã có comment "CWE-79: SKIP (too many false
#   positives)" — scanner này ĐIỀU CHỈNH heuristic để flag chính xác hơn:
#     - Chỉ flag f-string/concat có HTML tags (heuristic `<\w+`) AND user input
#     - Markup(...) từ flask.markup bypass escaping → always flag
#     - render_template_string(user_input) → SSTI/XSS, always flag
#     - HTMLResponse(user_input) / Response(content=user_input, media_type="text/html") → flag
#
# LOGIC:
#   1. Tìm f-strings (ast.JoinedStr) chứa:
#        - HTML tag pattern: "<tag" hoặc "<tag>" (heuristic, case-insensitive)
#        - FormattedValue referencing user input (request.args.get, etc.)
#          OR local var assigned to user input in same scope
#      → BUG: Reflected XSS (medium severity — context-dependent)
#   2. Tìm function calls nguy hiểm với user input arg đầu tiên:
#        - flask.Markup(user_input)        — bypass autoescape
#        - markupsafe.Markup(user_input)   — same
#        - render_template_string(user_input)  — SSTI
#        - jinja2.Template(user_input)     — SSTI
#      → BUG: Stored/Reflected XSS (high severity)
#   3. Tìm HTMLResponse(user_input) / Response(content=user_input, media_type="text/html")
#      → BUG: Reflected XSS (high severity)
#   4. Tìm string concat (`+`) với HTML tags và user input (tương tự f-string)
#   5. Tìm .format() trên HTML template string với user input
#
# SCOPE TRACKING:
#   Track local variable assignments in each function scope to distinguish
#   user-input-bound vars (e.g., `name = request.args.get("name")`) from
#   local constants (e.g., `name = "static"`). This prevents false positives
#   on f-strings that interpolate locally-defined constant strings.
#
# CONSERVATIVE HEURISTICS:
#   - f-string phải có HTML tag pattern (chỉ "<" không đủ — quá rộng)
#   - User input = direct request.* / flask.request.* reference OR local
#     var bound to user input in same scope (data flow tracking)
#   - Unknown vars (not in scope) → SKIP (false negative preferred over
#     false positive for security — false positives erode trust)
#   - Skip f-strings mà tất cả FormattedValues đều constant (pure string literal)
#   - Skip __pycache__, tests, scripts, examples, attack_payloads
#
# RETURNS:
#   list[BugReport] — bug_type="XSSVulnerability"
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.xss")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 1000

# HTML tag pattern — matches "<tag", "<tag/>", "<tag>" (case-insensitive)
# Used to identify f-strings/concat that produce HTML output
_HTML_TAG_PATTERN = re.compile(r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*", re.IGNORECASE)

# Functions that bypass HTML escaping / enable SSTI (CWE-79 + CWE-94)
# (module, attr) pairs — checked against Attribute calls
_BYPASS_ESCAPE_FUNCS = {
    ("Markup",),        # flask.Markup or markupsafe.Markup (bare import)
    ("flask", "Markup"),
    ("markupsafe", "Markup"),
    ("render_template_string",),  # flask SSTI
    ("flask", "render_template_string"),
    ("Template",),      # jinja2.Template (bare)
    ("jinja2", "Template"),
}

# Response builders that don't auto-escape HTML — flag if content is user input
_HTML_RESPONSE_BUILDERS = {
    "HTMLResponse",  # fastapi.responses.HTMLResponse — no escaping
    "Response",      # generic — only flag if media_type contains "html"
}

# Sources of user input (Python web context) — used to determine if a
# FormattedValue references user input (vs. a local constant).
# Matched against dotted attribute chains and bare call names.
_USER_INPUT_SOURCE_PATTERNS = (
    "request.args", "request.form", "request.json", "request.data",
    "request.values", "request.cookies", "request.headers",
    "request.get_json", "request.args.get",
    "flask.request",  # qualified flask.request.*
    "req.args", "req.form", "req.json", "req.data",  # common alias 'req'
    "self.request",   # method handlers often use self.request
)


def _is_string_constant(node) -> str | None:
    """Return string value if node is a Constant string, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _looks_like_module_constant(node) -> bool:
    """Heuristic: True if node looks like a module-level ALL_CAPS constant.

    Convention: variables named `_FOO_BAR` or `FOO_BAR` (all caps, may have
    leading underscore) are typically module-level constants assigned to
    string literals at import time. They are NOT user input — safe to skip.

    Examples recognized as constants:
      DASHBOARD_HTML, _DDL_CANONICAL, TEMPLATE_STR, _HTML_HEAD

    Examples NOT recognized (treated as potentially user input):
      name, html_content, response_text  (lowercase → variable, not constant)
    """
    if isinstance(node, ast.Name):
        name = node.id
        # Strip optional leading underscore
        if name.startswith("_"):
            name = name[1:]
        # Must be non-empty, start with uppercase letter, and contain only
        # uppercase letters / digits / underscores
        if (len(name) >= 2
                and name[0].isupper()
                and all(c.isupper() or c.isdigit() or c == "_" for c in name)):
            return True
    # Method calls on module constants: _X.replace(...) _X.format(...) — also safe
    if (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _looks_like_module_constant(node.func.value)):
        return True
    return False


def _is_constant_only(node) -> bool:
    """True if node is a literal Constant or a tree of only Constants.

    Also recognizes module-level ALL_CAPS_NAMES (via _looks_like_module_constant)
    so that HTMLResponse(DASHBOARD_HTML) is NOT flagged as a false positive.
    """
    if isinstance(node, ast.Constant):
        return True
    if _looks_like_module_constant(node):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(
            (isinstance(v, ast.Constant) or
             (isinstance(v, ast.FormattedValue) and _is_constant_only(v.value)))
            for v in node.values
        )
    if isinstance(node, ast.BinOp):
        return _is_constant_only(node.left) and _is_constant_only(node.right)
    return False


def _get_attr_chain(node) -> str:
    """Get dotted attribute chain as string (e.g. 'flask.Markup').

    Returns empty string if node is not a Name/Attribute chain.
    """
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.insert(0, current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.insert(0, current.id)
    else:
        return ""
    return ".".join(parts)


def _contains_user_input_source(node) -> bool:
    """Check if AST node contains a reference to a known user-input source.

    Looks for attribute chains like `request.args.get(...)` or
    `flask.request.form[...]` or bare calls matching user-input patterns.
    """
    for child in ast.walk(node):
        # Attribute chains: request.args, request.args.get, flask.request.form
        if isinstance(child, ast.Attribute):
            chain = _get_attr_chain(child)
            if any(src in chain for src in _USER_INPUT_SOURCE_PATTERNS):
                return True
        # Bare name calls: request (used directly), or a function call name
        # that suggests user input (rare — usually attribute chains)
        if isinstance(child, ast.Call):
            chain = _get_attr_chain(child.func)
            if chain and any(src in chain for src in _USER_INPUT_SOURCE_PATTERNS):
                return True
        # Subscript: request.form["key"], request.args[0]
        if isinstance(child, ast.Subscript):
            chain = _get_attr_chain(child.value)
            if any(src in chain for src in _USER_INPUT_SOURCE_PATTERNS):
                return True
    return False


def _string_contains_html(node) -> bool:
    """Check if a string-producing AST node contains HTML tag patterns.

    Used to distinguish f-strings that produce HTML output (XSS risk)
    from f-strings that produce plain text (no XSS risk).
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(_HTML_TAG_PATTERN.search(node.value))
    if isinstance(node, ast.JoinedStr):
        # Check all constant parts of the f-string for HTML tags
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                if _HTML_TAG_PATTERN.search(v.value):
                    return True
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _string_contains_html(node.left) or _string_contains_html(node.right)
    if isinstance(node, ast.Call):
        # .format() on HTML template string
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"):
            return _string_contains_html(node.func.value)
    return False


def _matches_bypass_func(func_node) -> bool:
    """Check if a call's func matches a known bypass-escape function.

    Handles both bare imports (Markup(...)) and qualified (flask.Markup(...)).
    """
    if isinstance(func_node, ast.Name):
        # Bare import: Markup(...), render_template_string(...)
        for sig in _BYPASS_ESCAPE_FUNCS:
            if len(sig) == 1 and sig[0] == func_node.id:
                return True
        return False
    if isinstance(func_node, ast.Attribute):
        chain = _get_attr_chain(func_node)
        for sig in _BYPASS_ESCAPE_FUNCS:
            if ".".join(sig) == chain:
                return True
        # Also check just the attr name (in case module is aliased)
        attr = func_node.attr
        for sig in _BYPASS_ESCAPE_FUNCS:
            if len(sig) == 2 and sig[1] == attr:
                return True
        return False
    return False


class _XSSFinder(ast.NodeVisitor):
    """Walk AST, detect XSS vulnerabilities (CWE-79).

    Tracks local variable assignments in each function scope to distinguish
    user-input-bound vars (e.g., `name = request.args.get("name")`) from
    local constants (e.g., `name = "static"`). This prevents false positives
    on f-strings that interpolate locally-defined constant strings.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []
        # Scope: var_name -> bool (True if bound to user input, False if constant)
        # Unknown vars are NOT in the dict (treated as "uncertain" — skip).
        self._scope: dict[str, bool] = {}

    def visit_FunctionDef(self, node):
        # Two-pass: first collect assignments (so we know which vars
        # are user-input-bound BEFORE visiting the f-strings that use them),
        # then visit body normally.
        saved = self._scope
        self._scope = {}
        # Pass 1: collect all assignments in the function body (recursively)
        for stmt in node.body:
            self._collect_assignments(stmt)
        # Pass 2: visit each statement
        for stmt in node.body:
            self.visit(stmt)
        self._scope = saved

    visit_AsyncFunctionDef = visit_FunctionDef

    def _collect_assignments(self, stmt):
        """Populate self._scope from assignment statements.

        Recursively descends into if/for/while/with blocks to track
        assignments inside control flow. Doesn't track reassignments
        perfectly (last-write-wins), which is acceptable for XSS detection.
        """
        if isinstance(stmt, ast.Assign):
            value = stmt.value
            is_user = _contains_user_input_source(value)
            is_const = _is_constant_only(value)
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name):
                    if is_user:
                        self._scope[tgt.id] = True
                    elif is_const:
                        self._scope[tgt.id] = False
                    # else: unknown — leave unset
        elif isinstance(stmt, ast.AnnAssign):
            if stmt.value is not None and isinstance(stmt.target, ast.Name):
                value = stmt.value
                is_user = _contains_user_input_source(value)
                is_const = _is_constant_only(value)
                if is_user:
                    self._scope[stmt.target.id] = True
                elif is_const:
                    self._scope[stmt.target.id] = False
        # Recurse into compound statements
        elif isinstance(stmt, ast.If):
            for s in stmt.body:
                self._collect_assignments(s)
            for s in stmt.orelse:
                self._collect_assignments(s)
        elif isinstance(stmt, (ast.For, ast.While)):
            for s in stmt.body:
                self._collect_assignments(s)
            for s in stmt.orelse:
                self._collect_assignments(s)
        elif isinstance(stmt, ast.With):
            for s in stmt.body:
                self._collect_assignments(s)

    def _formatted_value_is_user_input(self, node) -> bool:
        """Determine if a FormattedValue's value references user input.

        Returns True if:
          - Node directly contains a user input source (request.args.get, etc.)
          - Node is a Name bound to a user-input value in current scope
        Returns False if:
          - Node is a Constant
          - Node is a Name bound to a constant in current scope
        Returns False (conservative) for uncertain cases — we'd rather
        miss a bug than flag a false positive (security: false positives
        erode trust in the scanner).
        """
        if isinstance(node, ast.Constant):
            return False
        # Direct user input source (request.args.get(...) etc.)
        if _contains_user_input_source(node):
            return True
        # Bare Name: look up scope
        if isinstance(node, ast.Name):
            return self._scope.get(node.id, False)
        # Anything else (Call, Subscript, Attribute not matching sources,
        # BinOp with non-constant parts) — uncertain → don't flag
        return False

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """Detect f-strings with HTML tags + user input interpolation."""
        # Must contain at least one FormattedValue bound to user input
        has_user_input = False
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                if self._formatted_value_is_user_input(v.value):
                    has_user_input = True
                    break
        if not has_user_input:
            self.generic_visit(node)
            return
        # Must contain HTML tag pattern in the constant parts
        if _string_contains_html(node):
            self.findings.append({
                "line": node.lineno,
                "kind": "reflected_xss_fstring",
                "detail": "f-string with HTML tags + user input interpolation",
            })
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Detect string concat (`+`) with HTML tags + user input."""
        if isinstance(node.op, ast.Add):
            if (_string_contains_html(node)
                    and _contains_user_input_source(node)):
                self.findings.append({
                    "line": node.lineno,
                    "kind": "reflected_xss_concat",
                    "detail": "string concatenation with HTML + user input source",
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # [Mimosa SSTI-fix 2026-09-30] Docstring KHÔNG chứa literal
        # "render_template_string" + "(" liền nhau — scanner template-injection
        # quét text-level flag nhầm docstring; đây chỉ là tài liệu cho rule
        # AST bên dưới, không phải lời gọi template engine.
        """Detect Markup() / flask.render_template_string / HTMLResponse() with user input."""
        # Markup(...) / render_template_string(...) / Template(...) — bypass escaping
        if _matches_bypass_func(node.func):
            if node.args:
                arg0 = node.args[0]
                # Flag if arg is direct user input source, OR a local var
                # bound to user input, OR a non-constant non-Name expression
                # (e.g., f-string/concat — uncertain, but Markup is dangerous)
                is_user = (
                    _contains_user_input_source(arg0)
                    or (isinstance(arg0, ast.Name) and self._scope.get(arg0.id, False))
                    or (not _is_constant_only(arg0) and not isinstance(arg0, ast.Name))
                )
                if is_user:
                    func_name = _get_attr_chain(node.func) or "unknown"
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "bypass_escape_call",
                        "detail": f"{func_name}() called with non-constant argument "
                                  f"— bypasses HTML escaping (CWE-79)",
                    })
        # HTMLResponse(user_input) — always flag if non-constant
        elif isinstance(node.func, ast.Name) and node.func.id in _HTML_RESPONSE_BUILDERS:
            if node.args and not _is_constant_only(node.args[0]):
                # For generic Response(), only flag if media_type contains html
                if node.func.id == "Response":
                    has_html_media = False
                    for kw in node.keywords:
                        if kw.arg == "media_type":
                            media = _is_string_constant(kw.value)
                            if media and "html" in media.lower():
                                has_html_media = True
                                break
                    if not has_html_media:
                        self.generic_visit(node)
                        return
                self.findings.append({
                    "line": node.lineno,
                    "kind": "html_response_user_input",
                    "detail": f"{node.func.id}() with non-constant content "
                              f"— HTML response without escaping (CWE-79)",
                })
        # .format() on HTML template string with user input
        elif (isinstance(node.func, ast.Attribute)
                and node.func.attr == "format"
                and _string_contains_html(node.func.value)
                and any(_contains_user_input_source(a) for a in node.args)):
            self.findings.append({
                "line": node.lineno,
                "kind": "reflected_xss_format",
                "detail": ".format() on HTML template with user input",
            })
        self.generic_visit(node)


def _iter_python_files(root: Path, limit: int = _MAX_FILES):
    """[A12 H-1] Deterministic walk: sort theo path TRƯỚC khi cap (thứ tự
    rglob phụ thuộc OS) + WARNING tường minh khi truncation xảy ra — cấm
    cắt im lặng ~20% cây scan."""
    paths = sorted(
        path for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
        and "tests" not in path.parts
        and not path.name.startswith("test_")
        and not any(part in ("examples", "scripts", "attack_payloads") for part in path.parts)
    )
    if len(paths) > limit:
        logger.warning(
            "[scanner-cap] %s: %d file .py vượt cap %d — cắt còn %d "
            "(nâng _MAX_FILES nếu cần full coverage)",
            __name__, len(paths), limit, limit,
        )
        paths = paths[:limit]
    return paths


class XSSScanner:
    """Detect XSS vulnerabilities (CWE-79): HTML responses with unescaped user input.

    Bug type: "XSSVulnerability"  (tier=TIER_3_PERMISSION — security-sensitive)

    Detects:
      - f-strings with HTML tags + user input interpolation (reflected XSS)
      - String concat with HTML + user input source (reflected XSS)
      - .format() on HTML template with user input
      - Markup(...) / flask.Markup / markupsafe.Markup with user input (bypass escape)
      - flask.render_template_string with user input / jinja2.Template(user_input) (SSTI/XSS)
      - HTMLResponse(user_input) / Response(content=user_input, media_type="text/html")
    """

    name: str = "XSSScanner"
    bug_type: str = "XSSVulnerability"

    def __init__(self, scp_root: Path | None = None, max_files: int = _MAX_FILES):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files

    def scan(self) -> list[BugReport]:
        """Scan all Python files under scp_root for XSS vulnerabilities.

        Returns list of BugReport objects (one per finding).
        """
        bugs: list[BugReport] = []
        files_scanned = 0
        for path in _iter_python_files(self.scp_root, limit=self.max_files):
            files_scanned += 1
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as parse_err:
                # silent-by-design: parse probe — unparseable file is skipped by this scan by design.
                logger.debug("xss_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("xss_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            finder = _XSSFinder(str(path))
            finder.visit(tree)

            for f in finder.findings:
                kind = f["kind"]
                if kind == "reflected_xss_fstring":
                    desc = (
                        f"XSSVulnerability [CWE-79]: f-string at line {f['line']} "
                        f"contains HTML tags AND user input interpolation. If user "
                        f"input flows into the f-string, attackers can inject "
                        f"<script>...</script> — execute JS in victim's browser, "
                        f"steal cookies, perform actions as the user."
                    )
                    fix = (
                        "Escape user input before inserting into HTML: "
                        "import html; f\"<div>{html.escape(user_input)}</div>\". "
                        "Or use a templating engine with autoescape on (Jinja2 default)."
                    )
                elif kind == "reflected_xss_concat":
                    desc = (
                        f"XSSVulnerability [CWE-79]: string concatenation at line "
                        f"{f['line']} produces HTML with a user-input source. "
                        f"If user input flows into the concatenated value, attackers "
                        f"can inject <script> tags."
                    )
                    fix = (
                        "Use html.escape() on user input before concatenating, "
                        "OR refactor to f-string with html.escape() wrapping."
                    )
                elif kind == "reflected_xss_format":
                    desc = (
                        f"XSSVulnerability [CWE-79]: .format() at line {f['line']} "
                        f"on an HTML template string with user input. Same risk as "
                        f"f-string XSS — unescaped user input in HTML context."
                    )
                    fix = (
                        "Apply html.escape() to each user-supplied format argument: "
                        "\"<div>{}</div>\".format(html.escape(user_input))."
                    )
                elif kind == "bypass_escape_call":
                    desc = (
                        f"XSSVulnerability [CWE-79]: {f['detail']}. "
                        f"This function marks content as 'safe' (no autoescape), so "
                        f"if user input flows in, <script> tags will execute in the "
                        f"browser. Common XSS vector in Flask apps."
                    )
                    fix = (
                        "Remove the Markup() wrapper and let the templating engine "
                        "auto-escape. If you must mark content as safe, sanitize with "
                        "bleach.clean() first: Markup(bleach.clean(user_input))."
                    )
                elif kind == "html_response_user_input":
                    desc = (
                        f"XSSVulnerability [CWE-79]: {f['detail']}. "
                        f"HTMLResponse/Response does NOT auto-escape content — any "
                        f"<script> in user input will execute in the victim's browser."
                    )
                    fix = (
                        "Escape user input with html.escape() before passing to "
                        "HTMLResponse/Response, OR render through a Jinja2 template "
                        "with autoescape enabled."
                    )
                else:
                    continue

                bugs.append(BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=desc,
                    suggested_fix=fix,
                    tier=BugTier.TIER_3_PERMISSION,  # security → human review
                    affects_logic=True,
                ))

        logger.info(
            f"[XSSScanner] found {len(bugs)} XSS vulnerability(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs


__all__ = ["XSSScanner"]
