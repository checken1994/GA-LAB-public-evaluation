import logging
import os
import time
from pathlib import Path

from scp.autofix.classifier import BugReport

logger = logging.getLogger("scp.autofix")

# Single source of truth for the per-cycle AutoFix rate limit. The mixin is the
# only code user; engine.py re-exports this name for back-compat. Value 200 per
# the documented product decision: a 50-cap missed 14+ bugs per startup
# (scp/autofix/runner_phases/pre_startup.py) and the original never-reset 10
# bricked the engine after one cycle (engine.py EXEC-1 A3).
MAX_FIXES_PER_CYCLE = 200

class AutoFixMixin:

    def _auto_fix(self, bug: BugReport, report: bool, attack_mode: bool = False) -> dict:
        from pathlib import Path

        from scp.autofix.engine_parts.context import FixContext
        ctx = FixContext(
            bug=bug,
            filepath=Path(bug.file),
            report=report,
            attack_mode=attack_mode
        )

        res = self._auto_fix_gates(ctx)
        if res is not None: return res

        try:
            res = self._auto_fix_part1(ctx)
            if res is not None:
                if res.get("action") != "fixed" and getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    if (ctx.shadow_mgr.active_dir / ctx.shadow_tx_id).is_dir():
                        try:
                            ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"part1 non-fixed: {res.get('reason')}")
                        except Exception as rb_err:
                            logger.warning("[AutoFix] shadow rollback failed after part1 non-fixed — tx %s left in active dir (GC will reclaim): %s", ctx.shadow_tx_id, rb_err, exc_info=True)
                return res

            res = self._auto_fix_part2(ctx)
            if res is not None:
                if res.get("action") != "fixed" and getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    if (ctx.shadow_mgr.active_dir / ctx.shadow_tx_id).is_dir():
                        try:
                            ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"part2 non-fixed: {res.get('reason')}")
                        except Exception as rb_err:
                            logger.warning("[AutoFix] shadow rollback failed after part2 non-fixed — tx %s left in active dir (GC will reclaim): %s", ctx.shadow_tx_id, rb_err, exc_info=True)
                return res

            res = self._auto_fix_part3(ctx)
            # [SANDBOX-SKIP] Surface the visible realtime skip on the eventual
            # result dict: the realtime layer was sandbox-incompatible and its
            # check was delegated to the genuinely-executed shadow canary +
            # post_fix_verify layers. Annotation only — never flips the action.
            if res is not None and getattr(ctx, "realtime_skipped", False):
                res["realtime_skipped"] = True
            if res is not None:
                if res.get("action") != "fixed" and getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    if (ctx.shadow_mgr.active_dir / ctx.shadow_tx_id).is_dir():
                        try:
                            ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"part3 non-fixed: {res.get('reason')}")
                        except Exception as rb_err:
                            logger.warning("[AutoFix] shadow rollback failed after part3 non-fixed — tx %s left in active dir (GC will reclaim): %s", ctx.shadow_tx_id, rb_err, exc_info=True)
                return res

        except Exception as e:
            logger.error(f"[AutoFix] Critical error during auto-fix: {e}", exc_info=True)
            if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                try:
                    ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"auto-fix crash: {e}")
                except Exception as rb_err:
                    logger.critical("[AutoFix] DOUBLE FAILURE: auto-fix crashed AND shadow rollback failed — tx %s left in active dir, manual cleanup may be required: %s", ctx.shadow_tx_id, rb_err, exc_info=True)
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": f"auto-fix crash: {e}",
            }

        if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
            if (ctx.shadow_mgr.active_dir / ctx.shadow_tx_id).is_dir():
                try:
                    ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason="fell through")
                except Exception as rb_err:
                    logger.warning("[AutoFix] shadow rollback failed on fell-through path — tx %s left in active dir (GC will reclaim): %s", ctx.shadow_tx_id, rb_err, exc_info=True)

        return {"action": "skipped", "reason": "fell through"}

    def _auto_fix_gates(self, ctx) -> dict | None:
        """Apply the fix autonomously. Uses code_evolution_agent._apply_fix."""
        # [G2-FIX PERM-03] Protected path check — SCP cannot modify its own permission/security source
        from scp.autofix.runner_phases.ast_scan import _is_protected_path
        ctx.filepath = getattr(ctx.bug, 'file', '') or ''
        if _is_protected_path(ctx.filepath):
            logger.error(f"[G2-FIX] PROTECTED_PATH_BLOCKED: {ctx.filepath} — SCP cannot modify its own permission/security source")
            return {"status": "blocked", "reason": f"protected path: {ctx.filepath}", "action": "protected_path_blocked"}
        # [OPT-14 / Gà §12] Capability gate — check that the current
        # CapabilityManager level allows this kind of auto-fix. Mapping:
        #   Tier 1 (auto-fix no log)  → requires "apply_sandbox"  (Level ≥ 2)
        #   Tier 2 (auto-fix + log)   → requires "apply_test"     (Level ≥ 3)
        #   Tier 4 (attack mode)      → requires "apply_narrow"   (Level ≥ 4)
        # Tier 3 (permission) bypasses this gate — it doesn't apply, just asks.
        #
        # TẠI SAO: Gà §12 — AI không được tự nâng cấp capability. Default
        # level = FULL_PRODUCTION (env var SCP_CAPABILITY_LEVEL) preserves
        # existing behavior. Operators who want the gate set the env var to
        # ANALYSIS_ONLY / SANDBOX / etc.
        try:
            from scp.meta.capability_levels import get_capability_manager
            _cap = get_capability_manager()
            _required_action = "apply_narrow" if ctx.attack_mode else (
                "apply_test" if ctx.report else "apply_sandbox"
            )
            if not _cap.can_do(_required_action):
                logger.warning(
                    f"[AutoFix] Gà §12 — capability denied: current "
                    f"{_cap.get_current_level().name} does not allow "
                    f"'{_required_action}'. Set SCP_CAPABILITY_LEVEL env "
                    f"var to escalate (requires human approval via "
                    f"CapabilityManager.request_escalation)."
                )
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": f"capability denied — current level "
                              f"{_cap.get_current_level().name} lacks "
                              f"'{_required_action}' (Gà §12)",
                }
        except Exception as _cap_err:
            # [G2-FIX PERM-04] Fail-CLOSED: if CapabilityManager crashes, BLOCK auto-fix
            # (security > availability). Previous behavior was fail-open (proceed without
            # check) which allowed a single CapabilityManager ctx.bug to disable all of Layer 2.
            logger.error(f"[AutoFix] CapabilityManager crash — BLOCKING fix (security > availability): {_cap_err}", exc_info=True)
            return {
                "action": "blocked",
                "tier": int(ctx.bug.tier),
                "reason": f"CapabilityManager error (fail-closed): {_cap_err}",
            }

        # [P1-1 FIX R16] Wire verify_chain into the apply step.
        # BEFORE: verify_chain (policy_gate.py:420) was implemented but had 0 callers
        #         (G2-2 in dead-code audit, L1-4 in logic audit). The tamper-evidence
        #         gate was a no-op — audit log could be tampered without detection.
        # AFTER:  before applying any fix, call verify_chain(). If the chain is
        #         tampered (hash mismatch), BLOCK the fix. Fail-open on crash
        #         (DNA #7 — don't brick engine if policy_gate has a ctx.bug), but
        #         LOG LOUDLY so operator investigates.
        try:
            _gate = getattr(self, "policy_gate", None) or getattr(self, "_policy_gate", None)
            if _gate is not None and hasattr(_gate, "verify_chain"):
                _chain_ok, _chain_msg = _gate.verify_chain()
                if not _chain_ok:
                    logger.error(
                        f"[P1-1 R16] Policy gate verify_chain FAILED: {_chain_msg} — "
                        f"BLOCKING fix (audit log may be tampered)"
                    )
                    return {
                        "action": "blocked",
                        "tier": int(ctx.bug.tier),
                        "reason": f"verify_chain failed (audit log tampered?): {_chain_msg}",
                        "blocked_by": "verify_chain",
                    }
                logger.debug(f"[P1-1 R16] verify_chain OK: {_chain_msg}")
        except Exception as _vc_err:
            # Fail-open per DNA #7 (don't brick engine if policy_gate crashes)
            # but LOG LOUDLY — this is a security-sensitive path.
            logger.error(
                f"[P1-1 R16] verify_chain crashed (fail-open, DNA #7): {_vc_err} — "
                f"proceeding with fix, but operator must investigate policy_gate health", exc_info=True
            )

        # [ROOT-FIX-9] Skip auto-FIX entirely for BareExceptPass — runtime log
        # shows 63% rollback rate (24/38 attempts rolled back). LLM-fix
        # [ROOT-FIX 46] Re-enabled BareExceptPass auto-fix — was skipped because
        # llama3.2:3B had 63% rollback rate. Now AutoFix uses OpenRouter V4 flash
        # (deepseek-v4-flash-20260731) FIRST — V4 is much stronger than 3B.
        # validate_patch + diagnostic + monitor will catch bad patches.
        # If rollback rate stays high with V4, re-enable skip via env:
        #   SCP_SKIP_BAREEXCEPTPASS=1
        if ctx.bug.bug_type == "BareExceptPass" and os.environ.get("SCP_SKIP_BAREEXCEPTPASS", "0") == "1":
            logger.info(
                f"[AutoFix] SKIP BareExceptPass (SCP_SKIP_BAREEXCEPTPASS=1) "
                f"({ctx.bug.file}:{ctx.bug.line})"
            )
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "BareExceptPass skipped (SCP_SKIP_BAREEXCEPTPASS=1)",
            }

        # Rate limit
        if self._fixes_this_cycle >= MAX_FIXES_PER_CYCLE:
            return {"action": "skipped", "tier": int(ctx.bug.tier),
                    "reason": "rate limit — max fixes per cycle exceeded"}

        # [V9.0-WHY-GATE] WHY gates AutoFix — PRIMARY CONTROL GATE
        # TẠI SAO: v8.0 WHY = cố vấn (advisory). v9.0 WHY = chốt (block-capable).
        # WHY Gate can block a fix BEFORE it's applied (e.g., relaxation that
        # loosens security). Non-blocking on WHY error (default allow) so
        # AutoFix never breaks because WHY itself crashed. Constitution HARD
        # LOCK preserved inside gate() — WHY cannot override KILL.
        try:
            from scp.meta.why_gate import get_why_gate
            _why = get_why_gate().gate(
                action_type="autofix",
                action_desc=f"Fix {ctx.bug.bug_type} at {ctx.bug.file}:{ctx.bug.line}: {(ctx.bug.description or '')[:100]}",
                context=(ctx.bug.suggested_fix or "")[:200],
            )
            if _why.blocked:
                logger.info(
                    f"[V9.0-WHY-GATE] AutoFix blocked for {ctx.bug.file}:{ctx.bug.line}: "
                    f"{_why.falsification_reason[:100]}"
                )
                return {"action": "skipped", "tier": int(ctx.bug.tier),
                        "reason": f"WHY-GATE blocked: {_why.falsification_reason[:100]}"}
        except Exception as _why_err:
            logger.debug(f"[V9.0-WHY-GATE] WHY Gate error (non-blocking, default allow): {_why_err}", exc_info=True)

        # [R9 v4 WIRE — IMP-24] Constitutional Policy Gate (DEFAULT-DENY).
        # TẠI SAO: WHY gate (v9.0) asks "should we fix?" (action layer —
        # necessity + falsification). PolicyGate asks "does this PATCH TEXT
        # contain a forbidden pattern?" (content layer — constitution KILL).
        # Independent axis — a high-confidence fix can still violate
        # constitution (e.g. `verify=False`, `os.chmod 0o777`, `eval()`).
        # DNA #4 (Constitution KILL) + DNA #22 (PASS ≠ TRUE — confidence ≠
        # safety). HIGHEST SAFETY IMPACT — gate runs BEFORE any file write.
        # Fail-CLOSED per DNA #4: if policy_gate module crashes → BLOCK the
        # fix + log loudly (security > availability). NOT fail-open.
        try:
            from scp.autofix.policy_gate import (
                PolicyFix as _V4_PolicyFix,
            )
            from scp.autofix.policy_gate import (
                evaluate_fix as _v4_policy_evaluate,
            )
            _v4_pf = _V4_PolicyFix(
                fix_id=f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}",
                patch=ctx.bug.suggested_fix or "",
                patched_source="",  # not known yet — gate scans patch text only
                bug_file=ctx.bug.file or "",
                bug_line=int(ctx.bug.line or 0),
                scanner_name="autofix_engine",
                extra={"bug_type": ctx.bug.bug_type, "tier": int(ctx.bug.tier)},
            )
            _v4_decision = _v4_policy_evaluate(_v4_pf)
            if not _v4_decision.allowed:
                logger.warning(
                    f"[R9 v4 IMP-24] POLICY BLOCKED fix for "
                    f"{ctx.bug.file}:{ctx.bug.line}: patterns="
                    f"{_v4_decision.blocked_patterns} "
                    f"reason={_v4_decision.reason[:120]} "
                    f"audit_id={_v4_decision.audit_id}"
                )
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": (
                        f"policy_gate BLOCK (DNA #4): "
                        f"{_v4_decision.reason[:160]}"
                    ),
                    "patched": False,
                    "policy_blocked": True,
                    "policy_audit_id": _v4_decision.audit_id,
                    "policy_patterns": list(_v4_decision.blocked_patterns),
                }
            logger.debug(
                f"[R9 v4 IMP-24] policy gate ALLOWED fix for "
                f"{ctx.bug.file}:{ctx.bug.line} (severity={_v4_decision.severity})"
            )
        except ImportError as _v4_p_imp:
            # DEFAULT-DENY per DNA #4 — constitution KILL gate is DOWN.
            # Block + log loudly. NOT fail-open (security > availability).
            logger.error(
                f"[R9 v4 IMP-24] policy_gate module unavailable — "
                f"DEFAULT-DENY (DNA #4 Constitution KILL gate down): {_v4_p_imp}"
            )
            return {
                "action": "blocked",
                "tier": int(ctx.bug.tier),
                "reason": (
                    f"policy_gate ImportError — DEFAULT-DENY (DNA #4): "
                    f"{_v4_p_imp}"
                ),
                "policy_gate_down": True,
            }
        except Exception as _v4_p_err:
            # DEFAULT-DENY per DNA #4 — gate itself crashed.
            logger.error(
                f"[R9 v4 IMP-24] policy_gate evaluate_fix CRASH — "
                f"DEFAULT-DENY (DNA #4): {_v4_p_err}",
                exc_info=True,
            )
            # [SCP-DNA-FIX R12-11] Meta self-repair — attempt to auto-fix policy_gate.
            # TẠI SAO: VIGIL catches its own diagnostic tool crashes + repairs them
            # runtime. SCP's DEFAULT-DENY is correct (block fix, DNA #4), but it leaves
            # the gate DOWN for all subsequent fixes until manual intervention. Meta
            # self-repair: use LLM to patch policy_gate.py itself, then retry evaluate.
            # Safety: (1) only attempt ONCE per cycle (guard with flag), (2) fail-open
            # if LLM unavailable, (3) NEVER bypass DEFAULT-DENY — if repair fails, still
            # return blocked. DNA #21 (audit the auditor) + DNA #11 (fail loudly).
            try:
                _repaired = self._attempt_meta_repair("policy_gate", _v4_p_err)
                if _repaired:
                    # Retry evaluate after repair
                    from scp.autofix.policy_gate import (
                        PolicyFix as _V4_PolicyFix2,
                    )
                    from scp.autofix.policy_gate import (
                        evaluate_fix as _v4_policy_evaluate2,
                    )
                    _v4_pf2 = _V4_PolicyFix2(
                        fix_id=f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}",
                        patch=ctx.bug.suggested_fix or "",
                        patched_source="",
                        bug_file=ctx.bug.file or "",
                        bug_line=int(ctx.bug.line or 0),
                    )
                    _v4_decision2 = _v4_policy_evaluate2(_v4_pf2)
                    if not _v4_decision2.allowed:
                        return {
                            "action": "skipped", "tier": int(ctx.bug.tier),
                            "reason": f"policy_gate BLOCK after meta-repair: {_v4_decision2.reason[:160]}",
                            "patched": False, "policy_blocked": True,
                            "policy_audit_id": _v4_decision2.audit_id,
                            "policy_patterns": list(_v4_decision2.blocked_patterns),
                            "meta_repaired": True,
                        }
                    logger.info(" policy_gate meta-repair SUCCESS — gate back UP")
                    # Fall through to normal flow (don't return)
                else:
                    logger.warning(" policy_gate meta-repair failed — gate stays DOWN (DEFAULT-DENY)")
            except Exception as _meta_repair_err:
                logger.warning(f" meta-repair attempt crashed (fail-open): {_meta_repair_err}", exc_info=True)
            return {
                "action": "blocked",
                "tier": int(ctx.bug.tier),
                "reason": (
                    f"policy_gate crash — DEFAULT-DENY (DNA #4): {_v4_p_err}"
                ),
                "policy_gate_down": True,
            }

    def _auto_fix_part1(self, ctx) -> dict | None:
        from pathlib import Path as PathCls

        filepath = PathCls(ctx.bug.file)
        if not filepath.exists():
            return {"action": "skipped", "tier": int(ctx.bug.tier),
                    "reason": f"file not found: {ctx.bug.file}"}

        # R6: Durable ShadowSnapshot transaction
        from scp.autofix.shadow_snapshot import get_shadow_snapshot_manager
        ctx.shadow_mgr = get_shadow_snapshot_manager(shadow_dir=getattr(self, "data_dir", Path("data")) / "shadow")
        ctx.shadow_tx_id = ctx.shadow_mgr.begin(
            target_files=[filepath],
            bug_id=f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}",
        )
        ctx.pre_fix_content: str | None = None
        try:
            # Keep original line endings. The rollback registry hashes
            # UTF-8 content and writes with newline=""; read_text() uses
            # universal-newline conversion and made a CRLF fixture fail
            # its post-rollback byte hash on Windows.
            with filepath.open("r", encoding="utf-8", newline="") as _pre_fix_file:
                ctx.pre_fix_content = _pre_fix_file.read()
        except Exception as _bk_err:
            logger.debug(f" pre-fix backup failed (will skip verify): {_bk_err}", exc_info=True)

        # [OPT-24] XSS pattern fix — deterministic, no LLM.
        # TẠI SAO: XSS bugs (CWE-79) like Markup(user_input) have a single
        # canonical fix (wrap with html.escape()). LLM fix for these wastes
        # API tokens + risks regression (LLM may rewrite the whole function
        # or remove Markup() entirely). Pattern fixer applies the fix
        # surgically + idempotently (guard_skip_if_substring prevents
        # double-escape). If pattern matches → fix + return; else fall
        # through to LLM _apply_fix below. DNA #7 AutoFix safe + #9 No harm.
        if ctx.bug.bug_type == "XSSVulnerability":
            try:
                from scp.autofix.evolution import get_evolution_engine
                _evo = get_evolution_engine(data_dir=str(self.data_dir))
                _xss_result = _evo._apply_xss_pattern_fix(ctx.bug)
                if _xss_result and _xss_result.get("fixed"):
                    # Write patched source to file
                    try:
                        filepath.write_text(
                            _xss_result["patch"], encoding="utf-8"
                        )
                    except Exception as _write_err:
                        logger.warning(
                            f"[OPT-24] XSS pattern fix write failed: {_write_err}", exc_info=True
                        )
                        # Fall through to LLM fix
                    else:
                        # Verify the fix didn't break syntax (re-check after write)
                        try:
                            import ast as _ast_verify
                            _ast_verify.parse(
                                filepath.read_text(encoding="utf-8"),
                                filename=str(filepath),
                            )
                        except SyntaxError as _syn_err:
                            logger.warning(
                                f"[OPT-24] XSS pattern fix introduced "
                                f"SyntaxError post-write — ROLLING BACK: {_syn_err}"
                            )
                            # Rollback
                            if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                                ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"XSS_SYNTAX_ERROR: {_syn_err}")
                                # Re-open transaction for fall-through LLM fix
                                ctx.shadow_tx_id = ctx.shadow_mgr.begin(
                                    target_files=[filepath],
                                    bug_id=f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}",
                                )
                            elif ctx.pre_fix_content is not None:
                                filepath.write_text(
                                    ctx.pre_fix_content, encoding="utf-8", newline=""
                                )
                            # Fall through to LLM fix
                        else:
                            # Success — pattern fix applied + verified
                            self._fixes_this_cycle += 1
                            # [SCP-DNA-FIX R13-3] Invalidate LLM fix cache
                            # for this file (R12-2 fixed internal logic,
                            # R13-3 wired the caller). Stale LLM fix
                            # suggestions for this file are no longer
                            # served — next autofix will re-query LLM
                            # with fresh source context.
                            _xss_cache_invalidated = False
                            _xss_cache_error = ""
                            try:
                                from scp.autofix.llm_fix_cache import invalidate_cache_for_file
                                invalidate_cache_for_file(str(filepath))
                                _xss_cache_invalidated = True
                            except Exception as _inv_err:
                                _xss_cache_error = str(_inv_err)[:200]
                                logger.warning(
                                    f" cache invalidate failed after deterministic fix: {_inv_err}", exc_info=True
                                )
                            # Record for cooldown
                            bug_key = f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}"
                            self._recent_fixes[bug_key] = time.time()
                            # [SCP-DNA-FIX 4-b-012] Compute before_hash +
                            # after_hash + rollback_token + reality_test_result
                            # for this Tier 1/2/4 XSS pattern fix (DNA #8).
                            # Pre-fix: _write_audit logged only a message.
                            # Post-fix: AuditLogEntry Pydantic schema
                            # enforces all 4 fields for every tier.
                            _xss_rollback_registered = False
                            try:
                                from scp.autofix.audit_log import compute_hashes as _compute_hashes_4b012
                                _xss_post = filepath.read_text(encoding="utf-8")
                                _xss_bh, _xss_ah = _compute_hashes_4b012(
                                    ctx.pre_fix_content, _xss_post,
                                )
                                _xss_rtr = "pass"  # ast.parse already verified above
                                # Register an exact per-fix rollback token. The old
                                # fast-path only emitted backup:<path>, which was an
                                # audit sentinel and not present in the rollback registry.
                                _xss_token = self.register_fix_for_rollback(
                                    file_path=str(filepath),
                                    before_content=ctx.pre_fix_content or "",
                                    after_content=_xss_post,
                                    patch=_xss_result.get("patch", ""),
                                    bug_id=f"{ctx.bug.file}:{ctx.bug.line}",
                                    bug_type=ctx.bug.bug_type,
                                    tier=int(ctx.bug.tier),
                                    reality_test_result={
                                        "status": "pass",
                                        "method": "ast.parse",
                                        "fix_method": "xss_pattern",
                                    },
                                )
                                _xss_rollback_registered = True
                            except Exception as _xss_hash_err:
                                logger.warning(
                                    f"[4-b-012] XSS hash/rollback registration failed: {_xss_hash_err}", exc_info=True
                                )
                                _xss_bh = _xss_ah = "n/a"
                                _xss_rtr = "skipped"
                                _xss_token = f"backup:{filepath}"
                                _xss_rollback_registered = False
                            # Log to audit trail
                            if ctx.report or ctx.attack_mode:
                                self._write_audit(
                                    ctx.bug, "fixed", attack_mode=ctx.attack_mode,
                                    before_hash=_xss_bh, after_hash=_xss_ah,
                                    rollback_token=_xss_token,
                                    reality_test_result=_xss_rtr,
                                )
                            else:
                                self._write_audit(
                                    ctx.bug, "fixed_silent", attack_mode=False,
                                    before_hash=_xss_bh, after_hash=_xss_ah,
                                    rollback_token=_xss_token,
                                    reality_test_result=_xss_rtr,
                                )
                            logger.info(
                                f"[OPT-24] XSS pattern fix applied for "
                                f"{ctx.bug.file}:{ctx.bug.line} "
                                f"pattern={_xss_result.get('pattern', '?')} "
                                f"matches={_xss_result.get('matches', 0)} "
                                f"(skipped LLM call — deterministic fix)"
                            )
                            # [V5.7-WHY] Reflect on pattern fix too (best-effort)
                            try:
                                if os.environ.get("SCP_EVOLUTION_ENABLED", "0") == "1":
                                    _evo.reflect(ctx.bug, _xss_result["reason"])
                            except Exception as _reflect_err:
                                logger.debug(
                                    f"[V5.7-WHY] reflect on XSS pattern fix "
                                    f"failed (non-fatal): {_reflect_err}", exc_info=True
                                )
                            if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                                ctx.shadow_mgr.commit(ctx.shadow_tx_id)
                            return {
                                "action": "fixed",
                                "status": "fixed",
                                "tier": int(ctx.bug.tier),
                                "patched": True,
                                "ctx.attack_mode": ctx.attack_mode,
                                "method": "xss_pattern",
                                "pattern": _xss_result.get("pattern", ""),
                                "reason": _xss_result.get("reason", ""),
                                "before_hash": _xss_bh,
                                "after_hash": _xss_ah,
                                "rollback_token": _xss_token,
                                "rollback_registered": _xss_rollback_registered,
                                "reality_test_result": _xss_rtr,
                                "cache_invalidated": _xss_cache_invalidated,
                                "cache_invalidation_error": _xss_cache_error,
                            }
            except Exception as _xss_pattern_err:
                logger.debug(
                    f"[OPT-24] XSS pattern fix dispatch failed (non-fatal, "
                    f"fall through to LLM): {_xss_pattern_err}", exc_info=True
                )

        # Apply fix
        # [FIX-2] TẠI SAO: was incremented unconditionally → queued-for-review
        # fixes (patched=False) consumed rate limit slots → 10 "fixed" were
        # actually 10 queued + 0 real fixes. Only count REAL patches.

        # [OPT-26/27/28] Validate patch + diagnose + record to monitor
        # BEFORE calling _apply_fix. WHY: DNA SCP #7 AutoFix safe — validate
        # before write, not after. If validation fails, we never touch the
        # file (no rollback needed). DNA SCP #6 Evidence — record diagnosis
        # so future fixes can learn. DNA SCP #8 KB accumulation — monitor
        # tracks success rate by provider/bug_type/diagnosis.
        #
        # Only validate when suggested_fix contains an explicit search-replace
        # block (SEARCH/REPLACE or legacy OLD/NEW). If it's a fenced code
        # block or pending-review queue, _apply_fix will handle it via
        # Strategy 2/3 — validation isn't applicable.
        ctx._autofix_bug_id = f"{ctx.bug.file}:{ctx.bug.line}"
        ctx._autofix_provider = "predefined"  # default for non-LLM patches
        try:
            # If LLM generated this patch, attribute to preferred provider.
            # We can't easily tell from here, but select_provider_for_bug
            # gives us the smart-routing choice that would have been used.
            from scp.autofix.llm_fix import select_provider_for_bug as _spfb
            ctx._autofix_provider = _spfb(ctx.bug.bug_type)
        except Exception as e:
            logger.warning(f"Silent except: {e}", exc_info=True)

        _autofix_validation_skipped = False  # noqa: F841 — sentinel for future wiring (tracks validation skip status)
        try:
            import re as _autofix_re
            # Try SEARCH/REPLACE first, then legacy OLD/NEW
            _sr_pat = _autofix_re.compile(
                r"<<<<<<<\s*SEARCH\s*\n(.*?)\n={5,7}\s*\n(.*?)\n>>>>>>>\s*(?:REPLACE)?\s*",
                _autofix_re.DOTALL,
            )
            _old_pat = _autofix_re.compile(
                r"<<<<<<<\s*OLD\s*\n(.*?)\n={5,7}\s*\n(.*?)\n>>>>>>>\s*(?:NEW)?\s*",
                _autofix_re.DOTALL,
            )
            ctx.pairs: list[tuple[str, str]] = []
            if ctx.bug.suggested_fix:
                for _m in _sr_pat.finditer(ctx.bug.suggested_fix):
                    ctx.pairs.append((_m.group(1), _m.group(2)))
                if not ctx.pairs:
                    for _m in _old_pat.finditer(ctx.bug.suggested_fix):
                        ctx.pairs.append((_m.group(1), _m.group(2)))

            if ctx.pairs:
                from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
                from scp.autofix.monitor import FixAttempt as _FixAttempt
                from scp.autofix.monitor import get_monitor as _get_monitor
                from scp.autofix.validate_patch import validate_patch as _validate_patch

                _validation_failed = False
                _validation_reason = ""
                for _search, _replace in ctx.pairs:
                    _vresult = _validate_patch(str(filepath), _search, _replace)
                    if not _vresult.valid:
                        _validation_failed = True
                        _validation_reason = _vresult.reason
                        break

                if _validation_failed:
                    logger.warning(
                        f"[AutoFix] [OPT-26] Patch validation FAILED for "
                        f"{ctx.bug.file}:{ctx.bug.line}: {_validation_reason}"
                    )
                    ctx._diag = _diagnose(
                        bug_id=ctx._autofix_bug_id,
                        bug_type=ctx.bug.bug_type,
                        llm_output=ctx.bug.suggested_fix,
                        patch_parsed={"search": ctx.pairs[0][0], "replace": ctx.pairs[0][1]},
                        validation_result={"valid": False, "reason": _validation_reason},
                        apply_result="failed",
                    )
                    _get_monitor().record(_FixAttempt(
                        bug_id=ctx._autofix_bug_id,
                        bug_type=ctx.bug.bug_type,
                        provider=ctx._autofix_provider,
                        diagnosis=ctx._diag.diagnosis,
                        success=False,
                    ))
                    return {
                        "action": "skipped",
                        "tier": int(ctx.bug.tier),
                        "reason": f"validation failed: {_validation_reason}",
                        "patched": False,
                    }
            else:
                # No search-replace markers → _apply_fix will try fenced-code
                # or queue for review. Skip validation (not applicable).
                _autofix_validation_skipped = True  # noqa: F841 — sentinel
        except Exception as _val_err:
            # Fail-open: validation infrastructure crashed → don't block fix.
            logger.debug(f"[AutoFix] [OPT-26] validation harness error (non-blocking): {_val_err}", exc_info=True)
            _autofix_validation_skipped = True  # noqa: F841 — sentinel

        # [R9 v4 WIRE — IMP-14 + IMP-23 shared simulation]
        # Simulate patched_source by applying the same SEARCH/REPLACE pairs
        # that agent._apply_fix() will apply. Both IMP-14 (confidence ranker)
        # and IMP-23 (shadow canary) need to KNOW the post-patch source
        # BEFORE the real file is touched. Fail-open: simulation crash →
        # both v4 hooks skipped (proceed with old behavior).
        #
        # ctx.pairs is built inside the try/except above. If validation try
        # failed before that point, ctx.pairs is undefined — defensive getattr.
        # [EVIDENCE-FLOW-FIX] `locals().get("ctx.pairs", [])` was ALWAYS []
        # (locals() keys never contain dots) — the shadow-canary + confidence-
        # ranker simulation never ran and result dicts reported n/a/skipped.
        _v4_pairs = getattr(ctx, "pairs", []) or []
        ctx.sim_patched: str | None = None
        if ctx.pre_fix_content is not None and _v4_pairs:
            try:
                from scp.autofix.validate_patch import flexible_replace
                _v4_sim = ctx.pre_fix_content
                _v4_applied_any = False
                for _v4_s, _v4_r in _v4_pairs:
                    _res = flexible_replace(_v4_sim, _v4_s, _v4_r)
                    if _res is not None:
                        _v4_sim = _res
                        _v4_applied_any = True
                if _v4_applied_any and _v4_sim != ctx.pre_fix_content:
                    ctx.sim_patched = _v4_sim
            except Exception as _v4_sim_err:
                logger.debug(
                    f"[R9 v4 WIRE] patched_source simulation failed "
                    f"(fail-open — IMP-14 + IMP-23 skip): {_v4_sim_err}", exc_info=True
                )

        # [R9 v4 WIRE — IMP-14] Confidence Ranker (fail-open).
        # TẠI SAO: existing flow has exactly 1 candidate fix per ctx.bug.
        # IMP-14 scores it (ctx.bug-FP-rate × source-quality × blast-radius ×
        # ast-parse × reality-test × relaxation-cap) → confidence ∈ [0,1]
        # → disposition "auto_apply" | "review" | "discard". If disposition
        # == "discard" → SKIP the fix (low confidence + not a relaxation).
        # HIGHEST ACCURACY IMPACT — filters out low-quality LLM patches.
        # Fail-open per DNA #7: ranker crash → proceed with old behavior
        # (apply without scoring) + log. NOT fail-closed (unlike policy_gate).
        try:
            from scp.autofix.confidence_ranker import (
                best_fix as _v4_rank_best,
            )
            from scp.autofix.confidence_ranker import (
                make_fix as _v4_make_fix,
            )
            if ctx.sim_patched is not None:
                # Estimate lines_changed from replace block line counts.
                _v4_lines_changed = sum(
                    max(0, len(_r.splitlines()) - len(_s.splitlines()) + 1)
                    for _s, _r in _v4_pairs
                ) or sum(len(_r.splitlines()) for _, _r in _v4_pairs)
                _v4_candidate = _v4_make_fix(
                    fix_id=ctx._autofix_bug_id,
                    patch=ctx.bug.suggested_fix or "",
                    patched_source=ctx.sim_patched,
                    source="llm",  # SCP autofix patches are LLM-generated
                    bug_type=ctx.bug.bug_type,
                    bug_file=ctx.bug.file,
                    bug_line=int(ctx.bug.line or 0),
                    lines_changed=_v4_lines_changed,
                    reality_test_result=None,
                )
                _v4_ranked = _v4_rank_best([_v4_candidate], bug_type=ctx.bug.bug_type)
                if _v4_ranked is None or _v4_ranked.disposition == "discard":
                    logger.info(
                        f"[R9 v4 IMP-14] confidence ranker DISCARDED "
                        f"fix for {ctx.bug.file}:{ctx.bug.line} "
                        f"(confidence={_v4_candidate.confidence:.3f} "
                        f"disposition={_v4_candidate.disposition})"
                    )
                    # [OPT-27/28] Record discard — patch was ranked too low.
                    try:
                        from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
                        from scp.autofix.monitor import FixAttempt as _FixAttempt
                        from scp.autofix.monitor import get_monitor as _get_monitor
                        ctx._diag = _diagnose(
                            bug_id=ctx._autofix_bug_id,
                            bug_type=ctx.bug.bug_type,
                            llm_output=ctx.bug.suggested_fix,
                            patch_parsed={"search": "(ranked)", "replace": "(ranked)"},
                            validation_result={"valid": True, "reason": "pre-rank OK"},
                            apply_result="discarded_by_ranker",
                        )
                        _get_monitor().record(_FixAttempt(
                            bug_id=ctx._autofix_bug_id,
                            bug_type=ctx.bug.bug_type,
                            provider=ctx._autofix_provider,
                            diagnosis=ctx._diag.diagnosis,
                            success=False,
                        ))
                    except Exception as e:
                        logger.debug(f"Silent except: {e}", exc_info=True)
                    return {
                        "action": "skipped",
                        "tier": int(ctx.bug.tier),
                        "reason": (
                            f"confidence_ranker DISCARD "
                            f"(confidence={_v4_candidate.confidence:.3f})"
                        ),
                        "patched": False,
                        "confidence": _v4_candidate.confidence,
                        "disposition": "discard",
                    }
                logger.info(
                    f"[R9 v4 IMP-14] fix ranked: "
                    f"confidence={_v4_ranked.confidence:.3f} "
                    f"disposition={_v4_ranked.disposition} "
                    f"for {ctx.bug.file}:{ctx.bug.line}"
                )
        except ImportError as _v4_cr_imp:
            logger.debug(
                f"[R9 v4 IMP-14] confidence_ranker unavailable "
                f"(fail-open — apply without scoring): {_v4_cr_imp}"
            )
        except Exception as _v4_cr_err:
            logger.debug(
                f"[R9 v4 IMP-14] confidence_ranker crash "
                f"(fail-open — apply without scoring): {_v4_cr_err}", exc_info=True
            )

    def _auto_fix_part2(self, ctx) -> dict | None:
        # [R10 v4 WIRE — IMP-16 + IMP-20 PAIRED] Blast-Radius + Type-Flow Verify.
        # TẠI SAO: IMP-14 (confidence_ranker) scores a fix but DOES NOT walk
        # the caller graph. A fix that changes `def get_user(uid) ->
        # Optional[User]` → `-> User` (drop None) breaks 5 callers with
        # `if user is None: return 404` branches (dead branch logic regression).
        # IMP-16 computes blast_radius (caller count + risk tier), then
        # IMP-20 walks each caller to check type-flow compatibility.
        # If callers have breaking type-flow → escalate to review (Tier 3).
        # Fail-open per DNA #7: if either module crashes → proceed with
        # apply (no escalation). The 6-check _verify_fix gate still runs
        # post-apply as a separate safety net.
        try:
            from scp.autofix.runner_phases.blast_radius import (
                blast_radius_summary as _v4_blast_summary,
            )
            from scp.autofix.runner_phases.blast_radius import (
                compute_blast_radius as _v4_blast,
            )
            from scp.autofix.runner_phases.blast_radius import (
                should_escalate_tier as _v4_should_escalate,
            )
            from scp.autofix.runner_phases.blast_radius import (
                should_require_dry_run as _v4_should_dry_run,
            )
            # Walk caller graph for the ctx.bug's file + function name.
            # Derive target_function from ctx.bug description (best-effort:
            # if function name not on BugReport, fall back to bare module).
            _v4_target_func = (
                getattr(ctx.bug, "function_name", "")
                or getattr(ctx.bug, "method_name", "")
                or ""
            )
            # Try to extract function name from suggested_fix SEARCH block
            # (e.g. "def foo(...)") as a backup heuristic.
            if not _v4_target_func and ctx.bug.suggested_fix:
                import re as _v4_re_mod
                _v4_def_m = _v4_re_mod.search(
                    r"def\s+(\w+)\s*\(", ctx.bug.suggested_fix,
                )
                if _v4_def_m:
                    _v4_target_func = _v4_def_m.group(1)
            if _v4_target_func:
                _v4_blast_result = _v4_blast(
                    target_file=ctx.bug.file or "",
                    target_function=_v4_target_func,
                    scp_root=None,  # default: .../scp/
                    scan_tests=False,
                )
                _v4_blast_sum = _v4_blast_summary(_v4_blast_result)
                logger.info(
                    f"[R10 v4 IMP-16] blast_radius for {_v4_target_func}: "
                    f"callers={_v4_blast_sum['caller_count']} "
                    f"risk={_v4_blast_sum['risk_level']} "
                    f"bounded={_v4_blast_sum['bounded']}"
                )

                # [SCP-DNA-FIX R13-1+R13-4] Wire should_escalate_tier — was
                # imported (R10) but never called (2-source cross-validated:
                # R13-1 ruff F401 + R13-4 DeadCodeScanner). TẠI SAO: engine
                # hand-rolled escalation only for TYPE-FLOW BREAKAGE
                # (HIGH+break→Tier 3, see inline check below). This left
                # "HIGH/CRITICAL blast radius with NO type-flow breakage"
                # with NO escalation at all → Tier 1 fix applied silently
                # to a function with 10+ callers. Now: call the helper's
                # documented policy (HIGH→Tier 2, CRITICAL→Tier 3) FIRST as
                # the GENERAL escalation. The existing inline type-flow
                # break check below is preserved as a SECONDARY escalation
                # (DNA: "không mặc định" — type-flow breakage is strictly
                # worse than blast-radius alone, escalates higher).
                try:
                    _v4_orig_tier = int(getattr(ctx.bug, "tier", 1) or 1)
                except (TypeError, ValueError) as tier_err:
                    # silent-by-design: documented default — a non-numeric tier
                    # degrades to Tier 1, escalation policy still applies below.
                    logger.debug("[AutoFix] bug.tier not numeric, defaulting to 1: %s", tier_err, exc_info=True)
                    _v4_orig_tier = 1
                _v4_escalated_tier = _v4_should_escalate(
                    _v4_blast_result, _v4_orig_tier,
                )
                if _v4_escalated_tier > _v4_orig_tier:
                    logger.warning(
                        f" blast_radius policy escalated "
                        f"{ctx.bug.file}:{ctx.bug.line} from Tier "
                        f"{_v4_orig_tier} to Tier {_v4_escalated_tier} "
                        f"(risk={_v4_blast_sum['risk_level']}, "
                        f"callers={_v4_blast_sum['caller_count']})"
                    )
                    # Surface in result downstream — mutate ctx.bug.tier so the
                    # classifier / log path sees the escalated tier.
                    if hasattr(ctx.bug, "tier"):
                        try:
                            ctx.bug.tier = _v4_escalated_tier  # type: ignore[assignment]
                        except Exception as _tier_assignment_error:  # noqa: BLE001
                            logger.debug('[AUTOFIX] tier assignment failed; retaining original tier', exc_info=True)

                # [SCP-DNA-FIX R13-4] Wire should_require_dry_run — IMP-9
                # dry-run for HIGH/CRITICAL blast radius is documented in
                # V3_MANIFEST but was NEVER called (DeadCodeScanner R13-4).
                # TẠI SAO: fixes touching HIGH-blast functions (10+ callers)
                # can break unseen call sites. Dry-run generates a snapshot
                # for operator review BEFORE the real file write. We do NOT
                # hard-block here (fail-open per DNA #7) — but we DO log a
                # loud warning + generate a dry-run preview snapshot if the
                # engine has preview_fix_dry_run injected (IMP-9). The
                # snapshot_path is surfaced in the result so the operator
                # can review/apply manually if needed.
                if _v4_should_dry_run(_v4_blast_result):
                    _dry_run_snapshot = None
                    try:
                        _dry_run_preview_fn = getattr(
                            self, "preview_fix_dry_run", None,
                        )
                        if (_dry_run_preview_fn is not None
                                and ctx.pre_fix_content is not None
                                and ctx.bug.suggested_fix):
                            # Simulate patched content (best-effort).
                            import re as _v4_dr_re
                            _v4_dr_sim = ctx.pre_fix_content
                            for _old, _new in _v4_dr_re.findall(
                                r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>>',
                                ctx.bug.suggested_fix, _v4_dr_re.DOTALL,
                            ):
                                _v4_dr_sim = _v4_dr_sim.replace(_old, _new, 1)
                            if _v4_dr_sim != ctx.pre_fix_content:
                                _dr_out = _dry_run_preview_fn(
                                    ctx.bug.file, _v4_dr_sim,
                                )
                                _dry_run_snapshot = _dr_out.get("snapshot_path")
                    except Exception as _dr_err:  # noqa: BLE001
                        logger.debug(
                            f" dry-run preview failed (fail-open): {_dr_err}"
                        )
                    logger.warning(
                        f" HIGH/CRITICAL blast radius for "
                        f"{_v4_target_func} (risk={_v4_blast_sum['risk_level']}, "
                        f"callers={_v4_blast_sum['caller_count']}) — "
                        f"dry-run{' snapshot='+str(_dry_run_snapshot) if _dry_run_snapshot else ' unavailable (fail-open)'}"
                    )

                # Now run IMP-20 type-flow check against the caller list.
                # [SCP-DNA-FIX R12-13] REAL signature extraction — không còn empty.
                # Tại sao: R10 truyền empty signatures (args=[], returns="") →
                # verify_type_flow return compatible=True (silent no-op). R12-13
                # extract REAL signatures từ orig_source + patched_source bằng
                # ast.parse + ast.walk(FunctionDef). DNA #22 (PASS ≠ TRUE).
                try:
                    from scp.autofix.type_flow_verifier import (
                        Signature as _V4_TF_Sig,
                    )
                    from scp.autofix.type_flow_verifier import (
                        verify_type_flow as _v4_tflow,
                    )
                    if _v4_blast_sum["caller_count"] > 0:
                        # R12-13: Extract real signatures from orig + patched source
                        import ast as _ast_tf
                        def _extract_sig(source_text: str, func_name: str) -> _V4_TF_Sig:
                            """Extract function signature from source via AST."""
                            try:
                                tree = _ast_tf.parse(source_text)
                                for node in _ast_tf.walk(tree):
                                    if isinstance(node, (_ast_tf.FunctionDef, _ast_tf.AsyncFunctionDef)) and node.name == func_name:
                                        args = [a.arg for a in node.args.args if hasattr(a, 'arg')]
                                        returns = ""
                                        if node.returns:
                                            try:
                                                returns = _ast_tf.unparse(node.returns)
                                            except Exception as unp_err:
                                                # silent-by-design: unparse probe —
                                                # 'Any' is the documented fallback
                                                # signature for type-flow comparison.
                                                logger.debug("[AUTOFIX] return-annotation unparse failed, using 'Any': %s", unp_err, exc_info=True)
                                                returns = "Any"
                                        return _V4_TF_Sig(args=args, returns=returns)
                            except Exception as _signature_scan_error:
                                logger.debug('[AUTOFIX] signature scan failed; using empty signature', exc_info=True)
                            return _V4_TF_Sig(args=[], returns="")

                        _v4_orig_sig = _extract_sig(ctx.pre_fix_content or "", _v4_target_func)
                        # Read patched source if available
                        _v4_patched_src = ""
                        try:
                            # [hygiene F821-fix] `filepath` không tồn tại trong scope
                            # (NameError → rơi vào except → luôn dùng source rỗng);
                            # đích đúng là file của bug đang verify (same referent
                            # dùng ở _v4_tflow(target_file=ctx.bug.file...) bên dưới).
                            _v4_patched_src = Path(ctx.bug.file).read_text(encoding="utf-8")
                        except Exception as _patched_source_error:
                            logger.debug('[AUTOFIX] patched source read failed; using empty source', exc_info=True)
                        _v4_new_sig = _extract_sig(_v4_patched_src, _v4_target_func)

                        _v4_tflow_result = _v4_tflow(
                            target_file=ctx.bug.file or "",
                            target_function=_v4_target_func,
                            orig_signature=_v4_orig_sig,
                            new_signature=_v4_new_sig,
                            scp_root=str(
                                Path(__file__).resolve().parent.parent
                            ),
                        )
                        logger.info(
                            f" type_flow for "
                            f"{_v4_target_func}: compatible="
                            f"{_v4_tflow_result.compatible} "
                            f"callers={_v4_tflow_result.caller_count} "
                            f"orig_args={_v4_orig_sig.args} "
                            f"new_args={_v4_new_sig.args} "
                            f"reason={_v4_tflow_result.reason[:80]}"
                        )
                        # If type-flow check returns incompatible AND
                        # risk_level is HIGH/CRITICAL → escalate to Tier 3.
                        if (
                            not _v4_tflow_result.compatible
                            and _v4_blast_sum["risk_level"] in ("HIGH", "CRITICAL")
                        ):
                            logger.warning(
                                f" TYPE-FLOW BREAKAGE + "
                                f"HIGH risk — escalating {ctx.bug.file}:"
                                f"{ctx.bug.line} to review (Tier 3)"
                            )
                            return {
                                "action": "skipped",
                                "tier": 3,
                                "reason": (
                                    f"type_flow_verifier: "
                                    f"{len(_v4_tflow_result.incompatible_sites)} "
                                    f"breaking caller(s) + risk="
                                    f"{_v4_blast_sum['risk_level']}"
                                ),
                                "patched": False,
                                "blast_radius": _v4_blast_sum,
                                "type_flow_breaking": len(
                                    _v4_tflow_result.incompatible_sites
                                ),
                            }
                except ImportError as _v4_tf_imp:
                    logger.debug(
                        f"[R10 v4 IMP-20] type_flow_verifier unavailable "
                        f"(fail-open): {_v4_tf_imp}"
                    )
                except Exception as _v4_tf_err:
                    logger.debug(
                        f"[R10 v4 IMP-20] type_flow_verifier crash "
                        f"(fail-open): {_v4_tf_err}", exc_info=True
                    )
        except ImportError as _v4_br_imp:
            logger.debug(
                f"[R10 v4 IMP-16] blast_radius unavailable (fail-open): {_v4_br_imp}"
            )
        except Exception as _v4_br_err:
            logger.debug(
                f"[R10 v4 IMP-16] blast_radius crash (fail-open): {_v4_br_err}", exc_info=True
            )

        # [R9 v4 WIRE — IMP-23] Shadow-Apply + Canary Compare (fail-open).
        # TẠI SAO: pre-apply safety gate. Apply patch to a SHADOW COPY (temp
        # file), import as module, run default canary suite (ast_parse +
        # import + smoke_call + reality + property tests) on BOTH original
        # and shadow, compare outputs. Only promote (write to real file)
        # if shadow passed. HIGHEST SAFETY IMPACT (pre-apply).
        # Fail-open per DNA #7: canary crash → apply without canary + log.
        # Canary itself is fail-open internally (empty suite → passed=True
        # + flagged_for_review). DNA #11 fail-loudly on regressions.
        # [SANDBOX-SKIP] The canary verdict is stashed on ctx: it is a local
        # of part2 and part3's realtime-skip decision must be able to prove
        # that at least one genuinely-executed verification layer ran. None
        # means "canary never ran / unavailable" (fail-closed for the caller).
        ctx.v4_shadow_result = None
        try:
            from scp.autofix.runner_phases.shadow_canary import (
                ShadowFix as _V4_ShadowFix,
            )
            from scp.autofix.runner_phases.shadow_canary import (
                default_canary_suite as _v4_default_canary,
            )
            from scp.autofix.runner_phases.shadow_canary import (
                shadow_apply_and_compare as _v4_shadow_compare,
            )
            if ctx.sim_patched is not None and ctx.pre_fix_content is not None:
                _v4_shadow_fix = _V4_ShadowFix(
                    original_source=ctx.pre_fix_content,
                    patched_source=ctx.sim_patched,
                    fix_id=ctx._autofix_bug_id,
                )
                _v4_shadow_result = _v4_shadow_compare(
                    target_file=ctx.bug.file,
                    fix=_v4_shadow_fix,
                    canary_suite=_v4_default_canary(),
                )
                ctx.v4_shadow_result = _v4_shadow_result
                if not _v4_shadow_result.passed:
                    logger.warning(
                        f"[R9 v4 IMP-23] SHADOW CANARY FAILED for "
                        f"{ctx.bug.file}:{ctx.bug.line}: "
                        f"{_v4_shadow_result.reason[:120]} "
                        f"(tests_run={_v4_shadow_result.tests_run} "
                        f"diffs={len(_v4_shadow_result.diffs)})"
                    )
                    # [OPT-27/28] Record shadow fail.
                    try:
                        from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
                        from scp.autofix.monitor import FixAttempt as _FixAttempt
                        from scp.autofix.monitor import get_monitor as _get_monitor
                        ctx._diag = _diagnose(
                            bug_id=ctx._autofix_bug_id,
                            bug_type=ctx.bug.bug_type,
                            llm_output=ctx.bug.suggested_fix,
                            patch_parsed={"search": "(shadowed)", "replace": "(shadowed)"},
                            validation_result={"valid": True, "reason": "pre-shadow OK"},
                            apply_result="shadow_canary_failed",
                        )
                        _get_monitor().record(_FixAttempt(
                            bug_id=ctx._autofix_bug_id,
                            bug_type=ctx.bug.bug_type,
                            provider=ctx._autofix_provider,
                            diagnosis=ctx._diag.diagnosis,
                            success=False,
                        ))
                    except Exception as e:
                        logger.debug(f"Silent except: {e}", exc_info=True)
                    return {
                        "action": "skipped",
                        "tier": int(ctx.bug.tier),
                        "reason": (
                            f"shadow_canary FAIL: "
                            f"{_v4_shadow_result.reason[:160]}"
                        ),
                        "patched": False,
                        "shadow_canary_passed": False,
                        "shadow_diffs": list(_v4_shadow_result.diffs[:5]),
                        "shadow_tests_run": _v4_shadow_result.tests_run,
                    }
                logger.info(
                    f"[R9 v4 IMP-23] shadow canary OK for "
                    f"{ctx.bug.file}:{ctx.bug.line} "
                    f"(tests_run={_v4_shadow_result.tests_run} "
                    f"flagged={_v4_shadow_result.flagged_for_review})"
                )
        except ImportError as _v4_sc_imp:
            logger.warning(
                "[R9 v4 IMP-23] shadow_canary unavailable; blocking unverifiable patch: %s",
                type(_v4_sc_imp).__name__,
            )
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "shadow_canary unavailable; fix is UNVERIFIED",
                "patched": False,
                "shadow_canary_unverified": True,
            }
        except Exception as _v4_sc_err:
            logger.warning(
                "[R9 v4 IMP-23] shadow_canary failed; blocking unverifiable patch: %s",
                type(_v4_sc_err).__name__,
            exc_info=True)
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "shadow_canary failed; fix is UNVERIFIED",
                "patched": False,
                "shadow_canary_unverified": True,
            }

    def _auto_fix_part3(self, ctx) -> dict | None:
        # [STEP0-FIX 2026-09-02] `filepath` was only defined in _auto_fix_part1,
        # so every generic SEARCH/REPLACE fix hit NameError here and the
        # realtime-verifier gate fail-closed with "realtime verifier failed;
        # fix is UNVERIFIED" — the generic apply path never reached _apply_fix.
        # Bind it from the bug context so the gate evaluates the patch instead
        # of crashing (discovered by T09 Golden B, discovered-by-design).
        filepath = Path(ctx.bug.file)
        # [STEP0-FIX 2026-09-02] `agent` suffered the same scoping defect: it
        # was created only in _auto_fix_part1. Bind the same minimal executor
        # part1 uses so part3 can actually apply the patch.
        from scp.core.code_evolution_agent import CodeEvolutionAgent
        agent = CodeEvolutionAgent.__new__(CodeEvolutionAgent)
        agent.log_file = self.data_dir / "evolution_log.jsonl"
        # [SCP-DNA-FIX R12-18] Real-Time Verifier — check invariants BEFORE file write.
        # TẠI SAO: post_fix_verify (R12-6) chạy SAU patch apply → nếu break invariant
        # phải rollback (waste). Real-Time Verifier chạy TRƯỚC _apply_fix → nếu
        # will break → BLOCK patch (no waste). VIGIL có Observation real-time, SCP
        # thiếu → R12-18 thêm. DNA #22 (PASS ≠ TRUE): post-hoc ≠ real-time.
        # Verifier uncertainty is fail-closed: no file write may occur.
        try:
            from scp.autofix.realtime_verifier import verify_patch_realtime
            _rtv_patched_source = filepath.read_text(encoding="utf-8") if filepath.exists() else ""
            # Simulate patch: apply suggested_fix to orig source (best-effort)
            # If we cannot simulate the patch, block it as UNVERIFIED.
            if not ctx.pre_fix_content or not ctx.bug.suggested_fix:
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": "realtime patch simulation unavailable; fix is UNVERIFIED",
                    "patched": False,
                    "realtime_blocked": True,
                }
            _rtv_simulated = ctx.pre_fix_content
            # Simulate only the canonical SEARCH/REPLACE format.  A patch
            # that cannot be simulated is blocked rather than applied.
            import re as _rtv_re
            _rtv_blocks = _rtv_re.findall(
                r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>>',
                ctx.bug.suggested_fix, _rtv_re.DOTALL
            )
            if not _rtv_blocks:
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": "realtime patch format unsupported; fix is UNVERIFIED",
                    "patched": False,
                    "realtime_blocked": True,
                }
            from scp.autofix.validate_patch import flexible_replace
            for _rtv_old, _rtv_new in _rtv_blocks:
                _res = flexible_replace(_rtv_simulated, _rtv_old, _rtv_new)
                if _res is None:
                    return {
                        "action": "skipped",
                        "tier": int(ctx.bug.tier),
                        "reason": "realtime patch search block not found; fix is UNVERIFIED",
                        "patched": False,
                        "realtime_blocked": True,
                    }
                _rtv_simulated = _res
            if _rtv_simulated != ctx.pre_fix_content:
                _rtv_result = verify_patch_realtime(
                    orig_source=ctx.pre_fix_content,
                    patched_source=_rtv_simulated,
                    func_name=getattr(ctx.bug, "function_name", None) or getattr(ctx.bug, "method_name", None),
                )
                if not _rtv_result.ok:
                    # [SANDBOX-SKIP] A sandbox-incompatible realtime check is a
                    # VISIBLE SKIP — not a pass, not a hard block — but ONLY
                    # when the shadow canary GENUINELY PASSED in this run
                    # (ctx.v4_shadow_result, recorded by part2's IMP-23
                    # section): behavioral verification then really executed
                    # in a live layer, and post_fix_verify re-verifies after
                    # apply. Without a canary pass (failed OR never ran) the
                    # patch stays blocked: never promote without at least one
                    # genuinely-executed verification layer. All non-sandbox
                    # failures keep the hard block unchanged.
                    _rtv_canary_state = getattr(ctx, "v4_shadow_result", None)
                    _rtv_canary_passed = bool(getattr(_rtv_canary_state, "passed", False))
                    if (
                        getattr(_rtv_result, "sandbox_incompatible", False)
                        and _rtv_canary_passed
                    ):
                        logger.warning(
                            f" Real-Time Verifier SKIPPED (sandbox-incompatible source) for "
                            f"{ctx.bug.file}:{ctx.bug.line}: {_rtv_result.reason} — "
                            f"verification delegated to shadow canary + post_fix_verify"
                        )
                        ctx.realtime_skipped = True
                    else:
                        logger.warning(
                            f" Real-Time Verifier BLOCKED patch for "
                            f"{ctx.bug.file}:{ctx.bug.line}: {_rtv_result.reason} — skipping file write"
                        )
                        return {
                            "action": "skipped",
                            "tier": int(ctx.bug.tier),
                            "reason": f"realtime_verifier: {_rtv_result.reason[:160]}",
                            "patched": False,
                            "realtime_blocked": True,
                            "violations": _rtv_result.violations[:3],
                        }
                else:
                    logger.info(
                        f" Real-Time Verifier OK: {_rtv_result.reason} "
                        f"(inputs={_rtv_result.inputs_tested})"
                    )
        except ImportError as _rtv_imp:
            logger.warning(
                " realtime_verifier unavailable; blocking unverifiable patch: %s",
                type(_rtv_imp).__name__,
            )
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "realtime verifier unavailable; fix is UNVERIFIED",
                "patched": False,
                "realtime_blocked": True,
            }
        except Exception as _rtv_err:
            logger.warning(
                " realtime_verifier failed; blocking unverifiable patch: %s",
                type(_rtv_err).__name__,
            exc_info=True)
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "realtime verifier failed; fix is UNVERIFIED",
                "patched": False,
                "realtime_blocked": True,
            }


        patched = agent._apply_fix(filepath, ctx.bug.suggested_fix)

        if patched:
            self._fixes_this_cycle += 1
            # [SCP-DNA-FIX R13-3] Invalidate LLM fix cache for this file
            # (R12-2 fixed internal logic, R13-3 wired the caller). Stale
            # LLM fix suggestions for this file are no longer served.
            try:
                from scp.autofix.llm_fix_cache import invalidate_cache_for_file
                invalidate_cache_for_file(str(filepath))
            except Exception as _inv_err:
                logger.debug(f" cache invalidate failed (non-fatal): {_inv_err}", exc_info=True)
        else:
            if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason="apply_fix_failed")
            # [OPT-27/28] Record LLM_OUTPUT_FORMAT_ERROR (or queued-for-review)
            # to diagnostic + monitor. WHY: even "queued for review" is a
            # failure mode worth tracking — if many bugs queue for the same
            # reason, prompt needs improving.
            try:
                from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
                from scp.autofix.monitor import FixAttempt as _FixAttempt
                from scp.autofix.monitor import get_monitor as _get_monitor
                ctx._diag = _diagnose(
                    bug_id=ctx._autofix_bug_id,
                    bug_type=ctx.bug.bug_type,
                    llm_output=ctx.bug.suggested_fix,
                    patch_parsed=None,
                    validation_result=None,
                    apply_result="failed",
                )
                _get_monitor().record(_FixAttempt(
                    bug_id=ctx._autofix_bug_id,
                    bug_type=ctx.bug.bug_type,
                    provider=ctx._autofix_provider,
                    diagnosis=ctx._diag.diagnosis,
                    success=False,
                ))
            except Exception as e:
                logger.warning(f"Silent except: {e}", exc_info=True)
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "fix queued for human review (not auto-patchable)",
                "patched": False,
            }

        #  FixVerification layer — self-verify SAU khi apply patch.
        # TẠI SAO: WHY gate (v9.0) hỏi "có nên fix không?" (action layer).
        # _verify_fix hỏi "fix có thực sự work không? có introduce new ctx.bug không?" (verify layer).
        # WHY + verify = cùng độ sâu (2 layer) như WHY (necessity + falsification).
        # Any verify error must rollback (restore pre-fix content) and return skipped.
        try:
            _verify_ok, _verify_reason = self._verify_fix(filepath, [ctx.bug])
            if not _verify_ok:
                logger.warning(
                    f" Fix verification FAILED for {ctx.bug.file}:{ctx.bug.line}: "
                    f"{_verify_reason} — ROLLING BACK"
                )
                self._audit_v91("autofix_verify_fail_rollback", {
                    "file": ctx.bug.file, "line": ctx.bug.line, "bug_type": ctx.bug.bug_type,
                    "reason": _verify_reason,
                })
                # Rollback via ShadowSnapshotManager
                if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"VERIFY_FIX_FAILED: {_verify_reason}")
                elif ctx.pre_fix_content is not None:
                    try:
                        filepath.write_text(ctx.pre_fix_content, encoding="utf-8", newline="")
                        logger.info(f" Rollback OK for {ctx.bug.file}")
                    except Exception as _rb_err:
                        logger.error(f" Rollback FAILED for {ctx.bug.file}: {_rb_err}", exc_info=True)
                # Decrement counter (fix was undone)
                self._fixes_this_cycle = max(0, self._fixes_this_cycle - 1)
                # [OPT-27/28] Record rollback — patch applied but introduced new bugs.
                try:
                    from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
                    from scp.autofix.monitor import FixAttempt as _FixAttempt
                    from scp.autofix.monitor import get_monitor as _get_monitor
                    ctx._diag = _diagnose(
                        bug_id=ctx._autofix_bug_id,
                        bug_type=ctx.bug.bug_type,
                        llm_output=ctx.bug.suggested_fix,
                        patch_parsed={"search": "(applied)", "replace": "(applied)"},
                        validation_result={"valid": True, "reason": "pre-apply OK"},
                        apply_result="rollback",
                    )
                    _get_monitor().record(_FixAttempt(
                        bug_id=ctx._autofix_bug_id,
                        bug_type=ctx.bug.bug_type,
                        provider=ctx._autofix_provider,
                        diagnosis=ctx._diag.diagnosis,
                        success=False,
                    ))
                except Exception as e:
                    logger.warning(f"Silent except: {e}", exc_info=True)
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": f"fix verification failed (rolled back): {_verify_reason}",
                    "patched": False,
                }
            self._audit_v91("autofix_verify_ok", {
                "file": ctx.bug.file, "line": ctx.bug.line, "bug_type": ctx.bug.bug_type,
                "reason": _verify_reason,
            })

            # [SCP-DNA-FIX R12-6] Wire R7-Full post-fix verification orchestrator.
            # TẠI SAO: run_full_post_fix_verify() là IMP-1 orchestrator — kích hoạt
            # toàn bộ chain IMP-1 (vulture) + IMP-2 (reality_test) + IMP-3 (completeness)
            # + IMP-7 (lineage) + IMP-12 (diff_rescan) + IMP-15 (semantic_equiv).
            # Trước R12-6: 5,170+ LOC dead (wiring-scan ctx.report). R11 claim "12/12 wired"
            # nhưng chỉ import-level, không call-level. DNA #22 (PASS ≠ TRUE): import
            # ≠ wired ≠ called. Wire tại đây — SAU _verify_fix (gate nội bộ OK),
            # TRƯỚC cooldown record (để rollback nếu orchestrator fail).
            # Post-fix uncertainty is a rollback condition; a patch is not
            # successful unless every required post-fix phase reports pass.
            try:
                from scp.autofix.runner_phases.post_fix_verify import run_full_post_fix_verify
                _pfv_result = run_full_post_fix_verify(
                    bug_id=f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}",
                    file_path=str(filepath),
                    method_name=getattr(ctx.bug, "function_name", None) or getattr(ctx.bug, "method_name", None),
                    bug_type=ctx.bug.bug_type,
                    run_vulture=True,
                    run_import=True,
                    run_hypothesis=False,  # hypothesis needs test file — skip if none
                    run_reality_exercise=True,
                    run_completeness=True,
                    # [FA-04 repair] The REAL pre-fix content feeds the B-leg
                    # of the seeded evidence replay, so the generated
                    # characterization test must genuinely fail on the buggy
                    # state (not just on an import error of an empty file).
                    buggy_source=ctx.pre_fix_content,
                )
                if _pfv_result.get("ok") is not True:
                    _pfv_reason = _pfv_result.get("reason", "post-fix verification is UNVERIFIED")
                    _pfv_rollback = True
                    if _pfv_rollback:
                        logger.warning(
                            f" post_fix_verify ROLLBACK for {ctx.bug.file}:{ctx.bug.line}: "
                            f"{_pfv_reason} — restoring pre-fix content"
                        )
                        if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                            ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"POST_FIX_VERIFY_FAILED: {_pfv_reason}")
                        elif ctx.pre_fix_content is not None:
                            try:
                                filepath.write_text(ctx.pre_fix_content, encoding="utf-8", newline="")
                                logger.info(f" Rollback OK for {ctx.bug.file}")
                            except Exception as _rb_err:
                                logger.error(f" Rollback FAILED for {ctx.bug.file}: {_rb_err}", exc_info=True)
                        self._fixes_this_cycle = max(0, self._fixes_this_cycle - 1)
                    else:
                        logger.warning(
                            f" post_fix_verify escalate_to_tier3 for "
                            f"{ctx.bug.file}:{ctx.bug.line}: {_pfv_reason}"
                        )
                    # A non-true post-fix result is never promotable. The
                    # rollback above restores the exact pre-fix bytes; return
                    # now so the caller cannot receive `action=fixed` after
                    # the patch has already been rejected.
                    return {
                        "action": "skipped",
                        "tier": int(ctx.bug.tier),
                        "reason": (
                            f"post-fix verification rejected/unverified "
                            f"(rolled back): {_pfv_reason}"
                        ),
                        "patched": False,
                        "verification_status": "UNVERIFIED",
                        "post_fix_verification": _pfv_result,
                        "escalate_to_tier3": bool(
                            _pfv_result.get("escalate_to_tier3", True)
                        ),
                    }
                else:
                    logger.info(
                        f" post_fix_verify OK for {ctx.bug.file}:{ctx.bug.line} "
                        f"(phases: {list(_pfv_result.get('phases', {}).keys())})"
                    )
            except ImportError as _pfv_imp:
                logger.warning(
                    " post_fix_verify unavailable; rolling back unverifiable patch: %s",
                    type(_pfv_imp).__name__,
                )
                if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"POST_FIX_VERIFY_IMPORT_ERROR: {_pfv_imp}")
                elif ctx.pre_fix_content is not None:
                    filepath.write_text(ctx.pre_fix_content, encoding="utf-8", newline="")
                self._fixes_this_cycle = max(0, self._fixes_this_cycle - 1)
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": "post-fix verifier unavailable; fix is UNVERIFIED and was rolled back",
                    "patched": False,
                }
            except Exception as _pfv_err:
                logger.warning(
                    " post_fix_verify failed; rolling back unverifiable patch: %s",
                    type(_pfv_err).__name__,
                exc_info=True)
                if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                    ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"POST_FIX_VERIFY_ERROR: {_pfv_err}")
                elif ctx.pre_fix_content is not None:
                    filepath.write_text(ctx.pre_fix_content, encoding="utf-8", newline="")
                self._fixes_this_cycle = max(0, self._fixes_this_cycle - 1)
                return {
                    "action": "skipped",
                    "tier": int(ctx.bug.tier),
                    "reason": "post-fix verifier failed; fix is UNVERIFIED and was rolled back",
                    "patched": False,
                }
        except Exception as _verify_call_err:
            logger.warning(
                " verifier call failed; rolling back unverifiable patch: %s",
                type(_verify_call_err).__name__,
            exc_info=True)
            if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
                ctx.shadow_mgr.rollback(ctx.shadow_tx_id, reason=f"VERIFY_CALL_ERROR: {_verify_call_err}")
            elif ctx.pre_fix_content is not None:
                filepath.write_text(ctx.pre_fix_content, encoding="utf-8", newline="")
            self._fixes_this_cycle = max(0, self._fixes_this_cycle - 1)
            return {
                "action": "skipped",
                "tier": int(ctx.bug.tier),
                "reason": "verifier call failed; fix is UNVERIFIED and was rolled back",
                "patched": False,
            }

        # Record for cooldown
        bug_key = f"{ctx.bug.file}:{ctx.bug.line}:{ctx.bug.bug_type}"
        self._recent_fixes[bug_key] = time.time()

        # [SCP-DNA-FIX 4-b-012] Compute before_hash + after_hash +
        # rollback_token + reality_test_result for this Tier 1/2/4 fix
        # (DNA #8 KB accumulation). Pre-fix: _write_audit logged only
        # timestamp/file/line/bug_type/tier/action/description — NO
        # hashes, NO rollback_token, NO reality_test_result. Tier 3
        # already had these (via _write_tier3_auto_audit); Tier 1/2/4
        # did NOT. Now: AuditLogEntry Pydantic schema enforces all 4
        # fields for EVERY tier at write time.
        #
        # _verify_ok may be unset if _verify_fix raised (fail-open path
        # at line 1923-1924); default to None → reality_test="skipped".
        _verify_ok_local = locals().get("_verify_ok")
        _verify_reason_local = locals().get("_verify_reason")
        try:
            from scp.autofix.audit_log import (
                compute_hashes as _compute_hashes_4b012,
            )
            from scp.autofix.audit_log import (
                make_rollback_token_backup as _rb_token_4b012,
            )
            _main_post = filepath.read_text(encoding="utf-8")
            ctx.before_hash, ctx.after_hash = _compute_hashes_4b012(
                ctx.pre_fix_content, _main_post,
            )
            if _verify_ok_local is True:
                ctx.reality_test_result = "pass"
            elif _verify_ok_local is False:
                ctx.reality_test_result = f"fail:{(_verify_reason_local or 'unknown')[:80]}"
            else:
                ctx.reality_test_result = "skipped"
            # Tier 4 (ctx.attack_mode) prefers git revert ref; else backup path.
            if ctx.attack_mode:
                try:
                    from scp.autofix.audit_log import (
                        make_rollback_token_git as _git_token_4b012,
                    )
                    ctx.rollback_token = _git_token_4b012(str(filepath))
                except Exception as git_token_err:
                    # silent-by-design: failover to backup-file rollback token —
                    # rollback capability is preserved via the backup path.
                    logger.warning("[4-b-012] git rollback token unavailable, falling back to backup-file token: %s", git_token_err, exc_info=True)
                    ctx.rollback_token = _rb_token_4b012(str(filepath))
            else:
                ctx.rollback_token = _rb_token_4b012(str(filepath))
        except Exception as _main_hash_err:
            logger.debug(
                f"[4-b-012] main audit hash/token compute failed "
                f"(non-fatal — entry gets 'n/a'): {_main_hash_err}", exc_info=True
            )
            ctx.before_hash = ctx.after_hash = "n/a"
            ctx.reality_test_result = "skipped"
            ctx.rollback_token = "n/a"

        # Log to audit trail (Tier 2+ always; Tier 1 only if report=True)
        if ctx.report or ctx.attack_mode:
            self._write_audit(
                ctx.bug, "fixed", attack_mode=ctx.attack_mode,
                before_hash=ctx.before_hash, after_hash=ctx.after_hash,
                rollback_token=ctx.rollback_token,
                reality_test_result=ctx.reality_test_result,
            )
        else:
            # Tier 1: minimal log (for forensics, not reported to human)
            self._write_audit(
                ctx.bug, "fixed_silent", attack_mode=False,
                before_hash=ctx.before_hash, after_hash=ctx.after_hash,
                rollback_token=ctx.rollback_token,
                reality_test_result=ctx.reality_test_result,
            )

        # [V5.7-WHY] Change 1: WHY → Evolution Engine reflect feedback.
        # TẠI SAO: closes the loop "fix → reflect → KB update → next fix smarter".
        # Without this, each fix is a one-shot — SCP never learns WHY ctx.bug occurred.
        # Now: after a successful fix, ask EvolutionEngine.reflect(ctx.bug, fix_diff)
        # to extract root cause + lesson → write to evolution_reflect.jsonl →
        # next time same pattern detected, classifier/scanner can use the lesson.
        # SAFETY: opt-in via SCP_EVOLUTION_ENABLED=1 (default OFF). Wrap in
        # try/except — reflect failure MUST NOT break fix (fix already applied).
        # Reflect is best-effort: if LLM call fails, KB stays as-is, no harm.
        try:
            if os.environ.get("SCP_EVOLUTION_ENABLED", "0") == "1":
                from scp.autofix.evolution import get_evolution_engine
                _evo = get_evolution_engine(data_dir=str(self.data_dir))
                # fix_diff: pass the suggested_fix that was applied (best proxy
                # we have without diffing the file post-patch).
                _fix_diff = str(ctx.bug.suggested_fix) if ctx.bug.suggested_fix else ""
                _reflect_result = _evo.reflect(ctx.bug, _fix_diff)
                logger.info(
                    f"[V5.7-WHY] reflect: {ctx.bug.file}:{ctx.bug.line} "
                    f"self_falsified={getattr(_reflect_result, 'self_falsified', '?')} "
                    f"lesson={getattr(_reflect_result, 'lesson_learned', '')[:80]!r}"
                )
        except Exception as _reflect_err:
            # Reflect failure is non-fatal — fix already applied successfully.
            logger.debug(f"[V5.7-WHY] reflect failed (non-fatal): {_reflect_err}", exc_info=True)

        # [OPT-27/28] Record success — patch applied + verified.
        try:
            from scp.autofix.diagnostic import diagnose_fix_failure as _diagnose
            from scp.autofix.monitor import FixAttempt as _FixAttempt
            from scp.autofix.monitor import get_monitor as _get_monitor
            ctx._diag = _diagnose(
                bug_id=ctx._autofix_bug_id,
                bug_type=ctx.bug.bug_type,
                llm_output=ctx.bug.suggested_fix,
                patch_parsed={"search": "(applied)", "replace": "(applied)"},
                validation_result={"valid": True, "reason": "pre-apply OK"},
                apply_result="success",
            )
            _get_monitor().record(_FixAttempt(
                bug_id=ctx._autofix_bug_id,
                bug_type=ctx.bug.bug_type,
                provider=ctx._autofix_provider,
                diagnosis=ctx._diag.diagnosis,
                success=True,
            ))
        except Exception as e:
            logger.warning(f"Silent except: {e}", exc_info=True)

        # [R10 v3 WIRE — IMP-17] Regression Watcher (background daemon).
        # TẠI SAO: existing flow verifies the fix AT apply time (6-check
        # _verify_fix + IMP-19 property + IMP-23 shadow + IMP-14 rank).
        # But regressions can surface LATER (e.g. when a downstream caller
        # invokes the patched function with an input the post-apply suite
        # didn't exercise). IMP-17 spawns a daemon thread that re-runs
        # reality_test on patched files every 15s for 60s (TTL).
        # If reality_test fails post-T0 → auto-rollback via IMP-6 token.
        # Env SCP_REGRESSION_WATCHER_DISABLED=1 → noop (fail-open).
        # Fail-open per DNA #7: if watcher crashes → fix stays applied
        # (better to have a patched file than block all auto-fixes).
        try:
            from scp.autofix.runner_phases.auto_rollback import (
                get_regression_watcher as _v4_get_watcher,
            )
            # Generate a rollback token via the existing IMP-6 registry
            # (injected method on AutoFixEngine via engine_extensions).
            _v4_watch_token = ""
            if ctx.pre_fix_content is not None:
                try:
                    _v4_post_content = filepath.read_text(encoding="utf-8")
                    _v4_watch_token = self.register_fix_for_rollback(
                        file_path=str(filepath),
                        before_content=ctx.pre_fix_content,
                        after_content=_v4_post_content,
                        patch=ctx.bug.suggested_fix or "",
                        bug_id=ctx._autofix_bug_id,
                        bug_type=ctx.bug.bug_type,
                        tier=int(ctx.bug.tier),
                        reality_test_result=None,
                    )
                except Exception as _v4_rb_reg_err:
                    logger.debug(
                        f"[R10 v3 IMP-17] register_fix_for_rollback failed "
                        f"(non-fatal — watcher will log-only): {_v4_rb_reg_err}", exc_info=True
                    )
            # Register with the regression watcher. This also lazily
            # starts the daemon thread on first call (per IMP-17 design).
            if _v4_watch_token:
                _v4_watcher = _v4_get_watcher()
                _v4_watcher.register(
                    fix_id=ctx._autofix_bug_id,
                    file_path=str(filepath),
                    rollback_token=_v4_watch_token,
                    ttl=60,  # 60s watch window
                    extra={
                        "bug_type": ctx.bug.bug_type,
                        "tier": int(ctx.bug.tier),
                        "ctx.attack_mode": ctx.attack_mode,
                    },
                )
                logger.info(
                    f"[R10 v3 IMP-17] registered fix {ctx._autofix_bug_id} "
                    f"for regression watch (ttl=60s, token={_v4_watch_token[:8]}...)"
                )
        except ImportError as _v4_ar_imp:
            logger.debug(
                f"[R10 v3 IMP-17] auto_rollback unavailable (fail-open): {_v4_ar_imp}"
            )
        except Exception as _v4_ar_err:
            logger.debug(
                f"[R10 v3 IMP-17] auto_rollback wire crash (fail-open): {_v4_ar_err}", exc_info=True
            )

        # [SCP-DNA-FIX] Surface the evidence already computed above.
        # Before this return, Tier 1/2 deterministic fixes were reported as
        # `fixed` but callers received no hashes, rollback token or reality
        # result. That made an external orchestrator unable to distinguish
        # a real reversible fix from an incomplete claim (DNA #22).
        # Prefer the exact registry token created for the regression watcher;
        # fall back to the audit backup token only when registration failed.
        # [EVIDENCE-FLOW-FIX] `locals().get("ctx.<attr>", ...)` never matched
        # (locals() keys never contain dots) — before_hash / after_hash /
        # rollback_token / reality_test_result were reported as n/a/skipped
        # even when ctx carried the real values. Read them off ctx.
        _result_rollback_token = locals().get("_v4_watch_token") or getattr(ctx, "rollback_token", "n/a")
        _result_rollback_registered = bool(locals().get("_v4_watch_token"))
        if getattr(ctx, "shadow_tx_id", None) and getattr(ctx, "shadow_mgr", None):
            ctx.shadow_mgr.commit(ctx.shadow_tx_id)
        return {
            "action": "fixed",
            "tier": int(ctx.bug.tier),
            "patched": patched,
            "ctx.attack_mode": ctx.attack_mode,
            "before_hash": getattr(ctx, "before_hash", "n/a"),
            "after_hash": getattr(ctx, "after_hash", "n/a"),
            "rollback_token": _result_rollback_token,
            "rollback_registered": _result_rollback_registered,
            "reality_test_result": getattr(ctx, "reality_test_result", "skipped"),
            "post_fix_verification": locals().get("_pfv_result", {}),
        }
