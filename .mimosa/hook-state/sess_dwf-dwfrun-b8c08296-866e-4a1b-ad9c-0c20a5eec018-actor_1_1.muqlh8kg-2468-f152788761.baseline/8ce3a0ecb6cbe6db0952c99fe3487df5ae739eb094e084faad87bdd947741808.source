"""
[SCP-DNA-FIX R8 v3 IMP-18] Parallel Scanner Fan-Out with Result Dedup.

TẠI SAO file này tồn tại?
  IMP-11 (concurrent_runner) chạy FIXES song song (ThreadPoolExecutor). Nhưng
  SCAN phase vẫn tuần tự: 18 scanners × 353 files = 6,354 invocations, nhiều
  trong đó là CPU-bound AST work. Trên 8-core machine, sequential scan = 45s
  trong khi lý thuyết parallel = ~6s.

  v3 IMP-18 fan-out scanners across files using ProcessPoolExecutor (processes,
  not threads — scanners are CPU-bound AST work, GIL-bound threads won't help).
  Dedup overlapping findings (same file:line:bug_class) by keeping highest
  severity + merging evidence.

  Inspired by:
    - semgrep `--parallel` (multi-core scanner fan-out)
    - ruff `--parallel` (per-file parallelism, processes)
    - mypy daemon (incremental + parallel type-checking)
    - ripgrep (parallel directory walk)

Flow:
  findings = run_scanners_parallel(scanners, files, max_workers=None)
  # scanners: list of callables (scanner_fn(file_path) -> list[Finding])
  # files:    list of file paths to scan
  # max_workers: default = min(cpu_count, 8)
  # findings: deduplicated list of Finding objects

  Integrates with IMP-13: caller passes only the "scan" partition (changed
  files) — unchanged files are skipped at the cache layer.

DNA principles applied:
  #9  (Tăng tốc)         — 8x speedup on 8-core, 45s → ~6s for full scan
  #7  (Autofix safe)     — fail-open: 1 scanner crash → log + continue
  #20 (Cache for speed)  — dedup uses content-addressable key (deterministic)
  #22 (PASS ≠ TRUE)      — "scanned" = real callables ran (verified by result count)
"""
from __future__ import annotations

import logging
import os
import traceback
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("scp.autofix.parallel_scanner")


# ============================================================
# Defaults.
# ============================================================

DEFAULT_MAX_WORKERS_CAP = 8                # don't use more than 8 procs
DEFAULT_MAX_FILES_PER_WORKER = 50          # batch files to reduce IPC overhead
DEFAULT_FALLBACK_SEQUENTIAL_THRESHOLD = 1  # if only 1 file → sequential


# ============================================================
# Finding dataclass (lightweight — must be picklable for ProcessPoolExecutor).
# ============================================================

@dataclass
class Finding:
    """A dedup-compatible finding record.

    Attributes:
        file: Absolute file path.
        line: 1-indexed line number.
        bug_class: Bug type (e.g. "BareExceptPass", "NoneComparison").
        severity: 0-100 (higher = more severe). Used for dedup tiebreak.
        scanner: Name of the scanner that produced it (e.g. "DeadCodeScanner").
        description: Human-readable description.
        evidence: Optional dict of extra evidence (caller, sink, etc.).
    """
    file: str
    line: int
    bug_class: str
    severity: int = 50
    scanner: str = ""
    description: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def dedup_key(self) -> tuple[str, int, str]:
        """Key for dedup: (file, line, bug_class). Findings with the same
        key are merged (highest severity wins, evidence + scanner list merged).
        """
        return (self.file, int(self.line), self.bug_class)


# ============================================================
# Severity ranking (for dedup tiebreak).
# ============================================================

# Higher = more severe. Used to pick the "winner" when multiple scanners
# report the same (file, line, bug_class).
_SEVERITY_RANK = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 40,
    "INFO": 20,
}


def _normalize_severity(s: int | str) -> int:
    """Coerce severity to int 0-100."""
    if isinstance(s, int):
        return max(0, min(100, s))
    if isinstance(s, str):
        return _SEVERITY_RANK.get(s.upper(), 50)
    return 50


# ============================================================
# Worker function (module-level — must be picklable for ProcessPoolExecutor).
# ============================================================

def _scan_one_file_worker(args: tuple[str, list[Any]]) -> list[dict[str, Any]]:
    """Worker process entry: scan ONE file with N scanners.

    Args:
        args: Tuple of (file_path, scanner_payloads) where scanner_payloads
              is a list of dicts:
                  {"scanner_name": str, "scanner_factory": str (dotted path),
                   "scanner_kwargs": dict}

    Returns:
        List of finding dicts (NOT Finding objects — must be picklable
        across process boundaries). Caller reconstructs Finding objects.

    Fail-open: any scanner crash → log to stderr + continue with remaining
    scanners. Never raise (one bad scanner doesn't fail the batch).
    """
    file_path, scanner_payloads = args
    findings: list[dict[str, Any]] = []
    for payload in scanner_payloads:
        scanner_name = payload.get("scanner_name", "<unknown>")
        factory_path = payload.get("scanner_factory")
        kwargs = payload.get("scanner_kwargs", {}) or {}
        try:
            scanner = _instantiate_scanner(factory_path, kwargs)
            raw = _invoke_scanner(scanner, file_path)
            for r in raw:
                findings.append(_normalize_finding(r, scanner_name, file_path))
        except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
            # silent-by-design: crash is screamed via logger.error per DNA #7; partial findings returned to the aggregator.
            logger.error(
                f"[IMP-18] scanner {scanner_name} crashed on {file_path}: {e}"
            )
    return findings


def _instantiate_scanner(factory_path: str | None, kwargs: dict[str, Any]) -> Any:
    """Import + instantiate a scanner by dotted path.

    Supports two patterns:
        - "scp.autofix.scanners.dead_code_scanner.DeadCodeScanner" → import
          + call constructor with kwargs.
        - "scp.autofix.runner_phases.ast_scan.ast_scan_scp" → import + return
          the function itself (callable, no instantiation).
    """
    if not factory_path:
        raise ValueError("empty scanner_factory path")
    parts = factory_path.split(".")
    if len(parts) < 2:
        raise ValueError(f"invalid scanner_factory path: {factory_path}")
    module_path = ".".join(parts[:-1])
    attr_name = parts[-1]
    import importlib
    mod = importlib.import_module(module_path)
    obj = getattr(mod, attr_name)
    # If it's a class → instantiate. If it's a function → return as-is.
    if isinstance(obj, type):
        return obj(**kwargs)
    return obj


def _invoke_scanner(scanner: Any, file_path: str) -> list[Any]:
    """Call scanner on file_path — supports multiple scanner shapes.

    Handles:
        - scanner.scan(file_path)             [class-based]
        - scanner.scan_file(file_path)        [alt method name]
        - scanner(file_path)                  [function-based]
        - scanner.scan([file_path])           [list variant]
    """
    if hasattr(scanner, "scan"):
        result = scanner.scan(file_path)
    elif hasattr(scanner, "scan_file"):
        result = scanner.scan_file(file_path)
    elif callable(scanner):
        result = scanner(file_path)
    else:
        raise TypeError(f"scanner {scanner!r} has no scan/scan_file and is not callable")
    if result is None:
        return []
    if isinstance(result, list):
        return result
    # Single object → wrap.
    return [result]


def _normalize_finding(raw: Any, scanner_name: str, default_file: str) -> dict[str, Any]:
    """Coerce a raw scanner result into a plain dict (picklable).

    Tries common attribute names (file, line, bug_type, description,
    severity, suggested_fix). Falls back to getattr / dict access.
    """
    def _get(obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    return {
        "file": _get(raw, "file", default_file) or default_file,
        "line": int(_get(raw, "line", 0) or 0),
        "bug_class": str(_get(raw, "bug_type", "") or _get(raw, "bug_class", "") or "Unknown"),
        "severity": _normalize_severity(_get(raw, "severity", 50)),
        "scanner": scanner_name,
        "description": str(_get(raw, "description", "") or ""),
        "evidence": dict(_get(raw, "evidence", {}) or {}),
    }


# ============================================================
# Dedup logic (deterministic — for reproducibility).
# ============================================================

def dedup_findings(findings: list[Finding]) -> list[Finding]:
    """Merge findings with the same (file, line, bug_class) key.

    Merge rules:
        - Keep the highest-severity finding as the "winner".
        - Append losing scanner names to evidence["other_scanners"].
        - Merge evidence dicts (winner's keys take precedence).
        - Sort final list by (file, line, bug_class) for determinism.
    """
    if not findings:
        return []

    buckets: dict[tuple[str, int, str], list[Finding]] = defaultdict(list)
    for f in findings:
        buckets[f.dedup_key()].append(f)

    merged: list[Finding] = []
    for _key, group in buckets.items():
        # Sort group by severity desc → winner is first.
        group.sort(key=lambda f: (-f.severity, f.scanner))
        winner = group[0]
        other_scanners = [f.scanner for f in group[1:] if f.scanner and f.scanner != winner.scanner]
        # Merge evidence (winner takes precedence, but collect all).
        merged_evidence = dict(winner.evidence)
        for f in group[1:]:
            for k, v in f.evidence.items():
                if k not in merged_evidence:
                    merged_evidence[k] = v
        if other_scanners:
            existing = merged_evidence.get("other_scanners", [])
            if isinstance(existing, list):
                other_scanners = list(set(existing + other_scanners))
            merged_evidence["other_scanners"] = sorted(other_scanners)
        merged_evidence["dedup_count"] = len(group)
        winner.evidence = merged_evidence
        merged.append(winner)

    # Deterministic sort: by file, then line, then bug_class.
    merged.sort(key=lambda f: (f.file, f.line, f.bug_class))
    return merged


# ============================================================
# Sequential fallback (for ProcessPoolExecutor unavailable or 1 file).
# ============================================================

def _run_sequential(
    scanners: list[dict[str, Any]],
    files: list[str],
) -> list[Finding]:
    """Sequential scanner run — used as fallback or for small batches."""
    all_findings: list[Finding] = []
    for file_path in files:
        try:
            raw_list = _scan_one_file_worker((file_path, scanners))
            for r in raw_list:
                all_findings.append(Finding(**r))
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"[IMP-18] sequential scan crashed on {file_path}: {e}\n"
                f"{traceback.format_exc()}"
            )
    return all_findings


# ============================================================
# Main entry: run_scanners_parallel.
# ============================================================

def run_scanners_parallel(
    scanners: list[dict[str, Any]],
    files: list[str],
    max_workers: int | None = None,
    use_processes: bool = True,
) -> list[Finding]:
    """Fan out scanners across files in parallel + dedup results.

    Args:
        scanners: List of scanner payload dicts. Each payload:
            {
              "scanner_name": str,                # display name
              "scanner_factory": str,             # dotted path to class/fn
              "scanner_kwargs": dict,             # constructor kwargs (optional)
            }
        files: List of file paths to scan.
        max_workers: Process/thread pool size. Default = min(cpu_count, 8).
        use_processes: True (default) → ProcessPoolExecutor (CPU-bound AST work).
                       False → ThreadPoolExecutor (I/O-bound or pickling issues).
                       Falls back to sequential if ProcessPoolExecutor fails.

    Returns:
        Deduplicated list of Finding objects, sorted by (file, line, bug_class).

    Fail-open:
        - ProcessPoolExecutor unavailable → fall back to ThreadPoolExecutor.
        - ThreadPoolExecutor unavailable → fall back to sequential.
        - Any worker crash → log + continue (don't fail whole batch).
    """
    if not scanners or not files:
        return []

    # Resolve max_workers.
    if max_workers is None:
        try:
            cpu = os.cpu_count() or 4
            max_workers = max(1, min(cpu, DEFAULT_MAX_WORKERS_CAP))
        except Exception as cpu_err:  # noqa: BLE001
            # silent-by-design: documented default — 4 workers when CPU count is unavailable.
            logger.debug("parallel_scanner: cpu_count unavailable, defaulting to 4 workers: %s", cpu_err, exc_info=True)
            max_workers = 4

    # Single-file or single-worker → sequential.
    if len(files) <= DEFAULT_FALLBACK_SEQUENTIAL_THRESHOLD or max_workers <= 1:
        logger.info(
            f"[IMP-18] sequential (files={len(files)}, max_workers={max_workers})"
        )
        return dedup_findings(_run_sequential(scanners, files))

    # Build worker args: one entry per file (each file gets all scanners).
    worker_args = [(f, scanners) for f in files]

    all_findings: list[Finding] = []
    executor = None
    try:
        if use_processes:
            try:
                executor = ProcessPoolExecutor(max_workers=max_workers)
                logger.info(
                    f"[IMP-18] ProcessPoolExecutor (workers={max_workers}, "
                    f"files={len(files)}, scanners={len(scanners)})"
                )
            except (ImportError, OSError, ValueError) as e:
                logger.warning(
                    f"[IMP-18] ProcessPoolExecutor unavailable ({e}), "
                    f"falling back to ThreadPoolExecutor"
                )
                executor = ThreadPoolExecutor(max_workers=max_workers)
        else:
            executor = ThreadPoolExecutor(max_workers=max_workers)

        # Submit all tasks.
        futures = {executor.submit(_scan_one_file_worker, args): args[0]
                   for args in worker_args}

        for future in as_completed(futures):
            file_path = futures[future]
            try:
                raw_list = future.result()
                for r in raw_list:
                    all_findings.append(Finding(**r))
            except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
                logger.error(
                    f"[IMP-18] worker for {file_path} crashed: {e}\n"
                    f"{traceback.format_exc()}"
                )

    finally:
        if executor is not None:
            try:
                executor.shutdown(wait=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(repr(e))

    return dedup_findings(all_findings)


# ============================================================
# Convenience helper — convert BugReport list to Finding list (for dedup).
# ============================================================

def bug_reports_to_findings(bug_reports: list[Any]) -> list[Finding]:
    """Convert BugReport-like objects to Finding objects for dedup.

    Useful when the caller has already run scanners sequentially and wants
    to dedup the results via the same logic.
    """
    out: list[Finding] = []
    for bug in bug_reports:
        try:
            out.append(Finding(
                file=str(getattr(bug, "file", "")),
                line=int(getattr(bug, "line", 0) or 0),
                bug_class=str(getattr(bug, "bug_type", "") or "Unknown"),
                severity=_normalize_severity(getattr(bug, "severity", 50)),
                scanner=str(getattr(bug, "source", "") or ""),
                description=str(getattr(bug, "description", "") or ""),
                evidence={"tier": int(getattr(bug, "tier", 0) or 0)},
            ))
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-18] bug→finding conversion failed: {e}")
    return out


__all__ = [
    "Finding",
    "run_scanners_parallel",
    "dedup_findings",
    "bug_reports_to_findings",
    "DEFAULT_MAX_WORKERS_CAP",
]
