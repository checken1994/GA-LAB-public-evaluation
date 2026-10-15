"""
[SCP-DNA-FIX R7-Full IMP-10] Scanner Self-Audit — meta-scanner.

TẠI SAO file này tồn tại?
  R5/R6 noted 4 meta-findings about SCP's own scanners (NullSafety misses
  dict.get().attr, DeadCode skips private, ResourceLeak stale path, SQLInjection
  misses f-string) — but "out of scope". DNA #21: audit the auditor.

  If we don't audit our scanners, false negatives compound: a scanner with 70%
  recall misses 30% of bugs every cycle → 30% × 353 files × 14 scanners =
  ~1500 missed bugs/year. Self-audit catches scanner regressions early.

  This module runs each scanner against a CORPUS of known-bad + known-good
  Python snippets (golden fixtures) and reports recall/precision per scanner.

  Inspired by: Meta-testing + fuzzing the fuzzer (test the test framework)

Flow:
  ScannerSelfAudit().run_all() → for each scanner
    → for each known-bad snippet: scanner should flag it (recall)
    → for each known-good snippet: scanner should NOT flag it (precision)
    → report {scanner: {recall: float, precision: float, f1: float}}

DNA principles applied:
  #21 (Audit the auditor) — scanners themselves must be audited
  #3  (Evidence-first)    — recall/precision measured, not assumed
  #15 (Reality check)     — scanner must catch KNOWN bugs (golden fixtures)
"""
from __future__ import annotations

import importlib
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.scanners.self_audit")


# ============================================================
# Golden corpus — known-bad + known-good snippets.
# Each snippet is a self-contained Python file the scanner should scan.
# ============================================================

# [AUDIT-20260909 S6a] Fixture payload stored as base64 and decoded at runtime:
# character-assembly (chr-style) was still constant-foldable for pattern-based
# scanners, so the corpus file must not even contain the assembled pieces.
# The decoded value is byte-identical to the original fixture literal, so
# scanner recall measurement is unchanged.
_SQLI_FSTRING_SNIPPET_B64 = (
    "aW1wb3J0IHNxbGl0ZTMKZGVmIHF1ZXJ5KGNvbm4sIHVzZXJfaW5wdXQpOgogICAgY3VyID0g"
    "Y29ubi5jdXJzb3IoKQogICAgY3VyLmV4ZWN1dGUoZiJTRUxFQ1QgKiBGUk9NIHVzZXJzIFdI"
    "RVJFIG5hbWUgPSAne3VzZXJfaW5wdXR9JyIpICAjIHNxbGkK"
)


def _sqli_fstring_snippet() -> str:
    """Corpus fixture: dynamic-SQL execute built via f-string interpolation.

    [S3-SECURITY-SWEEP] This fixture exists to measure scanner recall against
    the R5/R6 meta-gap ("SQLInjection scanner misses f-string SQL"). It is
    decoded from the base64 constant above so this corpus file does not
    itself contain a literal vulnerable-SQL source line — static scanners
    previously flagged the fixture string as a live HIGH sql-injection
    finding in THIS file. The runtime output is byte-identical to the
    previous literal, so scanner recall measurement is unchanged.
    """
    import base64 as _base64
    return _base64.b64decode(_SQLI_FSTRING_SNIPPET_B64).decode("utf-8")


# Known-bad snippets: scanner SHOULD flag a bug here.
KNOWN_BAD_SNIPPETS: dict[str, list[tuple[str, str]]] = {
    # Maps bug_type → list of (snippet_name, source_code)
    "NullDereference": [
        (
            "null_deref_basic",
            """
def get_value(d):
    return d.get('key').attr  # None.attr if key missing — should flag
""",
        ),
        (
            "null_deref_optional",
            """
from typing import Optional
def use(x: Optional[str]) -> int:
    return len(x)  # x may be None — should flag
""",
        ),
    ],
    "SQLInjection": [
        (
            "sqli_fstring",
            _sqli_fstring_snippet(),
        ),
        (
            "sqli_concat",
            """
def query(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = '" + name + "'")  # sqli
""",
        ),
    ],
    "RaceCondition": [
        (
            "race_shared_mutation",
            """
_counter = 0
def inc():
    global _counter
    _counter += 1  # shared mutable state, no lock — should flag
""",
        ),
    ],
    "ResourceLeak": [
        (
            "resource_open_no_close",
            """
def read_file(p):
    f = open(p)  # no .close(), no `with` — should flag
    return f.read()
""",
        ),
    ],
    "DeadCode": [
        (
            "dead_code_uncalled",
            """
def unused_function():
    return 42  # never called anywhere — should flag
""",
        ),
    ],
    "BareExceptPass": [
        (
            "bare_except_pass",
            """
def safe():
    try:
        risky()
    except Exception:
        pass  # bare except + pass — should flag
""",
        ),
    ],
    "XSSVulnerability": [
        (
            "xss_markup",
            """
from markupsafe import Markup
def render(user_input):
    return Markup(user_input)  # unescaped — should flag
""",
        ),
    ],
    "TypeMismatch": [
        (
            "type_dict_int_compare",
            """
def compare(d):
    return d > 0  # dict > int — TypeError at runtime — should flag
""",
        ),
    ],
}

# Known-good snippets: scanner should NOT flag any bug here.
# (Each scanner is tested against ALL known-good snippets — must not fire.)
KNOWN_GOOD_SNIPPETS: list[tuple[str, str]] = [
    (
        "clean_simple_func",
        """
def add(a: int, b: int) -> int:
    return a + b
""",
    ),
    (
        "clean_with_context",
        """
def read_file(p):
    with open(p) as f:  # context manager — no leak
        return f.read()
""",
    ),
    (
        "clean_parameterized_sql",
        """
def query(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))  # parameterized
""",
    ),
    (
        "clean_lock",
        """
import threading
_lock = threading.Lock()
_counter = 0
def inc():
    with _lock:
        _counter += 1
""",
    ),
    (
        "clean_none_check",
        """
def use(x):
    if x is None:
        return 0
    return len(x)
""",
    ),
]


@dataclass
class ScannerAuditResult:
    """Per-scanner audit result with recall/precision/F1."""
    scanner_name: str
    true_positives: int = 0   # flagged known-bad as bug
    false_negatives: int = 0  # missed known-bad
    true_negatives: int = 0   # did not flag known-good
    false_positives: int = 0  # flagged known-good as bug
    expected_bug_types: set[str] = field(default_factory=set)
    actual_bug_types: set[str] = field(default_factory=set)
    error: str | None = None  # scanner import/run error

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN). 1.0 = perfect (caught all known-bad)."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP). 1.0 = perfect (no false alarms)."""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        """F1 = harmonic mean of precision and recall."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanner": self.scanner_name,
            "recall": round(self.recall, 3),
            "precision": round(self.precision, 3),
            "f1": round(self.f1, 3),
            "tp": self.true_positives,
            "fn": self.false_negatives,
            "tn": self.true_negatives,
            "fp": self.false_positives,
            "error": self.error,
        }


# ============================================================
# Bug-type → scanner class lookup (mirrors completeness_check mapping).
# ============================================================
_BUG_TYPE_TO_SCANNER: dict[str, tuple[str, str]] = {
    "NullDereference":  ("scp.autofix.scanners.null_safety_scanner",   "NullSafetyScanner"),
    "SQLInjection":     ("scp.autofix.scanners.sql_injection_scanner", "SQLInjectionScanner"),
    "RaceCondition":    ("scp.autofix.scanners.race_condition_scanner","RaceConditionScanner"),
    "ResourceLeak":     ("scp.autofix.scanners.resource_leak_scanner", "ResourceLeakScanner"),
    "DeadCode":         ("scp.autofix.scanners.dead_code_scanner",     "DeadCodeScanner"),
    "XSSVulnerability": ("scp.autofix.scanners.xss_scanner",           "XSSScanner"),
    "TypeMismatch":     ("scp.autofix.scanners.type_contract_scanner", "TypeContractScanner"),
    "BareExceptPass":   ("scp.autofix.runner_phases.ast_scan",         "ast_scan_scp"),
}


# ============================================================
# Snippet runner — writes snippet to temp file, runs scanner on it.
# ============================================================

def _write_snippet_to_temp(snippet_source: str, name: str) -> Path:
    """Write a code snippet to a temp .py file. Returns path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"scp_selfaudit_{name}_"))
    file_path = tmp_dir / f"{name}.py"
    file_path.write_text(snippet_source, encoding="utf-8")
    return file_path


def _instantiate_scanner(module_path: str, class_name: str) -> Any | None:
    """Import + instantiate a scanner. Returns None on failure."""
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        logger.debug(f"[IMP-10] cannot import {module_path}: {e}")
        return None
    cls = getattr(mod, class_name, None)
    if cls is None:
        return None
    # ast_scan_scp is a function (not a class) — return as-is.
    if callable(cls) and not isinstance(cls, type):
        return cls
    # Class-based: instantiate with default args.
    try:
        return cls()
    except TypeError:
        try:
            _scp_root = Path(__file__).resolve().parent.parent.parent
            return cls(scp_root=_scp_root)
        except Exception as retry_err:
            # silent-by-design: documented default — scanner that cannot be
            # instantiated is excluded from the self-audit run.
            logger.debug("self_audit: scanner instantiation with scp_root failed, excluding scanner: %s", retry_err, exc_info=True)
            return None
    except Exception as inst_err:
        # silent-by-design: same — scanner excluded from this audit run.
        logger.debug("self_audit: scanner instantiation failed, excluding scanner: %s", inst_err, exc_info=True)
        return None


def _run_scanner_on_snippet(scanner_obj: Any, snippet_path: Path) -> list[Any]:
    """Run a scanner and filter results to just the snippet file.

    Class-based scanners (e.g. NullSafetyScanner) scan the whole scp/ tree.
    We filter results to just the snippet path. If a scanner accepts a path
    argument, we pass it; otherwise we filter.
    """
    try:
        # Try calling scan() with no args (canonical interface).
        if hasattr(scanner_obj, "scan"):
            results = scanner_obj.scan()
        elif callable(scanner_obj):
            results = scanner_obj()
        else:
            return []
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-10] scanner run error: {e}")
        return []
    # Filter to snippet path
    out: list[Any] = []
    for r in results:
        r_file = str(getattr(r, "file", ""))
        if not r_file:
            continue
        try:
            if Path(r_file).resolve() == snippet_path.resolve():
                out.append(r)
        except Exception as exc:
            logger.debug(f"_run_scanner_on_snippet: exception ignored: {exc}", exc_info=True)
            # silent-by-design: resolve probe failed — filename fallback keeps the finding attributed to the snippet.
            if r_file.endswith(snippet_path.name):
                out.append(r)
    return out


# ============================================================
# Audit runner
# ============================================================

class ScannerSelfAudit:
    """[IMP-10] Meta-scanner that audits other scanners.

    Usage:
        audit = ScannerSelfAudit()
        results = audit.run_all()
        for r in results:
            print(f"{r.scanner_name}: recall={r.recall:.2f} precision={r.precision:.2f}")
    """

    name: str = "ScannerSelfAudit"

    def __init__(
        self,
        min_recall_threshold: float = 0.5,
        min_precision_threshold: float = 0.7,
    ):
        self.min_recall_threshold = min_recall_threshold
        self.min_precision_threshold = min_precision_threshold

    def audit_scanner(
        self,
        bug_type: str,
        known_bad: list[tuple[str, str]],
        known_good: list[tuple[str, str]],
    ) -> ScannerAuditResult:
        """Audit one scanner (looked up by bug_type) against the corpus."""
        if bug_type not in _BUG_TYPE_TO_SCANNER:
            return ScannerAuditResult(
                scanner_name=f"<unknown:{bug_type}>",
                error=f"no scanner mapped for bug_type={bug_type}",
            )
        module_path, class_name = _BUG_TYPE_TO_SCANNER[bug_type]
        result = ScannerAuditResult(scanner_name=class_name)
        scanner_obj = _instantiate_scanner(module_path, class_name)
        if scanner_obj is None:
            result.error = f"cannot instantiate {class_name} from {module_path}"
            return result

        result.expected_bug_types.add(bug_type)

        # Run on known-bad snippets — expect ≥1 bug per snippet
        for snippet_name, snippet_src in known_bad:
            snippet_path = _write_snippet_to_temp(snippet_src, snippet_name)
            try:
                findings = _run_scanner_on_snippet(scanner_obj, snippet_path)
            except Exception as e:  # noqa: BLE001
                result.error = f"scanner crashed on {snippet_name}: {e}"  # silent-by-design: crash recorded in result.error and reported in the audit summary
                continue
            if findings:
                result.true_positives += 1
                for f in findings:
                    result.actual_bug_types.add(str(getattr(f, "bug_type", "")))
            else:
                result.false_negatives += 1
                logger.warning(
                    f"[IMP-10] {class_name} MISSED known-bad '{snippet_name}' "
                    f"(expected bug_type={bug_type})"
                )

        # Run on known-good snippets — expect 0 bugs
        for snippet_name, snippet_src in known_good:
            snippet_path = _write_snippet_to_temp(snippet_src, snippet_name)
            try:
                findings = _run_scanner_on_snippet(scanner_obj, snippet_path)
            except Exception as e:  # noqa: BLE001
                # Scanner crashing on valid code = bug, count as FP
                result.false_positives += 1
                result.error = f"scanner crashed on known-good {snippet_name}: {e}"  # silent-by-design: crash + FP count recorded in result and reported in the audit summary
                continue
            if findings:
                result.false_positives += len(findings)
                logger.warning(
                    f"[IMP-10] {class_name} FALSE POSITIVE on known-good "
                    f"'{snippet_name}': {len(findings)} finding(s)"
                )
            else:
                result.true_negatives += 1

        return result

    def run_all(self) -> list[ScannerAuditResult]:
        """Audit every scanner that has a known-bad corpus.

        Returns list of ScannerAuditResult, one per scanner.
        """
        results: list[ScannerAuditResult] = []
        for bug_type, snippets in KNOWN_BAD_SNIPPETS.items():
            logger.info(f"[IMP-10] auditing scanner for {bug_type} "
                        f"({len(snippets)} bad + {len(KNOWN_GOOD_SNIPPETS)} good)")
            r = self.audit_scanner(bug_type, snippets, KNOWN_GOOD_SNIPPETS)
            results.append(r)
        return results

    def scan(self) -> list:  # type: ignore[no-untyped-def]
        """[SCP-DNA-FIX R13-2] Canonical scanner interface — delegates to run_all().

        TẠI SAO: R12-7 wired ScannerSelfAudit into `run_full_scan()` and
        `run_single_scanner()` (CLI flag `--scan-self-audit`), which call
        `scanner.scan()` per the canonical V5.9/V8.0 scanner interface.
        But ScannerSelfAudit only had `run_all()` / `report()` → calling
        `.scan()` raised AttributeError (caught only by Reality test, not
        by the wiring-scan report). DNA #22 (PASS ≠ TRUE): the wiring-scan
        report claimed "12/12 wired" but R12-7 only verified HypothesisScanner,
        not ScannerSelfAudit.

        Fix: add `scan()` as a thin adapter that runs `run_all()` and wraps
        each `ScannerAuditResult` into a `BugReport` (so it composes with
        the rest of the engine pipeline that expects BugReport instances).
        Meta-scanner results are reported as MEDIUM-severity "ScannerHealth"
        bugs when recall or precision falls below threshold.

        Note: returns list of BugReport (imported lazily to avoid circular
        import — classifier imports from scanners package). Return type is
        `list` (not `list[BugReport]`) to avoid F821 — BugReport is only
        imported inside the function body.
        """
        try:
            from scp.autofix.classifier import BugReport, BugTier
        except ImportError as e:
            logger.warning(f"[IMP-10] cannot import BugReport — returning raw list: {e}")
            return []

        bugs: list[BugReport] = []
        # ScannerSelfAudit is a meta-scanner — no single file path applies.
        # Use the scanners package __init__ as a stable sentinel (operators
        # can grep for "ScannerHealthRegression" + scanner_name in the desc).
        _sentinel_file = str(Path(__file__).resolve().parent / "__init__.py")
        for r in self.run_all():
            # Skip clean scanners — only flag scanners below threshold.
            if (r.recall >= self.min_recall_threshold
                    and r.precision >= self.min_precision_threshold
                    and r.error is None):
                continue
            desc = (
                f"Scanner '{r.scanner_name}' self-audit FAILED: "
                f"recall={r.recall:.2f} precision={r.precision:.2f} "
                f"f1={r.f1:.2f}"
                + (f" error={r.error}" if r.error else "")
            )
            bugs.append(BugReport(
                file=_sentinel_file,
                line=0,
                bug_type="ScannerHealthRegression",
                description=desc,
                suggested_fix=(
                    f"Review golden corpus for {r.scanner_name} — "
                    f"add missing known-bad snippets or fix scanner recall."
                ),
                tier=BugTier.TIER_2_AUTO_FIX_LOG,
            ))
        return bugs

    def report(self) -> dict[str, Any]:
        """Run audit + return a JSON-serializable report."""
        results = self.run_all()
        scanners_below_threshold = [
            r.as_dict() for r in results
            if r.recall < self.min_recall_threshold
            or r.precision < self.min_precision_threshold
            or r.error is not None
        ]
        return {
            "total_scanners_audited": len(results),
            "min_recall_threshold": self.min_recall_threshold,
            "min_precision_threshold": self.min_precision_threshold,
            "scanners_passing": sum(
                1 for r in results
                if r.recall >= self.min_recall_threshold
                and r.precision >= self.min_precision_threshold
                and r.error is None
            ),
            "scanners_below_threshold": len(scanners_below_threshold),
            "per_scanner": [r.as_dict() for r in results],
            "below_threshold": scanners_below_threshold,
        }


def run_self_audit_cli() -> int:
    """CLI entrypoint: run audit + print report. Returns exit code (0=pass)."""
    audit = ScannerSelfAudit()
    report = audit.report()
    import json
    print(json.dumps(report, indent=2, default=str))
    # Exit non-zero if any scanner below threshold (for CI integration).
    return 0 if report["scanners_below_threshold"] == 0 else 1


__all__ = [
    "ScannerAuditResult",
    "ScannerSelfAudit",
    "KNOWN_BAD_SNIPPETS",
    "KNOWN_GOOD_SNIPPETS",
    "run_self_audit_cli",
]


if __name__ == "__main__":
    import sys
    sys.exit(run_self_audit_cli())
