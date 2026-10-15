# [V8.0-SCANNER] SecurityScanner — detect CWE Top 25 patterns.
#
# TẠI SAO scanner này tồn tại?
#   OWASP/CWE Top 25 là danh sách các bug security phổ biến nhất. SCP không
#   thể tự quét tất cả, nhưng có thể detect những pattern rõ ràng nhất:
#     - CWE-79: XSS — render(user_input) không escape
#     - CWE-89: SQL injection (delegate to SQLInjectionScanner — không duplicate)
#     - CWE-22: Path traversal — open(user_path) không sanitize
#     - CWE-78: OS command injection — os.system(user_input), shell=True calls
#     - CWE-502: Deserialization — pickle.loads(user_data), yaml.load(data)
#     - CWE-798: Hardcoded credentials — password = "xxx" trong source
#     - CWE-312: Plaintext storage of sensitive info (closely related)
#     - CWE-209: Information exposure via error message — traceback to user
#
# LOGIC:
#   1. CWE-78: os.system(...), subprocess.call/run/Popen with shell=True AND
#      the command string contains f-string/string concat with non-constant
#   2. CWE-502: pickle.loads(...), pickle.load(...), yaml.load(data) without
#      Loader=SafeLoader, marshal.loads(...)
#   3. CWE-798: hardcoded password/token/secret/api_key assignments to Constants
#      (heuristic: var name contains password/pwd/token/secret/api_key AND
#       value is non-empty string Constant)
#   4. CWE-22: open(<var>) where var is a function parameter (no sanitize)
#   5. CWE-79: HTMLResponse(user_input) / render(template_string=user_input) /
#      flask.Markup(user_input) — too risky to flag without framework context,
#      SKIP (too many false positives)
#   6. CWE-209: traceback.format_exc() returned to client (too contextual, SKIP)
#
# CONSERVATIVE HEURISTICS:
#   - CWE-78: only flag if shell=True AND command is non-constant
#   - CWE-502: pickle.loads always flagged (no safe use case for untrusted data)
#   - CWE-798: skip values starting with "os.environ" / "getenv" (env-var reads)
#              skip values that look like format strings ("%s")
#              skip test files
#   - CWE-22: only flag if open()'s first arg is a Name (variable), AND the
#             variable is a function parameter
#   - Skip __pycache__, tests, scripts, examples
#
# RETURNS:
#   list[BugReport] — bug_type="SecurityIssue"
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.security")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 500

# Var names suggesting credentials (CWE-798)
_CRED_VAR_PATTERN = re.compile(
    r"(password|passwd|pwd|secret|api_key|apikey|access_key|secret_key|"
    r"auth_token|auth_token|bearer_token|private_key|client_secret)",
    re.IGNORECASE,
)

# Safe value patterns — skip these (they're env-var reads or format strings)
_CRED_SAFE_VALUE_PATTERN = re.compile(
    r"^(os\.environ|os\.getenv|getenv\(|environ\.get|config\.|settings\.|"
    r"\$\{|%s|<|your_|placeholder|example|xxx|todo|change_me|tbd)",
    re.IGNORECASE,
)

# [AUTOFIX-T1] Removed dead `_UNSAFE_DESERIALIZE` set — never referenced.
# CWE-502 detection currently handles ONLY `yaml.load(...)` inline (~L150).
# pickle/marshal/shelve detection MISSING — wiring it is Tier-3 (WHAT).

def _is_string_constant(node) -> str | None:
    """Return string value if node is a Constant string, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _has_non_constant_part(node) -> bool:
    """True if a JoinedStr (f-string) contains non-constant interpolation."""
    if isinstance(node, ast.JoinedStr):
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                if not isinstance(v.value, ast.Constant):
                    return True
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _has_non_constant_part(node.left) or _has_non_constant_part(node.right)
    if isinstance(node, ast.Constant):
        return False
    return True  # any other expr is non-constant


class _SecurityFinder(ast.NodeVisitor):
    """Walk AST, detect CWE Top 25 patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: list[dict] = []
        # Track function parameters (for CWE-22 path traversal detection)
        self._func_params: set[str] = set()

    def visit_FunctionDef(self, node):
        saved = set(self._func_params)
        self._func_params = set()
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self._func_params.add(arg.arg)
        for stmt in node.body:
            self.visit(stmt)
        self._func_params = saved

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call):
        # CWE-78: os.system(...) — always flag (shell command from code is risky)
        if isinstance(node.func, ast.Attribute):
            recv = node.func.value
            attr = node.func.attr
            # os.system(...) — flag if arg is non-constant
            if attr == "system" and isinstance(recv, ast.Name) and recv.id == "os":
                if node.args and _has_non_constant_part(node.args[0]):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "cwe78_os_system",
                        "detail": "os.system() with non-constant argument",
                    })
            # subprocess.run/call/Popen with shell=True
            if (attr in ("run", "call", "Popen", "check_output", "check_call")
                    and isinstance(recv, ast.Name) and recv.id == "subprocess"):
                shell_true = False
                for kw in node.keywords:
                    if (kw.arg == "shell"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True):
                        shell_true = True
                        break
                if shell_true and node.args and _has_non_constant_part(node.args[0]):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "cwe78_subprocess_shell",
                        "detail": f"subprocess.{attr} with shell enabled and non-constant command",
                    })
            # CWE-502: yaml.load(...) without SafeLoader
            if attr == "load" and isinstance(recv, ast.Name) and recv.id == "yaml":
                # Check if Loader kwarg is SafeLoader / CSafeLoader
                has_safe_loader = False
                for kw in node.keywords:
                    if kw.arg == "Loader":
                        if isinstance(kw.value, ast.Name) and "Safe" in kw.value.id:
                            has_safe_loader = True
                        elif isinstance(kw.value, ast.Attribute) and "Safe" in kw.value.attr:
                            has_safe_loader = True
                if not has_safe_loader:
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "cwe502_yaml_load",
                        "detail": "yaml.load without SafeLoader — arbitrary object construction",
                    })
        # Direct name call: pickle.loads(...)
        if isinstance(node.func, ast.Name):
            # pickle.loads / marshal.loads — can't detect module without tracking imports.
            # Conservative: flag bare `loads(...)` if name looks like pickle/marshal
            if node.func.id in ("loads", "load"):
                # Only flag if function name suggests deserialization
                # (can't tell without import tracking — skip)
                pass
            # eval(...) and exec(...) — code injection (CWE-94)  # nosec B102 — intentional exec in security scanner
            if node.func.id in ("eval", "exec"):
                if node.args and _has_non_constant_part(node.args[0]):
                    self.findings.append({
                        "line": node.lineno,
                        "kind": "cwe94_eval_exec",
                        "detail": f"{node.func.id}() with non-constant argument — code injection",
                    })
        self.generic_visit(node)

    def visit_Assign(self, node):
        # CWE-798: hardcoded credentials
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            value = node.value.value
            # Skip safe patterns (env-var reads, placeholders)
            if _CRED_SAFE_VALUE_PATTERN.match(value):
                pass
            elif len(value) >= 6 and not value.startswith("$"):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and _CRED_VAR_PATTERN.search(tgt.id):
                        self.findings.append({
                            "line": node.lineno,
                            "kind": "cwe798_hardcoded_cred",
                            "var": tgt.id,
                            "value_preview": value[:3] + "***",
                        })
                    elif isinstance(tgt, ast.Attribute) and _CRED_VAR_PATTERN.search(tgt.attr):
                        self.findings.append({
                            "line": node.lineno,
                            "kind": "cwe798_hardcoded_cred",
                            "var": tgt.attr,
                            "value_preview": value[:3] + "***",
                        })
        # CWE-22: open(<param_name>) — path traversal
        if (isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "open"
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id in self._func_params):
            param = node.value.args[0].id
            # Conservative: skip params named "path" / "file_path" that look
            # intentional — only flag if param looks user-supplied
            # (e.g. "user_input", "query", "request_path")
            user_input_hints = ("user", "input", "query", "request", "arg",
                                "param", "raw", "unsafe", "untrusted")
            if any(h in param.lower() for h in user_input_hints):
                self.findings.append({
                    "line": node.lineno,
                    "kind": "cwe22_path_traversal",
                    "param": param,
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


class SecurityScanner:
    """Detect CWE Top 25 patterns: OS command injection, deserialization,
    hardcoded credentials, path traversal, code injection (eval/exec)."""

    name: str = "SecurityScanner"
    bug_type: str = "SecurityIssue"

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
                logger.debug("security_scanner: skipping unparseable file %s: %s", path, parse_err, exc_info=True)
                continue
            except Exception as read_err:  # noqa: S112
                logger.debug("security_scanner: skipping unreadable file %s: %s", path, read_err, exc_info=True)
                continue

            finder = _SecurityFinder(str(path))
            finder.visit(tree)

            for f in finder.findings:
                kind = f["kind"]
                if kind == "cwe78_os_system":
                    desc = (
                        f"SecurityIssue [CWE-78]: os.system() called at line {f['line']} "
                        f"with non-constant argument. If user input flows into this "
                        f"command, attackers can inject shell metacharacters (`;`, `&&`, "
                        f"`|`) to execute arbitrary commands on the host."
                    )
                    fix = (
                        "Use safe_run(['cmd', 'arg1', 'arg2']) from scp.core.safe_process "
                        "with argument list (no shell interpretation). Or use shlex.quote() "
                        "to escape user input when shell interpretation is unavoidable."
                    )
                elif kind == "cwe78_subprocess_shell":
                    desc = (
                        f"SecurityIssue [CWE-78]: {f['detail']} at line {f['line']}. "
                        f"Shell-enabled subprocess with non-constant command = command injection."
                    )
                    fix = "Pass argument list (shell interpretation disabled) OR use shlex.quote() per arg."
                elif kind == "cwe502_yaml_load":
                    desc = (
                        f"SecurityIssue [CWE-502]: yaml.load at line {f['line']} "
                        f"without Loader=yaml.SafeLoader — allows arbitrary Python "
                        f"object construction from YAML tags like `!!python/object/apply:os.system`."
                    )
                    fix = "Use yaml.safe_load(data), or pass Loader=yaml.SafeLoader."
                elif kind == "cwe798_hardcoded_cred":
                    desc = (
                        f"SecurityIssue [CWE-798]: hardcoded credential in `{f['var']}` "
                        f"at line {f['line']} (value: {f['value_preview']}). Anyone with "
                        f"source access has the credential — leaks via git, backups, logs."
                    )
                    fix = (
                        "Move credential to env var: `os.environ.get('SECRET_KEY')` "
                        "or a secrets manager (vault, AWS Secrets Manager). Add to .env "
                        "(gitignored) for local dev."
                    )
                elif kind == "cwe22_path_traversal":
                    desc = (
                        f"SecurityIssue [CWE-22]: open() called at line {f['line']} "
                        f"with function parameter `{f['param']}` that looks user-supplied. "
                        f"Attackers can pass `../../etc/passwd` to read arbitrary files."
                    )
                    fix = (
                        "Sanitize: use os.path.realpath() + check against allowed base "
                        "dir, OR use pathlib.Path.resolve() and verify .is_relative_to(base)."
                    )
                elif kind == "cwe94_eval_exec":
                    desc = (
                        f"SecurityIssue [CWE-94]: {f['detail']} at line {f['line']}. "
                        f"If user input flows in, attackers can execute arbitrary Python."
                    )
                    fix = "Avoid eval/exec entirely. Use ast.literal_eval() for literals, or refactor."
                else:
                    continue
                bugs.append(BugReport(
                    file=str(path),
                    line=f["line"],
                    bug_type=self.bug_type,
                    description=desc,
                    suggested_fix=fix,
                    tier=BugTier.TIER_3_PERMISSION,  # security → always human review
                    affects_logic=True,
                ))

        logger.info(
            f"[SecurityScanner] found {len(bugs)} security issue(s) "
            f"(scanned {files_scanned} files)"
        )
        return bugs
