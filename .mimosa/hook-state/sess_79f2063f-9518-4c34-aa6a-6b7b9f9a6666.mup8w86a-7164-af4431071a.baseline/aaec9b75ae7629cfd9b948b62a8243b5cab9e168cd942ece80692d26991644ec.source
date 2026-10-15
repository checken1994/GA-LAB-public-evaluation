"""
EvolutionEngine mixin — extracted from evolution.py (Task 19-A).
 kept verbatim; only the method location changed.
"""
import ast
import json
import logging
from pathlib import Path as _Path

_SCP_ROOT = _Path(__file__).resolve().parent.parent.parent.parent  # scp-vietnam/

logger = logging.getLogger("scp.autofix")
import os
import re
import time
from pathlib import Path

from scp.core.learning_run_ledger import ledger_run
from scp.core.subsystem_telemetry import telemetry_sync_cycle

logger = logging.getLogger("scp.autofix.evolution")

def _write_evolution_stage(stage: str, **details) -> None:
    """Write sanitized child checkpoint for parent timeout diagnosis."""
    stage_file = os.environ.get("SCP_EVOLUTION_STAGE_FILE", "").strip()
    if not stage_file:
        return
    try:
        payload = {"stage": stage, **{k: str(v)[:120] for k, v in details.items()}}
        target = Path(stage_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        logger.debug("[EVOLUTION_STAGE] checkpoint write failed: %s", type(exc).__name__)

from scp.autofix.classifier import BugReport
from scp.autofix.evolution import (
    EVOLUTION_TIMEOUT_SECONDS,
    MAX_EVOLUTION_ACTIONS_PER_HOUR,
    ReflectResult,
)


class EvolutionEngineReflectMixin:
    """Mixin for EvolutionEngine — provides ReflectMixin methods."""

    def reflect(self, bug: BugReport, fix_diff: str) -> ReflectResult:
        """Học từ mỗi bug đã fix — WHY-controlled.

        Flow:
          1. WHY layer 1: "Tại sao bug này xảy ra?" (root cause)
          2. WHY layer 2: "Tại sao nguyên nhân này đúng? Bác bỏ được không?"
          3. If self_falsified → don't learn (log to rejected)
          4. If not → extract lesson, suggest pattern/rule
          5. Write to evolution_reflect.jsonl (human review)
        """
        action_desc = f"reflect: {bug.file}:{bug.line} ({bug.bug_type})"

        if not self._should_evolve(action_desc):
            return ReflectResult(
                bug_file=bug.file, bug_line=bug.line, bug_type=bug.bug_type,
                fix_diff=fix_diff, why_necessity="evolution disabled",
                why_falsification="", self_falsified=True, lesson_learned=""
            )

        # WHY layer 1: root cause
        why1_prompt = f"""Phân tích root cause của bug sau:

Bug: {bug.bug_type} at {bug.file}:{bug.line}
Description: {bug.description}
Fix applied: {fix_diff[:500]}

Hỏi: "Tại sao bug này xảy ra?" — tìm root cause (1-2 câu).
"""
        # [2026-08-29 WIRED BRAIN — Reality Check v3] Reflect phase PHẢI ăn
        # kho tri thức TOP-1% (đã deep-scrape README thật): root-cause phân
        # tích có tham chiếu cách các hệ thống hàng đầu xử lý cùng vấn đề,
        # thay vì học trong chân không. Fail-open: warehouse trống/lỗi →
        # prompt giữ nguyên.
        try:
            from scp.autofix.llm_fix import _top_systems_references

            references = _top_systems_references(bug)
            if references:
                why1_prompt += (
                    "\n\n[SCP TOP-1% KNOWLEDGE WAREHOUSE — thực hành đã thu thập từ các hệ thống hàng đầu, "
                    "dùng để đối chiếu root cause, không copy mù]\n" + references
                )
        except Exception as _ref_err:
            logger.debug(f"[reflect] warehouse enrichment skipped: {_ref_err}", exc_info=True)

        try:
            from scp.autofix.llm_fix import _call_openrouter
            why1_response = _call_openrouter(why1_prompt, max_tokens=300) or ""
        except Exception as why1_err:
            # silent-by-design: documented default — WHY1 enrichment is
            # best-effort; reflection continues with an empty WHY1 response.
            logger.debug("[reflect] WHY1 LLM enrichment failed, continuing without it: %s", why1_err, exc_info=True)
            why1_response = ""

        # WHY layer 2: falsification
        is_falsified, why2 = self._why_falsification_check(
            f"Root cause: {why1_response[:200]}",
            f"Bug: {bug.description}\nFix: {fix_diff[:300]}"
        )

        result = ReflectResult(
            bug_file=bug.file, bug_line=bug.line, bug_type=bug.bug_type,
            fix_diff=fix_diff, why_necessity=why1_response.strip(),
            why_falsification=why2, self_falsified=is_falsified,
            lesson_learned="" if is_falsified else why1_response.strip()[:200],
        )

        # Extract suggested pattern/rule (if not falsified)
        if not is_falsified:
            result.suggested_pattern = self._extract_pattern(bug, why1_response)
            result.suggested_rule = self._extract_rule(bug, why1_response)

        # Audit
        self._evolution_timestamps.append(time.time())
        self._reflects_done += 1
        self._write_reflect(result)

        # [V8.0-WHY] Deep WHY analysis — bug-type-specific WHY modes.
        # TẠI SAO: WHY layer 1+2 trong reflect() (necessity + falsification) là
        # generic — không phân biệt bug type. v8.0 WhyEngine có 3 mode mới
        # (type_inference_why, data_flow_why, security_threat_why) hỏi bug-type-
        # specific WHY questions. Mỗi mode OPT-IN via env var (default OFF —
        # don't break existing flow). Analysis logged to audit nhưng KHÔNG ảnh
        # hưởng ReflectResult.self_falsified (set by WHY layer 2). Chỉ enrich
        # audit trail cho human review.
        try:
            v80_analysis = self._v80_why_deep_analysis(bug, fix_diff)
            if v80_analysis:
                self._write_audit({
                    "action": "v80_why_deep_analysis",
                    "bug_file": bug.file,
                    "bug_line": bug.line,
                    "bug_type": bug.bug_type,
                    "analysis": v80_analysis,
                })
        except Exception as e:
            logger.debug(f"[V8.0-WHY] deep analysis dispatch failed: {e}", exc_info=True)

        # [V10.0-KB-EVOLVE] Save lesson to KB — accumulate for scanner evolution
        # TẠI SAO: v9.1 reflect → lesson → ĐỂ ĐÓ. v10.0: lesson → KB → scanner evolve
        # → "càng chạy lâu càng thông minh" THẬT
        try:
            from scp.meta.kb_evolve import extract_lesson_from_reflect, extract_pattern_from_lesson, get_kb_store
            _kb = get_kb_store()
            _lesson = extract_lesson_from_reflect(result, fix_verified=True)
            if _lesson:
                _kb.save_lesson(_lesson)
                # Extract pattern → save for scanner evolution
                _pattern = extract_pattern_from_lesson(_lesson)
                if _pattern:
                    _kb.save_pattern(_pattern)
                    logger.info(f"[V10.0-KB-EVOLVE] Lesson + pattern saved: "
                                f"bug_type={_lesson.bug_type}, lesson_id={_lesson.lesson_id}")
        except Exception as _kb_err:
            logger.warning(f"[V10.0-KB-EVOLVE] KB save error: {_kb_err}", exc_info=True)  # [V10.1-FIX] was debug → warning

        return result


    @ledger_run("evolution")
    @telemetry_sync_cycle
    def evolve_cycle(self, max_bugs: int = 20) -> dict:
        """Vòng lặp khép kín: WHY → Audit → Fix → Reflect.

        Flow:
          1. WHY: "Còn thiếu gì?" (dựa trên KB hiện tại — skip if KB empty)
          2. Audit: AST scan scp/
          3. Fix: AutoFix.process_bug() for each (Tier 1/2 auto, Tier 3 if env)
          4. Reflect: học từ mỗi fix
          5. (KB update happens via reflect)

        Returns summary dict.
        """
        action_desc = f"evolve_cycle: max_bugs={max_bugs}"
        _write_evolution_stage("cycle_start", max_bugs=max_bugs)

        if not self._should_evolve(action_desc):
            return {"action": "skipped", "reason": "evolution disabled"}

        # Step 1: WHY — ask "còn thiếu gì?" (placeholder, would query KB)
        # Skip for now — KB query is complex

        # Step 2: Audit
        cycle_started = time.monotonic()
        logger.info("[EVOLUTION_STAGE] scan_start max_bugs=%s", max_bugs)
        _write_evolution_stage("scan_start", max_bugs=max_bugs)
        from scp.autofix.runner import ast_scan_scp
        bugs = ast_scan_scp(max_bugs=max_bugs)
        logger.info("[EVOLUTION_STAGE] scan_complete findings=%s elapsed_ms=%s", len(bugs), int((time.monotonic() - cycle_started) * 1000))
        _write_evolution_stage("scan_complete", findings=len(bugs))
        logger.info(f"[EVOLUTION] Audit found {len(bugs)} bugs")

        # Step 3: Fix
        fixed = 0
        reflects = []
        for bug_index, bug in enumerate(bugs, 1):
            logger.info("[EVOLUTION_STAGE] finding_start index=%s total=%s file=%s line=%s", bug_index, len(bugs), getattr(bug, "file", ""), getattr(bug, "line", ""))
            _write_evolution_stage("finding_start", index=bug_index, total=len(bugs))
            # [V9.0-WHY-GATE] WHY gates evolution cycle — PRIMARY CONTROL GATE
            # TẠI SAO: v8.0 WHY = cố vấn. v9.0 WHY = chốt. WHY Gate can skip a
            # bug in the evolve cycle (e.g., relaxation that loosens security)
            # before LLM bridge + reflect run. Non-blocking on WHY error.
            # NOTE: `fix_diff` not available pre-fix — use suggested_fix as the
            # closest pre-fix context (adapted from task spec).
            try:
                from scp.meta.why_gate import get_why_gate
                _why = get_why_gate().gate(
                action_type="autofix",
                    action_desc=f"Evolve cycle: fix bug {bug.file}:{bug.line}",
        context=("deterministic BareExceptPass logging replacement" if getattr(bug, "bug_type", "") == "BareExceptPass" else (str(bug.suggested_fix) if bug.suggested_fix else "")[:200]),
                )
                if not _why.allowed:
                    logger.info(
                        f"[V9.0-WHY-GATE] Evolve-cycle bug skipped by WHY: "
                        f"{bug.file}:{bug.line} — {_why.falsification_reason[:80]}"
                    )
                    continue  # skip this bug in evolve cycle
            except Exception as _why_err:
                # [REAUDIT-FIX] Changed from "default allow" to "default UPHOLD" for consistency
                # with G2-FIX PERM-05 (WHY Gate must fail-closed on errors)
                logger.warning(
                    f"[V9.0-WHY-GATE] WHY Gate error (default UPHOLD [G2-FIX]): {_why_err}", exc_info=True
                )
                continue  # skip this bug — don't proceed without WHY check

            try:
                # Use LLM bridge (from v5.1 FIX-3)
                from scp.autofix.llm_fix import process_bug_with_llm
                logger.info("[EVOLUTION_STAGE] fix_start index=%s", bug_index)
                _write_evolution_stage("fix_start", index=bug_index)
                result = process_bug_with_llm(bug, self.autofix)
                logger.info("[EVOLUTION_STAGE] fix_complete index=%s action=%s", bug_index, result.get("action") if isinstance(result, dict) else "unknown")
                _write_evolution_stage("fix_complete", index=bug_index)
                if result.get("action") == "fixed":
                    fixed += 1
                    # Step 4: Reflect
                    fix_diff = result.get("patched", "")
                    logger.info("[EVOLUTION_STAGE] reflect_start index=%s", bug_index)
                    _write_evolution_stage("reflect_start", index=bug_index)
                    reflect_result = self.reflect(bug, str(fix_diff))
                    logger.info("[EVOLUTION_STAGE] reflect_complete index=%s", bug_index)
                    _write_evolution_stage("reflect_complete", index=bug_index)
                    reflects.append({
                        "file": bug.file, "line": bug.line,
                        "self_falsified": reflect_result.self_falsified,
                        "lesson": reflect_result.lesson_learned[:100],
                    })
            except Exception as e:
                logger.warning(f"[EVOLUTION] Fix+reflect failed for {bug.file}:{bug.line}: {e}", exc_info=True)

        self._evolution_timestamps.append(time.time())
        self._evolves_completed += 1
        self._write_audit({
            "action": "evolve_cycle",
            "bugs_found": len(bugs),
            "bugs_fixed": fixed,
            # [R39] Make the durable learning contract explicit. `verified`
            # counts fixes that passed the AutoFix verification path; `stored`
            # counts reflect records durably appended by `_write_reflect`.
            "verified": fixed,
            "stored": len(reflects),
            "reflects": reflects,
        })

        return {
            "action": "evolved",
            "bugs_found": len(bugs),
            "bugs_fixed": fixed,
            "verified": fixed,
            "stored": len(reflects),
            "reflects": reflects,
        }


    def fix_dead_slm(self, bug: BugReport) -> dict:
        """[V5.9-SCANNER] Mode 4: Fix DeadSLM by generating routing keywords.

        Flow:
          1. Safety guards (env, timeout, rate limit, constitution)
          2. WHY layer 1: "Tại sao cần route SLM này?"
          3. LLM generate routing keywords (Vietnamese + English)
          4. WHY layer 2: "Tại sao keywords này đúng? Bác bỏ được không?"
          5. Backup judge.py → .evolutionbak
          6. Insert routing block before `return domains` in _route_question()
          7. Verify syntax (ast.parse)
          8. Re-scan: dead SLM count should decrease
          9. Audit log
        """
        # [G2-FIX OV-01] Layer 3 must respect Layer 2 capability check
        try:
            from scp.meta.capability_levels import CapabilityManager
            _cap = CapabilityManager()
            if not _cap.can_do("build_module"):
                # [SCP-DNA-FIX R5-2] TẠI SAO: `_cap.level` doesn't exist on
                # CapabilityManager — only `_current_level` (private) +
                # `get_current_level()` (public accessor) exist. AttributeError
                # was swallowed by the broad `except Exception` below → wrong
                # error message on operator-restricted SCP_CAPABILITY_LEVEL.
                # pylint E1101 caught it. Same fix as buildmixin.py:47,330.
                return {"status": "blocked", "reason": f"capability_level={_cap.get_current_level()} denies build_module"}
        except Exception as _e:
            logger.debug(f"EvolutionEngineReflectMixin.fix_dead_slm: exception ignored: {_e}", exc_info=True)
            # silent-by-design: explicit blocked status carrying the error reason is returned to the caller.
            return {"status": "blocked", "reason": f"CapabilityManager error: {_e}"}
        action_desc = f"fix_dead_slm: {bug.description[:100]}"
        if not self._should_evolve(action_desc):
            return {"action": "skipped", "reason": "evolution guards blocked"}

        # Extract domain name from bug description
        # Description format: "DeadSLM: SLM 'X' is initialized..."
        import re as _re
        m = _re.search(r"SLM\s+'(\w+)'", bug.description)
        if not m:
            return {"action": "skipped", "reason": "could not extract SLM name from bug"}
        slm_name = m.group(1)

        # WHY layer 1: necessity
        is_necessary, why1 = self._why_necessity_check(
            action_desc, f"SLM: {slm_name}\nFile: {bug.file}:{bug.line}"
        )
        if not is_necessary:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_necessity_failed: {why1}")
            return {"action": "rejected_by_why", "reason": why1, "layer": "necessity"}

        # LLM generate routing keywords
        keywords = self._llm_generate_routing_keywords(slm_name)
        if not keywords:
            return {"action": "skipped", "reason": "LLM keyword generation failed"}

        # WHY layer 2: falsification
        is_falsified, why2 = self._why_falsification_check(
            f"Keywords {keywords} correctly route {slm_name}-related questions",
            f"SLM: {slm_name}\nKeywords: {keywords}"
        )
        if is_falsified:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_falsification_failed: {why2}")
            return {"action": "rejected_by_why", "reason": why2, "layer": "falsification"}

        # Backup + patch judge.py
        judge_path = Path(bug.file)
        if not judge_path.exists():
            return {"action": "skipped", "reason": f"file not found: {judge_path}"}
        bak = judge_path.with_suffix(judge_path.suffix + ".evolutionbak")
        if not bak.exists():
            bak.write_text(judge_path.read_text(encoding="utf-8"), encoding="utf-8")

        original = judge_path.read_text(encoding="utf-8")
        # Build routing block — insert BEFORE the final `return domains`
        # in _route_question(). Naive insertion: find "return domains" and
        # insert before it. (Conservative — don't try to find a semantic spot.)
        kw_list_str = ", ".join(repr(k) for k in keywords)
        routing_block = (
            f"        # [V5.9-SCANNER] auto-generated routing for {slm_name}\n"
            f"        if any(kw in q_lower for kw in [{kw_list_str}]):\n"
            f"            domains.append({slm_name!r})\n"
        )
        # Insert before last `return domains` (the one in _route_question)
        # We need to find a UNIQUE marker. Use the comment line just before
        # `return domains` if present, else just the first `return domains`.
        if "return domains" not in original:
            return {"action": "skipped", "reason": "no 'return domains' marker in judge.py"}
        patched = original.replace("return domains", routing_block + "        return domains", 1)

        # Verify syntax
        try:
            ast.parse(patched, filename=str(judge_path))
        except SyntaxError as e:
            return {"action": "skipped", "reason": f"patched code SyntaxError: {e}"}

        # [P0-FIX] CWE-22 path traversal defense
        if not judge_path.resolve().is_relative_to(_SCP_ROOT):
            raise ValueError(f"Path traversal blocked: {judge_path} outside SCP_ROOT")
        judge_path.write_text(patched, encoding="utf-8")

        # Audit
        self._evolution_timestamps.append(time.time())
        self._write_audit({
            "action": "fix_dead_slm",
            "slm_name": slm_name,
            "keywords": keywords,
            "why_necessity": why1,
            "why_falsification": why2,
            "file": str(judge_path),
            "line": bug.line,
        })

        return {
            "action": "fixed",
            "slm_name": slm_name,
            "keywords_added": keywords,
            "file": str(judge_path),
            "why_necessity": why1,
            "why_falsification": why2,
        }


    def _llm_generate_routing_keywords(self, slm_name: str) -> list[str] | None:
        """Call LLM to generate routing keywords for a domain SLM.

        Returns list of 5-10 keywords (Vietnamese + English mix).
        """
        prompt = f"""Generate routing keywords for an SLM (Specialized Language Model) named "{slm_name}" in SCP.

The SLM verifies questions about this domain. Routing keywords are matched
case-insensitively against the lowercased question (q_lower). If ANY keyword
appears in the question, it routes to this SLM.

Requirements:
- Generate 5-10 keywords covering common question phrasings
- Include BOTH Vietnamese and English (SCP serves both languages)
- Include synonyms, abbreviations, technical terms
- Avoid overly generic words (e.g. "the", "of", "what")
- Format: comma-separated list on one line, no quotes

Example for "medical": bệnh, thuốc, triệu chứng, điều trị, vaccine, dosage, treatment, symptom, medicine, health

Output ONLY the comma-separated keywords, nothing else."""
        try:
            from scp.autofix.llm_fix import _call_openrouter
            response = _call_openrouter(prompt, max_tokens=200)
            if not response:
                return None
            # Strip newlines/markdown
            response = response.strip().strip("`").strip()
            # Split on commas, clean up
            keywords = [k.strip().strip('"').strip("'").lower() for k in response.split(",")]
            keywords = [k for k in keywords if k and len(k) > 1]
            return keywords[:10]  # cap at 10
        except Exception as e:
            logger.warning(f"[EVOLUTION] LLM keyword gen failed for {slm_name}: {e}", exc_info=True)
            return None


    def _llm_generate_api_method(self, api_key_var: str, target_file: str) -> str | None:
        """Call LLM to generate a fetch_from_xxx() method for an API."""
        prompt = f"""Generate a Python method that fetches data from an API.

API key env var: {api_key_var}
Target file: {target_file}

Requirements:
- Method name: fetch_from_{api_key_var.lower().replace('_api_key', '')}
- Read API key via: os.environ.get("{api_key_var}", "").strip()
- Return None if key is empty (don't even try to call)
- Use scp.core.api_utils.fetch_with_retry for HTTP
- Wrap in try/except, log errors via logger.warning(...)
- Return a dict with at least {{"value": ..., "source": "{api_key_var}", "confidence": 0.7}}
- Be defensive: validate response, handle None/missing fields
- Use type hints (Python 3.10+)
- 30-50 lines max

Output ONLY the Python function code, no markdown fences, no explanation.
The function should be a module-level function (not a class method).
"""
        try:
            from scp.autofix.llm_fix import _call_openrouter
            response = _call_openrouter(prompt, max_tokens=1500)
            if not response:
                return None
            # Strip markdown fences
            response = re.sub(r'^```python\s*\n', '', response)
            response = re.sub(r'\n```\s*$', '', response)
            return response.strip()
        except Exception as e:
            logger.warning(f"[EVOLUTION] LLM API method gen failed: {e}", exc_info=True)
            return None


    def _v80_why_deep_analysis(self, bug: BugReport, fix_diff: str) -> dict:
        """[V8.0-WHY] Dispatch bug → right v8.0 WHY mode based on bug type.

        Returns analysis dict from WhyEngine.{type_inference_why,
        data_flow_why, security_threat_why}, or {} if no mode matches.
        Never raises — wraps all calls in try/except.
        """
        try:
            from scp.meta.why_engine import WhyEngine
            why = WhyEngine()
        except Exception as e:
            logger.debug(f"[V8.0-WHY] WhyEngine init failed: {e}", exc_info=True)
            return {}

        bug_type_lower = (bug.bug_type or "").lower()
        desc = bug.description or ""

        # Dispatch based on bug type / scanner.
        # Note: bug_type_lower has no underscores (e.g. "typemismatch", "dataflow",
        # "securitythreat") — check both with and without underscore for safety.
        if "type" in bug_type_lower and "mismatch" in bug_type_lower:
            var_name, expected, actual = self._v80_extract_type_mismatch(desc)
            return why.type_inference_why(var_name, expected, actual, fix_diff)
        elif "data_flow" in bug_type_lower or "dataflow" in bug_type_lower or "taint" in bug_type_lower:
            source, sink, path = self._v80_extract_data_flow(desc)
            return why.data_flow_why(source, sink, path, fix_diff)
        elif "security" in bug_type_lower or "cwe" in bug_type_lower:
            cwe_id = self._v80_extract_cwe(desc)
            return why.security_threat_why(desc, cwe_id, fix_diff)

        return {}  # no matching mode


    def _should_evolve(self, action_desc: str) -> bool:
        """Check if evolution action is allowed (WHY-controlled).

        Guards:
          1. SCP_EVOLUTION_ENABLED=1 env var
          2. Auto-timeout 4h
          3. Rate limit 20/hour (WHY-controlled, không chặt như Tier 3)
          4. WHY layer 1 (necessity) — "Tại sao cần action này?"
          5. WHY layer 2 (falsification) — "Tại sao đúng? Bác bỏ được không?"
          6. Constitution HARD LOCK check
        """
        # Guard 1: explicit env contract. Missing means OFF, never implicit AUTO.
        # Production child-safe.env sets SCP_EVOLUTION_ENABLED=0. Staging must
        # set it to 1 explicitly and still keep AUTO promotion disabled.
        # [R8-2 FIX] The env-transition tracking below must run BEFORE Guard 1
        # returns, so a real 0/unset -> 1 operator re-arm is observable even
        # while the env var is off (Guard 1 denies without recording it).
        now = time.time()
        _env_now = os.environ.get("SCP_EVOLUTION_ENABLED", "0")
        _last_env = getattr(self, "_evolution_env_last_seen", "0")
        if _env_now == "1" and _last_env != "1":
            # Operator re-enabled (was 0/unset, now 1) → reset expired + clock.
            self._evolution_expired = False
            self._evolution_enabled_at = 0.0
            logger.info("[EVOLUTION] Re-arm permitted — env var transition 0→1 detected")
        self._evolution_env_last_seen = _env_now

        if _env_now != "1":
            return False

        # Guard 2: timeout
        # [R8-2 FIX] TẠI SAO: logic cũ set `_evolution_enabled_at = 0.0` khi
        # timeout → next call thấy == 0.0 → re-arm ngay lập tức → Tier-4
        # evolution tự bật lại mỗi 4h chừng nào env var còn set. Fix (same
        # pattern as engine.py Tier-3 auto-approve): set `_evolution_expired`
        # and KEEP the first-enable timestamp. Subsequent calls see
        # expired=True → return False (no re-arm). The expired flag resets
        # ONLY on a genuine 0/unset → 1 env transition (operator intent).
        if getattr(self, "_evolution_expired", False):
            logger.warning(
                f"[EVOLUTION] Expired after {EVOLUTION_TIMEOUT_SECONDS}s -- "
                f"re-enable by UNSETTING + re-SETTING SCP_EVOLUTION_ENABLED=1 "
                f"(R8-2: previous behavior re-armed silently on next action)"
            )
            return False
        if self._evolution_enabled_at == 0.0:
            self._evolution_enabled_at = now  # first call starts the clock
        elif now - self._evolution_enabled_at > EVOLUTION_TIMEOUT_SECONDS:
            logger.warning(
                f"[EVOLUTION] Timed out after {EVOLUTION_TIMEOUT_SECONDS}s -- "
                f"re-enable SCP_EVOLUTION_ENABLED=1"
            )
            self._evolution_expired = True
            # NOTE: keep _evolution_enabled_at as-is (first-enable ts) so
            # subsequent calls still see expiry + stay expired (no re-arm).
            return False

        # Guard 3: rate limit
        self._evolution_timestamps = [t for t in self._evolution_timestamps if now - t < 3600]
        if len(self._evolution_timestamps) >= MAX_EVOLUTION_ACTIONS_PER_HOUR:
            logger.warning(
                f"[EVOLUTION] Rate limit -- {MAX_EVOLUTION_ACTIONS_PER_HOUR}/hour exceeded"
            )
            return False

        # Guard 6: Constitution HARD LOCK
        if self._touches_constitution(action_desc):
            logger.warning(
                f"[EVOLUTION] HARD LOCK -- action touches Constitution: {action_desc[:100]}"
            )
            self._write_rejected(action_desc, "constitution_hard_lock")
            return False

        # WHY layer 1 + 2 are checked in specific modes (build_module/reflect)
        # because they need context (SPEC or bug diff)
        return True


    def _why_necessity_check(self, action_desc: str, context: str) -> tuple[bool, str]:
        """WHY layer 1: 'Tại sao action này cần thiết?'

        Returns (is_necessary, why_reason).
        If not necessary → skip action.
        """
        # Use LLM to ask "Tại sao cần?"
        prompt = f"""Bạn là WHY engine của SCP. Hỏi: "Tại sao action này cần thiết?"

Action: {action_desc}
Context: {context[:500]}

Trả lời 2 phần:
1. WHY: tại sao action này cần thiết (1-2 câu)
2. NECESSARY: yes/no — action có thực sự cần, hay có thể skip?

Output JSON: {{"why": "...", "necessary": true/false}}
"""
        try:
            from scp.autofix.llm_fix import _call_openrouter
            response = _call_openrouter(prompt, max_tokens=500)
            if not response:
                return False, "LLM unavailable [G2-FIX PERM-05] — default UPHOLD (block evolution)"
            # Parse JSON
            import re as _re
            json_match = _re.search(r'\{[^{}]*"why"[^{}]*"necessary"[^{}]*\}', response, _re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return bool(data.get("necessary", True)), data.get("why", "")
        except Exception as e:
            logger.debug(f"[EVOLUTION] WHY necessity check failed: {e}", exc_info=True)
            return False, f"WHY check error [G2-FIX] -- default UPHOLD: {e}"
        return False, "default UPHOLD [G2-FIX PERM-05]: LLM unavailable — block evolution"


    def _why_falsification_check(self, claim: str, context: str) -> tuple[bool, str]:
        """WHY layer 2: 'Tại sao claim này đúng? Bác bỏ được không?'

        Returns (is_falsified, falsification_reason).
        If falsified → REJECT (don't learn/apply).
        """
        prompt = f"""Bạn là WHY engine của SCP. Phản biện claim sau:

Claim: {claim}
Context: {context[:500]}

Trả lời 2 phần:
1. FALSIFICATION: thử bác bỏ claim. Tìm 1 trường hợp claim SAI.
2. SELF_FALSIFIED: yes/no -- claim có bị bác bỏ không?

Output JSON: {{"falsification": "...", "self_falsified": true/false}}
"""
        try:
            from scp.autofix.llm_fix import _call_openrouter
            response = _call_openrouter(prompt, max_tokens=500)
            if not response:
                return False, "LLM unavailable [G2-FIX] -- cannot falsify, default UPHOLD"
            import re as _re
            json_match = _re.search(r'\{[^{}]*"falsification"[^{}]*"self_falsified"[^{}]*\}', response, _re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return bool(data.get("self_falsified", False)), data.get("falsification", "")
        except Exception as e:
            logger.debug(f"[EVOLUTION] WHY falsification check failed: {e}", exc_info=True)
            return False, f"WHY check error [G2-FIX] -- default UPHOLD: {e}"
        return False, "default UPHOLD [G2-FIX]"


