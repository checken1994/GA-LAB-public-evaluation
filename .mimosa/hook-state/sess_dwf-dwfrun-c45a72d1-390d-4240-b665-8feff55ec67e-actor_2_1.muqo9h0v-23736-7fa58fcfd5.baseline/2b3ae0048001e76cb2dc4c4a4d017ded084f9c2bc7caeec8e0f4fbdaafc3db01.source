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
  - import aliases: ``from requests import Session; s = Session()`` (the
    import-alias map is populated before analysis — [AUDIT-R2 M-01] it was
    dead code before and never ran)
  - inline constructor calls: ``requests.Session().get(url)``
  - interprocedural one-hop: passing a tracked client as an argument marks the
    corresponding parameter of a same-file callee as tracked
    (``self._call_llm(client, ...)`` → ``client.post`` inside is flagged)
  - [AUDIT-R2 M-01b] CROSS-MODULE imports: a module-level client variable
    exported by module A (e.g. ``_common._SESSION = requests.Session()``) and
    imported into module B (``from ._common import _SESSION``) is tracked in
    B — the exact blind spot that hid the F-03 arxiv fetch. Both
    ``from module import client_var`` bindings and ``import module as m`` →
    ``m.client_var`` dotted attribute access are tracked, including relative
    imports, with a bounded fixpoint for re-export chains.

What is NOT flagged (false-positive guards):
  - method calls on attributes OF a client (``session.cookies.get('k')``,
    ``session.headers.update(...)``) — only direct method calls on the client
    itself are HTTP I/O
  - ``dict.get``/``list.append``/``Path`` ops — receivers are never tracked
    clients, so they can never match

Gating exemption (fail-closed, [AUDIT-R2 M-01c]): a call-site is considered
GATED only when its enclosing function scope contains a call to
``enforce_egress_policy`` (the PEP that reads SCP_EGRESS_MODE) that DOMINATES
the call — the gate is guaranteed to execute before the fetch on every path
to it AND a gate denial cannot fall through to the fetch. Dominance is
approximated over statement-list nesting (see ``_gate_dominates``):
  - a gate inside an ``if``/``for``/``with`` body does NOT exempt a call
    outside that block (conditional gating = fail-open potential)
  - a gate in a ``try`` body exempts what follows ONLY when every except
    handler exits (return/raise) — ``try: gate() except: <return>`` is the
    canonical fail-closed shape; ``except: pass`` followed by the fetch
    stays flagged
  - a call in the ``finally`` of the same enclosing try is never exempt
  - a gate AFTER the call in the same block does not exempt (unchanged)
  - same-statement positions (if-test / call-argument order) still count as
    dominating — the gate provably runs before the fetch there
SSRF-only checks (``validate_url``) deliberately do NOT exempt — V-EE-1
proved "SSRF check + raw Session.get" is exactly a bypass. Anything else must
be fixed or pinned with a justification in the gate.

Fail-loud parsing ([AUDIT-R2 M-01a]): a file that fails to parse is a hole
in egress visibility — the scanners RAISE ``SyntaxError`` naming the file by
default, or collect the file paths into the caller-supplied ``unparsable``
list (callers must fail on it; the census reports it and exits non-zero).
The old ``except SyntaxError: continue`` silently shrunk the scan surface
and is gone.

Known limits (named, not hidden): cross-module tracking is export-map based
(module-level client variables + one bounded fixpoint over re-exports; a
client built inside a function and returned through non-obvious dataflow is
only caught by the same-file factory/one-hop rules), constructor SUBCLASSes
(``class S(requests.Session)``) are not tracked, and the dominance rule is
an AST approximation of CFG dominance, not full dataflow. The census/gate
output carries ``function`` + ``receiver`` so every flagged site can be
reviewed by a human.
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


def _block_always_exits(stmts: list) -> bool:
    """True iff every execution path through the statement list leaves the
    enclosing function (final effect is return/raise, through If branches,
    or a fully-exiting try). Used to decide whether an exception raised in a
    Try body can fall through to statements after the Try."""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return True
    if isinstance(last, ast.If):
        if not last.orelse:
            return False
        return _block_always_exits(last.body) and _block_always_exits(last.orelse)
    if isinstance(last, (ast.Try, ast.TryStar)):
        if not last.handlers:
            return False
        if not _block_always_exits(last.body):
            return False
        if not all(_block_always_exits(h.body) for h in last.handlers):
            return False
        if last.orelse and not _block_always_exits(last.orelse):
            return False
        if last.finalbody and not _block_always_exits(last.finalbody):
            return False
        return True
    return False


def _gate_dominates(gate_chain: tuple, call_chain: tuple) -> bool:
    """True iff the gate statement is guaranteed to run before the call on
    every path reaching the call, and a gate DENIAL cannot fall through to
    the call.

    Chains are tuples of (list_id, index, owner_stmt, role) from the
    function/module body down to the statement's block. Rules:
      - shared prefix levels must keep gate index <= call index;
      - gate in an enclosing block (or same list) of the call → dominates;
      - diverged subtrees: the gate still dominates when every compound on
        the gate's tail path is a Try — ``body`` with all-exiting handlers
        (denial returns/raises, never swallowed), ``finalbody`` (always
        runs) — anything conditional (If/For/... bodies, orelse, handlers)
        means the gate can be skipped → NOT dominating;
      - a call inside the ``finalbody`` of the SAME try that encloses the
        gate is never exempt (finally runs even after a denial-return)."""
    m = min(len(gate_chain), len(call_chain))
    if m == 0:
        return False
    k = 0
    while k < m and gate_chain[k][0] == call_chain[k][0]:
        k += 1
    if k == 0:
        return False
    for lvl in range(k):
        if gate_chain[lvl][1] > call_chain[lvl][1]:
            return False
    if k == len(gate_chain):
        return True
    # diverged at level k — sibling subtrees (k < len(gate_chain)). The call
    # chain may be exhausted here too (call sits at an enclosing level after
    # the gate's compound); the same-owner role checks only apply when the
    # call chain still has an entry at level k.
    if k < len(call_chain):
        call_owner_k = call_chain[k][2]
        gate_owner_k = gate_chain[k][2]
        if call_chain[k][3] == "finalbody" and call_owner_k is gate_owner_k:
            return False  # finally runs even after a denial-return
        if call_chain[k][3] == "handlers" and call_owner_k is gate_owner_k:
            return False  # the denial handler itself performs the fetch
        if (
            call_chain[k][3] == "orelse"
            and call_owner_k is gate_owner_k
            and gate_chain[k][3] == "body"
        ):
            # try/else: the else block runs only when the body (and gate) succeeded
            return True
    for lvl in range(k, len(gate_chain)):
        _lid, _idx, owner, role = gate_chain[lvl]
        if not isinstance(owner, (ast.Try, ast.TryStar)):
            return False  # conditional compound: gate may be skipped entirely
        if role == "finalbody":
            continue  # a finally always executes
        if role != "body":
            return False  # orelse/handler positions are conditional
        if owner.handlers and not all(
            _block_always_exits(h.body) for h in owner.handlers
        ):
            return False  # a handler can swallow the denial and fall through
    return True


def _resolve_from_module(module: str | None, level: int, package: str | None) -> str | None:
    """Resolve an ``ast.ImportFrom`` target to a dotted module name.

    ``level`` is the relative-import depth (0 = absolute); ``package`` is the
    dotted package of the file containing the import (None for standalone
    scripts, whose relative imports cannot be resolved here)."""
    if not level:
        return module
    if not package:
        return None
    parts = package.split(".")
    drop = level - 1
    if drop > len(parts):
        return None
    if drop:
        parts = parts[:-drop]
    base = ".".join(parts)
    if module:
        return f"{base}.{module}" if base else module
    return base or None


def _package_and_module_names(path: Path) -> tuple[str | None, str | None]:
    """(package, module) dotted names derived from the filesystem layout:
    walk up while ``__init__.py`` exists. Returns (None, None) for standalone
    scripts outside any package."""
    directory = path.parent
    if not (directory / "__init__.py").exists():
        return None, None
    parts: list[str] = []
    walk = directory
    while (walk / "__init__.py").exists():
        parts.append(walk.name)
        walk = walk.parent
    package = ".".join(reversed(parts))
    module = package if path.name == "__init__.py" else f"{package}.{path.stem}"
    return package, module


class _FileAnalyzer:
    """Single-traversal per-file analysis: scopes, tracked clients, edges."""

    def __init__(
        self,
        tree: ast.AST,
        rel_path: str,
        *,
        cross_clients: dict[str, set[str]] | None = None,
        known_modules: set[str] | None = None,
        package_name: str | None = None,
    ):
        self.tree = tree
        self.rel_path = rel_path
        self.cross_clients = cross_clients if cross_clients is not None else {}
        self.known_modules = known_modules if known_modules is not None else set()
        self.package_name = package_name
        self.aliases: dict[str, str] = {}
        self.module_vars: set[str] = set()          # module-level tracked names
        self.client_attrs: set[str] = set()         # dotted attr chains, file-wide
        self.factories: set[str] = set()            # func names returning clients
        self.scope_vars: dict[int, set[str]] = {}
        self.scope_qualname: dict[int, str] = {}
        self.scope_params: dict[int, list[str]] = {}
        self.scope_first_is_self: dict[int, bool] = {}
        self.scope_gate_chains: dict[int, list[tuple]] = {}
        self.funcs_by_name: dict[str, list[int]] = {}
        self.sites: list[ClientCallSite] = []
        self._candidate_sites: list[tuple[int | None, ast.Call, tuple]] = []
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
        if not parts:
            return False
        resolved = self._resolve_dotted(parts)
        if resolved and resolved.split(".")[-1] == EGRESS_GATE_NAME:
            return True
        return parts[-1] == EGRESS_GATE_NAME

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
        """Populate the alias map and apply cross-module client tracking.

        [AUDIT-R2 M-01] This method existed but was never invoked — the alias
        map stayed empty and ``from requests import Session``-style ctor
        aliases were invisible. It is now part of ``analyze()``."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    self.aliases[local] = alias.name if alias.asname else local
                    if alias.asname and alias.name in self.known_modules:
                        self._add_module_member_clients(alias.asname, alias.name)
            elif isinstance(node, ast.ImportFrom) and (node.module or node.level):
                resolved = _resolve_from_module(node.module, node.level, self.package_name)
                for alias in node.names:
                    if alias.name == "*":
                        # [M-01b] star-import of a module that exports clients
                        if resolved and resolved in self.cross_clients:
                            for var in self.cross_clients[resolved]:
                                self._track(None, var)
                        continue
                    local = alias.asname or alias.name
                    if resolved:
                        self.aliases[local] = f"{resolved}.{alias.name}"
                        member_clients = self.cross_clients.get(resolved, set())
                        if alias.name in member_clients:
                            # [M-01b] cross-module client variable import
                            self._track(None, local)
                        elif f"{resolved}.{alias.name}" in self.known_modules:
                            self._add_module_member_clients(
                                local, f"{resolved}.{alias.name}"
                            )
                    else:
                        self.aliases[local] = alias.name

    def _add_module_member_clients(self, local_alias: str, module_name: str) -> None:
        """``import known_module as m`` → ``m.<client_var>`` is a client
        (dotted attribute chain tracked file-wide)."""
        for var in self.cross_clients.get(module_name, ()):
            self.client_attrs.add(f"{local_alias}.{var}")

    def module_surface(self) -> tuple[set[str], list[tuple[ast.ImportFrom, str | None]]]:
        """Module-level surface for the cross-module export map:
        (client variable names bound at module level, module-level
        ``from ... import`` nodes with their resolved target module)."""
        names: set[str] = set()
        imports_from: list[tuple[ast.ImportFrom, str | None]] = []

        def visit(stmts: list) -> None:
            for stmt in stmts:
                if isinstance(stmt, _SCOPE_NODES + (ast.ClassDef,)):
                    continue  # function/class bodies are not module surface
                if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                    value = stmt.value
                    targets = (
                        stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                    )
                    if value is not None and self._is_ctor_call(value):
                        for target in targets:
                            if isinstance(target, ast.Name):
                                names.add(target.id)
                elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                    for item in stmt.items:
                        if (
                            item.optional_vars is not None
                            and isinstance(item.optional_vars, ast.Name)
                            and self._is_ctor_call(item.context_expr)
                        ):
                            names.add(item.optional_vars.id)
                elif isinstance(stmt, ast.ImportFrom) and (stmt.module or stmt.level):
                    imports_from.append(
                        (stmt, _resolve_from_module(stmt.module, stmt.level, self.package_name))
                    )
                for _field, value in ast.iter_fields(stmt):
                    if not isinstance(value, list):
                        continue
                    if value and all(isinstance(v, ast.stmt) for v in value):
                        visit(value)
                    elif value and all(isinstance(v, ast.excepthandler) for v in value):
                        for handler in value:
                            visit(handler.body)
                    elif value and all(isinstance(v, ast.match_case) for v in value):
                        for case in value:
                            visit(case.body)

        visit(getattr(self.tree, "body", []))
        return names, imports_from

    # ------------------------------------------------------------- pass 2
    def analyze(self) -> list[ClientCallSite]:
        self.collect_imports()
        self._scan_stmts(getattr(self.tree, "body", []), None, (), None, "module")
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
        for sid, call, chain in self._candidate_sites:
            receiver = call.func.value
            if not self._receiver_tracked(sid, receiver):
                continue
            try:
                receiver_src = ast.unparse(receiver)
            except Exception as _unparse_err:  # pragma: no cover — unparse is best-effort
                logger.debug("ast.unparse failed for receiver at %s:%s", getattr(call, "lineno", "?"), getattr(call, "col_offset", "?"), exc_info=True)
                receiver_src = "<unparseable>"
            # [AUDIT-R2 M-01c] dominance-based exemption (was line-order).
            gated = any(
                _gate_dominates(gchain, chain)
                for gchain in self.scope_gate_chains.get(sid, ())
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

    # ------------------------------------------------- statement traversal
    def _scan_stmts(self, stmts: list, sid: int | None, chain: tuple,
                    owner: ast.AST | None, role: str) -> None:
        """Scan a statement list. ``chain`` carries (list_id, index, owner,
        role) pairs from the outermost block to here — the dominance record
        for every call and gate found inside."""
        if not stmts:
            return
        list_id = id(stmts)
        for idx, stmt in enumerate(stmts):
            self._scan_stmt(stmt, sid, chain + ((list_id, idx, owner, role),))

    def _scan_stmt(self, stmt: ast.stmt, sid: int | None, chain: tuple) -> None:
        if isinstance(stmt, _SCOPE_NODES):
            # decorators / default args execute in the ENCLOSING scope
            for expr in stmt.decorator_list:
                self._collect_expr_calls(expr, sid, chain)
            for default in (
                *stmt.args.defaults,
                *(d for d in stmt.args.kw_defaults if d is not None),
            ):
                self._collect_expr_calls(default, sid, chain)
            child_sid = self._register_scope(stmt, sid)
            self._scan_stmts(stmt.body, child_sid, (), stmt, "body")
            return
        if isinstance(stmt, ast.ClassDef):
            for expr in stmt.decorator_list:
                self._collect_expr_calls(expr, sid, chain)
            # class body: treated as the enclosing scope (over-approx)
            self._scan_stmts(stmt.body, sid, chain, stmt, "body")
            return
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if (
                    item.optional_vars is not None
                    and isinstance(item.optional_vars, ast.Name)
                    and self._is_ctor_call(item.context_expr)
                ):
                    self._track(sid, item.optional_vars.id)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            value = stmt.value
            if value is not None:
                targets = (
                    stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                )
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
        elif isinstance(stmt, ast.Return) and stmt.value is not None:
            self._pending_return.append((sid, stmt.value))
        # expression-level calls of THIS statement (its own dominance chain)
        self._collect_expr_calls(stmt, sid, chain)
        # nested statement blocks (same scope, deeper chain level)
        if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While,
                             ast.With, ast.AsyncWith)):
            self._scan_stmts(stmt.body, sid, chain, stmt, "body")
            orelse = getattr(stmt, "orelse", None)
            if orelse:
                self._scan_stmts(orelse, sid, chain, stmt, "orelse")
        elif isinstance(stmt, (ast.Try, ast.TryStar)):
            self._scan_stmts(stmt.body, sid, chain, stmt, "body")
            if stmt.orelse:
                self._scan_stmts(stmt.orelse, sid, chain, stmt, "orelse")
            self._scan_stmts(stmt.finalbody, sid, chain, stmt, "finalbody")
            for handler in stmt.handlers:
                if handler.type is not None:
                    self._collect_expr_calls(handler.type, sid, chain)
                self._scan_stmts(handler.body, sid, chain, stmt, "handlers")
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                if case.guard is not None:
                    self._collect_expr_calls(case.guard, sid, chain)
                self._scan_stmts(case.body, sid, chain, stmt, "cases")

    def _collect_expr_calls(self, root: ast.AST, sid: int | None, chain: tuple) -> None:
        """Walk an expression tree collecting calls (and walrus ctor bindings),
        without descending into nested statement blocks (those carry their own
        chain via _scan_stmts)."""
        stack = [root]
        while stack:
            cur = stack.pop()
            for child in ast.iter_child_nodes(cur):
                if isinstance(child, (ast.stmt, ast.ExceptHandler, ast.match_case)):
                    continue  # handled by block recursion with its own chain
                if isinstance(child, ast.Call):
                    self._handle_call(child, sid, chain)
                elif isinstance(child, ast.NamedExpr) and isinstance(child.target, ast.Name):
                    if self._is_ctor_call(child.value):
                        self._track(sid, child.target.id)
                stack.append(child)

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

    def _handle_call(self, call: ast.Call, sid: int | None, chain: tuple) -> None:
        if self._is_gate_call(call):
            self.scope_gate_chains.setdefault(sid, []).append(chain)
            return
        if not isinstance(call.func, ast.Attribute) or call.func.attr not in CLIENT_HTTP_METHODS:
            # maybe an interprocedural edge (client passed to a callee)
            self._pending_calls.append((sid, call))
            return
        # Verdict is deferred to after the fixpoint: the receiver may only
        # become a tracked client via an interprocedural edge resolved later
        # (e.g. a client parameter of this same function).
        self._candidate_sites.append((sid, call, chain))

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


def _parse_targets(
    paths,
    unparsable: list[str] | None = None,
) -> list[tuple[Path, ast.AST, str | None, str | None]]:
    """Parse every target file once. [AUDIT-R2 M-01a] fail-loud: a file that
    cannot be parsed is a hole in egress visibility — raises SyntaxError by
    default, or collects the path into ``unparsable`` when the caller supplies
    a list (the caller must then fail on it)."""
    targets: list[tuple[Path, ast.AST, str | None, str | None]] = []
    for path in paths:
        p = Path(path)
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError as exc:
                if unparsable is None:
                    raise SyntaxError(
                        "[egress_static_scan] unparsable file blocks egress "
                        f"visibility (fail-closed): {f} (line {exc.lineno}): {exc.msg}"
                    ) from exc
                unparsable.append(str(f))
                continue
            package_name, module_name = _package_and_module_names(f)
            targets.append((f, tree, module_name, package_name))
    return targets


def _build_cross_module_client_map(
    targets: list[tuple[Path, ast.AST, str | None, str | None]],
) -> tuple[dict[str, set[str]], set[str]]:
    """[AUDIT-R2 M-01b] Build (module → module-level client variable names)
    plus the set of known module names, with a bounded fixpoint over
    module-level re-exports (``from other_module import client_var``)."""
    analyzers: dict[str, _FileAnalyzer] = {}
    for path, tree, module_name, package_name in targets:
        if not module_name or module_name in analyzers:
            continue
        light = _FileAnalyzer(tree, path.as_posix(), package_name=package_name)
        light.collect_imports()
        analyzers[module_name] = light

    exports: dict[str, set[str]] = {}
    surfaces: dict[str, list[tuple[ast.ImportFrom, str | None]]] = {}
    for module_name, light in analyzers.items():
        names, imports_from = light.module_surface()
        exports[module_name] = names
        surfaces[module_name] = imports_from

    for _ in range(12):
        changed = False
        for module_name, imports_from in surfaces.items():
            mine = exports[module_name]
            for imp_node, resolved in imports_from:
                if not resolved or resolved == module_name:
                    continue
                target_set = exports.get(resolved)
                if not target_set:
                    continue
                for alias in imp_node.names:
                    if alias.name == "*":
                        for var in target_set:
                            if var not in mine:
                                mine.add(var)
                                changed = True
                    elif alias.name in target_set:
                        local = alias.asname or alias.name
                        if local not in mine:
                            mine.add(local)
                            changed = True
        if not changed:
            break
    return exports, set(analyzers.keys())


def scan_client_method_calls(
    paths,
    *,
    unparsable: list[str] | None = None,
) -> list[dict]:
    """Scan python files/dirs for method calls on tracked HTTP clients.

    Returns a list of dicts for ALL matched call-sites (gated and ungated):
    {file, line, col, method, receiver, function, gated}. Callers decide
    policy; the static gate fails on ``gated == False`` sites not pinned.
    Unparsable files: raises by default; with ``unparsable`` the paths are
    collected there and the caller must fail on the list (fail-closed).
    """
    targets = _parse_targets(paths, unparsable)
    cross_clients, known_modules = _build_cross_module_client_map(targets)
    results: list[dict] = []
    for path, tree, _module_name, package_name in targets:
        analyzer = _FileAnalyzer(
            tree,
            path.as_posix(),
            cross_clients=cross_clients,
            known_modules=known_modules,
            package_name=package_name,
        )
        for site in analyzer.analyze():
            results.append(site.as_dict())
    return results


def scan_raw_http_calls(
    paths,
    *,
    unparsable: list[str] | None = None,
) -> list[tuple[str, int, str]]:
    """AST scan for direct-spelling raw HTTP call-sites: urllib.request.urlopen,
    requests/httpx module-level verb calls (get/post/put/patch/delete/head/
    options). Returns (path, line, kind) tuples. Moved here from the gate test
    so the census runner and the test share one implementation (EE-G1).
    Unparsable files: fail-loud (see _parse_targets)."""
    _verbs = {"get", "post", "put", "patch", "delete", "head", "options"}
    violations: list[tuple[str, int, str]] = []
    for path in paths:
        p = Path(path)
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError as exc:
                if unparsable is None:
                    raise SyntaxError(
                        "[egress_static_scan] unparsable file blocks egress "
                        f"visibility (fail-closed): {f} (line {exc.lineno}): {exc.msg}"
                    ) from exc
                unparsable.append(str(f))
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
