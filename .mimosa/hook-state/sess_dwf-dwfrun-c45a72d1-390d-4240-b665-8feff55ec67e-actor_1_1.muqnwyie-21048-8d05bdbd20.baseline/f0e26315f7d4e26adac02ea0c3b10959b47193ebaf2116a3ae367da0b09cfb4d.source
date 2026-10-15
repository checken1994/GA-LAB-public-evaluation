# [V5.9-SCANNER] DeadSLMScanner — detect SLMs init but never routed.
#
# TẠI SAO scanner này tồn tại?
#   SCP_CONTEXT_MEMORY.md V5.8 worklog: "26 dead SLMs found" — SLMs được init
#   trong `self.slms = {...}` (judge.py:216-275) nhưng KHÔNG BAO GIỜ được
#   append vào `domains` (judge.py:686-1080). SLMs chiếm memory, import time,
#  但没有 bao giờ được dùng để verify câu hỏi.
#
#   PATTERN-MAP audit cũ phát hiện thủ công. Scanner này tự động hóa.
#
# LOGIC:
#   1. Parse judge.py — extract `self.slms = { "X": XxxSLM(), ... }` → init SLMs
#   2. Parse judge.py — extract all `domains.append("X")` calls → routed domains
#   3. DIFF: init SLMs NOT in routed list = DEAD SLMs
#   4. Special handling:
#      - "universal" / "general" are FALLBACK domains (used by SmartClassifier
#        or when no domain matches) → NOT dead even if no explicit append
#      - "city" routes to "geography" (comment at judge.py:240) → check if
#        parent domain is routed
#      - domains.append(domain_id) / domains.append(domain) use VARIABLES —
#        we extract the for-loop source to see what those variables iterate over
#
# RETURNS:
#   list[BugReport] — one BugReport per dead SLM, bug_type="DeadSLM"
from __future__ import annotations

import ast
import logging
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.dead_slm")

# scp/ package root — `scanners/` is at scp/autofix/scanners/, so go up 3 levels
_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/

# [SCP-DNA-FIX R15] Fix stale path: judge.py routing moved to judge_parts/judgeroute_mixin.py
# R13 META-BUG 1: scanner used _JUDGE_PATH = runtime/judge.py but Task 10-B moved
# SLM routing logic to judge_parts/judgeroute_mixin.py. Result: 51/51 findings were
# false positives (scanner couldn't find routing → thought all SLMs were dead).
# [S26 2026-09-13] judge_parts/ đã bị XÓA (god-split thế hệ cũ, 0 caller sống —
# judge.py hiện hành là RealityJudge tier1+LLM, không dùng self.slms dict).
# Scan target duy nhất trở lại là runtime/judge.py.
_JUDGE_PATH = _SCP_ROOT / "runtime" / "judge.py"

# SLMs explicitly marked as "fallback" — never dead even without explicit append
_FALLBACK_SLMS = {"universal", "general"}


class _SLMInitCollector(ast.NodeVisitor):
    """Walk judge.py AST, collect `self.slms = { "X": XxxSLM(), ... }` keys.

    Returns dict {domain_name: line_number}.

    Handles BOTH:
      - `self.slms = { ... }` (ast.Assign)
      - `self.slms: dict[...] = { ... }` (ast.AnnAssign — type annotation)
    """

    def __init__(self):
        self.slms_init: dict[str, int] = {}

    def _check_target_is_self_slms(self, tgt) -> bool:
        """Return True if tgt is `self.slms`."""
        return (isinstance(tgt, ast.Attribute)
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "self"
                and tgt.attr == "slms")

    def visit_Assign(self, node: ast.Assign):
        for tgt in node.targets:
            if self._check_target_is_self_slms(tgt):
                if isinstance(node.value, ast.Dict):
                    for key, _val in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            self.slms_init[key.value] = key.lineno
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        # [V5.9-SCANNER] Handle `self.slms: dict[...] = { ... }`
        if self._check_target_is_self_slms(node.target):
            if node.value is not None and isinstance(node.value, ast.Dict):
                for key, _val in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        self.slms_init[key.value] = key.lineno
        self.generic_visit(node)


class _RoutedDomainCollector(ast.NodeVisitor):
    """Walk judge.py AST, collect all `domains.append("X")` literal strings.

    Also handles `domains.append(domain_id)` / `domains.append(domain)` by
    extracting the for-loop source list (e.g. `for domain_id in [...]`).
    """

    def __init__(self):
        self.routed_domains: set[str] = set()
        self.routed_lines: dict[str, int] = {}

    def visit_Call(self, node: ast.Call):
        # Match `domains.append("X")` or `self.domains.append("X")`
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"):
            # Check the receiver is `domains` (Name) or `self.domains`
            recv = node.func.value
            is_domains = (
                (isinstance(recv, ast.Name) and recv.id == "domains")
                or (isinstance(recv, ast.Attribute)
                    and isinstance(recv.value, ast.Name)
                    and recv.value.id == "self"
                    and recv.attr == "domains")
            )
            if is_domains and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.routed_domains.add(arg.value)
                    self.routed_lines[arg.value] = node.lineno
                # Variable args (domain_id, domain, frame) handled by for-loop visitor
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        """Catch `for domain_id in [...]: domains.append(domain_id)` patterns.

        Extract the iter list if it's a literal list of strings.
        """
        if (isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.List)):
            for elt in node.iter.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.routed_domains.add(elt.value)
                    self.routed_lines[elt.value] = node.lineno
        self.generic_visit(node)


class DeadSLMScanner:
    """Detect SLMs init in judge.py but never routed via domains.append()."""

    name: str = "DeadSLMScanner"
    bug_type: str = "DeadSLM"

    def __init__(self, judge_path: Path | None = None):
        self.judge_path = judge_path or _JUDGE_PATH

    def scan(self) -> list[BugReport]:
        """Run the scanner. Returns list of BugReports for dead SLMs."""
        if not self.judge_path.exists():
            logger.warning(
                f"[DeadSLMScanner] judge.py not found at {self.judge_path}"
            )
            return []

        try:
            source = self.judge_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(self.judge_path))
        except SyntaxError as e:
            logger.error(f"[DeadSLMScanner] judge.py SyntaxError: {e}")
            return []
        except Exception as e:
            logger.error(f"[DeadSLMScanner] parse failed: {e}", exc_info=True)
            return []

        # Collect init SLMs
        init_collector = _SLMInitCollector()
        init_collector.visit(tree)
        slms_init = init_collector.slms_init

        # Collect routed domains
        route_collector = _RoutedDomainCollector()
        route_collector.visit(tree)
        routed_domains = route_collector.routed_domains

        # DIFF: init but not routed
        bugs: list[BugReport] = []
        for domain, line in slms_init.items():
            if domain in routed_domains:
                continue
            if domain in _FALLBACK_SLMS:
                # universal/general are fallbacks — used by SmartClassifier
                logger.debug(
                    f"[DeadSLMScanner] {domain!r} is fallback — skipping"
                )
                continue
            # Build BugReport
            bugs.append(BugReport(
                file=str(self.judge_path),
                line=line,
                bug_type=self.bug_type,
                description=(
                    f"DeadSLM: SLM {domain!r} is initialized in `self.slms` "
                    f"at line {line} but never appended to `domains` in "
                    f"`_route_question()`. It occupies memory + import time "
                    f"but never verifies any question."
                ),
                suggested_fix=(
                    f"Either: (a) add routing keywords for {domain!r} in "
                    f"`_route_question()` so questions get routed to it; "
                    f"(b) remove {domain!r} from `self.slms` if not needed; "
                    f"(c) confirm it's a fallback (like universal/general) "
                    f"and add an exception to _FALLBACK_SLMS."
                ),
                tier=BugTier.TIER_2_AUTO_FIX_LOG,
                affects_logic=False,  # doesn't change verdict — just dead code
            ))

        logger.info(
            f"[DeadSLMScanner] found {len(bugs)} dead SLM(s) "
            f"(init={len(slms_init)}, routed={len(routed_domains)})"
        )
        return bugs
