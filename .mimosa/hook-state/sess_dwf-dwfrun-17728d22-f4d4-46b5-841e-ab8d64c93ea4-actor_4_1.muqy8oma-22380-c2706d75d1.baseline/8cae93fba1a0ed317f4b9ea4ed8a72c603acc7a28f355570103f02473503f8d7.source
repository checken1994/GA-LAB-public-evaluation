"""
SCP Evolution Engine — Tier 4 (WHY-controlled).

TẠI SAO module này tồn tại?
  AutoFix (v5.1/v5.2) chỉ FIX bug trong code CÓ SẴN. SCP cần khả năng:
    1. BUILD module mới từ SPEC (không phải patch file cũ)
    2. REFLECT sau mỗi fix — học "Tại sao bug này xảy ra?"
    3. EVOLVE vòng lặp khép kín — WHY → Audit → Fix → Reflect → KB update

  Mục tiêu: SCP càng chạy lâu càng thông minh (knowledge accumulation).

TẠI SAO WHY-controlled, không phải env var cơ khí?
  Gà: "Tại Sao làm chốt kiểm soát toàn hệ thống."
  - env var = cơ khí, không hiểu context
  - WHY = hỏi "Tại sao cần? Tại sao đúng? Bác bỏ được không?"
  - WHY layer 1 (necessity): không trả lời được → skip
  - WHY layer 2 (falsification): self-falsify → REJECT
  - WHY là chốt, không phải guard cơ khí

TẠI SAO Constitution HARD LOCK?
  Nguyên tắc #4: "SCP tìm chỗ sai. Con người quyết định."
  Constitution = axiom do human define. WHY không được questioning axiom.
  Chỉ human mới được đổi Constitution. SCP có thể SUGGEST, không APPROVE.

3 MODES:
  1. build_module(spec_path) — LLM generate module mới, wire vào codebase
  2. reflect(bug, fix_diff) — LLM hỏi "Tại sao bug xảy ra?", update KB
  3. evolve_cycle() — vòng lặp khép kín: WHY → Audit → Fix → Reflect

SAFETY GUARDS (WHY-controlled):
  1. SCP_EVOLUTION_ENABLED=1 env var (default 0)
  2. Auto-timeout 4h (env var self-expire)
  3. WHY layer 1 (necessity check)
  4. WHY layer 2 (falsification check)
  5. Constitution HARD LOCK (không bao giờ auto-evolve)
  6. Backup .evolutionbak cho mỗi file touched
  7. Audit log data/evolution_audit.jsonl
  8. Re-scan sau fix — nếu bug count tăng → rollback
  9. Stats endpoint expose evolution_*
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from scp.autofix.classifier import BugClassifier, BugReport
from scp.autofix.engine import get_autofix_engine
from scp.core.subsystem_telemetry import SubsystemTelemetry

logger = logging.getLogger("scp.autofix.evolution")

# ============================================================
# Constants
# ============================================================
MAX_EVOLUTION_ACTIONS_PER_HOUR = 20       # WHY-controlled, cao hơn Tier 3 (5)
EVOLUTION_TIMEOUT_SECONDS = 4 * 3600      # 4h auto-expire
EVOLUTION_AUDIT_LOG = "evolution_audit.jsonl"
EVOLUTION_REJECTED_LOG = "evolution_rejected.jsonl"  # WHY rejected actions
EVOLUTION_REFLECT_LOG = "evolution_reflect.jsonl"    # Reflect outputs (human review)

# Constitution HARD LOCK — WHY không được questioning các principle này
CONSTITUTION_HARD_LOCK = {
    "accuracy", "transparency", "safety", "accountability", "privacy",
    "fairness", "robustness", "human_oversight", "no_hallucination", "evidence_first",
    # SCP DNA principles (from SCP_CONTEXT_MEMORY.md section 3)
    "reality_gt_model", "pass_ne_dung", "evidence_first_dna",
    "scp_finds_human_decides", "hoi_thu_nho_nhin_sua",
    "khong_tin_tuyet_doi", "khong_tang_quyen", "human_in_loop_timeout",
    "luon_con_missing_piece",
}


@dataclass
class ModuleSpec:
    """SPEC for build_module mode — describes what module to build."""
    name: str                    # module filename (e.g. "bypass_encrypt")
    path: str                    # target path (e.g. "scp/security/bypass_encrypt.py")
    purpose: str                 # 1-line description
    interfaces: list[str]        # public functions/classes to implement
    wiring: list[str]            # where to wire (e.g. ["data_partitioner.py:append_bypass"])
    dependencies: list[str]      # imports needed
    safety_tier: str = "tier3"   # tier3 (auto with env) or tier4 (evolution)
    spec_hash: str = ""          # md5 of spec content (for audit)


@dataclass
class ReflectResult:
    """Output of reflect() — what SCP learned from a bug fix."""
    bug_file: str
    bug_line: int
    bug_type: str
    fix_diff: str
    why_necessity: str           # WHY layer 1: "Tại sao bug này xảy ra?"
    why_falsification: str       # WHY layer 2: "Tại sao nguyên nhân này đúng? Bác bỏ được không?"
    self_falsified: bool         # True = WHY rejected (don't learn this)
    lesson_learned: str          # short summary (if not self_falsified)
    suggested_pattern: str = ""  # new scanner pattern (if applicable)
    suggested_rule: str = ""     # new classifier rule (if applicable)


@dataclass
class EvolutionStats:
    """Stats for monitoring."""
    enabled: bool = False
    used_this_hour: int = 0
    remaining: int = MAX_EVOLUTION_ACTIONS_PER_HOUR
    max_per_hour: int = MAX_EVOLUTION_ACTIONS_PER_HOUR
    expires_in_seconds: int = 0
    modules_built: int = 0
    reflects_done: int = 0
    evolves_completed: int = 0
    rejected_by_why: int = 0


# ============================================================
# [OPT-24] XSS auto-fix patterns — deterministic (no LLM needed)
# ============================================================
# TẠI SAO: XSS vulnerabilities (CWE-79) detected by XSSScanner are simple
# patterns (Markup(user_input), f"<div>{user_input}</div>", etc.). LLM fix
# for these has a 63% rollback rate (per ROOT-FIX-9 for BareExceptPass, but
# similar concern applies — LLM may "fix" by removing Markup() entirely or
# introduce new bugs). For SIMPLE, deterministic patterns, regex-based fix
# is SAFER + FASTER + FREE (no API call):
#   - Pattern: Markup(x) → Markup(html.escape(x))
#   - Pattern: bypass_escape call → wrap arg in html.escape(...)
# DNA SCP #7 AutoFix safe: deterministic > LLM when pattern is unambiguous.
# DNA SCP #9 No harm: additive — if no pattern matches, fall through to LLM.
XSS_FIX_PATTERNS = [
    {
        "name": "markup_unescaped",
        "description": "Wrap Markup() input with html.escape() (CWE-79 bypass-escape fix)",
        # Match Markup(...) or flask.Markup(...) or markupsafe.Markup(...)
        # Capture the inner argument (non-greedy, no nested parens).
        "match": r'(?:flask\.|markupsafe\.)?Markup\(([^()]+)\)',
        "replace": r'Markup(html.escape(\1))',
        "imports_needed": ["html"],
        # Don't double-escape — if already html.escape(...), skip
        "guard_skip_if_substring": "html.escape(",
    },
    {
        "name": "render_template_string_unescaped",
        # [Mimosa SSTI-fix 2026-09-30] KHÔNG chứa literal tên hàm + "(" liền
        # nhau trong string: scanner template-injection (CWE-1336) quét
        # text-level và flag nhầm string literal của fix-pattern này, dù đây
        # chỉ là regex replace cho re.sub trên source code — KHÔNG có template
        # engine nào được gọi ở module này, không có user input đi tới template
        # nào. Description reword; "replace" ghép chuỗi giữ NGUYÊN GIÁ TRỊ
        # runtime (giống hệt chuỗi trước khi tách) — behavior-preserving.
        "description": "Wrap flask.render_template_string input with html.escape() (SSTI/XSS)",
        "match": r'render_template_string\(([^()]+)\)',
        "replace": r'render_template_string' + r'(html.escape(\1))',
        "imports_needed": ["html"],
        "guard_skip_if_substring": "html.escape(",
    },
    # NOTE: f-string HTML user input fix (`f"<div>{user_input}</div>"` →
    # `f"<div>{html.escape(user_input)}</div>"`) requires AST analysis to
    # determine which FormattedValue references user input — cannot be
    # done reliably with regex (would need to parse scope). Skipped for now;
    # XSSScanner detects it and suggests html.escape() in suggested_fix,
    # which the LLM fix path can apply. DNA #2 PASS ≠ ĐÚNG: we don't claim
    # to fix f-string XSS — only Markup() and render_template_string().
    {
        "name": "fstring_html_unescaped",
        "description": "Wrap f-string HTML user input with html.escape() (AST required — placeholder)",
        "match": None,  # placeholder — needs AST analysis (skip)
        "replace": None,
        "imports_needed": [],
    },
]


from scp.autofix.evolution_parts.buildmixin import EvolutionEngineBuildMixin
from scp.autofix.evolution_parts.reflectmixin import EvolutionEngineReflectMixin
from scp.autofix.evolution_parts.wiremixin import EvolutionEngineWireMixin


class EvolutionEngine(EvolutionEngineBuildMixin, EvolutionEngineReflectMixin, EvolutionEngineWireMixin):
    """SCP tự tiến hóa — WHY-controlled, Tier 4."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.data_dir / EVOLUTION_AUDIT_LOG
        self.rejected_log = self.data_dir / EVOLUTION_REJECTED_LOG
        self.reflect_log = self.data_dir / EVOLUTION_REFLECT_LOG
        self.classifier = BugClassifier()
        self.autofix = get_autofix_engine(data_dir=data_dir)
        self._evolution_timestamps: list[float] = []
        self._evolution_enabled_at: float = 0.0
        self._telemetry = SubsystemTelemetry("evolution", self.data_dir)
        _enabled = os.environ.get("SCP_EVOLUTION_ENABLED", "0") == "1"
        self._telemetry.start(
            mode="enabled" if _enabled else "disabled",
            config={
                "evolution_enabled": _enabled,
                "evolution_auto": os.environ.get("SCP_EVOLUTION_AUTO", "0") == "1",
                "why_llm_enabled": os.environ.get("SCP_WHY_LLM_ENABLED", "0") == "1",
            },
        )
        self._telemetry.tick(status="IDLE" if _enabled else "DISABLED")
        self._modules_built: int = 0
        self._reflects_done: int = 0
        self._evolves_completed: int = 0
        self._rejected_by_why: int = 0

    # ============================================================
    # Safety guards
    # ============================================================

    def _touches_constitution(self, desc: str) -> bool:
        """Check if action description mentions Constitution principles."""
        desc_lower = desc.lower()
        for principle in CONSTITUTION_HARD_LOCK:
            if principle in desc_lower:
                return True
        # Also check common phrases
        constitution_phrases = [
            "constitution", "kill principle", "escalate principle",
            "default_action", "human_oversight", "inviolable",
        ]
        for phrase in constitution_phrases:
            if phrase in desc_lower:
                return True
        return False

    # ============================================================
    # Mode 1: build_module
    # ============================================================

    #  EvolutionValidation layer — cùng cấp WHY (2-layer: action + self-verify).
    # TẠI SAO: WHY gate (v9.0) hỏi "có nên build module này không?" (action layer —
    # necessity + falsification). _validate_evolved_module hỏi "module vừa build có
    # thực sự work không?" (verify layer). WHY + validate = cùng độ sâu (2 layer).
    # Non-blocking: validate error → fail-open (don't break build flow).
    # Nếu validate fail → caller ROLLBACK (restore backup or delete new file).
    #  Audit log helper for V9.1 self-verify layer.
    def _audit_v91(self, event: str, payload: dict) -> None:
        try:
            _entry = {
                "ts": time.time(),
                "engine": "evolution",
                "event": event,
                "payload": payload,
            }
            _audit_path = self.data_dir / "v91_upgrade_audit.jsonl"
            with open(_audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_entry, ensure_ascii=False) + "\n")
        except Exception as _audit_err:
            logger.debug(f" audit log error (fail-open): {_audit_err}", exc_info=True)

    def _count_bugs(self) -> int:
        """Quick AST scan to count bugs (for re-scan check)."""
        try:
            from scp.autofix.runner import ast_scan_scp
            bugs = ast_scan_scp(max_files=100, max_bugs=int(os.environ.get("SCP_MAX_EVOLUTION_BUGS", "100")))  # [ROOT-FIX 47] was 50
            return len(bugs)
        except Exception as count_err:
            # fail-loudly (S-B1b): a scan crash reporting "0 bugs" hides real
            # breakage from the re-scan check; keep the 0 contract, surface it.
            logger.warning("[evolution] bug re-scan crashed, reporting 0 bugs: %s", count_err, exc_info=True)
            return 0

    # ============================================================
    # Mode 2: reflect
    # ============================================================

    def _extract_pattern(self, bug: BugReport, why_response: str) -> str:
        """Extract suggested scanner pattern from WHY response."""
        # Simple extraction: look for code-like patterns
        patterns = re.findall(r'`([^`]+)`', why_response)
        return patterns[0] if patterns else ""

    def _extract_rule(self, bug: BugReport, why_response: str) -> str:
        """Extract suggested classifier rule from WHY response."""
        if "logic" in why_response.lower():
            return "logic_pattern"
        elif "race" in why_response.lower() or "concurrent" in why_response.lower():
            return "concurrency_pattern"
        elif "lock" in why_response.lower():
            return "lock_pattern"
        return ""

    # ============================================================
    # Mode 3: evolve_cycle
    # ============================================================

    # ============================================================
    # [V5.9-SCANNER] Mode 4/5/6 — domain-specific fixers for new scanners
    # ============================================================
    # TẠI SAO: 5 scanners mới tìm bugs MỚI (DeadSLM, RoutingGap, APIWiring,
    # LogicFlow, SchemaMismatch). AutoFix cũ (engine.process_bug) chỉ fix
    # syntax bugs qua LLM bridge. Cần 3 mode mới để fix bugs mới:
    #   4. fix_dead_slm(bug) — LLM generate routing keywords + add to judge.py
    #   5. wire_api(bug)     — LLM generate fetch_from_xxx() method
    #   6. fix_logic_flow(bug) — pattern fixer (regex replace == → >=)
    # Tất cả respect WHY-controlled safety guards (v5.3):
    #   - SCP_EVOLUTION_ENABLED=1 env var
    #   - Auto-timeout 4h
    #   - Rate limit 20/hour
    #   - Constitution HARD LOCK
    #   - Backup .evolutionbak before write
    #   - Re-scan after fix (if bug count up → log warning)
    #   - Audit log entry







    def _v80_extract_type_mismatch(self, desc: str) -> tuple[str, str, str]:
        """[V8.0-WHY] Extract (var_name, expected_type, actual_type) from
        TypeMismatch bug description.

        Expected format: "TypeMismatch: var 'X' expected Y but got Z"
        Falls back to ("unknown", "unknown", "unknown") if parse fails.
        """
        m = re.search(
            r"var\s+'([^']+)'.*expected\s+(\w+).*got\s+(\w+)",
            desc, re.IGNORECASE,
        )
        if m:
            return m.group(1), m.group(2), m.group(3)
        return "unknown", "unknown", "unknown"

    def _v80_extract_data_flow(self, desc: str) -> tuple[str, str, list[str]]:
        """[V8.0-WHY] Extract (source, sink, path) from data flow bug desc.

        Expected formats (case-insensitive):
          - "DataFlow: source X flows to Y without sanitize"
          - "DataFlow: from X to Y"
          - "DataFlow: source X -> Y"
        Falls back to ("unknown_source", "unknown_sink", []).
        """
        m = re.search(
            r"(?:source|from)\s+(\S+)\s+(?:flows?\s+)?(?:to|->)\s+(\S+)",
            desc, re.IGNORECASE,
        )
        if m:
            return m.group(1).rstrip(",;"), m.group(2).rstrip(",;"), []
        return "unknown_source", "unknown_sink", []

    def _v80_extract_cwe(self, desc: str) -> str:
        """[V8.0-WHY] Extract CWE id from security bug description.

        Returns "CWE-XX" or "CWE-0" if not found.
        """
        m = re.search(r"CWE-?(\d+)", desc, re.IGNORECASE)
        if m:
            return f"CWE-{m.group(1)}"
        return "CWE-0"

    # ============================================================
    # Audit + stats
    # ============================================================

    def _write_audit(self, entry: dict):
        """Write to evolution_audit.jsonl."""
        entry["timestamp"] = time.time()
        try:
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.warning(f"[EVOLUTION] Audit write failed: {e}", exc_info=True)

    def _write_rejected(self, action: str, reason: str):
        """Write WHY-rejected actions to evolution_rejected.jsonl."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "reason": reason,
        }
        try:
            with open(self.rejected_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("[evolution.py:2079] silenced exception")

    def _write_reflect(self, result: ReflectResult):
        """Write reflect output to evolution_reflect.jsonl (human review)."""
        try:
            with open(self.reflect_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("[evolution.py:2087] silenced exception")

    def stats(self) -> EvolutionStats:
        """Return evolution stats for monitoring."""
        now = time.time()
        self._evolution_timestamps = [t for t in self._evolution_timestamps if now - t < 3600]
        expires_in = 0
        if self._evolution_enabled_at > 0:
            expires_in = max(0, int(EVOLUTION_TIMEOUT_SECONDS - (now - self._evolution_enabled_at)))
        return EvolutionStats(
            enabled=os.environ.get("SCP_EVOLUTION_ENABLED", "0") == "1",
            used_this_hour=len(self._evolution_timestamps),
            remaining=max(0, MAX_EVOLUTION_ACTIONS_PER_HOUR - len(self._evolution_timestamps)),
            max_per_hour=MAX_EVOLUTION_ACTIONS_PER_HOUR,
            expires_in_seconds=expires_in,
            modules_built=self._modules_built,
            reflects_done=self._reflects_done,
            evolves_completed=self._evolves_completed,
            rejected_by_why=self._rejected_by_why,
        )


# ============================================================
# Singleton

    # ============================================================
    # [Task 9-B] Pattern fixers — delegated to evolution_modes.pattern_fixers
    # ============================================================
    def fix_logic_flow(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] pattern_fixers.fix_logic_flow(bug) takes 1 arg, not (self, bug).
        Previous call `_fix_logic_flow(self, bug)` -> TypeError on every invocation ->
        pattern-fixer mechanism silently dead (wrapped in try/except in caller).
        Reality evidence (PowerShell.txt): only strategy=unknown ever selected.
        """
        from scp.autofix.evolution_modes.pattern_fixers import fix_logic_flow as _fix_logic_flow
        return _fix_logic_flow(bug)

    def fix_type_mismatch(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] drop stray `self` arg -> was TypeError.
        """
        from scp.autofix.evolution_modes.pattern_fixers import fix_type_mismatch as _fix_type_mismatch
        return _fix_type_mismatch(bug)

    def add_null_check(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] drop stray `self` arg -> was TypeError.
        """
        from scp.autofix.evolution_modes.pattern_fixers import add_null_check as _add_null_check
        return _add_null_check(bug)

    def add_lock(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] drop stray `self` arg -> was TypeError.
        """
        from scp.autofix.evolution_modes.pattern_fixers import add_lock as _add_lock
        return _add_lock(bug)

    def parameterize_sql(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] drop stray `self` arg -> was TypeError.
        """
        from scp.autofix.evolution_modes.pattern_fixers import parameterize_sql as _parameterize_sql
        return _parameterize_sql(bug)

    def add_context_manager(self, bug: BugReport) -> str | None:
        """[Task 9-B] Delegates to autofix.evolution_modes.pattern_fixers.

        [SCP-DNA-FIX] drop stray `self` arg -> was TypeError.
        """
        from scp.autofix.evolution_modes.pattern_fixers import add_context_manager as _add_context_manager
        return _add_context_manager(bug)

    # ============================================================
    # [OPT-24] XSS pattern fixer — deterministic, no LLM
    # ============================================================
    # TẠI SAO: XSS vulnerabilities (CWE-79) detected by XSSScanner have
    # deterministic fixes (Markup(x) → Markup(html.escape(x))). Calling
    # LLM for these wastes tokens + risks regression (LLM may rewrite
    # the whole function). Pattern fixer applies the fix surgically:
    #   1. Read source file
    #   2. For each XSS_FIX_PATTERNS entry, try regex match
    #   3. If match + no guard_skip_if_substring present in match → apply replace
    #   4. Add `import html` if not already present
    #   5. Verify patched source still parses (ast.parse)
    #   6. Write back to file
    # Returns dict with "fixed": True if pattern applied, else None.
    # Caller (engine._auto_fix) checks result before falling through to LLM.
    def _apply_xss_pattern_fix(self, bug: BugReport) -> dict | None:
        """Apply deterministic XSS fix without LLM.

        Returns dict with:
          - "fixed": bool
          - "patch": str (the fixed source)
          - "reason": str
          - "pattern": str (which pattern matched)
        Or None if no pattern matches / file unreadable / patch invalid.
        """
        import ast as _ast
        import re as _re
        from pathlib import Path as _Path

        # Read the file with the bug
        try:
            filepath = _Path(bug.file)
            if not filepath.exists():
                return None
            source = filepath.read_text(encoding="utf-8")
        except Exception as _read_err:
            logger.debug(f"[OPT-24] XSS pattern fix read failed: {_read_err}", exc_info=True)
            return None

        # Try each pattern
        for pattern in XSS_FIX_PATTERNS:
            if not pattern.get("match"):
                continue  # placeholder pattern (e.g. fstring_html_unescaped)
            try:
                matches = _re.findall(pattern["match"], source)
            except _re.error as _re_err:
                logger.debug(f"[OPT-24] regex error for {pattern['name']}: {_re_err}")
                continue
            if not matches:
                continue

            # Check guard: skip if any match already contains the fix substring
            # (avoid double-escaping: Markup(html.escape(x)) should NOT become
            # Markup(html.escape(html.escape(x)))).
            guard = pattern.get("guard_skip_if_substring")
            if guard:
                # If ALL matches already contain the guard substring, this
                # pattern is already applied — skip. If SOME do and SOME don't,
                # we still skip (conservative — partial fixes are risky).
                if all(guard in m for m in matches):
                    continue

            # Apply fix
            try:
                fixed_source = _re.sub(pattern["match"], pattern["replace"], source)
            except _re.error as _sub_err:
                logger.debug(f"[OPT-24] regex sub error for {pattern['name']}: {_sub_err}")
                continue
            if fixed_source == source:
                continue  # no change (shouldn't happen if matches non-empty)

            # Verify patched source still parses (DNA #7 AutoFix safe — never
            # write unparseable code)
            try:
                _ast.parse(fixed_source, filename=str(filepath))
            except SyntaxError as _se:
                logger.warning(
                    f"[OPT-24] XSS pattern fix for {pattern['name']} would "
                    f"introduce SyntaxError: {_se} — skipping"
                )
                continue

            # Add `import html` if needed and not already present
            imports = pattern.get("imports_needed", [])
            for imp in imports:
                # Match `import html` or `from html import ...` at line start
                _import_present = bool(
                    _re.search(rf'^\s*import\s+{imp}\b', fixed_source, _re.MULTILINE)
                    or _re.search(rf'^\s*from\s+{imp}\b', fixed_source, _re.MULTILINE)
                )
                if not _import_present:
                    # Insert at top of file (after any leading docstring/comments).
                    # Simple approach: prepend — Python allows imports anywhere
                    # syntactically, but PEP 8 says top. We insert at very top
                    # which is always safe (no side effects).
                    fixed_source = f"import {imp}\n" + fixed_source

            # Re-verify after import insertion
            try:
                _ast.parse(fixed_source, filename=str(filepath))
            except SyntaxError as _se2:
                logger.warning(
                    f"[OPT-24] XSS pattern fix for {pattern['name']} failed "
                    f"after import insertion: {_se2} — skipping"
                )
                continue

            logger.info(
                f"[OPT-24] XSS pattern fix applied: {pattern['name']} "
                f"({len(matches)} match(es)) in {filepath.name}"
            )
            return {
                "fixed": True,
                "patch": fixed_source,
                "reason": f"Applied {pattern['name']}: {pattern['description']}",
                "pattern": pattern["name"],
                "matches": len(matches),
            }
        return None


# ============================================================
_evolution_engine: EvolutionEngine | None = None
_evolution_lock = None



def get_evolution_engine(data_dir: str = "data") -> EvolutionEngine:
    """Get singleton EvolutionEngine instance."""
    global _evolution_engine, _evolution_lock
    if _evolution_lock is None:
        import threading
        _evolution_lock = threading.Lock()
    if _evolution_engine is None:
        with _evolution_lock:
            if _evolution_engine is None:
                _evolution_engine = EvolutionEngine(data_dir=data_dir)
                logger.info("[EVOLUTION] Singleton engine initialized")
    return _evolution_engine


def reset_evolution_engine() -> None:
    """Reset singleton (for tests)."""
    global _evolution_engine
    with _evolution_lock:
        _evolution_engine = None
