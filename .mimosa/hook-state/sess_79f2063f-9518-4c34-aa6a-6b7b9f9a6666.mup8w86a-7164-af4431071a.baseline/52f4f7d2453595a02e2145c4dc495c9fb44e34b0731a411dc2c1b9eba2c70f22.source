# SCP CIRCUIT: M07 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M07-closure.json)
"""
[EXEC-1 A4] AST SCANNERS — detect bugs by parsing source.

TÁI SAO: EXEC-2's runner consumes an EXPLICIT bug list or JSONL audit
trail — but if neither is provided, run_once() returns an empty summary
(no bugs to process). For the /v105/autofix/run-audit API endpoint to
actually DO something useful, we need a SCANNER that detects bugs by
parsing the source code. These AST visitors catch the top patterns from
the FRESH-1 manual audit:
  - bare `except: pass` (silent error swallowing — #1 cause of dead bugs)
  - undefined names (NameError candidates — variables used before assignment)
  - syntax errors (file doesn't parse — blocks other scanners)

Extracted from `autofix/runner.py` in Task 10-B (Modularity Refactor B).
Wired back into runner.py via re-export — backward compatible.
"""
from __future__ import annotations

import ast
import json
import logging
import os

# [G2-FIX PERM-03] Protected paths — SCP cannot modify its own permission/security source
# These files define the very permissions that constrain SCP. If SCP could modify them,
# it could escalate its own privileges (e.g., disable verify_admin, change capability levels).
PROTECTED_PATHS = [
    "scp/task_kernel.py",
    "scp/persistence/db.py",
    "scp/epistemic/evidence_store.py",
    "scp/contracts/",
    "scp/security/auth.py",
    "scp/security/auth_config.py",
    "scp/llm_gateway/",
    "scp/governance/",
    "scp/hands/task_kernel_bridge.py",
    "scp/hands/hands_executor.py",
    "spec/complete_scp_reference.yaml",
    "spec/protected_invariants.yaml",
    "spec/scp_target_test_coverage.yaml",
    "spec/scp_future_target_manifest.yaml",
    "tests/",
    "scp/security/capability_epoch.py",
    "scp/security/os_sandbox.py",
    "scp/verifier.py",
    "scp/autofix/policy_gate.py",
    "scp/autofix/permission.py",
    "scp/autofix/engine.py",
    "scp/autofix/classifier.py",
    "scp/meta/capability_levels.py",
    "scp/meta/constitution.py",
    "scp/meta/governance_v97.py",
    "scp/meta/why_gate.py",
    "scp/api/_shared.py",
    "scp/api/_lifespan.py",
    "scp/security/dos_protection.py",
    "scp/security/threat_simulator.py",
    "scp/security/unified_detector.py",
    "scp/security/memory_guard.py",
    "scp/security/image_voice_detector.py",
    "scp/security/multi_turn_tracker.py",
]

def _normalize_protected_path_input(filepath: str) -> str:
    """[PERM-03 FIX] Normalize a candidate path for protected-path matching.

    TẠI SAO: `str(Path(...))` on Windows yields backslash separators, so the
    previous raw substring match against POSIX-style PROTECTED_PATHS entries
    NEVER fired for absolute Windows paths (probe before fix:
    ``_is_protected_path(r"D:\\scp\\scp\\autofix\\engine.py") == False``).
    The PERM-03 gate was vacuous for exactly the paths it exists to block —
    autofix could rewrite its own security files. Normalization:
      1. backslashes -> forward slashes;
      2. absolute paths are resolved and relativized against the scp package
         root or the repo root, so ``D:\\scp\\scp\\autofix\\engine.py`` and
         ``scp/autofix/engine.py`` both normalize to ``scp/autofix/engine.py``.

    Fail-closed: when relativization is impossible (path outside both roots)
    the resolved absolute POSIX path is returned — PROTECTED_PATHS entries can
    still substring-match it, so unknown roots stay protected rather than
    silently becoming writable.
    """
    if not filepath:
        return ""
    normalized = filepath.replace("\\", "/")
    try:
        path_obj = Path(filepath)
        if path_obj.is_absolute():
            resolved = path_obj.resolve().as_posix()
            # 1) Repo-root-relative is the primary form: PROTECTED_PATHS
            #    entries ("scp/autofix/engine.py", "tests/", "spec/...") are
            #    expressed relative to the repo checkout root.
            repo_posix = _REPO_ROOT.resolve().as_posix()
            if resolved == repo_posix:
                return ""
            if resolved.startswith(repo_posix + "/"):
                return resolved[len(repo_posix) + 1:]
            # 2) Fallback: package root (scp/) — for checkouts where the
            #    package is not under the repo root, re-prefix the remainder
            #    with "scp/" so the same PROTECTED_PATHS entries still match.
            pkg_posix = _SCP_ROOT.resolve().as_posix()
            if resolved == pkg_posix:
                return ""
            if resolved.startswith(pkg_posix + "/"):
                return "scp/" + resolved[len(pkg_posix) + 1:]
            return resolved
        return Path(normalized).as_posix()
    except Exception as exc:
        logger.debug(f"_normalize_protected_path_input: exception ignored: {exc}", exc_info=True)
        # silent-by-design: normalization probe — the slash-normalized string
        # is the documented fallback for unresolvable paths.
        return normalized


def _is_protected_path(filepath: str) -> bool:
    """Check if file is in protected paths — SCP cannot auto-modify these.

    [PERM-03 FIX] The candidate path is normalized (backslashes -> forward
    slashes; absolute paths relativized to the repo/package root) BEFORE
    matching, and the match is case-insensitive: Windows filesystems are
    case-insensitive, so a case-based miss would reopen the self-modification
    hole (this widens protection only — fail-closed direction).
    """
    candidate = _normalize_protected_path_input(filepath).lower()
    if not candidate:
        return False
    for protected in PROTECTED_PATHS:
        if protected.lower() in candidate:
            return True
    return False
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.runner")

# Cap scans so the runner finishes quickly even on large codebases
_MAX_SCAN_FILES = 500
_MAX_BUGS_PER_SCAN = 200

# scp/ package root — scan target (avoid tests/, examples/, scripts/)
# runner_phases/ is one level deeper than runner.py, so parent.parent.parent
# points to .../scp/ (runner_phases/ -> autofix/ -> scp/).
_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
# [PERM-03 FIX] Repo root — parent of the scp/ package. Used by
# _normalize_protected_path_input to relativize absolute candidate paths.
_REPO_ROOT = _SCP_ROOT.parent  # repo checkout root (parent of scp/)

# [EXEC-1 A4] deep-audit results log — per-bug outcomes from AST scans
DEEP_AUDIT_RESULTS_FILE = "data/deep_audit_results.jsonl"


class _BareExceptPassFinder(ast.NodeVisitor):
    """Detect `except: pass` / `except Exception as e: pass` — swallows errors silently.

    These are the #1 cause of "silent failure" bugs (the audit trail catches
    exceptions but never surfaces them). Auto-fixable in most cases by
    re-raising or logging.
    """

    def __init__(self):
        self.findings: list[dict] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        is_bare = node.type is None
        is_broad = (
            isinstance(node.type, ast.Name)
            and node.type.id in ("Exception", "BaseException")
        )
        if is_bare or is_broad:
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                self.findings.append({
                    "line": node.lineno,
                    "bug_type": "BareExceptPass",
                    "description": (
                        f"{'bare' if is_bare else 'broad'} except with bare `pass` "
                        f"at line {node.lineno} — swallows errors silently"
                    ),
                    "suggested_fix": (
                        "Replace `pass` with `logger.exception(...)` or re-raise. "
                        "Silent exception swallowing hides real bugs."
                    ),
                })
        self.generic_visit(node)


class _ModuleNameCollector(ast.NodeVisitor):
    """[V5.3-SCANNER-FIX] Pass 1 helper — collect ALL module-level name bindings.

    Walks top-level statements (caller passes `tree.body` statements one by
    one). Recurses into "container" statements (If/Try/For/With/While/
    ExceptHandler) so that names bound inside `if __name__ == "__main__":`
    or `try:` blocks at module level are also collected. Does NOT recurse
    into FunctionDef/ClassDef bodies — those introduce separate scopes.

    Why: Python executes module body top-to-bottom, binding each name before
    any function is *called*. So a function defined LATER in the file can
    still be referenced EARLIER (inside another function body that runs at
    call time). This is the "forward reference" pattern the old scanner
    falsely flagged.
    """

    def __init__(self, names: set):
        self._names = names

    # --- Bindings (do not recurse into function/class bodies) ---

    def visit_FunctionDef(self, node):
        self._names.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._names.add(node.name)

    def visit_Import(self, node):
        for alias in node.names:
            self._names.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            self._names.add(alias.asname or alias.name)

    def visit_Assign(self, node):
        for tgt in node.targets:
            self._collect_target(tgt)
        # RHS may contain walrus (visit_NamedExpr) — visit value too.
        self.visit(node.value)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self._names.add(node.target.id)
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node):
        # x += 1 requires x already defined — doesn't create new binding
        # but visit value in case it contains walrus.
        self.visit(node.value)

    def visit_For(self, node):
        self._collect_target(node.target)
        self.visit(node.iter)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    visit_AsyncFor = visit_For

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                self._collect_target(item.optional_vars)
            self.visit(item.context_expr)
        for stmt in node.body:
            self.visit(stmt)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node):
        if node.name:
            self._names.add(node.name)
        if node.type is not None:
            self.visit(node.type)
        for stmt in node.body:
            self.visit(stmt)

    def visit_Try(self, node):
        for stmt in node.body:
            self.visit(stmt)
        for handler in node.handlers:
            self.visit(handler)
        for stmt in node.orelse:
            self.visit(stmt)
        for stmt in node.finalbody:
            self.visit(stmt)

    def visit_If(self, node):
        self.visit(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_While(self, node):
        self.visit(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_NamedExpr(self, node):
        # Walrus at module level binds target in module scope.
        if isinstance(node.target, ast.Name):
            self._names.add(node.target.id)
        self.visit(node.value)

    def _collect_target(self, tgt):
        if isinstance(tgt, ast.Name):
            self._names.add(tgt.id)
        elif isinstance(tgt, (ast.Tuple, ast.List)):
            for elt in tgt.elts:
                self._collect_target(elt)
        elif isinstance(tgt, ast.Starred):
            self._collect_target(tgt.value)
        # Attribute/Subscript targets don't bind new names


class _UndefinedNameFinder(ast.NodeVisitor):
    """Detect NameError candidates — names USED but never DEFINED.

    [V5.3-SCANNER-FIX] Two-pass design:
      Pass 1: collect ALL module-level names (functions, classes, imports,
              assignments, with-items, for-targets, except-handler names,
              walrus targets) — see `_ModuleNameCollector`. These act as
              forward-reference targets (Python resolves them at call time,
              not parse time).
      Pass 2: walk the AST with proper scope tracking. A name is "defined"
              if it's in the current scope stack OR in module-level names
              OR in builtins.

    Scope tracking covers (each fix tagged `# [V5.3-SCANNER-FIX]`):
      1. `except X as exc`     — visit_ExceptHandler (was missing)
      2. `with ... as var`     — visit_With (already worked, verified)
      3. `for x in items`      — visit_For (already worked)
      4. lambda args           — visit_Lambda (was missing)
      5. comprehension vars    — visit_ListComp/SetComp/DictComp/GeneratorExp
                                 (was missing — caused most false positives)
      6. walrus `:=`           — visit_NamedExpr (was missing)
      7. function/class args   — visit_FunctionDef/visit_ClassDef (improved:
                                 decorators visited in ENCLOSING scope before
                                 name binding; annotations SKIPPED to avoid
                                 false positives on forward-ref type hints)
      8. type annotations      — skipped (forward refs are valid Python)
      9. forward references    — Pass 1 collects module-level names so a
                                 function defined later can be called earlier
    """

    _BUILTINS = set(dir(__builtins__)) if not isinstance(__builtins__, dict) \
        else set(__builtins__.keys())
    _BUILTINS |= {"__name__", "__file__", "__package__", "__spec__",
                  "__builtins__", "self", "cls"}

    def __init__(self, tree: ast.Module | None = None):
        self.findings: list[dict] = []
        # [V5.3-SCANNER-FIX] Pass 1: collect module-level names for
        # forward-reference tolerance. Python resolves module-level names
        # at call time, so a function defined LATER can still be called
        # EARLIER in the file.
        self._module_names: set[str] = set()
        if tree is not None and isinstance(tree, ast.Module):
            collector = _ModuleNameCollector(self._module_names)
            for stmt in tree.body:
                collector.visit(stmt)
        # Outermost scope = module scope, seeded with module-level names so
        # any reference (forward or backward) resolves correctly.
        self._scope_stack: list[set[str]] = [set(self._module_names)]

    # ----- Pass 2: scope-tracking walk -----

    def _enter_scope(self):
        self._scope_stack.append(set())

    def _exit_scope(self):
        self._scope_stack.pop()

    def _define(self, name: str):
        self._scope_stack[-1].add(name)

    def _is_defined(self, name: str) -> bool:
        return any(name in s for s in self._scope_stack) or name in self._BUILTINS

    def _define_target(self, tgt):
        """Recursively define names in an assignment/with-as/for target."""
        if isinstance(tgt, ast.Name):
            self._define(tgt.id)
        elif isinstance(tgt, (ast.Tuple, ast.List)):
            for elt in tgt.elts:
                self._define_target(elt)
        elif isinstance(tgt, ast.Starred):
            self._define_target(tgt.value)
        elif isinstance(tgt, ast.Attribute):
            self.visit(tgt.value)
        elif isinstance(tgt, ast.Subscript):
            self.visit(tgt.value)
            if tgt.slice is not None:
                self.visit(tgt.slice)
        else:
            self.visit(tgt)

    def _define_args(self, args: ast.arguments):
        """Define all argument names (posonly, args, kwonly, vararg, kwarg).

        [V5.3-SCANNER-FIX] Annotations are NOT visited — type hints may be
        string forward refs (`def foo(x: "SomeType")`) or names not yet
        imported. Skipping them prevents false positives.
        """
        for arg in args.posonlyargs + args.args + args.kwonlyargs:
            self._define(arg.arg)
        if args.vararg:
            self._define(args.vararg.arg)
        if args.kwarg:
            self._define(args.kwarg.arg)

    def visit_FunctionDef(self, node):
        # [V5.3-SCANNER-FIX] Decorators are evaluated in ENCLOSING scope
        # BEFORE the function name is bound. Visit them first (in current
        # scope, before _define(node.name)).
        for dec in node.decorator_list:
            self.visit(dec)
        # Function name binds in ENCLOSING scope (current top of stack).
        self._define(node.name)
        # Enter function scope.
        self._enter_scope()
        self._define_args(node.args)
        # NOTE: deliberately NOT visiting node.returns or arg.annotation —
        # type hints can be forward references / string literals.
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        # [V5.3-SCANNER-FIX] Decorators + bases + keyword args evaluated in
        # ENCLOSING scope before class name is bound.
        for dec in node.decorator_list:
            self.visit(dec)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw.value)
        self._define(node.name)
        self._enter_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._exit_scope()

    def visit_Import(self, node):
        for alias in node.names:
            self._define(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue
            self._define(alias.asname or alias.name)

    def visit_Assign(self, node):
        # RHS evaluated first, then targets bound.
        self.visit(node.value)
        for tgt in node.targets:
            self._define_target(tgt)

    def visit_AnnAssign(self, node):
        # [V5.3-SCANNER-FIX] Skip annotation — type hints (`x: int = 5` or
        # `def foo(x: "SomeType"):`) can be forward references / string
        # literals. Visit value, define target, skip annotation entirely.
        if node.value is not None:
            self.visit(node.value)
        if node.target is not None:
            self._define_target(node.target)

    def visit_AugAssign(self, node):
        # x += 1 → x must already be defined; visit both target and value.
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node):
        # iter evaluated in current scope, then target bound.
        self.visit(node.iter)
        self._enter_scope()
        self._define_target(node.target)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self._exit_scope()

    visit_AsyncFor = visit_For

    def visit_With(self, node):
        # [V5.3-SCANNER-FIX] with ... as var: visit context_expr first,
        # then bind optional_vars in current scope, then visit body.
        # (Pre-existing behavior verified correct — withitem.optional_vars
        # is bound before body executes.)
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._define_target(item.optional_vars)
        for stmt in node.body:
            self.visit(stmt)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node):
        # [V5.3-SCANNER-FIX] except X as exc:
        #   - Exception type evaluated in ENCLOSING scope (current)
        #   - `exc` bound for the handler body (Python unbinds after exit,
        #     but for our purposes defining in current scope is sufficient —
        #     we don't re-flag the same name).
        # This was the #1 false positive: `except socket.gaierror as exc:`
        # was flagging `exc` as undefined when used in the except body.
        if node.type is not None:
            self.visit(node.type)
        if node.name:
            self._define(node.name)
        for stmt in node.body:
            self.visit(stmt)

    def visit_Lambda(self, node):
        # [V5.3-SCANNER-FIX] Lambda has its own scope for arguments.
        # `lambda x, y: x + y` — x and y are bound in lambda scope.
        self._enter_scope()
        self._define_args(node.args)
        self.visit(node.body)
        self._exit_scope()

    def visit_ListComp(self, node):
        # [V5.3-SCANNER-FIX] Comprehensions have their own scope.
        self._visit_comprehension(node, element=node.elt)

    def visit_SetComp(self, node):
        self._visit_comprehension(node, element=node.elt)

    def visit_GeneratorExp(self, node):
        self._visit_comprehension(node, element=node.elt)

    def visit_DictComp(self, node):
        self._visit_comprehension(node, element=node.key, value=node.value)

    def _visit_comprehension(self, node, element, value=None):
        # [V5.3-SCANNER-FIX] Comprehension scope rules (PEP 3104 / Python
        # semantics): the leftmost iter is evaluated in ENCLOSING scope;
        # everything else (target, ifs, subsequent iters, element) lives
        # in the comprehension's own scope.
        #   `[x for x in items if x > 0]`
        #    ^   ^   ^^^^^^^^^^^^^^^^^^
        #    comp scope | enclosing | comp scope
        # This was the #2 false positive: `[r for r in v.slm_responses]`
        # was flagging `r` as undefined.
        self._enter_scope()
        gens = node.generators
        if gens:
            # First generator's iter: enclosing scope (still current).
            self.visit(gens[0].iter)
            # Bind first target in comp scope.
            self._define_target(gens[0].target)
            for if_clause in gens[0].ifs:
                self.visit(if_clause)
            # Subsequent generators: all in comp scope.
            for gen in gens[1:]:
                self.visit(gen.iter)
                self._define_target(gen.target)
                for if_clause in gen.ifs:
                    self.visit(if_clause)
        # Element (and value for DictComp) in comp scope.
        self.visit(element)
        if value is not None:
            self.visit(value)
        self._exit_scope()

    def visit_NamedExpr(self, node):
        # [V5.3-SCANNER-FIX] Walrus operator (PEP 572): `(y := expr)`.
        # Visit value first, then bind target in current scope.
        # (Python actually binds in the nearest enclosing function/module
        # scope, not comprehension scope — but binding in current scope is
        # a safe approximation for our undefined-name detection.)
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self._define(node.target.id)
        else:
            self._define_target(node.target)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if not self._is_defined(node.id):
                self.findings.append({
                    "line": node.lineno,
                    "bug_type": "PossiblyUndefinedName",
                    "description": f"Name `{node.id}` used at line {node.lineno} "
                                   f"may be undefined in this scope",
                    "suggested_fix": (
                        f"Add `from X import {node.id}` or define `{node.id}` "
                        f"before first use."
                    ),
                })
                # Don't re-flag same name in same scope
                self._define(node.id)


def _iter_python_files(root: Path, limit: int = _MAX_SCAN_FILES):
    """Iterate .py files under root (skip __pycache__, tests, examples)."""
    count = 0
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.name.startswith("test_"):
            continue
        if any(part in ("examples", "scripts", "attack_payloads")
               for part in path.parts):
            continue
        if count >= limit:
            break
        yield path
        count += 1


def _scan_file(path: Path) -> list[dict]:
    """Run all AST scanners on one file. Returns list of findings
    (each has line, bug_type, description, suggested_fix)."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return [{
            "line": e.lineno or 1,
            "bug_type": "SyntaxError",
            "description": f"File does not parse: {e.msg}",
            "suggested_fix": "Fix the syntax error before any other scan can run.",
        }]
    except Exception as scan_err:
        # fail-loudly (S-B1b): a read/scan crash must not masquerade as a
        # clean file; the [] return contract for parallel workers is kept.
        logger.warning("[ast-scan] scan crashed on %s, reporting no findings: %s", path, scan_err, exc_info=True)
        return []

    findings: list[dict] = []

    bare_finder = _BareExceptPassFinder()
    bare_finder.visit(tree)
    findings.extend(bare_finder.findings)

    name_finder = _UndefinedNameFinder(tree)  # [V5.3-SCANNER-FIX] pass tree for Pass 1 module-name collection
    name_finder.visit(tree)
    for f in name_finder.findings:
        # Filter builtins (re-check in case __builtins__ differed at runtime)
        name_match = f["description"].split("`")[1] if "`" in f["description"] else ""
        if name_match and name_match not in _UndefinedNameFinder._BUILTINS:
            findings.append(f)

    return findings


def _build_bug_report(file: str, finding: dict) -> BugReport:
    """Convert a scanner finding into a BugReport for the classifier."""
    return BugReport(
        file=file,
        line=finding["line"],
        bug_type=finding["bug_type"],
        description=finding["description"],
        suggested_fix=finding["suggested_fix"],
        tier=BugTier.TIER_1_AUTO_FIX,  # classifier will re-tier
    )


def _write_deep_audit_result(result: dict, results_file: str) -> None:
    """Append one deep-audit result to data/deep_audit_results.jsonl."""
    try:
        path = Path(results_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.warning(f"[runner] failed to write deep-audit result: {e}", exc_info=True)


def ast_scan_scp(max_files: int = _MAX_SCAN_FILES,
                 max_bugs: int = _MAX_BUGS_PER_SCAN,
                 include_enterprise: bool = True) -> list[BugReport]:
    """[EXEC-1 A4] AST-scan the scp/ package for common bug patterns.

    Returns a list of BugReports ready to feed into engine.process_bug().
    Bounded by max_files (cap scan time) and max_bugs (cap engine load).

    [ENTERPRISE-V4] Now also runs enterprise scanners (Ruff S-series, Bandit,
    Vulture, Bugbear, Dlint) via scp.autofix.enterprise_scanners.scan_scp_enterprise().
    Fail-open: if enterprise module is unavailable, fall back to original
    BareExceptPass + UndefinedName scanners only.

    [R10 v3 WIRE — IMP-13] Incremental AST-diff cache. Before scanning, call
    `ASTDiffCache.partition_files(all_paths)` to split paths into {scan, cached}.
    Only the "scan" partition is re-scanned — "cached" files (unchanged content
    + AST hash) are skipped. Force full re-scan every 10 cycles (safety net).
    Fail-open: corrupt cache → rebuild from scratch.

    [R10 v3 WIRE — IMP-18] Parallel scanner dispatch. If >1 file in the scan
    partition, fan out across CPU cores via `run_scanners_parallel()`. Falls
    back to sequential loop if ProcessPoolExecutor unavailable.
    """
    bugs: list[BugReport] = []

    # [R10 v3 WIRE — IMP-13] Partition paths into {scan, cached} using AST-diff cache.
    # TẠI SAO: full scan walks ~378 .py files. Most are unchanged since last
    # scan — re-scanning them wastes 3-5s. IMP-13 hashes content + AST and
    # skips files where BOTH hashes match cache. Safety net: force_full every
    # DEFAULT_FULL_RESCAN_INTERVAL=10 cycles.
    _v3_all_paths: list[str] = []
    try:
        from scp.autofix.ast_diff_cache import get_ast_diff_cache as _v3_get_cache
        _v3_cache = _v3_get_cache()
        # Collect candidate paths first (apply the same max_files limit).
        for path in _iter_python_files(_SCP_ROOT, limit=max_files):
            _v3_all_paths.append(str(path))
        _v3_partition = _v3_cache.partition_files(_v3_all_paths)
        _v3_scan_paths = _v3_partition.get("scan", [])
        _v3_cached_paths = _v3_partition.get("cached", [])
        logger.info(
            f"[R10 v3 IMP-13] partition: {len(_v3_scan_paths)} scan / "
            f"{len(_v3_cached_paths)} cached (total={len(_v3_all_paths)})"
        )
    except ImportError as _v3_ad_imp:
        logger.debug(f"[R10 v3 IMP-13] ast_diff_cache unavailable (fail-open): {_v3_ad_imp}")
        _v3_scan_paths = None  # sentinel: fall back to original loop
    except Exception as _v3_ad_err:
        logger.debug(f"[R10 v3 IMP-13] partition crash (fail-open): {_v3_ad_err}", exc_info=True)
        _v3_scan_paths = None

    # Helper to update cache after scan (fail-open).
    def _v3_update_cache(path_str: str, findings_count: int, syntax_error: bool = False) -> None:
        try:
            from scp.autofix.ast_diff_cache import get_ast_diff_cache as _v3_get_cache
            _v3_get_cache().update(path_str, findings_count, syntax_error=syntax_error)
        except Exception as exc:
            logger.debug(f"ast_scan_scp._v3_update_cache: exception ignored: {exc}", exc_info=True)
            pass  # silent-by-design: fail-open — cache update is best-effort

    # [R10 v3 WIRE — IMP-18] Parallel scanner dispatch (HOOK ACTIVATION).
    # TẠI SAO: scanning N files sequentially = N × (parse + visit) time. With
    # 8-core CPU, ProcessPoolExecutor fans out to 8 workers → ~8x speedup.
    #
    # [SCP-DNA-FIX R12-12] REAL parallel dispatch — không còn probe-call empty.
    # Tại sao: R10 claim "hook available" nhưng chỉ probe-call với empty inputs
    # (wiring-scan report: "probe-called with empty inputs"). R12-12 wire THẬT:
    # dùng ThreadPoolExecutor (không cần picklable — tránh Tier-3 refactor) để
    # chạy _scan_file song song trên N files. DNA #22 (PASS ≠ TRUE): probe ≠ wired.
    # ThreadPoolExecutor thay ProcessPoolExecutor vì:
    #   1. _scan_file dùng AST visitors (CPU-bound nhưng GIL释放 ở I/O)
    #   2. Tránh pickle requirement (AST objects không picklable)
    #   3. Simpler — không cần if __name__ == "__main__" guard
    # Trade-off: không 8x speedup (GIL), nhưng 2-3x trên I/O + parse. Đủ value.
    _v3_parallel_available = False
    try:
        from scp.autofix.parallel_scanner import run_scanners_parallel as _v3_rsp  # noqa: F401
        _v3_parallel_available = True
        logger.debug("[R10 v3 IMP-18] parallel_scanner module available")
    except ImportError as _v3_ps_imp:
        logger.debug(f"[R10 v3 IMP-18] parallel_scanner unavailable (sequential only): {_v3_ps_imp}")

    # R12-12: REAL parallel dispatch via ThreadPoolExecutor (bypass pickle issue)
    _v3_scan_paths = (
        _v3_scan_paths
        if _v3_scan_paths is not None
        else [str(p) for p in _iter_python_files(_SCP_ROOT, limit=max_files)]
    )

    if _v3_parallel_available and len(_v3_scan_paths) > 10:
        # Real parallel: ThreadPoolExecutor (threads avoid pickle requirement)
        import concurrent.futures as _cf
        _v3_max_workers = min(8, (os.cpu_count() or 4))
        # [SCP-DNA-FIX R12-20] Keep (path, finding) pairs — không flatten _v3_all_findings.
        # Tại sao: R12-12 (old) gán WRONG file path cho findings vì _fut biến loop
        # cuối cùng. ast_scan báo BareExceptPass ở predictive.py:421 nhưng thật ra
        # finding từ file khác (line 421 của predictive.py là 'continue' không phải except).
        # Fix: store (path, finding) tuples, gán đúng path khi build BugReport.
        _v3_all_findings: list[tuple[str, dict]] = []  # (path_str, finding)
        try:
            with _cf.ThreadPoolExecutor(max_workers=_v3_max_workers) as _pool:
                _v3_futures = {_pool.submit(_scan_file, Path(p)): p for p in _v3_scan_paths}
                for _fut in _cf.as_completed(_v3_futures):
                    _fut_path = _v3_futures.get(_fut, "")
                    try:
                        _fut_findings = _fut.result(timeout=30)
                        # Store (path, finding) pairs — not flat findings
                        for f in _fut_findings:
                            _v3_all_findings.append((_fut_path, f))
                    except Exception as _fut_err:
                        logger.debug(f" scan_file error for {_fut_path}: {_fut_err}", exc_info=True)
            # Merge parallel findings into bugs list (respecting max_bugs cap)
            for _finding_path, finding in _v3_all_findings:
                if len(bugs) >= max_bugs:
                    logger.info(f" parallel scan capped at {max_bugs} bugs (safety limit)")
                    return bugs
                bugs.append(_build_bug_report(_finding_path, finding))
            logger.info(
                f" parallel scan done: {len(_v3_scan_paths)} files, "
                f"{len(_v3_all_findings)} findings, {_v3_max_workers} threads"
            )
        except Exception as _parallel_err:
            logger.warning(f" parallel scan failed, falling back to sequential: {_parallel_err}", exc_info=True)
            _v3_parallel_available = False  # fall through to sequential

    if not _v3_parallel_available or len(_v3_scan_paths) <= 10:
        # Sequential scan loop (small file counts or parallel failed)
        for _v3_path_str in _v3_scan_paths:
            try:
                _v3_path = Path(_v3_path_str)
                findings = _scan_file(_v3_path)
            except Exception as e:
                logger.warning(f"[runner] scan failed for {_v3_path_str}: {e}", exc_info=True)
                _v3_update_cache(_v3_path_str, 0, syntax_error=True)
                continue
            for finding in findings:
                if len(bugs) >= max_bugs:
                    logger.info(
                        f"[runner] AST scan capped at {max_bugs} bugs "
                        f"(safety limit)"
                    )
                    return bugs
                bugs.append(_build_bug_report(str(_v3_path), finding))
            # Update cache: file scanned, record findings_count.
            _v3_update_cache(_v3_path_str, len(findings))

    # [SCP-DNA] Enterprise scanners are optional for bounded startup scans.
    # Full enterprise scan remains default for normal/background callers.
    if not include_enterprise:
        return bugs

    # [ENTERPRISE-V4] Wire 8 enterprise tools into AutoFix pipeline.
    # TÁI SAO: existing 2 scanners (BareExceptPass + UndefinedName) only detect
    # 2 bug types. Enterprise tools detect 427+ issues (292 S-series + 55 B +
    # 80 DUO). Without this wire, 13 SCP scanners + 8 enterprise tools exist
    # but never run automatically → dead code. This wire activates them.
    # DNA SCP #6 Evidence — each finding has tool + rule code + file:line.
    # DNA SCP #7 AutoFix safe — fail-open, doesn't break existing flow.
    try:
        from scp.autofix.enterprise_scanners import scan_scp_enterprise
        enterprise_bugs = scan_scp_enterprise(max_files=max_files)
        for bug in enterprise_bugs:
            if len(bugs) >= max_bugs:
                logger.info(
                    f"[runner] AST scan capped at {max_bugs} bugs "
                    f"(safety limit, enterprise portion)"
                )
                return bugs
            bugs.append(bug)
        logger.info(
            f"[runner] enterprise scan added {len(enterprise_bugs)} findings "
            f"(total: {len(bugs)})"
        )
    except ImportError as e:
        logger.debug(f"[runner] enterprise_scanners unavailable (fail-open): {e}")
    except Exception as e:
        logger.warning(f"[runner] enterprise scan error (fail-open): {e}", exc_info=True)

    return bugs


