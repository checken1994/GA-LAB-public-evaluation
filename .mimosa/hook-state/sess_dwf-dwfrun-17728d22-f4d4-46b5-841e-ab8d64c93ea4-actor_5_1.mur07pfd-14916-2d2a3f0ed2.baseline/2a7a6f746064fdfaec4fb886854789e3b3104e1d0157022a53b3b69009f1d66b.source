# [V5.9-SCANNER] RoutingGapScanner — detect SLMs with missing/narrow routing.
#
# TẠI SAO scanner này tồn tại?
#   DeadSLMScanner catches "init but ZERO routes". Nhưng còn 1 tầng sâu hơn:
#   SLM CÓ route, nhưng keywords quá hẹp — chỉ Vietnamese, không có English.
#   Hoặc keywords quá cụ thể — chỉ 1 câu hỏi, không generalize được.
#
#   VÍ DỤ (từ judge.py):
#     if any(kw in q_lower for kw in ["chuyển đổi", "convert"]):
#         domains.append("conversion")
#   → có EN + VN ✅
#
#     if any(kw in q_lower for kw in ["bệnh", "thuốc", "triệu chứng"]):
#         domains.append("medical")
#   → chỉ VN ❌ — "what is diabetes?" không được route
#
# LOGIC:
#   1. Parse judge.py — extract `if any(kw in ... for kw in [...])` blocks
#      followed by `domains.append("X")`
#   2. For each routed domain:
#      a. If NO keywords found → "RoutingGap" (zero keywords)
#      b. If keywords are ALL Vietnamese → "RoutingGapVN" (narrow)
#      c. If keywords have < 3 entries → "RoutingGapNarrow" (too few)
#   3. Skip fallback domains (universal/general) — they don't need keywords
#
# RETURNS:
#   list[BugReport] — bug_type="RoutingGap" or "RoutingGapVN" or "RoutingGapNarrow"
from __future__ import annotations

import ast
import logging
import string
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier

logger = logging.getLogger("scp.autofix.scanners.routing_gap")

_SCP_ROOT = Path(__file__).resolve().parent.parent.parent  # .../scp/
_JUDGE_PATH = _SCP_ROOT / "runtime" / "judge.py"
# [S26 2026-09-13] judge_parts/ đã xóa (god-split cũ, 0 caller sống) —
# scan target duy nhất là runtime/judge.py.

# Domains that are fallbacks (routed by classifier or unconditional append)
_FALLBACK_DOMAINS = {"universal", "general"}

# ASCII letter check — if a keyword has NO ASCII letters, it's Vietnamese-only
_ASCII_LETTERS = set(string.ascii_letters)


def _has_english_keyword(keywords: list[str]) -> bool:
    """Return True if any keyword contains ASCII letters (English)."""
    for kw in keywords:
        if any(c in _ASCII_LETTERS for c in kw):
            return True
    return False


class _RoutingKeywordCollector(ast.NodeVisitor):
    """Walk judge.py AST.

    For each `if any(kw in q_lower for kw in [...]): domains.append("X")` block,
    extract the list of keywords and the domain they route to.
    """

    def __init__(self):
        # domain -> list of keyword strings (across all `if` blocks for this domain)
        self.domain_keywords: dict[str, list[str]] = {}

    def visit_If(self, node: ast.If):
        """Match `if any(kw in q_lower for kw in [...])` followed by
        `domains.append("X")` (possibly nested in the if body).
        """
        keywords = self._extract_keywords_from_test(node.test)
        if keywords is not None:
            # Find domains.append("X") calls in the if body
            domains_in_body = self._find_domain_appends(node.body)
            for domain in domains_in_body:
                self.domain_keywords.setdefault(domain, [])
                self.domain_keywords[domain].extend(keywords)
        # Recurse into body and orelse (other if statements may be nested)
        self.generic_visit(node)

    def _extract_keywords_from_test(self, test) -> list[str] | None:
        """Extract the keyword list from `any(kw in X for kw in [...])`.

        Returns the list of keyword strings, or None if test doesn't match.
        """
        # Pattern 1: any(kw in q_lower for kw in [...])
        if (isinstance(test, ast.Call)
                and isinstance(test.func, ast.Name)
                and test.func.id == "any"):
            for arg in test.args:
                kws = self._extract_keywords_from_comprehension(arg)
                if kws is not None:
                    return kws
        # Pattern 2: kw in q_lower (single keyword, no any())
        if (isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.In)
                and isinstance(test.left, ast.Constant)
                and isinstance(test.left.value, str)):
            return [test.left.value]
        return None

    def _extract_keywords_from_comprehension(self, node) -> list[str] | None:
        """Extract `[...]` from `kw in q_lower for kw in [...]`."""
        # ast.GeneratorExp for `any(kw in q_lower for kw in [...])`
        if isinstance(node, (ast.GeneratorExp, ast.ListComp)):
            for gen in node.generators:
                if isinstance(gen.iter, ast.List):
                    kws = []
                    for elt in gen.iter.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            kws.append(elt.value)
                    if kws:
                        return kws
        return None

    def _find_domain_appends(self, body: list) -> list[str]:
        """Find all `domains.append("X")` calls in a statement list."""
        domains: list[str] = []
        for stmt in body:
            for child in ast.walk(stmt):
                if (isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "append"
                        and child.args):
                    arg = child.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        recv = child.func.value
                        if (isinstance(recv, ast.Name) and recv.id == "domains"):
                            domains.append(arg.value)
        return domains


class RoutingGapScanner:
    """Detect SLMs with missing or too-narrow routing keywords."""

    name: str = "RoutingGapScanner"

    def __init__(self, judge_path: Path | None = None):
        self.judge_path = judge_path or _JUDGE_PATH

    def scan(self) -> list[BugReport]:
        """Run the scanner. Returns list of BugReports for routing gaps.

        [GLM-AUDIT-FIX] Trước đây scan cả judge_parts/*.py; [S26] judge_parts/
        đã xóa nên chỉ còn judge.py là nguồn routing duy nhất.
        """
        sources_to_parse: list[Path] = []
        if self.judge_path.exists():
            sources_to_parse.append(self.judge_path)
        else:
            logger.warning(
                f"[RoutingGapScanner] judge.py not found at {self.judge_path}"
            )
            return []

        kw_collector = _RoutingKeywordCollector()
        slms_init: dict[str, int] = {}

        for source_path in sources_to_parse:
            try:
                source = source_path.read_text(encoding="utf-8", errors="replace")
                if not source.strip():
                    continue  # Skip empty files
                tree = ast.parse(source, filename=str(source_path))
            except SyntaxError as e:
                logger.error(f"[RoutingGapScanner] SyntaxError in {source_path}: {e}")
                continue

            # Collect init SLMs from this file
            from scp.autofix.scanners.dead_slm_scanner import _SLMInitCollector
            init_collector = _SLMInitCollector()
            init_collector.visit(tree)
            slms_init.update(init_collector.slms_init)

            # Collect routing keywords from this file
            kw_collector.visit(tree)

        bugs: list[BugReport] = []
        for domain, init_line in slms_init.items():
            if domain in _FALLBACK_DOMAINS:
                continue
            kws = kw_collector.domain_keywords.get(domain, [])

            if not kws:
                # Routed (since SLM is init and exists in domains.append at least once)
                # but no keyword list detected → ambiguous; skip if NOT routed
                # We need to check if domain IS routed. If routed but no kws found,
                # it could be via variable (domains.append(domain_id)). Skip to avoid
                # false positives — DeadSLMScanner already catches "no route at all".
                continue

            # Bug type A: too few keywords (< 3)
            if len(kws) < 3:
                bugs.append(BugReport(
                    file=str(self.judge_path),
                    line=init_line,
                    bug_type="RoutingGapNarrow",
                    description=(
                        f"RoutingGapNarrow: SLM {domain!r} routes on only "
                        f"{len(kws)} keyword(s): {kws}. Too narrow — most "
                        f"real questions won't match. Recommend ≥ 5 keywords "
                        f"covering common phrasings."
                    ),
                    suggested_fix=(
                        f"Add more routing keywords for {domain!r} in "
                        f"`_route_question()`. Cover: synonyms, abbreviations, "
                        f"common question patterns (Vietnamese + English)."
                    ),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                ))
                continue  # don't double-report

            # Bug type B: Vietnamese-only (no English keywords)
            if not _has_english_keyword(kws):
                bugs.append(BugReport(
                    file=str(self.judge_path),
                    line=init_line,
                    bug_type="RoutingGapVN",
                    description=(
                        f"RoutingGapVN: SLM {domain!r} routes on keywords "
                        f"{kws} — all Vietnamese, no English. English "
                        f"questions ({domain!r}-related) won't be routed. "
                        f"SCP loses cross-lingual coverage."
                    ),
                    suggested_fix=(
                        f"Add English keywords for {domain!r} routing "
                        f"(e.g. synonyms, technical terms). "
                        f"Keep Vietnamese, ADD English alongside."
                    ),
                    tier=BugTier.TIER_2_AUTO_FIX_LOG,
                ))

        logger.info(
            f"[RoutingGapScanner] found {len(bugs)} routing gap(s) "
            f"(scanned {len(slms_init)} init SLMs, "
            f"{len(kw_collector.domain_keywords)} with keyword data)"
        )
        return bugs
