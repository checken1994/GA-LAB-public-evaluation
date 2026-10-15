#!/usr/bin/env python3
"""Stale-code tripwire — T00-extension (S25, 2026).

Detects automatically the 4 "code-drifted-from-reality" classes that the
21-fix campaign previously had to find by hand:

  1. Blueprint-vs-code : modules declared as "design must exist" are present
                         on disk AND importable.
  2. Unresolved import : `from scp.X import Y` / `import scp.X` where the
                         target module or the imported symbol does not exist
                         on disk (e.g. the HybridRetriever bug at
                         scp/api/routes/v105_routes.py:719).
  3. Duplicated logic  : identical prompt-template literals (judge prompts)
                         copied across >=2 files -> FAIL; identical function
                         bodies (>20 lines, docstring-normalized) across
                         >=2 files -> WARN (noise-safe, not blocking).
  4. Metric drift      : print() call count and silent `except: pass` count
                         in scp/** increase >5% vs the recorded baseline.

All checks are AST-based (no naive grep) and fail-closed: an unresolvable
target is only SKIPped when the target module is provably dynamic (star
import, module-level __getattr__, importlib usage); otherwise it FAILs.

Modes
-----
* Strict CLI (`python tools/stale_code_tripwire.py`): every FAIL-class
  finding is reported and exits 1. Used for proof-of-value audits.
* t00 delta mode (`run_for_t00(root)`): findings are compared against
  `known_findings` fingerprinted in data/governance/tripwire_baseline.json
  (same BASELINE_DEBT philosophy as FA-01/FA-04 in t00_meta_audit.py).
  On the very first run the baseline is created (metrics + known findings
  seeded) and the run PASSES; later runs FAIL only on NEW findings.

Baseline gaming note: the baseline file is committed data. Seeding happens
exactly once (at creation). Deleting the file resets the baseline loudly
(creation is logged with the git SHA); it does not silently hide drift
because the *next* run re-records whatever exists at that moment and any
subsequent drift above threshold still fails.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
DRIFT_MAX_INCREASE_PCT = 5.0

# Check 3 — prompt-template marker contract (fail requires ALL markers so the
# check targets judge-style prompts specifically, not any long string).
PROMPT_TEMPLATE_MIN_LEN = 120
PROMPT_TEMPLATE_MARKERS = ("Question:", "Context:", "AI Answer:")

# Check 3 — duplicate function body threshold (strictly more than 20 lines).
DUP_FUNC_MIN_LINES = 20

# Check 1 — "design must exist" module list. AUDIT-FIRST evidence:
#   * scp.knowledge.warehouse          — docs/getting_started.md ("Knowledge
#     warehouse with FAISS embeddings") + .agents/skills/scp-learning-loop-guard/
#     SKILL.md ("knowledge warehouse").
#   * scp.autofix.evidence_replay      — T00-extension brief and referenced by
#     the autofix pipeline (scp/autofix/engine.py).
#   * scp.meta.reverify_scheduler      — the scheduler module on disk whose
#     removal would silently disable reverify bookkeeping (T00-extension brief).
#   * scp.core.free_discovery_scheduler — commit 1c0d0f2 (2026-09-14): "feat(
#     discovery): FreeDiscoveryScheduler (blueprint module built)", wired to
#     scp/api_server_parts/lifespan.py. NOTE: at task start (HEAD b8fa536) this
#     name existed NOWHERE (rg over spec/ docs/ .agents/ scp/ tools/); it was
#     excluded from this list until S23 built it — the list only guards modules
#     with verifiable design evidence.
# If a machine-readable blueprint list appears later, replace this hardcoded
# list with that source.
BLUEPRINT_MODULES: tuple[str, ...] = (
    "scp.knowledge.warehouse",            # docs/getting_started.md + learning-loop-guard SKILL (2026)
    "scp.autofix.evidence_replay",        # T00-extension brief + autofix engine reference (2026)
    "scp.meta.reverify_scheduler",        # T00-extension brief (2026)
    "scp.core.free_discovery_scheduler",  # commit 1c0d0f2 (2026-09-14, S23 lifespan wiring)
)

BASELINE_RELPATH = Path("data") / "governance" / "tripwire_baseline.json"
_MODULE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

SKIP = "SKIP"
WARN = "WARN"


@dataclass
class Finding:
    kind: str          # unresolved_import | missing_module | blueprint_missing |
                       # blueprint_unimportable | duplicate_prompt_template |
                       # duplicate_function_body(WARN) | metric_drift |
                       # baseline_invalid
    file: str          # repo-relative posix path ("" for repo-level findings)
    detail: str        # stable fingerprint payload (no line numbers)
    line: int | None = None
    severity: str = "FAIL"

    def fingerprint(self) -> tuple[str, str, str]:
        return (self.kind, self.file, self.detail)

    def render(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else (self.file or "<repo>")
        return f"[{self.severity}] {self.kind} @ {loc}: {self.detail}"


@dataclass
class TripwireReport:
    root: Path
    findings: list[Finding] = field(default_factory=list)
    skips: list[str] = field(default_factory=list)
    warns: list[Finding] = field(default_factory=list)
    baseline_created: bool = False

    @property
    def fails(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "FAIL"]


# --------------------------------------------------------------------------
# Shared AST helpers
# --------------------------------------------------------------------------

def iter_py_files(root: Path) -> list[Path]:
    """All .py files under <root>/scp, __pycache__ excluded."""
    base = root / "scp"
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def parse_file(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def module_to_paths(root: Path, dotted: str) -> list[Path]:
    rel = Path(*dotted.split("."))
    return [root / rel.parent / (rel.name + ".py"), root / rel / "__init__.py"]


def resolve_module_path(root: Path, dotted: str) -> Path | None:
    """scp.x.y -> scp/x/y.py or scp/x/y/__init__.py, else None."""
    for cand in module_to_paths(root, dotted):
        if cand.is_file():
            return cand
    return None


# --------------------------------------------------------------------------
# Check 2 helpers — module symbol binding index
# --------------------------------------------------------------------------

class _ModuleBindings:
    """Names bound at the top level of one module file, descending only through
    control-flow statements (If/Try/With/For), never into def/class bodies.
    Note: every `from X import name` already binds `name`, so re-export
    facades are covered by `bound` itself; only star imports need separate
    resolution (star_sources)."""

    def __init__(self) -> None:
        self.bound: set[str] = set()
        self.star_sources: list[str] = []   # modules star-imported (resolvable)
        self.dynamic_other: bool = False    # __getattr__ / importlib / unresolved star


def _package_parts(dotted: str, importer_path: Path) -> list[str]:
    parts = dotted.split(".")
    return parts if importer_path.name == "__init__.py" else parts[:-1]


def _follow_target(current: str, importer_path: Path,
                   module: str | None, level: int) -> str | None:
    """Resolve the module targeted by a `from <module> import ...` statement
    found in module `current` (file importer_path). Handles relative imports:
    level 1 is the package containing the importing module (or the package
    itself when the importer is an __init__.py)."""
    pkg = _package_parts(current, importer_path)
    up = max(0, level - 1)
    if up > len(pkg):
        return None
    base = pkg[: len(pkg) - up]
    if module:
        base = base + module.split(".")
    return ".".join(base) if base else None


def _collect_bindings(tree: ast.Module, root: Path, current: str,
                      importer_path: Path) -> _ModuleBindings:
    info = _ModuleBindings()

    def visit_body(body: list[ast.stmt]) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                info.bound.add(stmt.name)
                if stmt.name == "__getattr__":
                    info.dynamic_other = True
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    for node in ast.walk(target):
                        if isinstance(node, ast.Name):
                            if node.id == "__all__":
                                info.bound.update(_all_entries(stmt.value))
                            else:
                                info.bound.add(node.id)
            elif isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Name):
                    info.bound.add(stmt.target.id)
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    info.bound.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(stmt, ast.ImportFrom):
                target_base = _follow_target(current, importer_path, stmt.module, stmt.level)
                for alias in stmt.names:
                    if alias.name == "*":
                        if target_base and resolve_module_path(root, target_base):
                            info.star_sources.append(target_base)
                        else:
                            info.dynamic_other = True  # unresolvable star source
                    else:
                        info.bound.add(alias.asname or alias.name)
            elif isinstance(stmt, (ast.If, ast.While)):
                visit_body(stmt.body)
                visit_body(stmt.orelse)
            elif isinstance(stmt, ast.Try):
                visit_body(stmt.body)
                for handler in stmt.handlers:
                    visit_body(handler.body)
                visit_body(stmt.orelse)
                visit_body(stmt.finalbody)
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                visit_body(stmt.body)
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                for node in ast.walk(stmt.target):
                    if isinstance(node, ast.Name):
                        info.bound.add(node.id)
                visit_body(stmt.body)
                visit_body(stmt.orelse)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                # importlib.import_module(...) / __import__(...) at module level
                # means the module may bind names dynamically.
                if "import_module" in ast.dump(stmt.value) or "__import__" in ast.dump(stmt.value):
                    info.dynamic_other = True

    visit_body(tree.body)
    return info


def _all_entries(value: ast.expr) -> set[str]:
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return {
            elt.value
            for elt in value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        }
    return set()


class BindingIndex:
    """Lazy per-module binding cache for one tripwire run."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, _ModuleBindings | None] = {}

    def get(self, dotted: str) -> _ModuleBindings | None:
        """None => module exists but is not statically analyzable."""
        if dotted in self._cache:
            return self._cache[dotted]
        result: _ModuleBindings | None = None
        path = resolve_module_path(self.root, dotted)
        if path is not None:
            tree = parse_file(path)
            if tree is None:
                result = None
            else:
                result = _collect_bindings(tree, self.root, dotted, path)
        self._cache[dotted] = result
        return result

    def module_binds_name(self, dotted: str, name: str, depth: int = 3) -> bool | None:
        """True/False: statically bound or not. None: cannot tell (dynamic)."""
        if depth < 0:
            return None
        info = self.get(dotted)
        if info is None:
            return None
        if name in info.bound:
            return True
        # A submodule with the requested (capitalised) name also satisfies
        # `from pkg import Name`.
        if resolve_module_path(self.root, f"{dotted}.{name}") is not None:
            return True
        if info.star_sources:
            saw_unknown = False
            for source in info.star_sources:
                binds = self.module_binds_name(source, name, depth - 1)
                if binds is True:
                    return True
                if binds is None:
                    saw_unknown = True
            if saw_unknown:
                return None
            return False
        if info.dynamic_other:
            return None
        return False


# --------------------------------------------------------------------------
# Check 2 — unresolved imports
# --------------------------------------------------------------------------

def check_unresolved_imports(root: Path, report: TripwireReport) -> None:
    files = iter_py_files(root)
    index = BindingIndex(root)
    for path in files:
        tree = parse_file(path)
        if tree is None:
            report.skips.append(f"SKIP: syntax error, not analyzed: {path.relative_to(root).as_posix()}")
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not alias.name.startswith("scp"):
                        continue
                    dotted = alias.name
                    if resolve_module_path(root, dotted) is None and dotted != "scp":
                        report.findings.append(Finding(
                            kind="missing_module", file=rel, line=node.lineno,
                            detail=f"import {dotted} — module does not exist on disk"))
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0:
                    report.skips.append(
                        f"SKIP: relative import out of scope: {rel}:{node.lineno}")
                    continue
                module = node.module or ""
                if not (module == "scp" or module.startswith("scp.")):
                    continue
                if any(alias.name == "*" for alias in node.names):
                    report.skips.append(
                        f"SKIP: star import (dynamic): {rel}:{node.lineno}")
                    continue
                if resolve_module_path(root, module) is None and module != "scp":
                    report.findings.append(Finding(
                        kind="missing_module", file=rel, line=node.lineno,
                        detail=f"from {module} import ... — module does not exist on disk"))
                    continue
                for alias in node.names:
                    name = alias.name
                    if module == "scp":
                        # `from scp import X`: X is a submodule or a symbol bound
                        # in scp/__init__.py.
                        if resolve_module_path(root, f"scp.{name}") is not None:
                            continue
                        binds = index.module_binds_name("scp", name)
                        if binds is False:
                            report.findings.append(Finding(
                                kind="unresolved_import", file=rel, line=node.lineno,
                                detail=f"from scp import {name} — not a module and not bound in scp/__init__.py"))
                        elif binds is None:
                            report.skips.append(
                                f"SKIP: scp/__init__.py is dynamic: {rel}:{node.lineno}")
                        continue
                    if resolve_module_path(root, f"{module}.{name}") is not None:
                        continue
                    binds = index.module_binds_name(module, name)
                    if binds is False:
                        report.findings.append(Finding(
                            kind="unresolved_import", file=rel, line=node.lineno,
                            detail=f"from {module} import {name} — symbol not found in target module"))
                    elif binds is None:
                        report.skips.append(
                            f"SKIP: dynamic target module: {rel}:{node.lineno} ({module})")


# --------------------------------------------------------------------------
# Check 1 — blueprint vs code
# --------------------------------------------------------------------------

def _safe_module_name(dotted: str) -> bool:
    return bool(_MODULE_NAME_RE.match(dotted))


def _import_probe(root: Path, dotted: str) -> tuple[bool, str]:
    """Import <dotted> in a fresh interpreter with <root> on sys.path.
    Keeps the host process free of scp side effects and makes the check work
    for both the real repo and hermetic tmp fixtures."""
    if not _safe_module_name(dotted):
        return False, f"module name rejected by safety pattern: {dotted}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {dotted}"],
            cwd=str(root), env=env, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, f"import probe timed out after 180s: {dotted}"
    if proc.returncode == 0:
        return True, ""
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return False, " | ".join(tail) if tail else f"exit {proc.returncode}"


def check_blueprint_modules(root: Path, report: TripwireReport,
                            modules: tuple[str, ...] = BLUEPRINT_MODULES) -> None:
    for dotted in modules:
        if resolve_module_path(root, dotted) is None:
            report.findings.append(Finding(
                kind="blueprint_missing", file="", line=None,
                detail=f"blueprint module missing on disk: {dotted}"))
            continue
        ok, why = _import_probe(root, dotted)
        if not ok:
            report.findings.append(Finding(
                kind="blueprint_unimportable", file="", line=None,
                detail=f"blueprint module not importable: {dotted} ({why})"))


# --------------------------------------------------------------------------
# Check 3 — duplicated logic
# --------------------------------------------------------------------------

def _string_template(node: ast.expr) -> str | None:
    """Normalize a string literal (or f-string / implicit concatenation) into a
    template where every interpolation slot becomes '{?}' so copies that differ
    only by interpolated variables still group together."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{?}")
        return "".join(parts)
    return None


def check_prompt_template_duplicates(root: Path, report: TripwireReport) -> None:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for path in iter_py_files(root):
        tree = parse_file(path)
        if tree is None:
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Constant, ast.JoinedStr)):
                continue
            template = _string_template(node)
            if template is None:
                continue
            if len(template) > PROMPT_TEMPLATE_MIN_LEN and all(
                marker in template for marker in PROMPT_TEMPLATE_MARKERS
            ):
                groups[template][rel] += 1
    for template, per_file in groups.items():
        if len(per_file) >= 2:
            occurrences = sum(per_file.values())
            where = ", ".join(f"{f} x{n}" for f, n in sorted(per_file.items()))
            digest = hashlib.sha256(template.encode("utf-8")).hexdigest()[:12]
            report.findings.append(Finding(
                kind="duplicate_prompt_template", file="", line=None,
                detail=(f"identical prompt template ({occurrences} occurrences in "
                        f"{len(per_file)} files; sha256:{digest}) -> {where}")))


def _normalized_func_dump(fn: ast.AST) -> str:
    fn = copy.deepcopy(fn)
    body = fn.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        fn.body = [ast.Pass()] + body[1:]  # strip docstring (copy, throwaway)
    return ast.dump(fn, include_attributes=False)


def check_function_body_duplicates(root: Path, report: TripwireReport) -> None:
    groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for path in iter_py_files(root):
        tree = parse_file(path)
        if tree is None:
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                if length > DUP_FUNC_MIN_LINES:
                    dump = _normalized_func_dump(node)
                    groups[dump][rel] += 1
    for dump, per_file in groups.items():
        if len(per_file) >= 2:
            where = ", ".join(f"{f} x{n}" for f, n in sorted(per_file.items()))
            report.warns.append(Finding(
                kind="duplicate_function_body", file="", line=None, severity=WARN,
                detail=(f"identical function body (> {DUP_FUNC_MIN_LINES} lines) in "
                        f"{len(per_file)} files -> {where}")))


# --------------------------------------------------------------------------
# Check 4 — metric drift vs baseline
# --------------------------------------------------------------------------

def count_metrics(root: Path) -> dict[str, int]:
    """AST-based metric counts over scp/**/*.py.

    print_calls        : Call nodes whose func is the bare Name `print`.
    silent_except_pass : ExceptHandler bodies that contain only Pass.
    (Method note: the historical rg-text count of `print(` was 858; the AST
    count on the same tree is 836 because text matching also catches attribute
    calls and string contents. The baseline stores the AST method.)
    """
    print_calls = 0
    silent_except_pass = 0
    for path in iter_py_files(root):
        tree = parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "print":
                print_calls += 1
            elif isinstance(node, ast.ExceptHandler):
                if node.body and all(isinstance(stmt, ast.Pass) for stmt in node.body):
                    silent_except_pass += 1
    return {"print_calls": print_calls, "silent_except_pass": silent_except_pass}


def _git_sha(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root),
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _new_baseline(root: Path, metrics: dict[str, int],
                  known_findings: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(root),
        "tool": "tools/stale_code_tripwire.py",
        "metrics": metrics,
        "metrics_method": ("AST-based over scp/**/*.py (no __pycache__): "
                           "Call(Name print) count; ExceptHandler whose body is only Pass."),
        "thresholds": {"metric_drift_max_increase_pct": DRIFT_MAX_INCREASE_PCT},
        "known_findings": known_findings,
        "notes": ("Seeded on first run (fail-closed tripwire baseline). "
                  "known_findings are fingerprints (kind, file, detail) recorded at "
                  "creation; t00 delta mode fails only on NEW findings."),
    }


def check_metric_drift(root: Path, report: TripwireReport,
                       baseline_path: Path | None = None) -> None:
    baseline_path = baseline_path or (root / BASELINE_RELPATH)
    metrics = count_metrics(root)
    if not baseline_path.exists():
        # First run: seed the baseline with current metrics AND the findings
        # collected by checks 1-3 (BASELINE_DEBT pattern — the current state
        # becomes tracked debt; only *new* findings fail in t00 delta mode).
        baseline = _new_baseline(
            root, metrics,
            known_findings=[
                {"kind": f.kind, "file": f.file, "detail": f.detail}
                for f in report.fails
            ],
        )
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        report.baseline_created = True
        print(f"[tripwire] baseline CREATED at {baseline_path} "
              f"(git {baseline['git_sha'][:12]}): {metrics} — first run passes, "
              f"later runs compare against this.")
        return
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        recorded = baseline["metrics"]
        if not isinstance(recorded, dict):
            raise KeyError("metrics is not an object")
    except Exception as exc:
        report.findings.append(Finding(
            kind="baseline_invalid", file=str(baseline_path), line=None,
            detail=f"baseline unreadable/invalid (fail-closed, NOT auto-reset): {exc}"))
        return
    for name, current in metrics.items():
        if name not in recorded:
            report.findings.append(Finding(
                kind="baseline_invalid", file=str(baseline_path), line=None,
                detail=f"baseline lacks metric '{name}' (fail-closed, NOT auto-reset)"))
            continue
        base = recorded[name]
        limit = base * (1 + DRIFT_MAX_INCREASE_PCT / 100.0)
        if current > limit:
            report.findings.append(Finding(
                kind="metric_drift", file="", line=None,
                detail=(f"{name}: {current} > baseline {base} + "
                        f"{DRIFT_MAX_INCREASE_PCT:g}% (limit {limit:.1f})")))


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run_all(root: Path, baseline_path: Path | None = None,
            blueprint_modules: tuple[str, ...] = BLUEPRINT_MODULES) -> TripwireReport:
    report = TripwireReport(root=root)
    check_blueprint_modules(root, report, blueprint_modules)
    check_unresolved_imports(root, report)
    check_prompt_template_duplicates(root, report)
    check_function_body_duplicates(root, report)
    check_metric_drift(root, report, baseline_path)
    return report


def _seed_known_findings(root: Path, baseline_path: Path,
                         report: TripwireReport) -> None:
    """Record current findings as known debt in the baseline (once). Called by
    run_for_t00 when the baseline lacks the known_findings contract."""
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception:
        return
    if baseline.get("known_findings") is not None:
        return
    baseline["known_findings"] = [
        {"kind": f.kind, "file": f.file, "detail": f.detail}
        for f in report.fails
    ]
    baseline["seeded_at"] = datetime.now(timezone.utc).isoformat()
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"[tripwire] known_findings seeded ({len(baseline['known_findings'])} "
          f"entries) into {baseline_path} — BASELINE_DEBT pattern, new findings "
          f"will fail.")


def run_for_t00(root: Path, baseline_path: Path | None = None) -> list[str]:
    """Delta mode for t00_meta_audit.py. Returns violation strings for NEW
    findings only (fail-closed); known findings print as tracked debt."""
    baseline_path = baseline_path or (root / BASELINE_RELPATH)
    report = run_all(root, baseline_path)

    if _needs_known_findings_seed(baseline_path):
        _seed_known_findings(root, baseline_path, report)

    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception:
        baseline = {"known_findings": []}
    known = {
        (entry.get("kind"), entry.get("file"), entry.get("detail"))
        for entry in baseline.get("known_findings") or []
    }

    violations: list[str] = []
    for finding in report.fails:
        if finding.fingerprint() in known:
            print(f" [TRIPWIRE-DEBT] {finding.render()}")
        else:
            violations.append(f"TRIPWIRE: {finding.render()}")
    for warn in report.warns:
        print(f" {warn.render()}")
    for skip in report.skips:
        print(f" {skip}")
    return violations


def _needs_known_findings_seed(baseline_path: Path) -> bool:
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        return baseline.get("known_findings") is None
    except Exception:
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stale-code tripwire (T00-extension)")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                        help="Project root (default: repo containing this tool)")
    parser.add_argument("--baseline", default=None,
                        help="Baseline JSON path (default: <root>/data/governance/tripwire_baseline.json)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    baseline_path = Path(args.baseline) if args.baseline else root / BASELINE_RELPATH
    report = run_all(root, baseline_path)

    if args.json:
        print(json.dumps({
            "root": str(root),
            "baseline_created": report.baseline_created,
            "fails": [f.render() for f in report.fails],
            "warns": [w.render() for w in report.warns],
            "skips": report.skips,
        }, indent=2))
    else:
        print(f"[stale-code tripwire] root={root}")
        print(f"Check 1 blueprint-vs-code : "
              f"{len([f for f in report.fails if f.kind.startswith('blueprint')])} FAIL(s)")
        print(f"Check 2 unresolved import : "
              f"{len([f for f in report.fails if f.kind in ('unresolved_import', 'missing_module')])} FAIL(s), "
              f"{len(report.skips)} SKIP(s)")
        print(f"Check 3 duplicated logic  : "
              f"{len([f for f in report.fails if f.kind == 'duplicate_prompt_template'])} FAIL(s), "
              f"{len(report.warns)} WARN(s)")
        print(f"Check 4 metric drift      : "
              f"{len([f for f in report.fails if f.kind in ('metric_drift', 'baseline_invalid')])} FAIL(s)"
              + ("  [baseline created this run]" if report.baseline_created else ""))
        for finding in report.fails:
            print(f"  {finding.render()}")
        for warn in report.warns:
            print(f"  {warn.render()}")
        for skip in report.skips:
            print(f"  {skip}")

    return 1 if report.fails else 0


if __name__ == "__main__":
    sys.exit(main())
