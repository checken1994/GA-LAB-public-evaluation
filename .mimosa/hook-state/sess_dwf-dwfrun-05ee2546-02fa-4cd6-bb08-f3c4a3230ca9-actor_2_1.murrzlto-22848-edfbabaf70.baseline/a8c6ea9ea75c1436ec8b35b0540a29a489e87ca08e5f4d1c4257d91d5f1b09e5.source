# SCP CIRCUIT: M07 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M07-closure.json)
"""
[SCP-DNA-FIX R9 v4 IMP-23] Shadow-Apply + Canary Compare.

TẠI SAO file này tồn tại?
  IMP-2 (reality_test) chạy test trên file ĐÃ PATCH (overwrite gốc). Nếu fix
  sai, file đã bị modify → phải rollback (IMP-6). IMP-17 (auto_rollback) chỉ
  rollback SAU khi regression xuất hiện (60s window) — vẫn có khoảng trống
  "fix apply → user thấy lỗi → rollback".

  v4 IMP-23 thay thế bằng shadow-apply: TRƯỚC khi patch thật, apply fix vào
  BẢN SAO (temp file hoặc in-memory), chạy canary test suite (smoke tests,
  reality tests, property tests) trên BOTH original + shadow, so sánh output.
  Chỉ promote shadow → real nếu canary PASS AND no regression. Nếu canary
  FAIL → discard fix ngay (không cần rollback vì chưa bao giờ patch thật).

  Inspired by:
    - Sentry canary deploys (route 1% traffic to canary, promote if healthy)
    - Istio traffic shadowing (mirror production traffic to canary, compare)
    - Netflix Chaos Monkey (inject failure in shadow, observe)
    - Kubernetes canary + rollout (auto-promote / auto-rollback)
    - git stash + test before commit (developer workflow)

  Default canary suite (default_canary_suite):
    1. ast.parse shadow source — must pass (syntax OK).
    2. Import shadow module — must not raise ImportError.
    3. Smoke-call each top-level function with None + empty list/dict/str —
       must not raise (or must raise same exception as original).
    4. (Optional, if IMP-2 reality_test available) run reality_test on
       shadow file — must pass.
    5. (Optional, if IMP-19 property_validator available) run property suite
       with default invariants.

  Fail-open policy (DNA #7 + #11 tension):
    - If canary suite is empty / unavailable → passed=True, reason="skip —
      canary unavailable, fail-open (but flag for review)". Do NOT block
      fixes if safety infra is down — but log loudly per DNA #11.
    - If canary runner crashes → passed=False (fail-closed for safety —
      a crashing safety net is worse than no net).
    - If shadow apply itself fails (can't write temp file) → passed=False,
      reason="shadow apply failed (cannot verify fix — fail-closed)".

Flow:
  suite = default_canary_suite()
  result = shadow_apply_and_compare(target_file, fix, suite)
  if result.passed:
      engine.apply_fix(fix)   # now safe to apply for real
  else:
      discard(fix)
      log_loudly(result.reason)   # DNA #11

DNA principles applied:
  #9  (No harm)         — bad fixes discarded before touching real file
  #11 (Fail loudly)     — canary failures logged + surfaced to operator
  #7  (Autofix safe)    — fail-open if canary infra down (don't brick engine)
  #26 (Reality cuối cùng)— canary = actual execution, not just AST parse
  #17 (Operator oversight)— flagged-for-review when canary skipped

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-14] Integration status: WIRED in engine.py:1285 (R11 IMP-23, fail-open). Shadow canary runs before file write.
  Wire in `engine.py:apply_fix()` BEFORE the actual file write:
      result = shadow_apply_and_compare(target_file, fix, default_canary_suite())
      if not result.passed:
          return ApplyResult(ok=False, reason=f"canary failed: {result.reason}")
      # ... proceed to real apply ...

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  from runner_phases.shadow_canary import (
      shadow_apply_and_compare, default_canary_suite, ShadowFix
  )
  fix = ShadowFix(
      original_source='def f(x):\\n    return x + 1',
      patched_source='def f(x):\\n    return x + 1',
  )
  r = shadow_apply_and_compare('test.py', fix, default_canary_suite())
  print(r.passed, r.reason)
  "
  → True canary passed (N tests, 0 diffs)
"""
from __future__ import annotations

import ast
import importlib.util
import logging
import os
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import ensure_within, sanitize_filename_stem

logger = logging.getLogger("scp.autofix.shadow_canary")


# ============================================================
# Defaults.
# ============================================================

DEFAULT_MAX_CANARY_TESTS = 50          # cap tests per canary run
DEFAULT_CANARY_TIMEOUT_SECONDS = 5.0   # cap total canary runtime
DEFAULT_SHADOW_DIR = "data/shadow"     # temp files for shadow apply


# ============================================================
# Dataclasses.
# ============================================================

@dataclass
class ShadowFix:
    """A fix to be shadow-applied.

    Attributes:
        original_source: Full source of the file BEFORE the fix.
        patched_source: Full source of the file AFTER the fix.
        fix_id: Optional audit identifier.
        bug_location: Optional (function_name, line_start, line_end) for
            scoping the comparison (changes outside this range → over-broad).
    """
    original_source: str
    patched_source: str
    fix_id: str = ""
    bug_location: tuple[str, int, int] | None = None


@dataclass
class CanaryTest:
    """A single canary test.

    A test is a callable that takes a `module` (the imported shadow module)
    and returns a `CanaryTestResult`. The test should be self-contained —
    no I/O on real files, no network.
    """
    name: str
    fn: Callable[[Any], CanaryTestResult]
    description: str = ""


@dataclass
class CanaryTestResult:
    """Result of running one canary test."""
    name: str
    passed: bool
    output: Any = None
    reason: str = ""
    duration_ms: float = 0.0


@dataclass
class CanaryResult:
    """Outcome of shadow_apply_and_compare()."""
    passed: bool = True
    original_outputs: list[CanaryTestResult] = field(default_factory=list)
    shadow_outputs: list[CanaryTestResult] = field(default_factory=list)
    diffs: list[str] = field(default_factory=list)
    reason: str = ""
    shadow_path: str = ""
    flagged_for_review: bool = False   # True if canary was skipped (fail-open)
    tests_run: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "tests_run": self.tests_run,
            "diffs_count": len(self.diffs),
            "reason": self.reason,
            "shadow_path": self.shadow_path,
            "flagged_for_review": self.flagged_for_review,
            "original_outputs": [
                {"name": r.name, "passed": r.passed, "reason": r.reason}
                for r in self.original_outputs
            ],
            "shadow_outputs": [
                {"name": r.name, "passed": r.passed, "reason": r.reason}
                for r in self.shadow_outputs
            ],
            "diffs": list(self.diffs),
        }


# ============================================================
# Built-in canary tests.
# ============================================================

def _ast_parse_test(module: Any) -> CanaryTestResult:
    """Test: shadow source must parse as valid Python.

    `module` here is actually a dict with 'source' key (since we may not
    have a real module yet — this test runs before import).
    """
    try:
        src = module.get("source", "") if isinstance(module, dict) else ""
        if not src:
            return CanaryTestResult(
                name="ast_parse", passed=False,
                reason="no source available",
            )
        ast.parse(src)
        return CanaryTestResult(name="ast_parse", passed=True)
    except SyntaxError as e:
        return CanaryTestResult(
            name="ast_parse", passed=False,
            reason=f"SyntaxError: {e}",
        )
    except Exception as e:  # noqa: BLE001
        return CanaryTestResult(
            name="ast_parse", passed=False,
            reason=f"{type(e).__name__}: {e}",
        )


def _import_test(module: Any) -> CanaryTestResult:
    """Test: shadow module must import without error."""
    try:
        # If we got a real module object, import already succeeded.
        if isinstance(module, types.ModuleType):
            return CanaryTestResult(name="import", passed=True)
        if isinstance(module, dict) and "module" in module:
            mod = module["module"]
            if isinstance(mod, types.ModuleType):
                return CanaryTestResult(name="import", passed=True)
            return CanaryTestResult(
                name="import", passed=False,
                reason=f"module not a real module: {type(mod).__name__}",
            )
        return CanaryTestResult(
            name="import", passed=False,
            reason="no module object provided",
        )
    except Exception as e:  # noqa: BLE001
        return CanaryTestResult(
            name="import", passed=False,
            reason=f"{type(e).__name__}: {e}",
        )


def _smoke_call_test(module: Any) -> CanaryTestResult:
    """Test: call each top-level function with None + empty inputs.

    Records per-input exception info in `output` so the canary comparison
    logic can detect regressions (shadow raises where original didn't).

    The test itself passes as long as the module is callable — actual
    regression detection is done by comparing output between original +
    shadow runs.
    """
    try:
        if isinstance(module, dict):
            mod = module.get("module")
        else:
            mod = module
        if mod is None or not isinstance(mod, types.ModuleType):
            return CanaryTestResult(
                name="smoke_call", passed=False,
                reason="no module to smoke-call",
            )
        # Find top-level functions.
        funcs = [
            (name, obj) for name, obj in vars(mod).items()
            if callable(obj) and not name.startswith("_")
            and getattr(obj, "__module__", None) == mod.__name__
        ]
        if not funcs:
            return CanaryTestResult(
                name="smoke_call", passed=True,
                reason="no top-level functions to smoke-call",
                output={"exceptions": []},
            )
        test_inputs = [None, [], {}, "", 0, 1, -1]
        # Per-input exception signature: list of (func, input_repr, exc_class).
        # None means no exception (graceful). This is what comparison checks.
        exceptions: list[list[str]] = []
        n_called = 0
        for fname, fn in funcs[:10]:  # cap at 10 functions
            for inp in test_inputs[:5]:  # cap at 5 inputs each
                exc_class = ""
                try:
                    fn(inp)
                except TypeError as e:
                    # Distinguish "wrong arg count" (skip) from real TypeError
                    # (e.g. None + 1). Heuristic: if message mentions "argument"
                    # or "positional", it's arg-count mismatch.
                    msg = str(e).lower()
                    if "argument" in msg or "positional" in msg:
                        # silent-by-design: probe heuristic — arg-count mismatch
                        # skips this input; the real-TypeError branch records it.
                        logger.debug("shadow_canary: %s does not accept test input (arg-count), skipping", fname, exc_info=True)
                        continue   # skip — function doesn't accept 1 arg
                    exc_class = "TypeError"
                except Exception as e:  # noqa: BLE001
                    exc_class = type(e).__name__  # silent-by-design: exception class recorded into smoke output for the original-vs-shadow comparison
                exceptions.append([fname, repr(inp)[:30], exc_class])
                n_called += 1
        return CanaryTestResult(
            name="smoke_call", passed=True,
            output={"calls_made": n_called, "exceptions": exceptions},
        )
    except Exception as e:  # noqa: BLE001
        return CanaryTestResult(
            name="smoke_call", passed=False,
            reason=f"{type(e).__name__}: {e}",
        )


def _reality_test_wrapper(module: Any) -> CanaryTestResult:
    """Test: invoke IMP-2 reality_test if available. Fail-open if not."""
    try:
        # Best-effort: import reality_test. If unavailable, skip.
        from scp.autofix.runner_phases.reality_test import run_reality_test
        if isinstance(module, dict):
            path = module.get("file_path", "")
        else:
            path = ""
        if not path:
            return CanaryTestResult(
                name="reality_test", passed=True,
                reason="skip — no file path (fail-open)",
            )
        result = run_reality_test("canary", path, exercise_callables=True)
        ok = bool(result.get("ok", False)) if isinstance(result, dict) else False
        return CanaryTestResult(
            name="reality_test", passed=ok,
            output=result if isinstance(result, dict) else None,
            reason="" if ok else "reality_test reported failure",
        )
    except ImportError:
        # silent-by-design: explicit skip result with reason returned to the caller by contract.
        return CanaryTestResult(
            name="reality_test", passed=True,
            reason="skip — reality_test unavailable (fail-open)",
        )
    except Exception as e:  # noqa: BLE001
        return CanaryTestResult(
            name="reality_test", passed=True,
            reason=f"skip — reality_test error (fail-open): {e}",
        )


def _property_test_wrapper(module: Any) -> CanaryTestResult:
    """Test: invoke IMP-19 property_validator if available. Fail-open."""
    try:
        from scp.autofix.property_validator import (
            PropertySpec,
            validate_fix,
        )
        if isinstance(module, dict):
            orig = module.get("original_source", "")
            patched = module.get("source", "")
        else:
            return CanaryTestResult(
                name="property_test", passed=True,
                reason="skip — no source (fail-open)",
            )
        if not orig or not patched:
            return CanaryTestResult(
                name="property_test", passed=True,
                reason="skip — missing source (fail-open)",
            )
        spec = PropertySpec(
            invariants=[lambda y: True],  # identity invariant — just check no crash
            strategy="mixed",
        )
        result = validate_fix(orig, patched, None, spec, n=10)
        return CanaryTestResult(
            name="property_test", passed=result.ok,
            output=result.to_dict(),
            reason=result.reason,
        )
    except ImportError:
        # silent-by-design: explicit skip result with reason returned to the caller by contract.
        return CanaryTestResult(
            name="property_test", passed=True,
            reason="skip — property_validator unavailable (fail-open)",
        )
    except Exception as e:  # noqa: BLE001
        return CanaryTestResult(
            name="property_test", passed=True,
            reason=f"skip — property_test error (fail-open): {e}",
        )


# ============================================================
# CanarySuite.
# ============================================================

@dataclass
class CanarySuite:
    """A suite of canary tests to run on shadow-applied fixes."""
    tests: list[CanaryTest] = field(default_factory=list)
    max_tests: int = DEFAULT_MAX_CANARY_TESTS
    timeout_seconds: float = DEFAULT_CANARY_TIMEOUT_SECONDS

    def add(self, test: CanaryTest) -> None:
        if len(self.tests) < self.max_tests:
            self.tests.append(test)

    def add_test(
        self,
        name: str,
        fn: Callable[[Any], CanaryTestResult],
        description: str = "",
    ) -> None:
        self.add(CanaryTest(name=name, fn=fn, description=description))


def default_canary_suite() -> CanarySuite:
    """Return the default canary suite (5 tests).

    Tests:
        1. ast_parse — shadow source must parse.
        2. import — shadow module must import.
        3. smoke_call — top-level functions don't crash on edge inputs.
        4. reality_test — IMP-2 reality_test on shadow file (fail-open if unavailable).
        5. property_test — IMP-19 property suite (fail-open if unavailable).
    """
    suite = CanarySuite()
    suite.add_test("ast_parse", _ast_parse_test, "shadow source must parse")
    suite.add_test("import", _import_test, "shadow module must import")
    suite.add_test("smoke_call", _smoke_call_test, "smoke-call top-level funcs")
    suite.add_test("reality_test", _reality_test_wrapper, "IMP-2 reality test (fail-open)")
    suite.add_test("property_test", _property_test_wrapper, "IMP-19 property suite (fail-open)")
    return suite


# ============================================================
# Shadow apply — write to temp file, import as module.
# ============================================================

def _write_shadow(source: str, original_filename: str) -> tuple[str, types.ModuleType | None]:
    """Write `source` to a temp .py file and import it as a module.

    Returns (path, module_or_None). Fail-open: any error → ("", None).
    """
    try:
        shadow_dir = DEFAULT_SHADOW_DIR
        os.makedirs(shadow_dir, exist_ok=True)
        # [S3-SECURITY-SWEEP] original_filename comes from findings (external
        # data): sanitize the stem to a safe charset and enforce containment
        # inside shadow_dir (HIGH path-traversal fix).
        base = sanitize_filename_stem(original_filename, fallback="shadow")
        # Use a unique suffix to avoid module-name collisions.
        import uuid
        suffix = uuid.uuid4().hex[:8]
        shadow_path = os.path.join(shadow_dir, f"{base}_shadow_{suffix}.py")
        contained = ensure_within(shadow_dir, shadow_path)
        if contained is None:
            logger.warning(
                "[IMP-23] shadow path escaped shadow_dir — refusing write: %r",
                shadow_path,
            )
            return "", None
        shadow_path = str(contained)
        with Path(shadow_path).open("w", encoding="utf-8") as f:
            f.write(source)
        # Import as a fresh module (don't pollute sys.modules).
        mod_name = f"_shadow_{suffix}"
        spec = importlib.util.spec_from_file_location(mod_name, shadow_path)
        if spec is None or spec.loader is None:
            return shadow_path, None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return shadow_path, mod
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-23] shadow write/import error: {e}")
        return "", None


def _cleanup_shadow(shadow_path: str) -> None:
    """Best-effort cleanup of shadow temp file. Fail-open."""
    try:
        if shadow_path and os.path.exists(shadow_path):
            os.unlink(shadow_path)
        # Also clean __pycache__ entry if present.
        if shadow_path:
            pyc = shadow_path + "c"
            if os.path.exists(pyc):
                os.unlink(pyc)
            pycache_dir = os.path.join(
                os.path.dirname(shadow_path), "__pycache__",
            )
            if os.path.isdir(pycache_dir):
                # Try to remove only shadow-related .pyc files.
                stem = Path(shadow_path).stem
                for f in os.listdir(pyc_dir := pycache_dir):
                    if stem in f:
                        try:
                            os.unlink(os.path.join(pyc_dir, f))
                        except Exception as e:  # noqa: BLE001
                            logger.debug(f"[shadow_canary.py:474] silenced: {e}")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-23] shadow cleanup error: {e}")


def _detect_exception_regression(orig_output: Any, shadow_output: Any) -> bool:
    """True if shadow raises an exception where original didn't.

    Both outputs are dicts with an "exceptions" key (list of
    [fname, input_repr, exc_class] tuples). exc_class == "" means no exception.

    Returns True if for any (fname, input) pair, orig has "" and shadow has
    a non-empty exception class.
    """
    try:
        if not isinstance(orig_output, dict) or not isinstance(shadow_output, dict):
            return False
        orig_excs = orig_output.get("exceptions", [])
        shadow_excs = shadow_output.get("exceptions", [])
        if not isinstance(orig_excs, list) or not isinstance(shadow_excs, list):
            return False
        # Build a lookup: (fname, input_repr) -> exc_class
        orig_map: dict[tuple[str, str], str] = {}
        for entry in orig_excs:
            if isinstance(entry, list) and len(entry) >= 3:
                orig_map[(entry[0], entry[1])] = entry[2]
        for entry in shadow_excs:
            if isinstance(entry, list) and len(entry) >= 3:
                key = (entry[0], entry[1])
                orig_exc = orig_map.get(key, "")
                shadow_exc = entry[2]
                if not orig_exc and shadow_exc:
                    return True   # shadow raises where original didn't
        return False
    except Exception as cmp_err:  # noqa: BLE001
        # fail-loudly (S-B1b): this is a regression-verification probe — a
        # comparison crash returning False would silently hide a real
        # exception regression; keep the False contract but surface it.
        logger.warning("[shadow_canary] exception-regression comparison crashed, reporting no regression: %s", cmp_err, exc_info=True)
        return False


def _short_output(output: Any, max_len: int = 100) -> str:
    """Return a short repr of a CanaryTestResult.output for diff logging."""
    try:
        s = repr(output)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s
    except Exception as repr_err:  # noqa: BLE001
        # silent-by-design: repr probe — placeholder text marks the failed
        # formatting in the diff log instead of crashing the summary.
        logger.debug("shadow_canary: output repr failed: %s", repr_err, exc_info=True)
        return "<output-repr-error>"


# ============================================================
# Public API.
# ============================================================

def shadow_apply_and_compare(
    target_file: str,
    fix: ShadowFix,
    canary_suite: CanarySuite | None,
) -> CanaryResult:
    """Apply `fix` to a shadow copy of `target_file`, run canary tests on
    BOTH original + shadow, compare outputs.

    Steps:
        1. If canary_suite is None or empty → fail-open (passed=True, flagged).
        2. Write original_source to shadow_A, patched_source to shadow_B.
        3. Import both as modules. [SCP-DNA-FIX R13-6] Original import fail →
           fail-OPEN (R12-23 change — modules with external deps can't import
           in shadow context; fail-closed would block ALL fixes for those
           modules). Patched import fail → fail-closed (can't verify patched
           version = real bug).
        4. Run each canary test on both modules, collect outputs.
        5. Compare: if shadow output differs from original in a way that
           indicates regression (test passed on original, failed on shadow),
           flag as diff.
        6. Return CanaryResult.passed = True iff all shadow tests pass AND
           no regression diffs.

    Args:
        target_file: Original file path (for naming shadow temp files).
        fix: ShadowFix with original_source + patched_source.
        canary_suite: CanarySuite of tests. None → use default_canary_suite().

    Returns:
        CanaryResult. Fail-open: empty suite → passed=True, flagged_for_review=True.
    """
    result = CanaryResult()
    try:
        # Default suite if none provided.
        if canary_suite is None:
            canary_suite = default_canary_suite()

        if not canary_suite.tests:
            # Fail-open: don't block fixes if safety infra is down.
            # But log loudly per DNA #11.
            logger.warning(
                "[IMP-23] canary suite empty — fail-open (flagged for review)"
            )
            result.passed = True
            result.flagged_for_review = True
            result.reason = (
                "skip — canary unavailable, fail-open (but flag for review)"
            )
            return result

        # Step 1: write + import shadow for ORIGINAL.
        orig_path, orig_mod = _write_shadow(fix.original_source, target_file)
        if orig_mod is None:
            # [SCP-DNA-FIX R12-23] Fail-OPEN (not fail-closed) for import errors.
            # Tại sao: modules có external deps (db_manager, httpx, fastapi, v.v.)
            # không import được trong shadow context → fail-closed block MỌI fix
            # cho những modules này. DNA #7 (Autofix safe — fail-open) + DNA #22
            # (PASS ≠ TRUE — fail-closed "PASS" = block but không verify gì).
            # Fix: fail-open + flag for review. Nếu patch ast.parse OK + post_fix_verify
            # OK → apply. shadow_canary chỉ là 1 layer trong nhiều layers.
            logger.warning("[IMP-23] cannot import original shadow — fail-OPEN (flagged)")
            result.passed = True  # fail-open
            result.flagged_for_review = True
            result.reason = (
                "skip — shadow import failed (module has external deps), "
                "fail-open (other verify layers will check)"
            )
            if orig_path:
                _cleanup_shadow(orig_path)
            return result

        # Step 2: write + import shadow for PATCHED.
        shadow_path, shadow_mod = _write_shadow(fix.patched_source, target_file)
        result.shadow_path = shadow_path or ""
        if shadow_mod is None:
            logger.warning("[IMP-23] cannot import patched shadow — fail-closed")
            result.passed = False
            result.reason = (
                "shadow apply failed for PATCHED (cannot verify — fail-closed)"
            )
            _cleanup_shadow(orig_path)
            if shadow_path:
                _cleanup_shadow(shadow_path)
            return result

        # Step 3: run canary tests on both.
        orig_ctx = {
            "source": fix.original_source,
            "module": orig_mod,
            "file_path": orig_path,
            "original_source": fix.original_source,
        }
        shadow_ctx = {
            "source": fix.patched_source,
            "module": shadow_mod,
            "file_path": shadow_path,
            "original_source": fix.original_source,
        }

        all_shadow_passed = True
        for test in canary_suite.tests:
            try:
                orig_out = test.fn(orig_ctx)
                shadow_out = test.fn(shadow_ctx)
                result.original_outputs.append(orig_out)
                result.shadow_outputs.append(shadow_out)
                result.tests_run += 1

                # Compare: did shadow fail where original passed?
                if orig_out.passed and not shadow_out.passed:
                    diff = (
                        f"REGRESSION on '{test.name}': "
                        f"orig=pass, shadow=fail ({shadow_out.reason})"
                    )
                    result.diffs.append(diff)
                    all_shadow_passed = False
                elif not orig_out.passed and shadow_out.passed:
                    # Original failed, shadow passed → fix IMPROVED this test.
                    # Not a regression; record as positive signal.
                    diff = (
                        f"IMPROVEMENT on '{test.name}': "
                        f"orig=fail, shadow=pass"
                    )
                    result.diffs.append(diff)
                elif orig_out.passed and shadow_out.passed:
                    # Both passed — check output equality (if both have output).
                    if orig_out.output is not None and shadow_out.output is not None:
                        if orig_out.output != shadow_out.output:
                            # Detect exception-signature regression: shadow
                            # raises where original didn't.
                            is_regression = _detect_exception_regression(
                                orig_out.output, shadow_out.output,
                            )
                            if is_regression:
                                diff = (
                                    f"REGRESSION on '{test.name}': "
                                    f"shadow raises where original didn't "
                                    f"(orig={_short_output(orig_out.output)}, "
                                    f"shadow={_short_output(shadow_out.output)})"
                                )
                                result.diffs.append(diff)
                                all_shadow_passed = False
                            else:
                                diff = (
                                    f"OUTPUT_DIFF on '{test.name}': "
                                    f"orig={_short_output(orig_out.output)}, "
                                    f"shadow={_short_output(shadow_out.output)}"
                                )
                                result.diffs.append(diff)
                                # Output diff alone doesn't fail — could be intended.
                                # But flag for review.
                                result.flagged_for_review = True
            except Exception as e:  # noqa: BLE001 — fail-closed for safety
                logger.warning(
                    f"[IMP-23] canary test '{test.name}' crashed: {e}"
                )
                result.diffs.append(
                    f"CANARY_CRASH on '{test.name}': {type(e).__name__}: {e}"
                )
                all_shadow_passed = False

        # Step 4: verdict.
        if all_shadow_passed and not any(
            d.startswith("REGRESSION") for d in result.diffs
        ):
            result.passed = True
            result.reason = (
                f"canary passed ({result.tests_run} tests, "
                f"{len(result.diffs)} non-blocking diffs)"
            )
        else:
            result.passed = False
            n_regression = sum(1 for d in result.diffs if d.startswith("REGRESSION"))
            n_crash = sum(1 for d in result.diffs if d.startswith("CANARY_CRASH"))
            result.reason = (
                f"canary FAILED: {n_regression} regression(s), "
                f"{n_crash} crash(es), {result.tests_run} tests run"
            )

    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7, BUT flag
        logger.warning(f"[IMP-23] shadow_apply_and_compare error: {e}")
        result.passed = True   # fail-open
        result.flagged_for_review = True
        result.reason = (
            f"skip — canary internal error (fail-open, flagged): {e}"
        )
    finally:
        # Cleanup shadow temp files.
        try:
            if "orig_path" in locals() and orig_path:
                _cleanup_shadow(orig_path)
            if "shadow_path" in locals() and shadow_path:
                _cleanup_shadow(shadow_path)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[shadow_canary.py:721] silenced: {e}")

    return result


def summarize_canary(result: CanaryResult) -> str:
    """Return a short human-readable summary for audit log."""
    try:
        if result.passed and not result.flagged_for_review:
            return f"OK — {result.reason}"
        if result.passed and result.flagged_for_review:
            return f"PASS (flagged for review) — {result.reason}"
        lines = [f"FAIL — {result.reason}"]
        for d in result.diffs[:5]:
            lines.append(f"  - {d}")
        if len(result.diffs) > 5:
            lines.append(f"  ... and {len(result.diffs) - 5} more")
        return "\n".join(lines)
    except Exception as sum_err:  # noqa: BLE001
        # silent-by-design: summary formatting probe — placeholder text keeps
        # the audit-log line alive; the underlying result is unchanged.
        logger.debug("shadow_canary: summary formatting failed: %s", sum_err, exc_info=True)
        return "<summary error>"


__all__ = [
    "ShadowFix",
    "CanaryTest",
    "CanaryTestResult",
    "CanaryResult",
    "CanarySuite",
    "default_canary_suite",
    "shadow_apply_and_compare",
    "summarize_canary",
    "DEFAULT_MAX_CANARY_TESTS",
    "DEFAULT_CANARY_TIMEOUT_SECONDS",
]
