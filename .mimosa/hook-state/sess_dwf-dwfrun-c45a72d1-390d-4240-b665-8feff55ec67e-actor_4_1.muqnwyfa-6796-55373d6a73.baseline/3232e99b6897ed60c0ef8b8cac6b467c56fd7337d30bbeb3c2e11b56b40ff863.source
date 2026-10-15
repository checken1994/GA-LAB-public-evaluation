"""Bounded, fail-closed mutation testing for SCP.

The engine deliberately runs a small deterministic campaign. It is not a
replacement for a full mutmut/cosmic-ray campaign; it is a CI tripwire that
proves selected tests fail when selected production semantics are changed.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Sequence


class MutationRunError(RuntimeError):
    """The campaign could not produce trustworthy mutation evidence."""


@dataclass(frozen=True)
class MutationCandidate:
    line: int
    operator: str
    source: str


@dataclass(frozen=True)
class MutationOutcome:
    line: int
    operator: str
    status: str
    duration_seconds: float
    return_code: int | None
    output_tail: str


@dataclass(frozen=True)
class MutationReport:
    target: str
    tests: list[str]
    functions: list[str]
    original_sha256: str
    baseline_duration_seconds: float
    outcomes: list[MutationOutcome]

    @property
    def killed(self) -> int:
        return sum(item.status in {"killed", "timeout_killed"} for item in self.outcomes)

    @property
    def survived(self) -> int:
        return sum(item.status == "survived" for item in self.outcomes)

    @property
    def score(self) -> float:
        if not self.outcomes:
            raise MutationRunError("mutation score is undefined without mutants")
        return self.killed / len(self.outcomes)

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "tests": self.tests,
            "functions": self.functions,
            "original_sha256": self.original_sha256,
            "baseline_duration_seconds": round(self.baseline_duration_seconds, 4),
            "mutants": len(self.outcomes),
            "killed": self.killed,
            "survived": self.survived,
            "score": round(self.score, 6),
            "outcomes": [asdict(item) for item in self.outcomes],
        }


class MutationVisitor(ast.NodeTransformer):
    """Apply exactly one mutation at a selected source line."""

    def __init__(self, target_line: int) -> None:
        self.target_line = target_line
        self.mutated = False
        self.operator = ""

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if self.mutated or getattr(node, "lineno", -1) != self.target_line:
            return node
        replacements: dict[type[ast.cmpop], type[ast.cmpop]] = {
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Lt: ast.LtE,
            ast.LtE: ast.Lt,
            ast.Gt: ast.GtE,
            ast.GtE: ast.Gt,
            ast.Is: ast.IsNot,
            ast.IsNot: ast.Is,
            ast.In: ast.NotIn,
            ast.NotIn: ast.In,
        }
        changed = False
        new_ops: list[ast.cmpop] = []
        labels: list[str] = []
        for current in node.ops:
            replacement = replacements.get(type(current))
            if replacement is None:
                new_ops.append(current)
                continue
            new_ops.append(replacement())
            labels.append(f"{type(current).__name__}->{replacement.__name__}")
            changed = True
        if changed:
            node.ops = new_ops
            self.mutated = True
            self.operator = ",".join(labels)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self.mutated or getattr(node, "lineno", -1) != self.target_line:
            return node
        if isinstance(node.value, bool):
            node.value = not node.value
            self.mutated = True
            self.operator = "bool_flip"
        elif isinstance(node.value, int):
            original = node.value
            node.value = original + 1
            self.mutated = True
            self.operator = f"int:{original}->{node.value}"
        return node


def _selected_lines(source: str, include_functions: Sequence[str] | None) -> set[int] | None:
    if not include_functions:
        return None
    tree = ast.parse(source)
    ranges: dict[str, set[int]] = {}

    class Collector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            qualified = ".".join([*self.scope, node.name])
            ranges[qualified] = set(range(node.lineno, (node.end_lineno or node.lineno) + 1))
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

    Collector().visit(tree)
    missing = sorted(set(include_functions) - ranges.keys())
    if missing:
        raise MutationRunError(f"selected functions not found: {', '.join(missing)}")
    selected: set[int] = set()
    for name in include_functions:
        selected.update(ranges[name])
    return selected


def generate_mutants(
    file_path: Path,
    *,
    max_mutants: int = 5,
    include_functions: Sequence[str] | None = None,
) -> list[MutationCandidate]:
    """Generate at most ``max_mutants`` deterministic single-line mutants."""
    if max_mutants <= 0:
        raise MutationRunError("max_mutants must be positive")
    source = file_path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        raise MutationRunError(f"cannot parse target {file_path}: {exc}") from exc

    allowed_lines = _selected_lines(source, include_functions)
    candidates: list[MutationCandidate] = []
    for line in range(1, len(source.splitlines()) + 1):
        if allowed_lines is not None and line not in allowed_lines:
            continue
        tree = ast.parse(source, filename=str(file_path))
        visitor = MutationVisitor(line)
        visitor.visit(tree)
        if not visitor.mutated:
            continue
        ast.fix_missing_locations(tree)
        candidates.append(
            MutationCandidate(line=line, operator=visitor.operator, source=ast.unparse(tree) + "\n")
        )
        if len(candidates) >= max_mutants:
            break
    if not candidates:
        raise MutationRunError(f"no supported mutation sites found in {file_path}")
    return candidates


def _invoke_generate_mutants(
    target_path: Path,
    *,
    max_mutants: int,
    include_functions: Sequence[str] | None,
) -> list[MutationCandidate]:
    """Call the generator without breaking legacy injected test doubles.

    Older callers monkeypatch ``generate_mutants(path)`` and may return simple
    ``(line, source)`` tuples. Supporting that shape keeps the public test seam
    stable while the real generator remains bounded and function-selective.
    """
    try:
        parameters = inspect.signature(generate_mutants).parameters
    except (TypeError, ValueError):
        parameters = {}
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    kwargs: dict[str, object] = {}
    if accepts_kwargs or "max_mutants" in parameters:
        kwargs["max_mutants"] = max_mutants
    if accepts_kwargs or "include_functions" in parameters:
        kwargs["include_functions"] = include_functions
    raw_candidates = generate_mutants(target_path, **kwargs)
    if not raw_candidates:
        raise MutationRunError(f"no supported mutants found in {target_path}")

    normalized: list[MutationCandidate] = []
    for candidate in raw_candidates:
        if isinstance(candidate, MutationCandidate):
            normalized.append(candidate)
            continue
        if isinstance(candidate, tuple) and len(candidate) == 2:
            line, source = candidate
            normalized.append(
                MutationCandidate(line=int(line), operator="legacy_injected", source=str(source))
            )
            continue
        raise MutationRunError(f"unsupported mutation candidate shape: {candidate!r}")
    return normalized


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _tail(output: str, limit: int = 1600) -> str:
    compact = output.replace("\x00", "")
    return compact[-limit:]


def _resolve_inside(root: Path, value: str | Path, *, kind: str) -> Path:
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise MutationRunError(f"{kind} must stay inside repository root: {path}") from exc
    if not path.is_file():
        raise MutationRunError(f"{kind} does not exist: {path}")
    return path


@contextmanager
def _campaign_lock(repo_root: Path) -> Iterator[None]:
    digest = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"scp-mutation-{digest}.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        owner = lock_path.read_text(encoding="utf-8", errors="replace").strip()
        raise MutationRunError(f"another mutation campaign holds {lock_path} ({owner})") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()} root={repo_root}".encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _run_pytest(
    repo_root: Path,
    tests: Sequence[Path],
    *,
    timeout_seconds: float,
    temp_root: Path,
) -> tuple[int, float, str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        f"--basetemp={temp_root}",
        *[str(path.relative_to(repo_root)) for path in tests],
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )
    duration = time.perf_counter() - started
    output = _text(completed.stdout) + _text(completed.stderr)
    return completed.returncode, duration, output


def run_mutation_campaign(
    target: str | Path,
    tests: Sequence[str | Path],
    *,
    repo_root: str | Path = ".",
    max_mutants: int = 5,
    timeout_seconds: float = 120.0,
    include_functions: Sequence[str] | None = None,
) -> MutationReport:
    """Run a baseline and a bounded mutation campaign.

    Return code 1 from pytest means a mutant was killed by an assertion. Pytest
    usage/collection/internal errors (codes 2+) invalidate the campaign. A
    timeout after a successful baseline counts as a killed mutant and is
    reported separately.
    """
    root = Path(repo_root).resolve()
    if timeout_seconds <= 0:
        raise MutationRunError("timeout_seconds must be positive")
    target_path = _resolve_inside(root, target, kind="target")
    if target_path.suffix != ".py":
        raise MutationRunError(f"target must be Python source: {target_path}")
    if not tests:
        raise MutationRunError("at least one explicit test path is required")
    test_paths = [_resolve_inside(root, item, kind="test") for item in tests]
    original_bytes = target_path.read_bytes()
    original_sha = _sha256(original_bytes)
    candidates = _invoke_generate_mutants(
        target_path,
        max_mutants=max_mutants,
        include_functions=include_functions,
    )

    with _campaign_lock(root), tempfile.TemporaryDirectory(prefix="scp-mutation-pytest-") as temp:
        temp_path = Path(temp)
        baseline_code, baseline_duration, baseline_output = _run_pytest(
            root,
            test_paths,
            timeout_seconds=timeout_seconds,
            temp_root=temp_path / "baseline",
        )
        if baseline_code != 0:
            raise MutationRunError(
                f"baseline tests failed with pytest code {baseline_code}: {_tail(baseline_output)}"
            )

        outcomes: list[MutationOutcome] = []
        for index, candidate in enumerate(candidates, start=1):
            if _sha256(target_path.read_bytes()) != original_sha:
                raise MutationRunError("target changed before mutation; refusing to overwrite it")
            mutated_bytes = candidate.source.encode("utf-8")
            target_path.write_bytes(mutated_bytes)
            started = time.perf_counter()
            try:
                try:
                    return_code, duration, output = _run_pytest(
                        root,
                        test_paths,
                        timeout_seconds=timeout_seconds,
                        temp_root=temp_path / f"mutant-{index}",
                    )
                except subprocess.TimeoutExpired as exc:
                    duration = time.perf_counter() - started
                    output = json.dumps({"timeout_seconds": timeout_seconds, "error": str(exc)})
                    outcomes.append(
                        MutationOutcome(
                            line=candidate.line,
                            operator=candidate.operator,
                            status="timeout_killed",
                            duration_seconds=round(duration, 4),
                            return_code=None,
                            output_tail=_tail(output),
                        )
                    )
                    continue

                if return_code == 0:
                    status = "survived"
                elif return_code == 1:
                    status = "killed"
                else:
                    raise MutationRunError(
                        f"mutant at line {candidate.line} produced pytest infrastructure/collection "
                        f"code {return_code}: {_tail(output)}"
                    )
                outcomes.append(
                    MutationOutcome(
                        line=candidate.line,
                        operator=candidate.operator,
                        status=status,
                        duration_seconds=round(duration, 4),
                        return_code=return_code,
                        output_tail=_tail(output),
                    )
                )
            finally:
                current = target_path.read_bytes()
                if current == mutated_bytes:
                    target_path.write_bytes(original_bytes)
                elif _sha256(current) != original_sha:
                    raise MutationRunError(
                        "target changed concurrently during a mutant; external content was left untouched"
                    )

        if _sha256(target_path.read_bytes()) != original_sha:
            raise MutationRunError("source restoration hash mismatch")

    return MutationReport(
        target=str(target_path.relative_to(root)).replace("\\", "/"),
        tests=[str(path.relative_to(root)).replace("\\", "/") for path in test_paths],
        functions=list(include_functions or []),
        original_sha256=original_sha,
        baseline_duration_seconds=baseline_duration,
        outcomes=outcomes,
    )


def run_mutation_tests(file_path_rel: str, test_file_path: str | None = None) -> float:
    """Compatibility wrapper used by the older test factory.

    Invalid targets and broken verification infrastructure raise instead of
    silently manufacturing a score. This keeps the compatibility entry point
    fail closed while the successful-path return type remains ``float``.
    """
    if not test_file_path:
        raise ValueError("explicit test_file_path is required")

    target = Path(file_path_rel)
    target_path = target.resolve() if target.is_absolute() else (Path.cwd() / target).resolve()
    if not target_path.is_file():
        raise FileNotFoundError(file_path_rel)
    if target_path.suffix != ".py":
        raise ValueError(f"target must be Python source: {target_path}")

    report = run_mutation_campaign(file_path_rel, [test_file_path])
    print(
        f"[MutationEngine] {report.target}: {report.score:.1%} "
        f"({report.killed}/{len(report.outcomes)} killed)"
    )
    return report.score
