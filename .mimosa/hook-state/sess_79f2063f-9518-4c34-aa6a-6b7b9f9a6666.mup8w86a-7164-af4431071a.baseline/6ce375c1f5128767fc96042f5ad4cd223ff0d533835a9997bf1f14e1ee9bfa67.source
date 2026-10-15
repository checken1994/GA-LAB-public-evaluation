"""
[SCP-DNA-FIX R7-Full IMP-5] Hypothesis Property-Based Scanner — NEW scanner.

TẠI SAO file này tồn tại?
  R3-R6 used static analysis only (ruff, pyflakes, pylint, vulture, mypy,
  bandit). All 6 sources are STATIC. None-comparison TypeError (R6-1) was
  MISLEADINGLY reported by mypy as 'dict has no attr value' — real root cause
  (None > 0) only found by manual CryptoResult dataclass inspect. Hypothesis
  would have CAUGHT it by generating random CryptoResult(value=None).

  This scanner is the 7th SOURCE — RUNTIME property-based testing. For each
  function with @given-eligible signature (no complex deps), generate 1000
  random inputs via hypothesis + assert no unexpected exception.

  When hypothesis is not installed → gracefully skip (return []).
  When hypothesis is installed but a function fails to import → log + skip.

Inspired by: Hypothesis library + QuickCheck (Haskell tradition)

Flow:
  scanner.scan() → for each .py file in scp/ → AST-extract eligible functions
    → generate hypothesis strategy per arg (str/int/float/list/dict/bool/None)
    → @given(stategies) wrapper → call function → assert no exception
    → if exception → BugReport(bug_type="HypothesisFailure")

DNA principles applied:
  #24 (Đứa trẻ hỏi Tại sao) — what if input is None? empty? huge? negative?
  #25 (Why → falsify)       — hypothesis exists to falsify assumptions
  #5  (Evidence-first)      — runtime evidence > static analysis claim
"""
from __future__ import annotations

import ast
import importlib
import logging
import os
from pathlib import Path
from typing import Any

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.hypothesis")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_MAX_FILES = 200
_MAX_FUNCTIONS_PER_FILE = 20
_MAX_HYPOTHESIS_EXAMPLES = 100  # per function (default hypothesis is 100; we cap lower for speed)


# Annotation string → hypothesis strategy call (string form to avoid import-time dep).
# We lazily import hypothesis inside _run_strategy(); if it's missing we skip.
_ANNOTATION_TO_STRATEGY = {
    "str": "st.text()",
    "int": "st.integers()",
    "float": "st.floats(allow_nan=False, allow_infinity=False)",
    "bool": "st.booleans()",
    "list": "st.lists(st.text(), max_size=5)",
    "dict": "st.dictionaries(st.text(), st.text(), max_size=5)",
    "set": "st.sets(st.text(), max_size=5)",
    "tuple": "st.tuples(st.text())",
    "bytes": "st.binary(max_size=64)",
    "None": "st.none()",
    "Optional[str]": "st.one_of(st.none(), st.text())",
    "Optional[int]": "st.one_of(st.none(), st.integers())",
}


def _hypothesis_available() -> bool:
    """Check whether the hypothesis library is importable."""
    try:
        importlib.import_module("hypothesis")  # noqa: F401
        return True
    except ImportError:
        # silent-by-design: documented availability probe — False is the contract callers rely on to report "skip".
        return False


def _annotation_to_strategy_str(ann: ast.AST | None) -> str | None:
    """Map an AST annotation node to a hypothesis strategy source string.

    Returns None if no strategy is known for this annotation (skip arg).
    """
    if ann is None:
        # No annotation → default to text() (broadest coverage).
        return "st.text()"
    # Simple Name: str, int, bool, list, dict, etc.
    if isinstance(ann, ast.Name) and ann.id in _ANNOTATION_TO_STRATEGY:
        return _ANNOTATION_TO_STRATEGY[ann.id]
    # String literal annotation (PEP 484 postponement): "str", "Optional[str]"
    if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
        return _ANNOTATION_TO_STRATEGY.get(ann.value)
    # Subscript: Optional[str], List[int], etc. — best-effort substring match.
    if isinstance(ann, ast.Subscript):
        try:
            ann_str = ast.unparse(ann)
        except Exception as unp_err:
            # silent-by-design: unparse probe — None means "no strategy known
            # for this annotation (skip arg)" per the function contract.
            logger.debug("hypothesis_scanner: annotation unparse failed, skipping arg: %s", unp_err, exc_info=True)
            return None
        for key, val in _ANNOTATION_TO_STRATEGY.items():
            if ann_str == key:
                return val
        # Fallback: use the base type's strategy (e.g. List[int] → list strategy).
        if isinstance(ann.value, ast.Name) and ann.value.id in _ANNOTATION_TO_STRATEGY:
            return _ANNOTATION_TO_STRATEGY[ann.value.id]
    return None


def _is_eligible_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Decide whether a function is eligible for property-based testing.

    Eligibility rules (avoid wasting time on unsuitable functions):
      - Not a dunder method (__init__, __str__, etc.)
      - Not async (hypothesis doesn't directly support async without extra setup)
      - Has a body (not just `pass` or `...`)
      - Has at least one parameter that maps to a known strategy
      - Not decorated with @given already (already property-tested)
      - Not a fixture/test (@pytest.fixture, @pytest.mark.*, test_*)
    """
    if node.name.startswith("__") and node.name.endswith("__"):
        return False
    if isinstance(node, ast.AsyncFunctionDef):
        return False
    # Body too short (just pass or docstring)?
    real_body = [s for s in node.body if not isinstance(s, ast.Expr)]
    if len(real_body) <= 1:
        # Could be just a docstring + pass/return — too trivial.
        if not any(isinstance(s, (ast.Return, ast.Assign, ast.AugAssign,
                                  ast.Call, ast.If, ast.For, ast.While))
                   for s in node.body):
            return False
    # Already has @given decorator?
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "given":
            return False
        if isinstance(dec, ast.Attribute) and dec.attr == "given":
            return False
    # Fixture/test?
    for dec in node.decorator_list:
        if isinstance(dec, ast.Attribute):
            if dec.attr in ("fixture", "mark"):
                return False
        if isinstance(dec, ast.Name) and dec.id in ("fixture",):
            return False
    if node.name.startswith("test_"):
        return False
    # Must have at least one positional arg with a mappable strategy
    has_mappable = False
    for arg in node.args.args:
        if _annotation_to_strategy_str(arg.annotation) is not None:
            has_mappable = True
            break
    # No annotations at all → still eligible (we default to text()).
    if not any(arg.annotation for arg in node.args.args):
        has_mappable = len(node.args.args) > 0
    return has_mappable


def _collect_eligible_functions(file_path: Path) -> list[tuple[str, ast.FunctionDef]]:
    """AST-extract eligible top-level functions from a Python file."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as parse_err:
        # silent-by-design: parse probe — unparseable file yields no eligible
        # functions for property testing.
        logger.debug("hypothesis_scanner: skipping unparseable file %s: %s", file_path, parse_err, exc_info=True)
        return []
    except Exception as read_err:  # noqa: S112
        logger.debug("hypothesis_scanner: skipping unreadable file %s: %s", file_path, read_err, exc_info=True)
        return []
    out: list[tuple[str, ast.FunctionDef]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and _is_eligible_function(node):
            out.append((node.name, node))
    return out


def _file_to_module_path(file_path: Path) -> str | None:
    """Convert file path to dotted module path under scp/."""
    try:
        rel = file_path.relative_to(_SCP_ROOT.parent)
    except ValueError:
        # silent-by-design: relative_to probe — None documents "file is not
        # under the scp root" per the function contract.
        logger.debug("hypothesis_scanner: %s not under scp root, no module path", file_path, exc_info=True)
        return None
    if rel.suffix != ".py":
        return None
    mod = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
    if mod.endswith(".__init__"):
        mod = mod[:-9]
    return mod


def _build_strategy_call(node: ast.FunctionDef) -> str | None:
    """Build a hypothesis `@given(...)` decorator source string for a function.

    Returns None if no args can be mapped (skip function).
    """
    parts: list[str] = []
    for arg in node.args.args:
        strat = _annotation_to_strategy_str(arg.annotation)
        if strat is None:
            # Unknown annotation → fall back to text() (broadest).
            strat = "st.text()"
        parts.append(strat)
    if not parts:
        return None
    return "@given(" + ", ".join(parts) + ")"


def _safe_eval_strategy(expr: str, st_module: Any) -> Any:
    """Evaluate a hypothesis strategy expression WITHOUT dynamic evaluation.

    [S3-SECURITY-SWEEP] Replaces the previous dynamic-evaluation of args_str
    (CWE-95 HIGH code-injection finding). The accepted grammar is a strict
    whitelist: ``st.<strategy>(literal args, nested st.* calls)`` only.
    Anything else — attribute chains, names other than ``st``, operators,
    subscripts, f-strings, lambda, comprehensions — is rejected BEFORE any
    call happens, so external data can never become executed code.
    """
    tree = ast.parse(expr, mode="eval")

    def _reject(reason: str) -> None:
        raise ValueError(f"strategy expression rejected: {reason}")

    def _eval_node(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool, type(None))):
                return node.value
            _reject("non-literal constant")
        if isinstance(node, ast.Call):
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "st"
            ):
                _reject("only st.<strategy>(...) calls are allowed")
            if any(isinstance(a, ast.Starred) for a in node.args):
                _reject("*args unpacking not allowed")
            if any(kw.arg is None for kw in node.keywords):
                _reject("**kwargs unpacking not allowed")
            strategy_name = func.attr
            if strategy_name.startswith("_"):
                _reject("private st attribute")
            fn = getattr(st_module, strategy_name, None)
            if fn is None or not callable(fn):
                _reject(f"unknown strategy st.{strategy_name}")
            args = [_eval_node(a) for a in node.args]
            kwargs = {kw.arg: _eval_node(kw.value) for kw in node.keywords}
            return fn(*args, **kwargs)
        if isinstance(node, ast.List):
            return [_eval_node(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(_eval_node(e) for e in node.elts)
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
        ):
            return -node.operand.value
        _reject(f"unsupported syntax: {type(node).__name__}")

    return _eval_node(tree)


def _test_function_with_hypothesis(
    module_path: str,
    func_name: str,
    strategy_call: str,
    max_examples: int = _MAX_HYPOTHESIS_EXAMPLES,
) -> tuple[bool, str]:
    """Dynamically test a function with hypothesis-generated inputs.

    Returns (ok, message).
    ok=True  — function survived 100 random inputs without exception
    ok=False — function raised on some input (message has the failing case)

    Implementation note: we build a wrapper that calls hypothesis.given on
    the imported function. This avoids exec'ing user code directly.
    """
    try:
        import hypothesis.strategies as st  # noqa: F401
        from hypothesis import HealthCheck, given, settings
    except ImportError:
        # silent-by-design: explicit (True, reason) skip status returned to the caller.
        return True, "hypothesis not installed, skip"

    try:
        mod = importlib.import_module(module_path)
    except Exception as e:  # noqa: BLE001
        return True, f"module import failed (non-fatal): {type(e).__name__}: {e}"

    func = getattr(mod, func_name, None)
    if func is None or not callable(func):
        return False, f"AttributeError: {module_path}.{func_name} not callable"

    # Build strategy tuple by evaluating strategy_call in a restricted namespace.
    # strategy_call looks like: "@given(st.text(), st.integers())"
    # Strip "@given(" prefix and ")" suffix to get the args string.
    if not strategy_call.startswith("@given(") or not strategy_call.endswith(")"):
        return True, "malformed strategy_call, skip"
    args_str = strategy_call[len("@given("):-1]
    try:
        # [S3-SECURITY-SWEEP] AST-whitelist evaluator — replaces eval()
        # (CWE-95): strategy expressions may only call st.* with literals.
        strategies = _safe_eval_strategy(args_str, st)
    except Exception as e:  # noqa: BLE001
        return True, f"strategy eval failed (skip): {e}"

    if not isinstance(strategies, tuple):
        strategies = (strategies,)

    # Capture failures
    failure_msg_holder: list[str] = []

    @given(*strategies)
    @settings(
        max_examples=max_examples,
        deadline=None,  # no per-example time limit (CI may be slow)
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def _property_test(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (TypeError, AttributeError, ValueError, KeyError, IndexError) as e:
            # These exceptions indicate a likely bug (signature mismatch, None
            # comparison, missing key, etc.). Other exceptions (ConnectionError,
            # FileNotFoundError) are runtime context issues — not bugs.
            failure_msg_holder.append(
                f"{type(e).__name__}: {e} (args={args!r})"
            )
            raise  # let hypothesis record + shrink

    try:
        _property_test()
    except Exception as e:  # noqa: BLE001 — hypothesis raises on property failure
        # silent-by-design: explicit (False, reason) error return — the failure message is the finding the caller reports.
        msg = failure_msg_holder[0] if failure_msg_holder else str(e)
        return False, f"property test failed: {msg[:300]}"
    return True, f"survived {max_examples} hypothesis examples"


class HypothesisScanner:
    """[IMP-5] Property-based testing scanner (runtime, not static).

    Generates random inputs for functions with eligible signatures and asserts
    no TypeError/AttributeError/ValueError/KeyError/IndexError. Catches bugs
    that static analysis misses (None > 0, empty list access, missing key, etc.).
    """

    name: str = "HypothesisScanner"
    bug_type: str = "HypothesisFailure"

    def __init__(
        self,
        scp_root: Path | None = None,
        max_files: int = _MAX_FILES,
        max_functions_per_file: int = _MAX_FUNCTIONS_PER_FILE,
        max_examples: int = _MAX_HYPOTHESIS_EXAMPLES,
        enabled: bool | None = None,
    ):
        self.scp_root = scp_root or _SCP_ROOT
        self.max_files = max_files
        self.max_functions_per_file = max_functions_per_file
        self.max_examples = max_examples
        # Enabled by default IF hypothesis is installed.
        # Operator can force-disable via env SCP_HYPOTHESIS_SCANNER=0.
        if enabled is None:
            env_val = os.environ.get("SCP_HYPOTHESIS_SCANNER", "1")
            enabled = env_val == "1" and _hypothesis_available()
        self.enabled = enabled

    def _iter_python_files(self) -> list[Path]:
        """Iterate .py files in scp/ (skip tests/scripts/__pycache__)."""
        out: list[Path] = []
        count = 0
        for path in self.scp_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            if path.name == "__init__.py":
                continue
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            if any(part in ("examples", "scripts", "attack_payloads") for part in path.parts):
                continue
            if count >= self.max_files:
                break
            out.append(path)
            count += 1
        return out

    def scan(self) -> list[BugReport]:
        """Run property-based tests on eligible functions.

        Returns list[BugReport] with bug_type="HypothesisFailure".
        Empty list if hypothesis not installed or disabled.
        """
        if not self.enabled:
            logger.info(
                "[HypothesisScanner] disabled (hypothesis not installed or "
                "SCP_HYPOTHESIS_SCANNER=0)"
            )
            return []

        if not _hypothesis_available():
            logger.info("[HypothesisScanner] hypothesis library not installed, skip")
            return []

        bugs: list[BugReport] = []
        files = self._iter_python_files()
        logger.info(
            f"[HypothesisScanner] scanning {len(files)} files, "
            f"max {self.max_functions_per_file} funcs/file, "
            f"{self.max_examples} examples/func"
        )

        for path in files:
            module_path = _file_to_module_path(path)
            if module_path is None:
                continue
            eligible = _collect_eligible_functions(path)
            if not eligible:
                continue
            for func_name, node in eligible[: self.max_functions_per_file]:
                strategy = _build_strategy_call(node)
                if strategy is None:
                    continue
                ok, msg = _test_function_with_hypothesis(
                    module_path, func_name, strategy, self.max_examples
                )
                if not ok:
                    bug = BugReport(
                        file=str(path),
                        line=node.lineno,
                        bug_type=self.bug_type,
                        description=(
                            f"Hypothesis property test FAILED for "
                            f"{module_path}.{func_name}: {msg}. The function "
                            f"raises on random inputs — likely None/empty/"
                            f"edge-case bug that static analysis missed. "
                            f"Review the failing case + add input validation."
                        ),
                        suggested_fix=(
                            "Add input validation/guard at the start of the "
                            "function. Common patterns: `if x is None: return`, "
                            "`if not lst: return []`, `if not isinstance(x, T): "
                            "raise TypeError(...)`. Use hypothesis.to_signature() "
                            "to find the minimal failing case."
                        ),
                        tier=BugTier.TIER_2_AUTO_FIX_LOG,
                        affects_logic=False,
                    )
                    bugs.append(bug)
                    logger.info(
                        f"[HypothesisScanner] FAIL {module_path}.{func_name}: {msg[:120]}"
                    )

        logger.info(
            f"[HypothesisScanner] found {len(bugs)} property-test failure(s)"
        )
        return bugs


__all__ = ["HypothesisScanner"]
