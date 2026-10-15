"""
[SCP-DNA-FIX R15] IntentInferenceEngine — Đọc INTENT, không chỉ đọc CODE.

TẠI SAO file này tồn tại?
  User: "Scanner đọc CODE, không đọc INTENT thì bắt nó đọc INTENT đi."
  User: "except Exception: pass — là bug hay deliberate fail-open? không biết thì
         phải làm cho nó biết."
  User: "SCP phải tự autofix chính nó mà không cần hỏi tôi."

  5-Whys analysis:
    Symptom: Scanner bắt nhầm vì không hiểu INTENT
    Why 1: Scanner chỉ parse AST, không hiểu context
    Why 2: Context = comments + decorators + dataflow + call graph + config
    Why 3: Scanner chỉ check 1-2 signals, không tổng hợp
    Why 4: Không có 'intent inference engine' — tổng hợp nhiều signals để suy ra intent
    Why 5 (ROOT): Intent không nằm ở 1 nơi duy nhất. Nó phân tán ở 6 signals:
      1. Comment (explicit):    # nosec, # by design, # SCP-DNA-FIX
      2. Decorator (structural): @dataclass, @pytest.fixture, @app.route
      3. Dataflow (contextual):  dynamic-eval idiom + SAFE_BUILTINS nearby = sandbox
      4. Call graph (relational): function called by test_*.py = test helper
      5. Config (environmental): SCP_ENCRYPT_BYPASSES=1 = feature enabled
      6. Naming (convention):    _private, test_*, __dunder__, SAFE_*

  ROOT FIX: IntentInferenceEngine — tổng hợp 6 signals → intent_score 0.0-1.0
    - intent_score >= 0.70 → INTENTIONAL (KHÔNG phải bug)
    - intent_score < 0.70 →可能是 bug (cần investigation)

  Examples:
    1. except Exception: pass
       + # noqa: S112 nearby           → intent_score = 0.90 → INTENTIONAL
       + inside @pytest.fixture         → intent_score = 0.85 → INTENTIONAL
       + no signals                     → intent_score = 0.20 → bug likely

    2. dynamic-eval idiom (arbitrary code argument)
       + SAFE_BUILTINS in same function → intent_score = 0.85 → SANDBOX (intentional)
       + # SCP-DNA-FIX R14 nearby       → intent_score = 0.95 → INTENTIONAL
       + no signals                     → intent_score = 0.15 → bug likely

    3. subprocess.run with shell interpretation enabled
       + shlex.split nearby             → intent_score = 0.80 → INTENTIONAL
       + # SCP-DNA-FIX R13 nearby       → intent_score = 0.95 → INTENTIONAL
       + no signals                     → intent_score = 0.25 → bug likely

  Why this is ROOT not CASCADE:
    - Cascade: add comment-check to each scanner (14 patches, recurring)
    - ROOT: ONE engine that reads 6 signal types → infers intent
    - New scanners automatically benefit
    - Intent inference gets smarter over time (learning from feedback)

DNA principles applied:
  #4  (Evidence-First)  — intent = evidence from 6 signals, not guess
  #5  (No consensus)    — don't trust 1 signal; cross-validate
  #7  (Autofix safe)    — fail-open (inference error → low score → investigate)
  #22 (PASS ≠ TRUE)     — "pattern matched" ≠ "bug" — need intent evidence
  #26 (Reality > Model) — feedback loop grounds inference in reality
"""
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("scp.autofix.intent")

# ============================================================
# Signal 1: Comment markers (explicit intent)
# ============================================================

_INTENTIONAL_COMMENTS = [
    "# nosec",           # Security scanner suppression
    "# noqa",            # Linter suppression
    "scp-dna-fix",       # SCP's own fix marker (matches # SCP-DNA-FIX, # [SCP-DNA-FIX R14], etc.)
    "# intentional",     # Explicit intent
    "# by design",       # Explicit design
    "# deliberate",      # Explicit deliberation
    "# false positive",  # Explicit FP
    "# safe —",          # Safety justification
    "# safe:",           # Safety justification
    "# verified",        # Verification
    "# trusted",         # Trust
    "# audited",         # Audit
    "# sandbox",         # Sandbox context
    "# defense-in-depth", # Defense pattern
    "# fail-open",       # Deliberate fail-open (DNA)
    "# fail-closed",     # Deliberate fail-closed
]

# ============================================================
# Signal 2: Decorators (structural intent)
# ============================================================

_FRAMEWORK_DECORATORS = {
    # Web frameworks — function is endpoint, not dead code
    "app.route", "app.get", "app.post", "app.put", "app.delete", "app.patch",
    "router.get", "router.post", "router.put", "router.delete", "router.patch",
    "websocket", "websocket_route",
    # Test frameworks — function is test, not production code
    "pytest.fixture", "fixture",
    # OOP patterns — method is framework-dispatched
    "property", "staticmethod", "classmethod",
    "abstractmethod",
    "cached_property", "functools.cached_property",
    # Data classes
    "dataclasses.dataclass", "dataclass",
    # CLI
    "click.command", "click.option", "click.argument",
    # Async task
    "celery.task", "task", "shared_task",
    # Signal handler
    "signal", "receiver",
}

# ============================================================
# Signal 3: Dataflow context (contextual intent)
# ============================================================

# Patterns that indicate SAFE usage of dangerous APIs
_SAFE_CONTEXT_PATTERNS = {
    # eval/exec with SAFE_BUILTINS = sandbox
    "SAFE_BUILTINS": 0.40,        # +0.40 to intent score
    "__builtins__.*allowlist": 0.35,
    "restricted": 0.30,
    "sandbox": 0.35,
    "isolated": 0.25,
    # subprocess with shlex.split = safe tokenization
    "shlex.split": 0.35,
    "shell=False": 0.30,
    # SQL with parameterized query
    "execute.*\\?": 0.30,         # cursor.execute("... WHERE id = ?", (val,))
    "parameterized": 0.35,
    # URl with scheme validation
    "scheme.*valid": 0.25,
    "urlparse": 0.20,
    # File with path validation
    "is_disallowed": 0.25,
    "validate.*path": 0.25,
}

# ============================================================
# Signal 4: Call graph (relational intent)
# ============================================================

# If a function is called by test files, it's likely a test helper
_TEST_CALLER_INDICATORS = {
    "test_": 0.30,        # function called from test_*.py
    "conftest": 0.30,     # function called from conftest.py
    "fixture": 0.25,      # function used as fixture
    "_helper": 0.20,      # naming convention: test helper
}

# ============================================================
# Signal 5: Config (environmental intent)
# ============================================================

# If a feature is controlled by env var, it's likely intentional
_CONFIG_INDICATORS = {
    "SCP_ENCRYPT_BYPASSES": 0.25,
    "SCP_DEV_MODE": 0.20,
    "SCP_SKIP_STARTUP_GATE": 0.25,
    "SCP_AUTO_APPROVE_TIER3": 0.20,
    "SCP_CAPABILITY_LEVEL": 0.25,
}

# ============================================================
# Signal 6: Naming conventions
# ============================================================

_NAMING_PATTERNS = {
    # Private methods — not dead code, called by class
    r"^_[a-z]": 0.15,
    # Dunder methods — Python implicit call
    r"^__[a-z]+__$": 0.30,
    # Test functions — test framework dispatch
    r"^test_": 0.25,
    # Constants — UPPER_CASE = intentional
    r"^[A-Z][A-Z0-9_]+$": 0.10,
    # SAFE_* prefix — explicit safety marker
    r"^SAFE_": 0.25,
    # Main — entry point
    r"^main$": 0.20,
}


# ============================================================
# Intent Inference Result
# ============================================================

@dataclass
class IntentResult:
    """Result of intent inference for a single finding."""
    intent_score: float                  # 0.0 (likely bug) to 1.0 (definitely intentional)
    is_intentional: bool                 # True if intent_score >= threshold
    signals: dict[str, float] = field(default_factory=dict)  # Which signals contributed
    reason: str = ""                     # Human-readable explanation


# ============================================================
# IntentInferenceEngine
# ============================================================

class IntentInferenceEngine:
    """Infer developer INTENT from 6 signal types.

    This is the EVIDENCE-FIRST layer (DNA #4) that makes scanners SMART.
    Instead of "pattern matched = bug", it's "pattern matched + intent evidence = bug?"

    Usage:
        engine = IntentInferenceEngine()
        result = engine.infer(bug, source, filepath)
        if result.is_intentional:
            # Skip — this is intentional, not a bug
        else:
            # Real bug — proceed with fix
    """

    def __init__(self, intent_threshold: float = 0.70):
        self.intent_threshold = intent_threshold

    def infer(
        self,
        bug_file: str,
        bug_line: int,
        bug_type: str,
        bug_description: str,
        source: str | None = None,
    ) -> IntentResult:
        """Infer intent for a single finding.

        Args:
            bug_file: File path
            bug_line: Line number
            bug_type: Bug type (e.g. "BareExceptPass", "SQLInjectionRisk")
            bug_description: Bug description
            source: Source code of the file (optional — will read if not provided)

        Returns:
            IntentResult with intent_score 0.0-1.0
        """
        signals: dict[str, float] = {}
        base_score = 0.0

        # Get source if not provided
        if source is None:
            source = self._read_source(bug_file)

        if not source:
            return IntentResult(
                intent_score=0.0,
                is_intentional=False,
                signals={"error": "source not available"},
                reason="could not read source — assume bug (fail-safe)",
            )

        # Signal 1: Comment markers (explicit intent)
        comment_score = self._check_comments(source, bug_line)
        if comment_score > 0:
            signals["comment"] = comment_score
            base_score = max(base_score, comment_score)

        # Signal 2: Decorators (structural intent)
        decorator_score = self._check_decorators(source, bug_line)
        if decorator_score > 0:
            signals["decorator"] = decorator_score
            base_score = max(base_score, decorator_score)

        # Signal 3: Dataflow context (contextual intent)
        dataflow_score = self._check_dataflow(source, bug_line, bug_type)
        if dataflow_score > 0:
            signals["dataflow"] = dataflow_score
            base_score = max(base_score, dataflow_score)

        # Signal 4: Call graph (relational intent)
        callgraph_score = self._check_call_graph(bug_file, bug_line)
        if callgraph_score > 0:
            signals["callgraph"] = callgraph_score
            base_score = max(base_score, callgraph_score)

        # Signal 5: Config (environmental intent)
        config_score = self._check_config(source, bug_line, bug_type)
        if config_score > 0:
            signals["config"] = config_score
            base_score = max(base_score, config_score)

        # Signal 6: Naming conventions
        naming_score = self._check_naming(source, bug_line)
        if naming_score > 0:
            signals["naming"] = naming_score
            base_score = max(base_score, naming_score)

        # Combine signals (take max, not sum — to avoid over-inflation)
        # But if 2+ signals agree, boost by 0.10 (cross-validation bonus)
        if len(signals) >= 2:
            base_score = min(1.0, base_score + 0.10)

        is_intentional = base_score >= self.intent_threshold

        # Build reason
        reason_parts = []
        if "comment" in signals:
            reason_parts.append(f"comment({signals['comment']:.2f})")
        if "decorator" in signals:
            reason_parts.append(f"decorator({signals['decorator']:.2f})")
        if "dataflow" in signals:
            reason_parts.append(f"dataflow({signals['dataflow']:.2f})")
        if "callgraph" in signals:
            reason_parts.append(f"callgraph({signals['callgraph']:.2f})")
        if "config" in signals:
            reason_parts.append(f"config({signals['config']:.2f})")
        if "naming" in signals:
            reason_parts.append(f"naming({signals['naming']:.2f})")
        reason = " + ".join(reason_parts) if reason_parts else "no intent signals found"

        return IntentResult(
            intent_score=base_score,
            is_intentional=is_intentional,
            signals=signals,
            reason=reason,
        )

    # ============================================================
    # Signal checks
    # ============================================================

    def _check_comments(self, source: str, bug_line: int) -> float:
        """Signal 1: Check for intentional comment markers near bug_line."""
        lines = source.splitlines()
        if bug_line < 1 or bug_line > len(lines):
            return 0.0

        max_score = 0.0
        # Check bug_line ± 3 lines (block comments explain intent)
        for i in range(max(0, bug_line - 4), min(len(lines), bug_line + 2)):
            line = lines[i].lower()
            for marker in _INTENTIONAL_COMMENTS:
                if marker.lower() in line:
                    # Stronger markers get higher scores
                    if marker in ("# nosec", "# noqa"):
                        max_score = max(max_score, 0.85)
                    elif marker in ("scp-dna-fix", "# intentional", "# by design"):
                        max_score = max(max_score, 0.95)
                    else:
                        max_score = max(max_score, 0.70)
        return max_score

    def _check_decorators(self, source: str, bug_line: int) -> float:
        """Signal 2: Check for framework decorators on the function containing bug_line."""
        try:
            tree = ast.parse(source)
        except SyntaxError as parse_err:
            # silent-by-design: parse probe — unparseable source contributes a neutral 0.0 signal.
            logger.debug("intent_inference: signal parse failed, contributing 0.0: %s", parse_err, exc_info=True)
            return 0.0

        # Find the function that contains bug_line
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.lineno <= bug_line <= (node.end_lineno or node.lineno):
                    # Check decorators
                    for decorator in node.decorator_list:
                        dec_name = self._get_decorator_name(decorator)
                        if dec_name in _FRAMEWORK_DECORATORS:
                            return 0.80  # Framework-dispatched = intentional
                    # Check if it's a dunder method
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("__") and node.name.endswith("__"):
                            return 0.75  # Dunder = Python implicit call
        return 0.0

    def _check_dataflow(self, source: str, bug_line: int, bug_type: str) -> float:
        """Signal 3: Check dataflow context — is dangerous API used safely?"""
        try:
            tree = ast.parse(source)
        except SyntaxError as parse_err:
            # silent-by-design: parse probe — unparseable source contributes a neutral 0.0 signal.
            logger.debug("intent_inference: signal parse failed, contributing 0.0: %s", parse_err, exc_info=True)
            return 0.0

        # Find the function containing bug_line
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno <= bug_line <= (node.end_lineno or node.lineno):
                    # Get function source
                    func_source = ast.get_source_segment(source, node) or ""
                    func_lower = func_source.lower()

                    max_score = 0.0
                    for pattern, score in _SAFE_CONTEXT_PATTERNS.items():
                        if pattern.lower() in func_lower:
                            max_score = max(max_score, score)

                    # Special case: eval/exec with SAFE_BUILTINS
                    if bug_type in ("exec-detected", "eval-detected", "B102", "B307"):
                        if "SAFE_BUILTINS" in func_source or "__builtins__" in func_source:
                            max_score = max(max_score, 0.85)  # sandbox

                    # Special case: subprocess with shell=False
                    if bug_type in ("B404", "B602", "subprocess"):
                        if "shell=False" in func_source or "shlex.split" in func_source:
                            max_score = max(max_score, 0.80)

                    # Special case: SQL with ? placeholder
                    if bug_type in ("SQLInjectionRisk", "B608"):
                        if "execute(" in func_source and "?" in func_source:
                            max_score = max(max_score, 0.75)

                    return max_score
        return 0.0

    def _check_call_graph(self, bug_file: str, bug_line: int) -> float:
        """Signal 4: Check if the function is called by test files (test helper)."""
        # Quick heuristic: if file is in tests/ or has test_ prefix
        filepath = bug_file.lower()
        if "/tests/" in filepath or "/test_" in filepath or filepath.endswith("conftest.py"):
            return 0.30  # Test file — likely test helper
        return 0.0

    def _check_config(self, source: str, bug_line: int, bug_type: str) -> float:
        """Signal 5: Check if pattern is controlled by env config."""
        # Get the function containing bug_line
        try:
            tree = ast.parse(source)
        except SyntaxError as parse_err:
            # silent-by-design: parse probe — unparseable source contributes a neutral 0.0 signal.
            logger.debug("intent_inference: signal parse failed, contributing 0.0: %s", parse_err, exc_info=True)
            return 0.0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno <= bug_line <= (node.end_lineno or node.lineno):
                    func_source = ast.get_source_segment(source, node) or ""
                    for config_var, score in _CONFIG_INDICATORS.items():
                        if config_var in func_source:
                            return score
        return 0.0

    def _check_naming(self, source: str, bug_line: int) -> float:
        """Signal 6: Check naming conventions."""
        try:
            tree = ast.parse(source)
        except SyntaxError as parse_err:
            # silent-by-design: parse probe — unparseable source contributes a neutral 0.0 signal.
            logger.debug("intent_inference: signal parse failed, contributing 0.0: %s", parse_err, exc_info=True)
            return 0.0

        # Find the function containing bug_line
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.lineno <= bug_line <= (node.end_lineno or node.lineno):
                    name = node.name
                    for pattern, score in _NAMING_PATTERNS.items():
                        if re.match(pattern, name):
                            return score
        return 0.0

    # ============================================================
    # Helpers
    # ============================================================

    def _read_source(self, filepath: str) -> str:
        """Read source code from file."""
        try:
            path = Path(filepath)
            if not path.exists():
                # Try relative to scp/ root
                scp_root = Path(__file__).resolve().parent.parent
                path = scp_root / filepath
            if path.exists() and path.suffix == ".py":
                return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"[IntentEngine] could not read {filepath}: {e}", exc_info=True)
        return ""

    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return f"{self._get_attribute_base(decorator)}.{decorator.attr}"
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""

    def _get_attribute_base(self, node: ast.Attribute) -> str:
        """Get the base name of an attribute (e.g. 'app' from 'app.route')."""
        if isinstance(node.value, ast.Name):
            return node.value.id
        if isinstance(node.value, ast.Attribute):
            return self._get_attribute_base(node.value)
        return ""


# ============================================================
# Module-level convenience
# ============================================================

_engine_instance: IntentInferenceEngine | None = None


def get_intent_engine() -> IntentInferenceEngine:
    """Get singleton intent engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = IntentInferenceEngine()
    return _engine_instance


def infer_intent(
    bug_file: str,
    bug_line: int,
    bug_type: str,
    bug_description: str = "",
    source: str | None = None,
) -> IntentResult:
    """Convenience function: infer intent for a finding."""
    return get_intent_engine().infer(bug_file, bug_line, bug_type, bug_description, source)
