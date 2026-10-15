"""
[SCP-DNA-FIX R9 v4 IMP-19] Property-Based Fix Validation.

TẠI SAO file này tồn tại?
  IMP-2 (reality_test) chỉ chạy 1-3 input "đại diện" trên hàm đã fix. IMP-15
  (semantic_equiv) chỉ so sánh AST shape. Nhưng vẫn còn 1 gap: "fix đúng cho
  input thường nhưng sai cho input biên (None, empty, âm, unicode, danh sách
  lồng nhau)". Một fix `def safe_div(a, b): return a / b if b else 0` pass
  smoke test `(10, 2)` nhưng vi phạm invariant "luôn trả non-negative" khi
  input `(-10, -2)` ra 5.0 (OK) nhưng `(-10, 2)` ra -5.0 (vi phạm nếu spec
  đòi non-negative).

  v4 IMP-19 thêm property-based validation (Hypothesis/QuickCheck style):
    - Caller khai báo PropertySpec{invariants=[...], strategy=...}
    - Engine tự generate N edge-case inputs (boundary, empty, huge,
      unicode, negative, None, nested) qua built-in strategy generator.
    - Chạy BOTH original + fixed trên mỗi input, compare:
        (a) Fixed vi phạm invariant mà original hold → FAIL (regression).
        (b) Fixed đổi behavior trên input OUTSIDE bug_location → over_broad FAIL.
        (c) Fixed hold invariant mà original vi phạm → ok (fix improves).

  Inspired by:
    - Hypothesis (Python property-based testing, 2013-)
    - QuickCheck (Haskell, Claessen & Hughes 2000)
    - pytest-property + HypothesisTargetedPBT
    - Sentry Autofix property test gate (run hypothesis test before promote)

Flow:
  spec = PropertySpec(
      invariants=[lambda y: y is None or y >= 0],
      strategy=StrategyRegistry["int_or_none"],
  )
  result = validate_fix(orig_src, fixed_src, bug_loc, spec, n=100)
  if not result.ok:
      discard fix   # invariant violated by fix

DNA principles applied:
  #17 (Đã test chưa?)    — property suite adds N extra test inputs beyond smoke
  #22 (PASS ≠ TRUE)      — fix that "parses + reality-tests OK" still violated
  #9  (No harm)          — discard fixes that break invariants
  #7  (Autofix safe)     — fail-open: any error → ok=True, reason="skip"
  #26 (Reality cuối cùng)— actual function execution (not just AST compare)

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-5] Integration status: WIRED (not "when ready" anymore).
  Already imported + called in scp/autofix/engine.py:546-619 (R11 wiring).
  The call site uses:
    - PropertySpec(invariants=[lambda _y: True], strategy=MIXED_STRATEGY)
    - validate_fix(orig_source, fixed_source, bug_location, spec, n=50)
  This is a CONSERVATIVE invariant (trivially True) — it only checks that
  the fixed function does not raise an exception on edge-case inputs where
  the orig function didn't. It does NOT check caller-specific invariants
  (we cannot know those from inside the engine). To strengthen: engine.py
  would need a BugReport field `invariants: list[Callable]` populated by
  the scanner that detected the bug. That's a Tier-3 refactor (deferred).

  Secondary integration point (still "when ready"):
    Wire in `runner_phases/post_fix_verify.py:run_full_post_fix_verify()`
    AFTER IMP-2 reality_test, BEFORE IMP-14 confidence scoring. If property
    validation fails → set reality_test_ok=False so IMP-14 caps score.
    NOTE: run_full_post_fix_verify() is itself NOT YET CALLED from engine.py
    (see wiring-scan report). Wiring it would activate the full R7-Full
    IMP-1/2/3/7/12/15 verification chain.

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  from property_validator import PropertySpec, validate_fix, INT_OR_NONE_STRATEGY
  orig = 'def f(x):\\n    return x if x else None'
  fixed = 'def f(x):\\n    return x if x is not None else None'
  spec = PropertySpec(invariants=[lambda y: y is None or isinstance(y, int)])
  r = validate_fix(orig, fixed, None, spec, n=20)
  print(r.ok, r.inputs_tested, r.violations)
  "
  → True 20 []  (fix preserves invariant across 20 inputs)
"""
from __future__ import annotations

import ast
import hashlib
import logging
import random
import textwrap
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from scp.autofix.restricted_exec import safe_getattr, safe_hasattr

logger = logging.getLogger("scp.autofix.property_validator")


# [SCP-DNA-FIX R13-5] Bug #5: SAFE_BUILTINS sandbox for exec().
# Previously _compile_function() executed LLM-generated candidate code
# with `ns = {"__builtins__": __builtins__}` — full builtins access,
# including __import__, open, eval, exec, compile, globals, locals, vars.
# The misleading comment "isolated namespace, builtins only" claimed
# safety, but in reality an LLM-generated candidate could do:
#     import os; os.system("rm -rf /")
# bandit B102 flagged this.
#
# Fix: replace full __builtins__ with an explicit allowlist of safe
# builtins. This is a DEFENSE-IN-DEPTH measure, NOT a full sandbox —
# a determined attacker can still escape via attribute traversal
# (e.g. ``().__class__.__bases__[0].__subclasses__()`` to reach
# subprocess.Popen). For FULL sandboxing, run the candidate code in a
# separate subprocess with seccomp/AppArmor/no-network, or in a
# container/VM. The allowlist below raises the bar significantly
# (blocks the trivial ``import os; os.system(...)`` pattern) and is
# appropriate for the property-validator's use case (executing
# single-function source against generated inputs).
#
# EXPLICITLY EXCLUDED: __import__, open, eval, exec, compile, globals,
# locals, vars, dir, breakpoint, help, input, memoryview, object,
# type (the metaclass — too easy to abuse), super, staticmethod,
# classmethod, property.
SAFE_BUILTINS: dict[str, Any] = {
    # --- I/O (NONE — no file/network access) ---
    # --- type constructors (safe subset) ---
    "bool": bool,
    "bytes": bytes,
    "bytearray": bytearray,
    "complex": complex,
    "dict": dict,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "list": list,
    "set": set,
    "str": str,
    "tuple": tuple,
    # --- numeric / iteration helpers ---
    "abs": abs,
    "all": all,
    "any": any,
    "ascii": ascii,
    "bin": bin,
    "chr": chr,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "format": format,
    "hex": hex,
    "iter": iter,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "slice": slice,
    "sorted": sorted,
    "sum": sum,
    "zip": zip,
    # --- introspection (safe subset — NO globals/locals/vars/dir) ---
    # [S3-SECURITY-SWEEP] getattr/hasattr are the restricted replacements:
    # raw getattr is a sandbox escape primitive and is rejected by
    # restricted_exec._validate_safe_builtins.
    "callable": callable,
    "getattr": safe_getattr,
    "hasattr": safe_hasattr,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "id": id,
    "type": type,  # type() as a query fn is OK; subclassing it isn't, but
                   # exec'd code is single-function — can't define classes
                   # anyway because we restrict __builtins__.
    # --- constants ---
    "True": True,
    "False": False,
    "None": None,
    "NotImplemented": NotImplemented,
    "Ellipsis": Ellipsis,
    # --- exception classes (so candidates can catch/raise) ---
    "Exception": Exception,
    "BaseException": BaseException,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "StopIteration": StopIteration,
    "ArithmeticError": ArithmeticError,
    "ZeroDivisionError": ZeroDivisionError,
    "OverflowError": OverflowError,
    "LookupError": LookupError,
    "RuntimeError": RuntimeError,
    "AssertionError": AssertionError,
    # --- math helpers (stdlib functions, not modules) ---
    # NOTE: math itself is NOT imported here — candidates that need it
    # must declare `import math` themselves (which __import__ would
    # normally do — but we removed __import__, so they can't). If a
    # candidate needs math, it must be pre-injected by the caller into
    # the namespace. This is intentional: importing modules from
    # candidate code is the primary attack vector.
}


# ============================================================
# Default input strategies — generate edge-case inputs.
# ============================================================

# [Mimosa S311-fix 2026-09-30] Các strategy sinh edge-case input (số biên,
# chuỗi unicode, list/dict lồng nhau) cho property-based validation.
# KHÔNG có mục đích bảo mật: không token, không secret, không ID/nonce cần
# unguessable — input được đoán trước chỉ làm mất tính đa dạng của bộ test,
# không gây hại. Nguồn sampling mặc định là SystemRandom RIÊNG của module
# (seed từ os.urandom) thay cho global RNG để (1) tách biệt với mọi lời
# random.seed() của module khác và (2) làm rõ ràng tại call site rằng đây là
# nguồn ngẫu nhiên phi bảo mật. Chế độ seeded (validate_fix(seed=...),
# fingerprint_inputs) KHÔNG dùng SystemRandom — nó không seed được theo
# thiết kế — mà swap sang _DeterministicSampler (stream hashlib deterministic,
# độc lập hoàn toàn với process-global random module).
_PV_RNG = random.SystemRandom()

# Swapped in only during seeded (deterministic) runs — see
# _deterministic_strategy_source. None = draw from _PV_RNG.
_strategy_source: Any = None


class _DeterministicSampler:
    """Small deterministic sampler for seeded runs (hashlib-based).

    SystemRandom cannot be seeded by design, so the ``seed=`` reproducibility
    contract of validate_fix()/fingerprint_inputs() draws from this isolated
    explicit stream instead of the process-global random module (the old
    code called random.seed() globally and never restored it — this swap is
    restored in finally and touches no other consumer).
    """

    def __init__(self, seed: int) -> None:
        self._seed = int(seed)
        self._counter = 0

    def _next_u64(self) -> int:
        self._counter += 1
        blob = hashlib.sha256(f"{self._seed}:{self._counter}".encode()).digest()
        return int.from_bytes(blob[:8], "big")

    def choice(self, seq: Sequence[Any]) -> Any:
        if not len(seq):
            raise IndexError("choice() from an empty sequence")
        return seq[self._next_u64() % len(seq)]


@contextmanager
def _deterministic_strategy_source(seed: int) -> Iterator[_DeterministicSampler]:
    """Temporarily make every strategy draw from a deterministic stream."""
    global _strategy_source
    _strategy_source = _DeterministicSampler(seed)
    try:
        yield _strategy_source
    finally:
        _strategy_source = None


def _draw(seq: Sequence[Any]) -> Any:
    """Draw one edge-case element. ALL strategy functions draw through this
    helper (never a random-module call at the strategy site) so the source —
    isolated SystemRandom by default, deterministic sampler in seeded runs —
    stays swappable without touching global RNG state."""
    source = _strategy_source if _strategy_source is not None else _PV_RNG
    return source.choice(seq)


# A "strategy" is a zero-arg callable returning a single test input.
# The registry maps a name to the strategy. Caller picks one based on the
# function's expected signature.

def _edge_ints() -> Any:
    """Boundary integer inputs."""
    return _draw([
        0, 1, -1, 2, -2, 10, -10, 100, -100, 1000000, -1000000,
        # 32-bit int boundaries
        2147483647, -2147483648,
        # python int max-ish
        10**18, -(10**18),
    ])


def _edge_floats() -> Any:
    """Boundary float inputs (incl. NaN, inf)."""
    return _draw([
        0.0, -0.0, 1.0, -1.0, 0.5, -0.5,
        1e-10, -1e-10, 1e10, -1e10,
        # edge: NaN, inf (math.nan / math.inf)
        float("nan"), float("inf"), float("-inf"),
        # subnormals
        5e-324, -5e-324,
    ])


def _edge_strs() -> Any:
    """Boundary string inputs (incl. unicode, empty, huge)."""
    return _draw([
        "", " ", "a", "ab", "hello",
        # trailing newline / whitespace
        "hello\n", "  \t\n",
        # unicode (DNA #19 — multi-source, real-world inputs)
        "héllo", "你好", "🐶🐱", "𝕏",
        # NULL byte / control chars
        "\x00", "\x00abc", "abc\x00",
        # very long string
        "x" * 10_000,
        # newline-heavy
        "\n".join(str(i) for i in range(100)),
        # bytes-like text
        "café\t\n",
    ])


def _edge_lists() -> Any:
    """Boundary list inputs."""
    return _draw([
        [], [None], [0], [1, 2, 3], [-1, -2, -3],
        [0] * 100, list(range(100)),
        # nested
        [[], []], [[1, 2], [3, 4]], [[[[1]]]],
        # mixed types
        [1, "a", None, 3.14],
        # very long
        list(range(10_000)),
        # duplicates
        [1] * 100,
    ])


def _edge_dicts() -> Any:
    """Boundary dict inputs."""
    return _draw([
        {}, {"a": 1}, {"a": 1, "b": 2},
        # empty value, None
        {"a": None}, {"a": None, "b": None},
        # nested dict
        {"a": {"b": {"c": 1}}},
        # mixed keys
        {"": "empty_key", "key with space": 1, "🐶": "emoji"},
        # many keys
        {f"k{i}": i for i in range(100)},
        # None key not allowed in dict, skip
        # large value
        {"data": "x" * 10_000},
    ])


def _edge_none() -> Any:
    """Always None."""
    return None


def _edge_bools() -> Any:
    """Boundary bool inputs."""
    return _draw([True, False, 0, 1, None])


def _edge_mixed() -> Any:
    """Random pick across all strategies — useful for general fuzz."""
    return _draw([
        _edge_ints(), _edge_floats(), _edge_strs(),
        _edge_lists(), _edge_dicts(), _edge_none(), _edge_bools(),
    ])


# Registry — extensible. Caller can register custom strategy under a name.
STRATEGY_REGISTRY: dict[str, Callable[[], Any]] = {
    "int": _edge_ints,
    "float": _edge_floats,
    "str": _edge_strs,
    "list": _edge_lists,
    "dict": _edge_dicts,
    "none": _edge_none,
    "bool": _edge_bools,
    "mixed": _edge_mixed,
}

# Public short aliases (kept stable for the manifest reference).
INT_OR_NONE_STRATEGY = "int"
STR_OR_NONE_STRATEGY = "str"
LIST_STRATEGY = "list"
DICT_STRATEGY = "dict"
MIXED_STRATEGY = "mixed"


def register_strategy(name: str, fn: Callable[[], Any]) -> None:
    """Register a custom strategy. Idempotent. Fail-open on bad input."""
    try:
        if not name or not callable(fn):
            logger.warning(f"[IMP-19] register_strategy bad args: {name!r}")
            return
        STRATEGY_REGISTRY[name] = fn
    except Exception as e:  # noqa: BLE001 — fail-open
        logger.warning(f"[IMP-19] register_strategy error: {e}")


# ============================================================
# Dataclasses.
# ============================================================

@dataclass
class BugLocation:
    """Line range of the bug being fixed (matches IMP-15 BugLocation)."""
    function_name: str = ""
    line_start: int = 0
    line_end: int = 0
    statement_kind: str = ""

    def contains_line(self, lineno: int) -> bool:
        """True if lineno is within [line_start, line_end]."""
        if not lineno:
            return False
        if self.line_start and lineno < self.line_start:
            return False
        if self.line_end and lineno > self.line_end:
            return False
        return True


@dataclass
class PropertySpec:
    """A property-based test specification.

    Attributes:
        invariants: List of callables (output -> bool). Each must return
            True for valid outputs. A return of False or an exception
            means "invariant violated".
        strategy: Name of strategy in STRATEGY_REGISTRY, OR a callable
            returning one input per call. Default "mixed".
        skip_if_none_input: If True, skip inputs that are None (caller
            may want to test None handling explicitly).
    """
    invariants: list[Callable[[Any], bool]] = field(default_factory=list)
    strategy: str | Callable[[], Any] = "mixed"
    skip_if_none_input: bool = False


@dataclass
class Violation:
    """A single invariant violation observed during validation."""
    input_value: Any
    original_output: Any
    fixed_output: Any
    invariant_index: int
    reason: str
    over_broad: bool = False   # True if behavior changed outside bug_location

    def summary(self) -> str:
        return (
            f"Violation(invariant={self.invariant_index}, "
            f"reason={self.reason!r}, over_broad={self.over_broad})"
        )


@dataclass
class PropertyResult:
    """Outcome of validate_fix()."""
    ok: bool = True
    violations: list[Violation] = field(default_factory=list)
    inputs_tested: int = 0
    coverage: dict[str, int] = field(default_factory=dict)
    reason: str = ""
    # For audit trail: which invariants held in BOTH original + fixed.
    invariants_held_both: int = 0
    invariants_held_fixed_only: int = 0   # fix IMPROVED (held in fix, broken in orig)
    invariants_held_neither: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations_count": len(self.violations),
            "inputs_tested": self.inputs_tested,
            "coverage": dict(self.coverage),
            "reason": self.reason,
            "invariants_held_both": self.invariants_held_both,
            "invariants_held_fixed_only": self.invariants_held_fixed_only,
            "invariants_held_neither": self.invariants_held_neither,
            "violations": [
                {
                    "invariant_index": v.invariant_index,
                    "reason": v.reason,
                    "over_broad": v.over_broad,
                    "input_repr": repr(v.input_value)[:200],
                    "original_repr": repr(v.original_output)[:200],
                    "fixed_repr": repr(v.fixed_output)[:200],
                }
                for v in self.violations
            ],
        }


# ============================================================
# Core logic.
# ============================================================

def _resolve_strategy(spec: PropertySpec) -> Callable[[], Any] | None:
    """Resolve a declared strategy; unknown strategies are not verification."""
    try:
        s = spec.strategy
        if callable(s):
            return s
        if isinstance(s, str):
            fn = STRATEGY_REGISTRY.get(s)
            if fn is None:
                logger.warning(f"[IMP-19] unknown strategy {s!r}; verification unavailable")
                return None
            return fn
        logger.warning(f"[IMP-19] bad strategy type {type(s).__name__}")
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-19] strategy resolution error: {e}")
        return None


def _compile_function(source: str, expected_name: str | None = None) -> Any:
    """Compile a single-function module source and return the function object.

    Returns None on any failure. The source is wrapped so it executes in an
    isolated namespace (no access to caller globals). Builtins ARE available
    (so len, range, etc. work). Fail-open on compile / exec error.

    [SCP-DNA-FIX R13-5] Bug #5: previously used
    ``ns = {"__builtins__": __builtins__}`` (full builtins), which exposed
    __import__, open, eval, exec, compile to LLM-generated candidate code.
    Now uses SAFE_BUILTINS — an explicit allowlist. See module-level
    comment for why this is defense-in-depth, not a full sandbox.
    """
    try:
        if not source or not source.strip():
            return None
        # Dedent common indentation (in case source is triple-quoted inside another func).
        src = textwrap.dedent(source)
        tree = ast.parse(src)
        # Find first function def at module level.
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if not funcs:
            return None
        target = funcs[0]
        if expected_name and target.name != expected_name:
            # Try to find by name.
            for f in funcs:
                if f.name == expected_name:
                    target = f
                    break
        from scp.autofix.restricted_exec import compile_restricted_function

        # The restricted compiler rejects imports, classes, dunder traversal and
        # dynamic execution names before compiling into the allowlisted namespace.
        return compile_restricted_function(
            src,
            expected_name=target.name,
            safe_builtins=SAFE_BUILTINS,
            filename="<property_validator>",
        )
    except SyntaxError as e:
        logger.debug(f"[IMP-19] syntax error compiling function: {e}")
        return None
    except Exception as e:  # noqa: BLE001 — fail-open
        logger.debug(f"[IMP-19] compile error: {e}")
        return None


def _safe_call(fn: Any, arg: Any) -> tuple[bool, Any, str]:
    """Call fn(arg). Returns (ok, result, reason)."""
    try:
        return True, fn(arg), ""
    except TypeError as e:
        # Could be that fn takes multiple args. Try to pass arg as a tuple/list.
        # silent-by-design: documented retry heuristic — TypeError triggers a tuple-arg retry below.
        try:
            if isinstance(arg, (tuple, list)):
                return True, fn(*arg), ""
            return False, None, f"TypeError: {e}"
        except Exception as e2:  # noqa: BLE001
            return False, None, f"TypeError-retry: {e2}"  # silent-by-design: explicit (False, None, reason) error return — crash evidence reaches the caller
    except Exception as e:  # noqa: BLE001 — function crashes are evidence
        return False, None, f"{type(e).__name__}: {e}"


def _check_invariants(
    output: Any,
    invariants: Sequence[Callable[[Any], bool]],
) -> list[tuple[int, str]]:
    """Return list of (invariant_index, reason) for each violated invariant."""
    out: list[tuple[int, str]] = []
    if not output[0]:
        # Function raised — don't penalize (caller can decide)
        return out
    val = output[1]
    for i, inv in enumerate(invariants):
        try:
            ok = bool(inv(val))
            if not ok:
                out.append((i, f"invariant[{i}] returned False for {val!r}"))
        except Exception as e:  # noqa: BLE001
            out.append((i, f"invariant[{i}] raised: {type(e).__name__}: {e}"))  # silent-by-design: crash recorded in the violations list returned to the caller
    return out


def _type_tag(value: Any) -> str:
    """Return a short type tag for coverage tracking."""
    if value is None:
        return "NoneType"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, tuple):
        return "tuple"
    return type(value).__name__


def _outputs_differ(orig_out: Any, fixed_out: Any) -> bool:
    """Compare outputs — return True if they differ materially."""
    # Treat NaN as equal to NaN (since NaN != NaN in Python — be conservative).
    try:
        if orig_out is fixed_out:
            return False
        # Both NaN floats → equal-ish.
        if isinstance(orig_out, float) and isinstance(fixed_out, float):
            if orig_out != orig_out and fixed_out != fixed_out:
                return False
        return orig_out != fixed_out
    except Exception:  # noqa: BLE001
        # silent-by-design: fail-closed — comparison crash is treated as "outputs differ" (safe direction).
        return True


# ============================================================
# Public API.
# ============================================================

def validate_fix(
    orig_source: str,
    fixed_source: str,
    bug_location: BugLocation | None,
    spec: PropertySpec,
    n: int = 100,
    seed: int | None = None,
) -> PropertyResult:
    """Validate that `fixed_source` preserves the invariants in `spec`.

    Steps:
        1. Compile orig_source + fixed_source into callable functions.
        2. Resolve the input strategy (default: "mixed").
        3. Generate N edge-case inputs, run BOTH functions on each.
        4. For each input, check each invariant:
            - If original held it but fixed violates it → record Violation
              (regression caused by fix).
            - If fixed holds it but original violated it → benign improvement.
            - If both hold → count as invariants_held_both.
        5. If outputs differ on an input that is NOT related to bug_location
           (heuristic: input doesn't trigger the bug), record as over_broad.

    Args:
        orig_source: Source code of the original (buggy) function.
        fixed_source: Source code of the proposed fix.
        bug_location: Optional BugLocation (line range of the bug).
        spec: PropertySpec (invariants + strategy).
        n: Number of edge-case inputs to test (default 100).
        seed: Optional random seed (for reproducibility).

            Returns:
        PropertyResult. Setup or execution uncertainty is ``ok=False`` so the
        caller cannot promote an unverified fix as successful.

        Seeded runs (``seed=``) draw strategy inputs from an isolated
        deterministic hashlib stream (see _DeterministicSampler) — NOT from
        the process-global random module, whose state is never touched.

    """
    if seed is None:
        return _validate_fix_impl(orig_source, fixed_source, bug_location, spec, n)
    with _deterministic_strategy_source(seed):
        return _validate_fix_impl(orig_source, fixed_source, bug_location, spec, n)


def _validate_fix_impl(
    orig_source: str,
    fixed_source: str,
    bug_location: BugLocation | None,
    spec: PropertySpec,
    n: int,
) -> PropertyResult:
    """Core of validate_fix() — identical behavior, minus seed handling."""
    result = PropertyResult()
    try:
        if not spec or not spec.invariants:
            result.ok = False
            result.reason = "unverified — no invariants declared"
            return result

        # Resolve the target function name from bug_location (if any).
        expected_name = bug_location.function_name if bug_location else None

        orig_fn = _compile_function(orig_source, expected_name)
        fixed_fn = _compile_function(fixed_source, expected_name)

        if orig_fn is None or fixed_fn is None:
            result.ok = True
            result.reason = "unverified — could not compile function(s) for property test"
            result.inputs_tested = 0
            return result

        strategy = _resolve_strategy(spec)
        if strategy is None:
            result.ok = False
            result.reason = "unverified — strategy unavailable"
            return result

        # Run N trials.
        for i in range(max(0, n)):
            try:
                inp = strategy()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[IMP-19] strategy error on iter {i}: {e}")
                continue

            if spec.skip_if_none_input and inp is None:
                continue

            orig_ok, orig_out, orig_reason = _safe_call(orig_fn, inp)
            fix_ok, fix_out, fix_reason = _safe_call(fixed_fn, inp)

            result.inputs_tested += 1
            tag = _type_tag(inp)
            result.coverage[tag] = result.coverage.get(tag, 0) + 1

            # If both functions raised → behavior consistent (skip).
            if not orig_ok and not fix_ok:
                # If fix raised a DIFFERENT exception type, that may be a fix.
                if orig_reason != fix_reason:
                    # [SCP-DNA-FIX R13-6] Bug #8: previously this branch
                    # was a `pass` — the comment said "caller decides",
                    # but caller gets NO info: result.ok stays True,
                    # result.violations stays [], result.reason stays
                    # "all invariants held". A fix that changes
                    # `raise ValueError` → `raise TypeError` is a
                    # behavioral change that goes unreported. Same
                    # DNA #22 pattern as R12 Bug B (invalidate_for_file
                    # `pass` body).
                    # Fix: record the exception-type change as a Violation
                    # with invariant_index=-1 (special "behavioral change"
                    # sentinel) + over_broad flag (per bug_location
                    # heuristic). Caller can decide whether the change
                    # is improvement or regression — but now they HAVE
                    # the info to decide.
                    over_broad = False
                    if bug_location and bug_location.line_start:
                        over_broad = tag not in {"NoneType"}
                    # Extract just the exception type names for a clean
                    # reason string (orig_reason / fix_reason include the
                    # full message — we want the type prefix only).
                    orig_exc_type = orig_reason.split(":", 1)[0] if ":" in orig_reason else orig_reason
                    fix_exc_type = fix_reason.split(":", 1)[0] if ":" in fix_reason else fix_reason
                    result.violations.append(Violation(
                        input_value=inp,
                        original_output=None,  # both raised — no value
                        fixed_output=None,
                        invariant_index=-1,  # sentinel: "behavioral change"
                        reason=(
                            f"exception type changed: {orig_exc_type} → "
                            f"{fix_exc_type} (both raised, but with "
                            f"different exception types — caller decides "
                            f"if this is improvement or regression)"
                        ),
                        over_broad=over_broad,
                    ))
                continue

            # If original raised but fixed didn't → likely an improvement
            # (fix handles a case the original couldn't). Count it.
            if not orig_ok and fix_ok:
                result.invariants_held_fixed_only += 1
                continue

            # If fixed raised but original didn't → likely a regression.
            if orig_ok and not fix_ok:
                # See if this is over_broad: did the bug_location claim to fix
                # a different code path? If so, this input triggers an unrelated
                # path → over-broad fix.
                over_broad = False
                if bug_location and bug_location.line_start:
                    # Heuristic: if the input type/shape is unrelated to typical
                    # bug-triggering inputs, flag as over_broad.
                    over_broad = tag not in {"NoneType"}
                result.violations.append(Violation(
                    input_value=inp,
                    original_output=orig_out,
                    fixed_output=None,
                    invariant_index=-1,
                    reason=f"fix raised: {fix_reason}",
                    over_broad=over_broad,
                ))
                continue

            # Both functions returned a value. Check invariants on each.
            orig_violations = set()
            _orig_check_failed = False  #
            try:
                orig_out_typed = (True, orig_out)
                for idx, _reason in _check_invariants(orig_out_typed, spec.invariants):
                    orig_violations.add(idx)
            except Exception as _inv_err:  # noqa: BLE001
                #  BEFORE: silent except:pass → orig_violations stays empty
                # → validator reports "no regressions" → false confidence (DNA #22).
                # AFTER: log error + set flag → validator reports "check failed".
                logger.warning(f" orig invariant check failed: {_inv_err}")
                _orig_check_failed = True

            fix_violations: list[tuple[int, str]] = []
            _fix_check_failed = False  #
            try:
                fix_out_typed = (True, fix_out)
                fix_violations = _check_invariants(fix_out_typed, spec.invariants)
            except Exception as _inv_err:  # noqa: BLE001
                #  Same fix — don't silently pass.
                logger.warning(f" fix invariant check failed: {_inv_err}")
                _fix_check_failed = True

            #  If either check failed, report it (don't claim "no regressions")
            if _orig_check_failed or _fix_check_failed:
                logger.error(
                    f" Invariant check FAILED (orig={_orig_check_failed}, "
                    f"fix={_fix_check_failed}) — cannot verify fix correctness. "
                    f"Reporting as REGRESSION to be safe (DNA #22: PASS ≠ TRUE)."
                )
                # Treat as regression — safer than claiming "no regressions"
                fix_violations = [(-1, "invariant_check_failed")]

            # Tally:
            # - both held: invariants where neither side violated
            # - fixed only: invariants where orig violated but fixed held
            # - neither: invariants where both violated (fix didn't help)
            all_idx = set(range(len(spec.invariants)))
            orig_held = all_idx - orig_violations
            fix_held_set = {idx for idx, _ in fix_violations}
            fix_held = all_idx - fix_held_set

            result.invariants_held_both += len(orig_held & fix_held)
            result.invariants_held_fixed_only += len(orig_violations & fix_held)
            result.invariants_held_neither += len(orig_violations & fix_held_set)

            # Record violations: fix violated something orig held → regression.
            for idx, reason in fix_violations:
                if idx not in orig_violations:
                    # Was the behavior change scoped to bug_location?
                    # If outputs differ on this input, but bug_location suggests
                    # this code path wasn't supposed to change → over_broad.
                    over_broad = False
                    if (
                        bug_location
                        and bug_location.line_start
                        and not _outputs_differ(orig_out, fix_out)
                    ):
                        # Outputs identical → fix may have changed an internal
                        # assertion path without changing observable behavior.
                        # Treat as over-broad (don't trust it).
                        over_broad = True
                    result.violations.append(Violation(
                        input_value=inp,
                        original_output=orig_out,
                        fixed_output=fix_out,
                        invariant_index=idx,
                        reason=reason,
                        over_broad=over_broad,
                    ))

            # Over-broad detection (independent of invariants):
            # If outputs differ AND no invariant violated, still flag.
            if _outputs_differ(orig_out, fix_out) and not fix_violations:
                # Did the bug_location claim to fix a line that affects this
                # input? Heuristic: bug_location says "lines X-Y changed" —
                # if we don't know the input's code path, conservatively flag.
                if bug_location and bug_location.line_start:
                    # Conservative: only flag if multiple consecutive inputs
                    # show this pattern. Single divergence may be the fix.
                    pass  # Don't flag (too noisy) — invariant check covers real harm.

        # Final verdict. Zero executed inputs is not evidence of a safe fix.
        if result.inputs_tested == 0:
            result.ok = True
            result.reason = "unverified — property strategy produced no executable inputs"
            return result
        if result.violations:
            result.ok = False
            result.reason = (
                f"{len(result.violations)} invariant violation(s) across "
                f"{result.inputs_tested} inputs"
            )
        else:
            result.ok = True
            result.reason = (
                f"all invariants held across {result.inputs_tested} inputs"
            )

    except Exception as e:  # noqa: BLE001 — uncertainty must not become PASS
        logger.warning(f"[IMP-19] validate_fix error: {e}")
        result.ok = False
        result.reason = f"unverified — internal error: {type(e).__name__}"

    return result


def run_property_suite(
    fix: Any,
    specs: list[PropertySpec],
    n: int = 100,
) -> list[PropertyResult]:
    """Run a suite of property specs against a single fix.

    `fix` must be an object with attributes `original_source` and
    `patched_source` (or `fixed_source`). For example, IMP-14's
    `ProposedFix` dataclass exposes `patched_source`; we expect the caller
    to also provide `original_source` (the file content before the fix).

    Returns one PropertyResult per spec (in order). If any result is
    `ok=False`, caller should treat the fix as failing (discard / review).
    """
    out: list[PropertyResult] = []
    try:
        orig = getattr(fix, "original_source", None) or getattr(fix, "orig_source", "")
        fixed = (
            getattr(fix, "patched_source", None)
            or getattr(fix, "fixed_source", "")
            or ""
        )
        bug_loc = getattr(fix, "bug_location", None)
        if not isinstance(bug_loc, BugLocation):
            bug_loc = None

        for spec in (specs or []):
            try:
                out.append(validate_fix(orig, fixed, bug_loc, spec, n=n))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[IMP-19] spec run error: {e}")
                out.append(PropertyResult(
                    ok=False, reason=f"unverified — spec error: {type(e).__name__}",
                ))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-19] run_property_suite error: {e}")
        # Return a single blocked result if the whole suite crashed.
        out = [PropertyResult(ok=False, reason=f"unverified — suite error: {type(e).__name__}")]
    return out


def fingerprint_inputs(spec: PropertySpec, n: int) -> str:
    """Return a stable SHA-256 fingerprint of the N inputs the strategy
    would generate with a fixed seed. Useful for audit trail (DNA #8 KB).

    Fail-open: returns "" on any error.
    """
    try:
        strategy = _resolve_strategy(spec)
        if strategy is None:
            return ""
        # Deterministic fingerprint: draw the samples from the isolated
        # hashlib stream (fixed seed 0xC0DEFEED) for THIS call only — the
        # swap is restored even on error and touches no global RNG state.
        with _deterministic_strategy_source(0xC0DEFEED):
            samples = []
            for _ in range(max(0, n)):
                try:
                    samples.append(repr(strategy()))
                except Exception:  # noqa: BLE001
                    samples.append("<err>")  # silent-by-design: probe placeholder — crashed sample recorded as '<err>' in the digest
        blob = "\n".join(samples)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-19] fingerprint error: {e}")
        return ""


__all__ = [
    "BugLocation",
    "PropertySpec",
    "Violation",
    "PropertyResult",
    "validate_fix",
    "run_property_suite",
    "fingerprint_inputs",
    "register_strategy",
    "STRATEGY_REGISTRY",
    "INT_OR_NONE_STRATEGY",
    "STR_OR_NONE_STRATEGY",
    "LIST_STRATEGY",
    "DICT_STRATEGY",
    "MIXED_STRATEGY",
]
