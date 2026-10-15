"""[EE-G1] Static AST scan for HTTP client method calls on tracked variables.

Closes the blind spot of the raw call-site gate (M13 G1 latch in
``tests/T03_capability/test_egress_enforcement.py``): that gate only matches
direct spellings (``requests.get``, ``urllib.request.urlopen``), so
``s = requests.Session(); s.get(url)`` — a method call on a client VARIABLE —
was invisible. V-EE found 2 real bypasses of exactly that shape by hand
(V-EE-1/2); this module makes the whole class machine-detectable.

Shared by:
  - the static regression gate in ``tests/T03_capability/test_egress_enforcement.py``
  - the census runner ``tools/ee_g1_census.py``

What is tracked (AST-based, no source regex):
  - variables assigned from HTTP client constructors:
    ``requests.Session()``/``requests.session()``, ``httpx.Client()``/
    ``httpx.AsyncClient()``, ``urllib.request.build_opener()``/
    ``OpenerDirector()``, ``aiohttp.ClientSession()``
  - ``with httpx.Client() as c:`` bindings (and async-with, and walrus)
  - attribute chains: ``self._session = requests.Session()`` (any method, not
    only ``__init__``), ``DirectAPIVerifier._session = ...``
  - aliases: ``s = session``, ``s = self._session``
  - inline constructor calls: ``requests.Session().get(url)``
  - interprocedural one-hop: passing a tracked client as an argument marks the
    corresponding parameter of a same-file callee as tracked
    (``self._call_llm(client, ...)`` → ``client.post`` inside is flagged)

What is NOT flagged (false-positive guards):
  - method calls on attributes OF a client (``session.cookies.get('k')``,
    ``session.headers.update(...)``) — only direct method calls on the client
    itself are HTTP I/O
  - ``dict.get``/``list.append``/``Path`` ops — receivers are never tracked
    clients, so they can never match

Gating exemption (fail-closed): a call-site is considered GATED only when its
enclosing function scope contains a call to ``enforce_egress_policy`` (the
PEP that reads SCP_EGRESS_MODE) at a line <= the call line. SSRF-only checks
(``validate_url``) deliberately do NOT exempt — V-EE-1 proved "SSRF check +
raw Session.get" is exactly a bypass. Anything else must be fixed or pinned
with a justification in the gate.

Known limits (named, not hidden): per-file analysis (a client constructed in
module A and imported into module B is not tracked across the import),
constructor SUBCLASSes (``class S(requests.Session)``) are not tracked, and
the exemption is function-scope + line-order, not full URL dataflow. The
census/gate output carries ``function`` + ``receiver`` so every flagged site
can be reviewed by a human.
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Constructors that yield an HTTP client/session/opener object.
CLIENT_CTORS: frozenset[str] = frozenset(
    {
        "requests.Session",
        "requests.session",
        "httpx.Client",
        "httpx.AsyncClient",
        "urllib.request.build_opener",
        "urllib.request.OpenerDirector",
        "aiohttp.ClientSession",
    }
)

# Methods that, when called directly on a tracked client, perform network I/O.
CLIENT_HTTP_METHODS: frozenset[str] = frozenset(
    {
        "get", "post", "put", "delete", "patch", "head", "options",
        "request", "stream", "send", "open", "urlopen",
    }
)

# Modules excluded from BOTH gates (raw + client): the choke point itself and
# the canonical fetchers that call it.
GATE_EXCLUDED_MODULES: frozenset[str] = frozenset(
    {
        "scp/security/url_safety.py",
        "scp/core/url_fetcher.py",
        "scp/core/api_utils.py",
    }
)

EGRESS_GATE_NAME = "enforce_egress_policy"

_RAW_URLLIB_KIND = "urllib.request.urlopen"

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass
class ClientCallSite:
    """One method call on a tracked HTTP client (gated or not)."""

    file: str
    line: int
    col: int
    method: str
    receiver: str
    function: str
    gated: bool

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "col": self.col,
            "method": self.method,
            "receiver": self.receiver,
            "function": self.function,
            "gated": self.gated,
        }


class _FileAnalyzer:
    """Single-traversal per-file analysis: scopes, tracked clients, edges."""

    def __init__(self, tree: ast.AST, rel_path: str):
        self.tree = tree
        self.rel_path = rel_path
        self.aliases: dict[str, str] = {}
        self.module_vars: set[str] = set()          # module-level tracked names
        self.client_attrs: set[str] = set()         # dotted attr chains, file-wide
        self.factories: set[str] = set()            # func names returning clients
        self.scope_vars: dict[int, set[str]] = {}
        self.scope_qualname: dict[int, str] = {}
        self.scope_params: dict[int, list[str]] = {}
        self.scope_first_is_self: dict[int, bool] = {}
        self.scope_gate_lines: dict[int, set[int]] = {}
        self.funcs_by_name: dict[str, list[int]] = {}
        self.sites: list[ClientCallSite] = []
        self._candidate_sites: list[tuple[int | None, ast.Call]] = []
        self._pending_alias: list[tuple[int | None, ast.expr, str]] = []
        self._pending_return: list[tuple[int | None, ast.expr]] = []
        self._pending_calls: list[tuple[int | None, ast.Call]] = []

    # ------------------------------------------------------------ helpers
    def _resolve_dotted(self, parts: tuple[str, ...]) -> str | None:
        """Resolve a dotted path through the file's import aliases."""
        if not parts:
            return None
        if parts[0] in self.aliases:
            root = self.aliases[parts[0]]
        else:
            root = parts[0]
        if len(parts) == 1:
            return root
        return root + "." + ".".join(parts[1:])

    def _is_ctor_call(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
            and self._resolve_dotted(_dotted_parts(node.func)) in CLIENT_CTORS
        )

    def _is_gate_call(self, node: ast.Call) -> bool:
        if not isinstance(node.func, (ast.Name, ast.Attribute)):
            return False
        parts = _dotted_parts(node.func)
        if not parts or parts[-1] != EGRESS_GATE_NAME:
            return False
        return self._resolve_dotted(parts) is not None and self._resolve_dotted(parts).endswith(EGRESS_GATE_NAME)

    def _effective_vars(self, sid: int | None) -> set[str]:
        eff = set(self.module_vars)
        if sid is not None:
            eff |= self.scope_vars.get(sid, set())
        return eff

    def _is_client_expr(self, sid: int | None, node: ast.AST) -> bool:
        if isinstance(node, ast.Await):
            return self._is_client_expr(sid, node.value)
        if self._is_ctor_call(node):
            return True
        if isinstance(node, ast.Name):
            return node.id in self._effective_vars(sid)
        if isinstance(node, ast.Attribute):
            parts = _dotted_parts(node)
            return parts is not None and ".".join(parts) in self.client_attrs
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            parts = _dotted_parts(node.func)
            return bool(parts) and parts[-1] in self.factories
        return False

    def _track(self, sid: int | None, name: str) -> bool:
        """Track a name; returns True if this is a NEW tracking."""
        if sid is None:
            if name in self.module_vars:
                return False
            self.module_vars.add(name)
            return True
        bucket = self.scope_vars.setdefault(sid, set())
        if name in bucket:
            return False
        bucket.add(name)
        return True

    # ------------------------------------------------------------- pass 1
    def collect_imports(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    self.aliases[local] = alias.name if alias.asname else local
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name != "*":
                        local = alias.asname or alias.name
                        self.aliases[local] = f"{node.module}.{alias.name}"

    # ------------------------------------------------------------- pass 2
    def analyze(self) -> list[ClientCallSite]:
        self._scan_body(self.tree, None)
        self._resolve_to_fixpoint()
        self._verdict_candidates()
        return self.sites

    def _receiver_tracked(self, sid: int | None, receiver: ast.AST) -> bool:
        if isinstance(receiver, ast.Name):
            return receiver.id in self._effective_vars(sid)
        if isinstance(receiver, ast.Attribute):
            parts = _dotted_parts(receiver)
            return parts is not None and ".".join(parts) in self.client_attrs
        if isinstance(receiver, ast.Call):
            return self._is_ctor_call(receiver)
        return False

    def _verdict_candidates(self) -> None:
        for sid, call in self._candidate_sites:
            receiver = call.func.value
            if not self._receiver_tracked(sid, receiver):
                continue
            try:
                receiver_src = ast.unparse(receiver)
            except Exception as _unparse_err:  # pragma: no cover — unparse is best-effort
                logger.debug("ast.unparse failed for receiver at %s:%s", getattr(call, "lineno", "?"), getattr(call, "col_offset", "?"), exc_info=True)
                receiver_src = "<unparseable>"
            gated = any(
                line <= call.lineno
                for line in self.scope_gate_lines.get(sid, set())
            )
            self.sites.append(
                ClientCallSite(
                    file=self.rel_path,
                    line=call.lineno,
                    col=call.col_offset,
                    method=call.func.attr,
                    receiver=receiver_src,
                    function=self.scope_qualname.get(sid, "<module>"),
                    gated=gated,
                )
            )

    def _scan_body(self, node: ast.AST, sid: int | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPE_NODES):
                child_sid = self._register_scope(child, sid)
                self._scan_body(child, child_sid)
            elif isinstance(child, ast.ClassDef):
                # class body: treated as the enclosing scope (over-approx)
                self._scan_body(child, sid)
            else:
                self._handle(child, sid)
                self._scan_body(child, sid)

    def _register_scope(self, fn: ast.AST, parent: int | None) -> int:
        sid = len(self.scope_qualname) + 1
        parent_name = self.scope_qualname.get(parent, "<module>") if parent is not None else "<module>"
        qualname = fn.name if parent_name == "<module>" else f"{parent_name}.{fn.name}"
        self.scope_qualname[sid] = qualname
        args = fn.args
        params = [a.arg for a in (*args.posonlyargs, *args.args)]
        self.scope_params[sid] = params
        self.scope_first_is_self[sid] = bool(params) and params[0] in ("self", "cls")
        self.scope_vars[sid] = set()
        self.funcs_by_name.setdefault(fn.name, []).append(sid)
        return sid

    def _handle(self, node: ast.AST, sid: int | None) -> None:
        if isinstance(node, ast.Call):
            self._handle_call(node, sid)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None:
                return
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    if self._is_ctor_call(value):
                        self._track(sid, target.id)
                    else:
                        self._pending_alias.append((sid, value, target.id))
                elif isinstance(target, ast.Attribute):
                    parts = _dotted_parts(target)
                    if parts and self._is_ctor_call(value):
                        self.client_attrs.add(".".join(parts))
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            if self._is_ctor_call(node.value):
                self._track(sid, node.target.id)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if (
                    item.optional_vars is not None
                    and isinstance(item.optional_vars, ast.Name)
                    and self._is_ctor_call(item.context_expr)
                ):
                    self._track(sid, item.optional_vars.id)
        elif isinstance(node, ast.Return) and node.value is not None:
            self._pending_return.append((sid, node.value))

    def _handle_call(self, call: ast.Call, sid: int | None) -> None:
        if self._is_gate_call(call):
            self.scope_gate_lines.setdefault(sid, set()).add(call.lineno)
            return
        if not isinstance(call.func, ast.Attribute) or call.func.attr not in CLIENT_HTTP_METHODS:
            # maybe an interprocedural edge (client passed to a callee)
            self._pending_calls.append((sid, call))
            return
        # Verdict is deferred to after the fixpoint: the receiver may only
        # become a tracked client via an interprocedural edge resolved later
        # (e.g. a client parameter of this same function).
        self._candidate_sites.append((sid, call))

    # ------------------------------------------------------------- pass 3
    def _resolve_to_fixpoint(self) -> None:
        for _ in range(12):
            changed = False

            still_alias = []
            for sid, value, name in self._pending_alias:
                if self._is_client_expr(sid, value):
                    changed |= self._track(sid, name)
                else:
                    still_alias.append((sid, value, name))
            self._pending_alias = still_alias

            still_return = []
            for sid, value in self._pending_return:
                if self._is_client_expr(sid, value):
                    fname = self.scope_qualname.get(sid, "<module>").split(".")[-1]
                    if fname and fname != "<module>" and fname not in self.factories:
                        self.factories.add(fname)
                        changed = True
                else:
                    still_return.append((sid, value))
            self._pending_return = still_return

            for sid, call in self._pending_calls:
                for callee_sid, param in self._map_call_args(sid, call):
                    changed |= self._track(callee_sid, param)
            # pending_calls are re-evaluated each round (args may become
            # tracked via aliases/factories in a later round); mapping is
            # idempotent so this terminates with the loop bound above.

            if not changed:
                break

    def _map_call_args(self, caller_sid: int | None, call: ast.Call) -> list[tuple[int, str]]:
        """Map tracked args onto parameters of same-file callees."""
        if not isinstance(call.func, (ast.Name, ast.Attribute)):
            return []
        parts = _dotted_parts(call.func)
        if not parts:
            return []
        callee_sids = self.funcs_by_name.get(parts[-1], [])
        if not callee_sids:
            return []
        mapped: list[tuple[int, str]] = []
        for callee_sid in callee_sids:
            params = self.scope_params.get(callee_sid, [])
            if not params:
                continue
            offset = 1 if (
                isinstance(call.func, ast.Attribute)
                and self.scope_first_is_self.get(callee_sid, False)
            ) else 0
            for idx, arg in enumerate(call.args):
                pidx = idx + offset
                if pidx >= len(params):
                    break
                if self._is_client_expr(caller_sid, arg):
                    mapped.append((callee_sid, params[pidx]))
            for kw in call.keywords:
                if kw.arg and kw.arg in params and self._is_client_expr(caller_sid, kw.value):
                    mapped.append((callee_sid, kw.arg))
        return mapped


def _dotted_parts(node: ast.AST) -> tuple[str, ...] | None:
    """Return the dotted path of a Name/Attribute chain, else None."""
    parts: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return tuple(reversed(parts))
    return None


def scan_client_method_calls(paths) -> list[dict]:
    """Scan python files/dirs for method calls on tracked HTTP clients.

    Returns a list of dicts for ALL matched call-sites (gated and ungated):
    {file, line, col, method, receiver, function, gated}. Callers decide
    policy; the static gate fails on ``gated == False`` sites not pinned.
    """
    results: list[dict] = []
    for path in paths:
        p = Path(path)
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for site in _FileAnalyzer(tree, f.as_posix()).analyze():
                results.append(site.as_dict())
    return results


def scan_raw_http_calls(paths) -> list[tuple[str, int, str]]:
    """AST scan for direct-spelling raw HTTP call-sites: urllib.request.urlopen,
    requests/httpx module-level verb calls (get/post/put/patch/delete/head/
    options). Returns (path, line, kind) tuples. Moved here from the gate test
    so the census runner and the test share one implementation (EE-G1)."""
    _verbs = {"get", "post", "put", "patch", "delete", "head", "options"}
    violations: list[tuple[str, int, str]] = []
    for path in paths:
        p = Path(path)
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                base = _dotted_parts(node.func.value)
                base_str = ".".join(base) if base else None
                attr = node.func.attr
                kind = None
                if attr == "urlopen" and base_str and base_str.startswith("urllib.request"):
                    kind = _RAW_URLLIB_KIND
                elif attr in _verbs and base_str in {"requests", "httpx"}:
                    kind = f"{base_str}.{attr}"
                elif attr in _verbs and base_str and base_str.startswith("httpx."):
                    kind = "httpx." + attr
                if kind:
                    violations.append((f.as_posix(), node.lineno, kind))
    return violations
