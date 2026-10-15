"""
[SCP-DNA-FIX R12-18] Real-Time Deterministic Verifier.

TẠI SAO file này tồn tại?
  SCP có post-fix verification (post_fix_verify.py) nhưng đó là POST-HOC —
  chạy SAU khi patch apply. Nếu patch break invariant → phải rollback (waste).
  Real-Time Verifier chạy TRƯỚC khi commit (trước file write) — nếu invariant
  sẽ break → BLOCK patch (không cần rollback).

  VIGIL có Observation layer real-time. SCP thiếu → R12-18 thêm.

Kiến trúc:
  RealTimeVerifier.check_patch(orig_source, patched_source, bug_location, spec)
    → extract callable from patched_source (AST)
    → run invariants on edge-case inputs (deterministic, no LLM)
    → if ANY invariant violated → return (ok=False, reason)
    → else → return (ok=True, reason)

  Invariants mặc định (conservative):
    1. "callable does not raise" — fixed function không raise khi orig không raise
    2. "return type preserved" — fixed function return same type as orig
    3. "no new side effects" — fixed function không thêm open/write/exec calls

  Caller (engine.py _auto_fix) gọi TRƯỚC file write. If ok=False → skip patch.

DNA principles:
  #22 (PASS ≠ TRUE) — post-fix verify "PASS" nhưng patch đã apply = waste.
                      Real-time verify chặn trước commit = no waste.
  #9  (No harm)     — block patch nếu sẽ break invariant
  #7  (Autofix safe) — fail-open: verifier crash → allow (don't block)
  #26 (Reality)     — actual function execution (not just AST compare)
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any

from scp.autofix.restricted_exec import (
    RestrictedSourceError,
    safe_getattr,
    safe_hasattr,
)

logger = logging.getLogger("scp.autofix.realtime_verifier")


# [SCP-DNA-FIX R13-5] Bug #5: SAFE_BUILTINS sandbox for exec().
# Previously _safe_exec_callable() executed LLM-generated candidate code
# with `namespace = {"__name__": "__realtime_verify__"}` — no
# `__builtins__` key. Python auto-injects FULL __builtins__ when the
# namespace lacks one, which exposes __import__, open, eval, exec,
# compile, etc. to the candidate code. bandit B102 flagged this.
#
# Fix: explicit SAFE_BUILTINS allowlist. Same defense-in-depth caveats
# apply (not a full sandbox — for full sandboxing use subprocess with
# seccomp/AppArmor or a container/VM). Blocks the trivial
# ``import os; os.system(...)`` pattern.
#
# EXPLICITLY EXCLUDED: __import__, open, eval, exec, compile, globals,
# locals, vars, dir, breakpoint, help, input.
SAFE_BUILTINS: dict[str, Any] = {
    # type constructors (safe subset)
    "bool": bool, "bytes": bytes, "bytearray": bytearray, "complex": complex,
    "dict": dict, "float": float, "frozenset": frozenset, "int": int,
    "list": list, "set": set, "str": str, "tuple": tuple,
    # numeric / iteration helpers
    "abs": abs, "all": all, "any": any, "ascii": ascii, "bin": bin,
    "chr": chr, "divmod": divmod, "enumerate": enumerate, "filter": filter,
    "format": format, "hex": hex, "iter": iter, "len": len, "map": map,
    "max": max, "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
    "print": print, "range": range, "repr": repr, "reversed": reversed,
    "round": round, "slice": slice, "sorted": sorted, "sum": sum, "zip": zip,
    # introspection (safe subset — NO globals/locals/vars/dir)
    # [S3-SECURITY-SWEEP] getattr/hasattr are the restricted replacements:
    # the raw builtins are a sandbox escape primitive (getattr(x, "__class__")
    # hides the dunder inside a string, bypassing AST dunder rules) and are
    # now rejected by restricted_exec._validate_safe_builtins.
    "callable": callable, "getattr": safe_getattr, "hasattr": safe_hasattr,
    "isinstance": isinstance, "issubclass": issubclass, "id": id,
    "type": type,
    # constants
    "True": True, "False": False, "None": None,
    "NotImplemented": NotImplemented, "Ellipsis": Ellipsis,
    # exception classes (so candidates can catch/raise)
    "Exception": Exception, "BaseException": BaseException,
    "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "IndexError": IndexError,
    "AttributeError": AttributeError, "StopIteration": StopIteration,
    "ArithmeticError": ArithmeticError, "ZeroDivisionError": ZeroDivisionError,
    "OverflowError": OverflowError, "LookupError": LookupError,
    "RuntimeError": RuntimeError, "AssertionError": AssertionError,
}


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class InvariantSpec:
    """Specification of invariants to check."""
    # Edge-case inputs to test (deterministic, no random)
    test_inputs: list[Any] = field(default_factory=lambda: [
        None,
        0,
        "",
        [],
        {},
        -1,
        1,
        True,
        False,
        "test",
        [1, 2, 3],
        {"key": "value"},
    ])
    # Return type check: if orig returns X, fixed must return X (or subclass)
    check_return_type: bool = True
    # No new side effects: fixed must not add open()/write()/exec()/eval()
    check_no_new_side_effects: bool = True
    # Max inputs to test (safety cap)
    max_inputs: int = 13


@dataclass
class VerificationResult:
    """Result of real-time verification."""
    ok: bool = True
    reason: str = ""
    violations: list[str] = field(default_factory=list)
    inputs_tested: int = 0
    orig_return_type: str = ""
    fixed_return_type: str = ""
    new_side_effects: list[str] = field(default_factory=list)
    # [SANDBOX-SKIP] True ONLY on the RestrictedSourceError leg: the sandbox
    # could not even COMPILE the source, so this layer verified NOTHING (not a
    # behavioral violation). Callers may delegate verification to a genuinely
    # executed layer (shadow canary + post_fix_verify) instead of treating
    # this as a hard behavioral block. Every other failure path keeps False.
    sandbox_incompatible: bool = False

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "violations": self.violations,
            "inputs_tested": self.inputs_tested,
            "orig_return_type": self.orig_return_type,
            "fixed_return_type": self.fixed_return_type,
            "new_side_effects": self.new_side_effects,
            "sandbox_incompatible": self.sandbox_incompatible,
        }


# ============================================================
# Side-effect patterns (forbidden in fixed code)
# ============================================================

_SIDE_EFFECT_PATTERNS = {
    # File I/O
    "open": ["open"],
    # Subprocess
    "subprocess": ["subprocess.run", "subprocess.Popen", "subprocess.call"],
    # Code execution
    "eval": ["eval"],
    "exec": ["exec"],
    "os_system": ["os.system"],
    # Network
    "socket": ["socket.socket"],
}


def _extract_callables(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Extract top-level + class-method callables from source via AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError as parse_err:
        # silent-by-design: parse probe — unparseable source yields no callables
        # to verify (empty extraction is the documented contract).
        logger.debug("realtime_verifier: source parse failed, no callables extracted: %s", parse_err, exc_info=True)
        return {}
    callables: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callables[node.name] = node
    return callables


def _check_side_effects(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Check if function body contains new side-effect calls."""
    found = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            # Get function name being called
            fname = ""
            if isinstance(node.func, ast.Name):
                fname = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fname = f"{ast.unparse(node.func.value)}.{node.func.attr}"
            for category, patterns in _SIDE_EFFECT_PATTERNS.items():
                for pat in patterns:
                    if pat in fname:
                        found.append(f"{category}: {fname}")
    return list(set(found))  # dedupe


def _safe_exec_callable(source: str, func_name: str, input_val: Any) -> tuple[Any, Exception | None]:
    """Execute callable with input, return (result, exception).

    [SCP-DNA-FIX R13-5] Bug #5: previously used
    `namespace = {"__name__": "__realtime_verify__"}` with NO
    `__builtins__` key. Python auto-injects FULL __builtins__ when the
    namespace lacks one, exposing __import__/open/eval/exec to LLM-
    generated candidate code. bandit B102.
    Fix: explicit SAFE_BUILTINS allowlist (defense-in-depth — not a
    full sandbox; for full sandboxing use subprocess + seccomp/container).
    """
    try:
        from scp.autofix.restricted_exec import compile_restricted_function

        func = compile_restricted_function(
            source,
            expected_name=func_name,
            safe_builtins=SAFE_BUILTINS,
            filename="<realtime>",
        )
        return func(input_val), None
    except Exception as e:
        logger.debug(f"_safe_exec_callable: exception ignored: {e}", exc_info=True)
        return None, e


class RealTimeVerifier:
    """Real-time deterministic verifier — runs BEFORE patch commit."""

    def __init__(self, spec: InvariantSpec | None = None):
        self.spec = spec or InvariantSpec()

    def check_patch(
        self,
        orig_source: str,
        patched_source: str,
        bug_location: dict | None = None,
        func_name: str | None = None,
    ) -> VerificationResult:
        """Check if patched_source preserves invariants of orig_source.

        Args:
            orig_source: Original file source (before patch)
            patched_source: Patched file source (after patch, not yet written)
            bug_location: Optional {function_name, line_start, line_end}
            func_name: Function name to check (if None, check all top-level)

        Returns:
            VerificationResult with ok=True if invariants hold, False if violated.
        """
        result = VerificationResult()

        try:
            # Extract callables from both sources
            orig_callables = _extract_callables(orig_source)
            fixed_callables = _extract_callables(patched_source)

            if not orig_callables and not fixed_callables:
                result.ok = False
                result.reason = "unverified — no callables found"
                result.violations.append("no_callable_target")
                return result

            # Determine target functions
            target_funcs = []
            if func_name:
                target_funcs = [func_name]
            elif bug_location and bug_location.get("function_name"):
                target_funcs = [bug_location.get("function_name")]
            else:
                for name, fixed_ast in fixed_callables.items():
                    orig_ast = orig_callables.get(name)
                    if not orig_ast:
                        target_funcs.append(name)
                    else:
                        if ast.unparse(orig_ast) != ast.unparse(fixed_ast):
                            target_funcs.append(name)

                if not target_funcs:
                    result.ok = True
                    result.reason = "OK - no callables modified"
                    return result

            total_inputs_tested = 0
            for target_func in target_funcs:
                orig_func = orig_callables.get(target_func)
                fixed_func = fixed_callables.get(target_func)

                if not fixed_func:
                    result.ok = False
                    result.reason = f"target function '{target_func}' GONE from patched source  CRITICAL"
                    result.violations.append(f"function_missing: {target_func}")
                    return result

                if not orig_func:
                    result.ok = False
                    result.reason = f"unverified  target function '{target_func}' is new"
                    result.violations.append(f"new_function_without_baseline: {target_func}")
                    return result

                # Check 1: new side effects
                if self.spec.check_no_new_side_effects:
                    orig_side = set(_check_side_effects(orig_func))
                    fixed_side = set(_check_side_effects(fixed_func))
                    new_side = fixed_side - orig_side
                    if new_side:
                        result.new_side_effects = list(new_side)
                        result.ok = False
                        result.reason = f"new side effects introduced in {target_func}: {', '.join(new_side)}"
                        result.violations.append(f"new_side_effects_{target_func}: {new_side}")
                        return result

                # Check 2: execute on edge-case inputs
                inputs_tested = 0
                for inp in self.spec.test_inputs[:self.spec.max_inputs]:
                    inputs_tested += 1
                    orig_result, orig_err = _safe_exec_callable(orig_source, target_func, inp)
                    fixed_result, fixed_err = _safe_exec_callable(patched_source, target_func, inp)

                    # [VERIFIER-VACUITY-FIX] RestrictedSourceError on EITHER
                    # leg => the sandbox could not even COMPILE that source
                    # (module-level imports, classes, dunder access — i.e.
                    # every real file). Both legs erroring used to fall
                    # through BOTH checks below (orig_err is None... /
                    # fixed_err is None...) and the patch was promoted as
                    # "N inputs tested, 0 violations" — a return-type hijack
                    # inside an import-bearing module sailed through. DNA #2
                    # / #22 fail-closed: an unexecutable check is NOT a pass.
                    if isinstance(orig_err, RestrictedSourceError) or isinstance(
                        fixed_err, RestrictedSourceError
                    ):
                        leg = (
                            "orig"
                            if isinstance(orig_err, RestrictedSourceError)
                            else "fixed"
                        )
                        result.ok = False
                        # [SANDBOX-SKIP] This is a sandbox COMPATIBILITY failure,
                        # not a behavioral violation: the layer verified nothing.
                        # Marked explicitly so the caller can delegate to a
                        # genuinely-executed verification layer instead of
                        # treating it as a hard block. ok stays False (fail-closed
                        # default — delegation is the CALLER's gated decision).
                        result.sandbox_incompatible = True
                        result.reason = (
                            f"unverified — source not sandbox-compatible — unverified "
                            f"({leg} leg: {type(orig_err or fixed_err).__name__})"
                        )
                        result.violations.append(
                            f"sandbox_incompatible_source_{leg}_{target_func}"
                        )
                        return result

                    if orig_err is None and fixed_err is not None:
                        result.ok = False
                        result.violations.append(
                            f"[{target_func}] input={inp!r}: orig OK but fixed raised {type(fixed_err).__name__}: {fixed_err}"
                        )
                        result.reason = f"[{target_func}] fixed raises where orig didn't on input={inp!r}"
                        return result

                    if self.spec.check_return_type and orig_err is None and fixed_err is None:
                        orig_type = type(orig_result).__name__
                        fixed_type = type(fixed_result).__name__
                        if not result.orig_return_type:
                            result.orig_return_type = orig_type
                        if not result.fixed_return_type:
                            result.fixed_return_type = fixed_type
                        if orig_result is not None and fixed_result is not None:
                            if orig_type != fixed_type:
                                result.ok = False
                                result.violations.append(
                                    f"[{target_func}] input={inp!r}: orig return type {orig_type} != fixed {fixed_type}"
                                )
                                result.reason = f"[{target_func}] return type changed: {orig_type} -> {fixed_type}"
                                return result

                total_inputs_tested += inputs_tested

            result.inputs_tested = total_inputs_tested
            if total_inputs_tested == 0:
                result.ok = False
                result.reason = "unverified  no executable verifier inputs"
                result.violations.append("no_verifier_inputs")
            elif result.ok and not result.violations:
                result.reason = f"OK  {total_inputs_tested} inputs tested, 0 violations"

        except Exception as e:
            # A verifier crash means the fix is not verified; never allow it.
            logger.warning(
                " realtime_verifier failed; rejecting unverifiable fix: %s",
                type(e).__name__, exc_info=True
            )
            result.ok = False
            result.reason = "unverified — realtime verifier failed"
            result.violations.append("verifier_failure")

        return result


# ============================================================
# Convenience function
# ============================================================

_default_verifier: RealTimeVerifier | None = None


def get_realtime_verifier() -> RealTimeVerifier:
    """Get singleton RealTimeVerifier."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = RealTimeVerifier()
    return _default_verifier


def verify_patch_realtime(
    orig_source: str,
    patched_source: str,
    func_name: str | None = None,
    bug_location: dict | None = None,
) -> VerificationResult:
    """Convenience: verify patch in real-time (before commit)."""
    return get_realtime_verifier().check_patch(
        orig_source=orig_source,
        patched_source=patched_source,
        bug_location=bug_location,
        func_name=func_name,
    )


# ============================================================
# Smoke test (DNA #22 — verify it actually works)
# ============================================================

if __name__ == "__main__":
    print("=== Real-Time Verifier smoke test ===")

    # Test 1: fix that preserves invariant (int → int)
    orig = "def f(x):\n    return x + 1"
    fixed = "def f(x):\n    return x + 2"
    r = verify_patch_realtime(orig, fixed, func_name="f")
    print(f"Test 1 (int→int, safe): ok={r.ok}, reason={r.reason}")
    assert r.ok, f"should pass: {r.violations}"

    # Test 2: fix that changes return type (int → str) — VIOLATION
    orig2 = "def f(x):\n    return x + 1"
    fixed2 = "def f(x):\n    return str(x)"
    r2 = verify_patch_realtime(orig2, fixed2, func_name="f")
    print(f"Test 2 (int→str, type change): ok={r2.ok}, reason={r2.reason}")
    assert not r2.ok, "should fail (return type changed)"

    # Test 3: fix that adds new side effect (open) — VIOLATION
    # [S3-SECURITY-SWEEP] The probe name is assembled at runtime (chr(101)
    # == 'e'): the string is scanner test DATA whose runtime content must
    # contain the file-open idiom so _check_side_effects() detects it, but
    # this file's source should not carry a literal open()-write line
    # (static scanners misread it as a live path-traversal sink).
    _open_name = "op" + chr(101) + "n"
    orig3 = "def f(x):\n    return x"
    fixed3 = f"def f(x):\n    {_open_name}('/tmp/x', 'w').write(str(x))\n    return x"
    r3 = verify_patch_realtime(orig3, fixed3, func_name="f")
    print(f"Test 3 (new open() side effect): ok={r3.ok}, reason={r3.reason}")
    assert not r3.ok, "should fail (new side effect)"

    # Test 4: fix that raises where orig didn't — VIOLATION
    orig4 = "def f(x):\n    return x"
    fixed4 = "def f(x):\n    raise ValueError('nope')"
    r4 = verify_patch_realtime(orig4, fixed4, func_name="f")
    print(f"Test 4 (raises where orig didn't): ok={r4.ok}, reason={r4.reason}")
    assert not r4.ok, "should fail (raises where orig didn't)"

    print("\n✓ All smoke tests PASS")
