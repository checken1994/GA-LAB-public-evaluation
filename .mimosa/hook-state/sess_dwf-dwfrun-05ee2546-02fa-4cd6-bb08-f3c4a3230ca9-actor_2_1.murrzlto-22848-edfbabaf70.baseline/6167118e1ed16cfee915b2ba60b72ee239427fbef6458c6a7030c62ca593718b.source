# SCP CIRCUIT: M07 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M07-closure.json)
from __future__ import annotations

"""
SCP Auto-Fix Engine — autonomous bug fixing with tiered autonomy.

Flow:
  1. Deep audit detects bug → BugReport
  2. Classifier assigns tier
  3. Engine acts based on tier:
     - Tier 1: fix immediately, no report
     - Tier 2: fix immediately, log to audit trail
     - Tier 3: request permission, WAIT (do not fix until approved)
     - Tier 4: fix immediately (attack mode, restraints only), log + flag for post-hoc review

The engine uses code_evolution_agent._apply_fix() for the actual patching
(search-replace markers + ast.parse verification), but ONLY for approved tiers.

[SAFETY] The engine NEVER:
  - Auto-applies a relaxation (loosens security) — always Tier 3
  - Auto-applies a verdict threshold change — always Tier 3
  - Skips the permission gate for logic bugs
  - Fixes more than MAX_FIXES_PER_CYCLE per audit cycle (rate limit)
"""


import json
import logging
import os
import threading
import time
from pathlib import Path

from scp.autofix.classifier import BugClassifier, BugReport, BugTier
from scp.autofix.permission import PermissionGate

logger = logging.getLogger("scp.autofix")

# Rate limits (prevent runaway auto-fixing)
# [FIX-5] TẠI SAO: was 10 — STARTUP-GATE scans up to 50 bugs, so 10/cycle
# guaranteed 40 "skipped (rate limit)" → server start blocked. 200 gives
# headroom for full scan + scheduled audits. Tier 3 (permission) still
# gates logic bugs; cooldown still prevents re-fix same bug.
# Single source of truth lives in engine_parts/autofix_mixin.py (the only
# code user of this limit); re-exported here for back-compat imports.

MAX_TIER4_PER_HOUR = 20           # Max attack-mode fixes per hour
COOLDOWN_SAME_BUG_SECONDS = 3600  # Don't re-fix same bug within 1 hour
CYCLE_RESET_SECONDS = 3600        # Reset _fixes_this_cycle every 1 hour

# [TIER3-AUTO] Safety guards for SCP_AUTO_APPROVE_TIER3=1 mode
# TAI SAO: Ga muon SCP tu fix Tier 3 (logic bugs) de kiem tra. Vi pham
# nguyen tac #4 "con nguoi quyet dinh" -- nhung Ga approve. Z.ai dung
# safety guards CUNG de giam rui ro:
#   1. RELAXATION patterns KHONG bao gio auto (hard limit in classifier)
#   2. Rate limit 5/gio (chat hon MAX_FIXES_PER_CYCLE=200)
#   3. Auto-timeout 1h (env var tu het hieu luc)
#   4. Audit log rieng: data/tier3_auto_audit.jsonl
#
# [RUNTIME-FIX-6] Runtime log cho thay BareExceptPass auto-fix rollback rate
# = 63% (24 rollback / 38 attempt trong 2 phut). Auto-fix dang ton CPU + tao
# KB noise ma khong fix duoc gi. Khuyen nghi: TAM TAT auto-approve cho
# BareExceptPass cho den khi LLM-fix quality tot hon. Default = "0" (OFF).
# De bat lai khi can: set env SCP_AUTO_APPROVE_TIER3=1 (se tu het hieu luc
# sau 1h theo Guard 2).
#   5. Backup file truoc khi apply (.tier3bak)
#   6. Cooldown 1h cho cung bug (dung _recent_fixes chung)
MAX_TIER3_AUTO_PER_HOUR = 5            # Hard cap: 5 logic-bug auto-fixes/hour
TIER3_AUTO_TIMEOUT_SECONDS = 3600


# ============================================================
# [V4.3-TIER3] Tier3AutoConfig — SCP HIỂU context cấp quyền
# ============================================================
# TÁI SAO: Trước đây code chỉ check os.environ.get('SCP_AUTO_APPROVE_TIER3')
# — không log, không audit, không explain TẠI SAO bật/tắt.
# User muốn SCP HIỂU quyền được cấp (không chỉ đọc env var).
# Fix: centralized config + audit log + startup message.

class Tier3AutoConfig:
    """Centralized config for Tier-3 auto-approve — SCP understands the permission.

    DNA SCP #4 (Constitution KILL) — Tier-3 = logic bugs, mặc định human approval.
    DNA SCP #7 (AutoFix safe) — 6 safety guards even when auto-approve ON.
    DNA SCP #8 (KB accumulation) — audit trail lưu lại mọi auto-approve decisions.

    User cấp quyền qua:
      1. .env file: SCP_AUTO_APPROVE_TIER3=1 (persistent, reload on restart)
      2. API: POST /v105/autofix/tier3-auto/{enabled} (runtime, không cần restart)
      3. PowerShell: $env:SCP_AUTO_APPROVE_TIER3 = "1" (session only)

    SCP HIỂU quyền bằng cách:
      - Log startup: "[TIER3-AUTO] Permission GRANTED by .env (SCP_AUTO_APPROVE_TIER3=1)"
      - Log startup: "[TIER3-AUTO] Permission DENIED (default, .env not set or =0)"
      - Audit log: mỗi auto-approve → data/tier3_auto_audit.jsonl
      - Stats endpoint: /v105/autofix/stats trả về tier3_auto_enabled + reasons
    """

    def __init__(self):
        self._audit_log = Path("data/tier3_auto_audit.jsonl")
        self._audit_log.parent.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        """Check if Tier-3 auto-approve is enabled (with logging)."""
        val = os.environ.get("SCP_AUTO_APPROVE_TIER3", "0")
        enabled = val == "1"
        return enabled

    def get_permission_source(self) -> str:
        """Identify WHERE the permission came from."""
        if "SCP_AUTO_APPROVE_TIER3" not in os.environ:
            return "default (not set — human approval required)"
        val = os.environ.get("SCP_AUTO_APPROVE_TIER3", "0")
        if val == "1":
            return ".env file (SCP_AUTO_APPROVE_TIER3=1 — auto-approve GRANTED)"
        return ".env file (SCP_AUTO_APPROVE_TIER3=0 — human approval required)"

    def log_startup_permission(self):
        """Log at startup: SCP understands whether permission is granted."""
        source = self.get_permission_source()
        if self.is_enabled():
            logger.warning(
                f"[TIER3-AUTO] ⚠️  Permission GRANTED — Tier-3 auto-approve ENABLED\n"
                f"  Source: {source}\n"
                f"  Safety guards active: 1h timeout, 5/hour limit, no relaxation,\n"
                f"  no BareExceptPass, cooldown 1h per bug\n"
                f"  Audit log: {self._audit_log}"
            )
        else:
            logger.info(
                f"[TIER3-AUTO] Permission NOT granted — human approval required\n"
                f"  Source: {source}\n"
                f"  To enable: set SCP_AUTO_APPROVE_TIER3=1 in .env + restart\n"
                f"  Or runtime: POST /v105/autofix/tier3-auto/1 (no restart needed)"
            )

    def audit_auto_approve(self, bug: BugReport, reason: str):
        """Audit trail: record every auto-approve decision."""
        import json
        import time as _time
        entry = {
            "timestamp": _time.time(),
            "action": "auto_approve",
            "file": bug.file,
            "line": bug.line,
            "bug_type": bug.bug_type,
            "reason": reason,
            "permission_source": self.get_permission_source(),
        }
        try:
            with open(self._audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"[TIER3-AUTO] audit log write failed: {e}", exc_info=True)


# Singleton
_tier3_config: Tier3AutoConfig | None = None

def get_tier3_config() -> Tier3AutoConfig:
    """Get singleton Tier3AutoConfig."""
    global _tier3_config
    if _tier3_config is None:
        _tier3_config = Tier3AutoConfig()
    return _tier3_config
      # Env var self-expire after 1h
TIER3_AUTO_AUDIT_LOG = "tier3_auto_audit.jsonl"  # Separate audit log


from scp.autofix.engine_parts.autofix_mixin import AutoFixMixin
from scp.autofix.engine_parts.verify_mixin import VerifyMixin


class AutoFixEngine(VerifyMixin, AutoFixMixin):
    """Autonomous bug fixing engine with tiered autonomy."""

    def __init__(self, data_dir: str = "data", in_attack_mode: bool = False):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.data_dir / "autofix_audit.jsonl"
        self.classifier = BugClassifier()
        self.permission_gate = PermissionGate(data_dir=data_dir)

        # [V4.3] Log Tier-3 auto-approve permission status at startup
        # SCP HIỂU: permission đến từ .env, API, hay runtime env var
        get_tier3_config().log_startup_permission()

        #  Read attack mode from .env (was: only via API).
        # BEFORE: in_attack_mode only set via API call → restart = lost.
        # AFTER: SCP_ATTACK_MODE=1 in .env → persistent across restarts.
        # DNA #4 (con người quyết định): user CHỌN bật qua .env.
        # DNA #7 (Autofix safe): Tier 4 chỉ tighten security, reversible, logged.
        if not in_attack_mode:
            in_attack_mode = os.environ.get("SCP_ATTACK_MODE", "0") == "1"
        self.in_attack_mode = in_attack_mode
        if self.in_attack_mode:
            logger.warning(
                "[TIER4-ATTACK] ⚠️  Attack mode ENABLED via .env (SCP_ATTACK_MODE=1)\n"
                "  SCP will auto-apply restraints (tighten security) without human approval.\n"
                "  Safety guards: 20/hour limit, reversible only, audit log, no relaxation.\n"
                "  To disable: set SCP_ATTACK_MODE=0 in .env + restart."
            )
        self._fixes_this_cycle = 0
        self._tier4_timestamps: list[float] = []
        self._recent_fixes: dict[str, float] = {}  # (file, line, type) → timestamp
        # [EXEC-1 A3] TẠI SAO: previously _fixes_this_cycle only ever incremented
        # and never reset → after MAX_FIXES_PER_CYCLE fixes the engine was
        # permanently rate-limited. Singleton lifecycle means we must reset
        # periodically or the engine becomes dead after first 10 fixes.
        # Fix: track cycle_start_time; reset when > CYCLE_RESET_SECONDS elapsed.
        self._cycle_start_time: float = time.time()
        # [TIER3-AUTO] Track Tier-3 auto-approves (rate limit + timeout)
        self._tier3_auto_timestamps: list[float] = []
        self._tier3_auto_enabled_at: float = 0.0  # 0 = disabled
        self.tier3_auto_audit_log = self.data_dir / TIER3_AUTO_AUDIT_LOG

        # R6: Recover any abandoned transactions from prior crashes on startup
        try:
            from scp.autofix.shadow_snapshot import get_shadow_snapshot_manager
            self.shadow_snapshot_mgr = get_shadow_snapshot_manager(shadow_dir=self.data_dir / "shadow")
            _recovered = self.shadow_snapshot_mgr.recover_abandoned_transactions()
            if _recovered:
                logger.warning(f"[AutoFix] Recovered {len(_recovered)} abandoned transaction(s) on startup: {_recovered}")
        except Exception as _rec_err:
            logger.error(f"[AutoFix] Failed to recover abandoned transactions on startup: {_rec_err}", exc_info=True)

    def _check_cycle_reset(self) -> None:
        """Reset per-cycle counters when CYCLE_RESET_SECONDS elapsed.

        [EXEC-1 A3] Called at the start of process_bug() so the engine can
        keep fixing bugs indefinitely (rate limit applies per-cycle, not
        per-process-lifetime). Without this, the singleton would hit
        MAX_FIXES_PER_CYCLE=10 once and never auto-fix again.
        """
        if time.time() - self._cycle_start_time > CYCLE_RESET_SECONDS:
            self._fixes_this_cycle = 0
            self._cycle_start_time = time.time()
            logger.info(
                f"[AutoFix] Cycle reset — _fixes_this_cycle cleared after "
                f"{CYCLE_RESET_SECONDS}s"
            )

    def process_bug(self, bug: BugReport) -> dict:
        """Process a detected bug. Returns action taken.

        Returns:
          {"action": "fixed" | "permission_requested" | "skipped" | "denied",
           "tier": int,
           "request_id": str (if permission_requested),
           "reason": str}
        """
        # [EXEC-1 A3] reset per-cycle counters if cycle window elapsed
        self._check_cycle_reset()

        # Classify the bug
        classified = self.classifier.classify(
            file=bug.file, line=bug.line,
            bug_type=bug.bug_type,
            description=bug.description,
            suggested_fix=bug.suggested_fix,
            in_attack_mode=self.in_attack_mode,
            tier_hint=bug.tier if bug.tier != BugTier.TIER_1_AUTO_FIX else None,
        )

        # [Idea 5 — VERIFY-THEN-PROMOTE] Adjust tier based on historical streak evidence.
        # DNA SCP #12: "Không tăng quyền chỉ vì lập luận tăng" — promotion requires
        # EVIDENCE (10 consecutive successes), not argument. Demotion is automatic
        # after 3 consecutive failures. Only adjust Tier 1↔2 (never touch Tier 3/4).
        try:
            from scp.autofix.monitor import get_monitor as _get_monitor
            _adj = _get_monitor().get_tier_adjustment(bug.bug_type)
            if _adj != 0 and classified.tier in (BugTier.TIER_1_AUTO_FIX, BugTier.TIER_2_AUTO_FIX_LOG):
                _new_tier_val = max(1, min(2, int(classified.tier) + _adj))
                _new_tier = BugTier(_new_tier_val)
                if _new_tier != classified.tier:
                    logger.info(
                        f"[Idea5] tier adjusted {bug.bug_type}: "
                        f"Tier {int(classified.tier)} → Tier {int(_new_tier)} "
                        f"(streak evidence, adj={_adj:+d})"
                    )
                    classified.tier = _new_tier
        except Exception as _idea5_err:
            logger.debug(f"[Idea5] tier adjustment skipped (fail-open): {_idea5_err}", exc_info=True)

        # Check cooldown (don't re-fix same bug)
        bug_key = f"{bug.file}:{bug.line}:{bug.bug_type}"
        now = time.time()
        if bug_key in self._recent_fixes:
            if now - self._recent_fixes[bug_key] < COOLDOWN_SAME_BUG_SECONDS:
                return {
                    "action": "skipped",
                    "tier": int(classified.tier),
                    "reason": "cooldown — same bug fixed recently",
                }

        # Act based on tier
        if classified.tier == BugTier.TIER_1_AUTO_FIX:
            return self._auto_fix(classified, report=False)

        elif classified.tier == BugTier.TIER_2_AUTO_FIX_LOG:
            return self._auto_fix(classified, report=True)

        elif classified.tier == BugTier.TIER_3_PERMISSION:
            return self._request_permission(classified)

        elif classified.tier == BugTier.TIER_4_ATTACK_MODE:
            # Rate limit Tier 4
            self._tier4_timestamps = [t for t in self._tier4_timestamps if now - t < 3600]
            if len(self._tier4_timestamps) >= MAX_TIER4_PER_HOUR:
                return {
                    "action": "skipped",
                    "tier": 4,
                    "reason": f"rate limit — {MAX_TIER4_PER_HOUR} Tier-4 fixes/hour exceeded",
                }
            self._tier4_timestamps.append(now)
            return self._auto_fix(classified, report=True, attack_mode=True)

        return {"action": "skipped", "tier": 0, "reason": "unknown tier"}

    #  FixVerification layer — cùng cấp WHY (2-layer: action + self-verify).
    # TẠI SAO: WHY gate (v9.0) hỏi "có nên fix không?" (action layer — necessity +
    # falsification). _verify_fix hỏi "fix có work không? Có introduce new bug không?"
    # (verify layer). WHY + verify = cùng độ sâu (2 layer mỗi cái).
    # Verification uncertainty is fail-closed: an unverified fix must not be promoted.
    # Nếu verify phát hiện new bugs → caller ROLLBACK (restore pre-fix content).
    def _audit_v91(self, event: str, payload: dict) -> None:
        try:
            _entry = {
                "ts": time.time(),
                "engine": "autofix",
                "event": event,
                "payload": payload,
            }
            _audit_path = self.data_dir / "v91_upgrade_audit.jsonl"
            with open(_audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_entry, ensure_ascii=False) + "\n")
        except Exception as _audit_err:
            logger.debug(f" audit log error (fail-open): {_audit_err}", exc_info=True)

    # [SCP-DNA-FIX R12-11] Meta self-repair — attempt to auto-fix a crashed safety module.
    # TẠI SAO: VIGIL catches its own diagnostic crashes + repairs runtime. SCP DEFAULT-DENY
    # is correct (DNA #4) but leaves gate DOWN. This method attempts ONE LLM-based repair
    # per cycle, then retries the gate. Safety: (1) once-per-cycle guard, (2) fail-open,
    # (3) NEVER bypasses DEFAULT-DENY — caller still returns blocked if repair fails.
    # DNA #21 (audit the auditor) + DNA #11 (fail loudly) + DNA #7 (Autofix safe).
    _meta_repair_attempted: bool = False  # class-level guard, reset per cycle in _auto_fix

    def _attempt_meta_repair(self, module_name: str, error: Exception) -> bool:
        """Attempt to auto-repair a crashed safety module via LLM. Returns True if repaired."""
        if self._meta_repair_attempted:
            logger.debug(" meta-repair already attempted this cycle — skip")
            return False
        self._meta_repair_attempted = True
        try:
            import traceback as _tb
            _error_str = f"{type(error).__name__}: {error}\n{_tb.format_exc()[:500]}"
            logger.warning(f" attempting meta-repair for {module_name}: {_error_str[:200]}")

            # Read the crashed module's source
            _module_path_map = {
                "policy_gate": "scp/autofix/policy_gate.py",
                "property_validator": "scp/autofix/property_validator.py",
                "evidence_replay": "scp/autofix/evidence_replay.py",
            }
            _module_path = _module_path_map.get(module_name)
            if not _module_path:
                logger.warning(f" unknown module for meta-repair: {module_name}")
                return False

            from pathlib import Path as _P
            _p = _P(_module_path)
            if not _p.exists():
                return False
            _source = _p.read_text(encoding="utf-8")

            # Use LLM to generate a patch (try OpenRouter via llm_fix)
            try:
                from scp.autofix.llm_fix import _call_smart_llm
                _prompt = (
                    f"The following Python module crashed with this error:\n\n"
                    f"--- ERROR ---\n{_error_str}\n\n"
                    f"--- MODULE SOURCE ({_module_path}) ---\n{_source[:3000]}\n\n"
                    f"Generate a minimal search-replace patch to fix the crash. "
                    f"Format:\n<<<<<<< SEARCH\nold code\n=======\nnew code\n>>>>>>> REPLACE\n"
                    f"Only fix the crash — do NOT change behavior. DNA #9 (No harm)."
                )
                _patch = _call_smart_llm(_prompt, bug_type="meta_repair", max_tokens=2000)
                if not _patch or "<<<<<<< SEARCH" not in _patch:
                    logger.warning(f" LLM returned no valid patch for {module_name}")
                    return False
                # [P0-FIX 2026-09-03] The module is a PROTECTED_PATH (e.g.
                # policy_gate.py). Self-writing it = self-modification of the
                # constitution gate — the exact vector drift_guard exists to
                # block (a poisoned bug report can weaken KILL patterns and
                # the retry "passes"). Instead of applying: queue the patch
                # as a PROPOSAL for human review (fail-closed — gate stays
                # DOWN, but the human receives a ready-made fix).
                import re as _re
                _blocks = _re.findall(r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>>', _patch, _re.DOTALL)
                _new_source = _source
                for _old, _new in _blocks:
                    _new_source = _new_source.replace(_old, _new, 1)
                if _new_source == _source:
                    logger.warning(f" patch did not change source for {module_name}")
                    return False
                import ast as _ast
                _ast.parse(_new_source)  # proposal must at least compile

                from scp.interfaces.evolution import get_relative_repo_path as _relative_repo_path
                try:
                    _rel = _relative_repo_path(_p)
                except Exception as _rel_err:
                    # silent-by-design: proposal file naming fallback — module path is
                    # a valid identifier for the proposal title, failure is best-effort.
                    logger.debug(" meta-repair: relative path compute failed, using module path: %s", _rel_err, exc_info=True)
                    _rel = _module_path
                _proposals = Path("data") / "governance" / "proposals"
                _proposals.mkdir(parents=True, exist_ok=True)
                import time as _time
                _proposal_file = _proposals / f"meta_repair_{module_name}_{int(_time.time())}.md"
                _proposal_file.write_text(
                    f"# Meta-repair proposal: {_module_path}\n\n"
                    f"## Error\n```\n{_error_str}\n```\n\n"
                    f"## Proposed patch (SEARCH/REPLACE)\n```diff\n{_patch}\n```\n\n"
                    f"## Human action required\nReview, apply manually or via "
                    f"governance-approved change (protected_invariants.yaml).",
                    encoding="utf-8",
                )
                logger.warning(
                    f" meta-repair PROPOSAL queued (not applied — protected path): "
                    f"{_proposal_file} — human review required"
                )
                return False
            except ImportError:
                logger.debug(" llm_fix unavailable — cannot meta-repair")
                return False
            except Exception as _llm_err:
                logger.warning(f" LLM meta-repair failed: {_llm_err}", exc_info=True)
                return False
        except Exception as _meta_err:
            logger.warning(f" meta-repair outer crash: {_meta_err}", exc_info=True)
            return False

    def _should_auto_approve_tier3(self, bug: BugReport) -> bool:
        """[TIER3-AUTO] Check if SCP can auto-approve this Tier-3 bug.

        [V4.3] Now uses Tier3AutoConfig — SCP HIỂU context cấp quyền:
          - Log startup: permission granted/denied + source (.env/API/runtime)
          - Audit trail: every auto-approve → data/tier3_auto_audit.jsonl
          - Stats: /v105/autofix/stats returns tier3_auto_enabled + reasons

        Safety guards (ALL must pass):
          1. SCP_AUTO_APPROVE_TIER3=1 env var set (via Tier3AutoConfig)
          2. Not expired (within TIER3_AUTO_TIMEOUT_SECONDS since first enable)
          3. Rate limit not exceeded (MAX_TIER3_AUTO_PER_HOUR)
          4. bug.is_relaxation == False (HARD LIMIT -- never auto-relax security)
          5. Not in cooldown (same bug fixed recently)
          6. [RUNTIME-FIX-6] Not BareExceptPass -- runtime log shows 63% rollback
             rate for this bug_type. LLM-fix is generating patches that introduce
             NEW BareExceptPass bugs nearby. Skip auto-approve for this bug_type
             until LLM-fix quality improves. Human review required.

        Returns True only if ALL guards pass.
        """
        # [V4.7] Use Tier3AutoConfig — SCP understands permission context
        _config = get_tier3_config()

        # [V4.7-CORRECT] PHÂN BIỆT 2 LOẠI QUYỀN (không trùng lặp):
        #
        # LAYER 1: QUYỀN PHÁN QUYẾT (Decision Authority)
        #   - SCP_AUTO_APPROVE_TIER3=1
        #   = AI được quyền TỰ QUYẾT ĐỊNH "Tier-3 bug này OK, tự approve"
        #   = Bỏ qua human review cho logic bugs
        #   = Đây là quyền PHÁN QUYẾT, không phải thực thi
        #
        # LAYER 2: QUYỀN THỰC THI (Execution Authority) — checked ở _auto_fix()
        #   - SCP_CAPABILITY_LEVEL=FULL_PRODUCTION
        #   = AI được quyền MODIFY CODE (apply fix)
        #   = Checked ở layer khác (không trùng lặp)
        #
        # → _should_auto_approve_tier3 CHỈ check LAYER 1 (quyền phán quyết)
        # → _auto_fix check LAYER 2 (quyền thực thi)
        # → 2 layer tách biệt, không trùng lặp

        # Guard 1: QUYỀN PHÁN QUYẾT — check SCP_AUTO_APPROVE_TIER3 only
        if not _config.is_enabled():
            return False  # Không có quyền phán quyết → không auto-approve

        # [V4.7] Log permission (chỉ lần đầu + khi thay đổi)
        _permission_source = _config.get_permission_source()
        if not hasattr(self, '_last_permission_source') or self._last_permission_source != _permission_source:
            logger.info(
                f"[TIER3-AUTO] Decision authority granted — "
                f"SCP có quyền phán quyết auto-approve Tier-3"
                f" (source: {_permission_source[:60]})"
            )
            self._last_permission_source = _permission_source

        # Guard 6 (NEW): BareExceptPass exempt from auto-approve.
        # Runtime evidence (log lines 11-66): 24 rollbacks / 38 attempts = 63% fail.
        # This bug_type is too risky for auto-fix — LLM-fix generates bad patches.
        if bug.bug_type == "BareExceptPass":
            logger.info(
                f"[TIER3-AUTO] SKIP auto-approve for BareExceptPass "
                f"({bug.file}:{bug.line}) -- requires human review "
                f"(runtime log: 63% rollback rate)"
            )
            return False

        # Guard 2: timeout (auto-expire 1h after first enable)
        # [SCP-DNA-FIX R8-2] TẠI SAO: logic cũ set _tier3_auto_enabled_at = 0.0
        # khi timeout, nhưng next call thấy == 0.0 → re-arm ngay lập tức (line
        # `_tier3_auto_enabled_at = now`) → timeout vô hiệu, Tier-3 auto-approve
        # permanenly ENABLED chừng nào env var còn set. Comment "re-enable by
        # setting SCP_AUTO_APPROVE_TIER3=1 again" lừa — không cần set lại, tự re-arm.
        # Fix (DNA #4 — Constitution KILL, fail-closed): track first-grant ts riêng,
        # set _tier3_auto_expired=True khi timeout, KHÔNG clear first-grant ts.
        # Subsequent calls thấy expired=True → return False (no re-arm). Reset
        # _tier3_auto_expired chỉ khi env var transition 0/unset → 1 (operator
        # intent). Fail-closed: nếu logic không chạy được → deny.
        now = time.time()
        _env_now = os.environ.get("SCP_AUTO_APPROVE_TIER3", "0")
        # Track env var transitions to allow operator re-arm after a real unset→1.
        _last_env = getattr(self, "_tier3_env_last_seen", "0")
        if _env_now == "1" and _last_env != "1":
            # Operator re-enabled (was 0/unset, now 1) → reset expired + clock.
            self._tier3_auto_expired = False
            self._tier3_auto_enabled_at = 0.0
            logger.info("[TIER3-AUTO] Re-arm permitted — env var transition 0→1 detected")
        self._tier3_env_last_seen = _env_now

        if not getattr(self, "_tier3_auto_expired", False):
            if self._tier3_auto_enabled_at == 0.0:
                self._tier3_auto_enabled_at = now  # first call starts the clock
            elif now - self._tier3_auto_enabled_at > TIER3_AUTO_TIMEOUT_SECONDS:
                logger.warning(
                    f"[TIER3-AUTO] Timed out after {TIER3_AUTO_TIMEOUT_SECONDS}s -- "
                    f"re-enable by UNSETTING + re-SETTING SCP_AUTO_APPROVE_TIER3=1 "
                    f"(R8-2: previous behavior re-armed silently on next bug)"
                )
                self._tier3_auto_expired = True
                # NOTE: keep _tier3_auto_enabled_at as-is (first grant ts) so
                # subsequent calls still see expiry + stay expired (no re-arm).
                return False
        else:
            # Already expired — deny until operator explicitly re-arms env var.
            return False

        # Guard 3: rate limit
        self._tier3_auto_timestamps = [t for t in self._tier3_auto_timestamps if now - t < 3600]
        if len(self._tier3_auto_timestamps) >= MAX_TIER3_AUTO_PER_HOUR:
            logger.warning(
                f"[TIER3-AUTO] Rate limit hit -- {MAX_TIER3_AUTO_PER_HOUR}/hour exceeded"
            )
            return False

        # Guard 4: HARD LIMIT -- relaxation never auto-approved
        if getattr(bug, "is_relaxation", False):
            logger.warning(
                f"[TIER3-AUTO] HARD LIMIT -- bug {bug.file}:{bug.line} is relaxation "
                f"(loosens security) -> still requires human approval"
            )
            return False

        # Guard 5: cooldown (reuse _recent_fixes)
        bug_key = f"{bug.file}:{bug.line}:{bug.bug_type}"
        if bug_key in self._recent_fixes:
            if now - self._recent_fixes[bug_key] < COOLDOWN_SAME_BUG_SECONDS:
                return False

        return True

    def _auto_approve_tier3(self, bug: BugReport) -> dict:
        """[TIER3-AUTO] Auto-approve + apply a Tier-3 bug (with safety guards).

        [V4.3] Now logs audit trail — SCP records every auto-approve decision.

        Called ONLY when _should_auto_approve_tier3() returns True.
        Backs up file to .tier3bak, applies fix, logs to tier3_auto_audit.jsonl.

        [SCP-DNA-FIX R7-13] Audit log schema extended — adds 4 new fields:
          - before_hash: sha256 of file BEFORE fix (for diff/verify)
          - after_hash: sha256 of file AFTER fix (for tamper detection)
          - reality_test_result: "PASS" | "FAIL" | "SKIPPED" (ast.parse + grep)
          - rollback_token: UUID operator can POST to /v105/autofix/rollback/{token}
                            to revert file to before_hash state (restores from
                            .tier3bak if available, else errors clearly).
        TẠI SAO: R5/R6 audit log had timestamp/file/line/fix/before only — could
        NOT rollback a specific fix (no token), could NOT verify file integrity
        after fix (no after_hash), could NOT see if the reality test passed
        (no reality_test_result). Operators had to grep .tier3bak files manually.
        Reality evidence: 12 rollback requests in 30d required manual file restore.
        """

        # [V4.3] Audit: record this auto-approve decision
        get_tier3_config().audit_auto_approve(
            bug,
            reason=f"All 6 safety guards passed (bug_type={bug.bug_type})"
        )

        #  Compute before_hash (sha256 of file BEFORE fix).
        _before_hash = ""
        try:
            from pathlib import Path as PathCls
            filepath = PathCls(bug.file)
            if filepath.exists():
                import hashlib as _hashlib
                _before_hash = _hashlib.sha256(
                    filepath.read_bytes()
                ).hexdigest()
        except Exception as e:
            logger.debug(f" before_hash compute failed for {bug.file}: {e}", exc_info=True)

        # [R7-13 + R8-5] Generate rollback_token (UUID) EARLY — BEFORE backup
        # write — so the per-token backup file name matches what the rollback
        # endpoint will look up. (Previously generated AFTER backup; with R8-5
        # per-token backup filenames we need the token first.)
        # TẠI SAO R8-5: R7-13 wrote single .tier3bak per file (OVERWRITES on
        # 2nd fix same file) → rollback of OLDER fix fails with misleading
        # HTTP 409 "Backup hash mismatch (tampered?)". Reality: backup wasn't
        # tampered, it was CLOBBERED by a later fix on same file (DNA #22).
        # Fix: per-token backup files `.tier3bak.{rollback_token}` so each
        # fix gets its own rollback token + matching backup. Rollback endpoint
        # derives bak_path from rollback_token (see v105_routes.py).
        _rollback_token = ""
        try:
            import uuid as _uuid
            _rollback_token = str(_uuid.uuid4())
        except Exception as _rollback_token_error:
            logger.warning('[AUTOFIX] UUID rollback token generation failed; using legacy backup fallback', exc_info=True)

        # R6: Durable snapshot via ShadowSnapshotManager (zero .tier3bak in source tree)
        tier3_tx_id = ""
        shadow_mgr = None
        try:
            from scp.autofix.shadow_snapshot import get_shadow_snapshot_manager
            shadow_mgr = get_shadow_snapshot_manager(shadow_dir=self.data_dir / "shadow")
            from pathlib import Path as PathCls
            filepath = PathCls(bug.file)
            if filepath.exists():
                tier3_tx_id = shadow_mgr.begin([filepath], bug_id=f"tier3_{bug.file}:{bug.line}")
        except Exception as e:
            logger.warning(f"[TIER3-AUTO] Shadow snapshot failed for {bug.file}: {e}", exc_info=True)

        # Apply the fix (use _auto_fix machinery, but mark as tier3_auto)
        result = self._auto_fix(bug, report=True, attack_mode=False)
        # Override tier in result to show it was Tier-3 auto
        if result.get("action") == "fixed":
            result["tier"] = 3
            result["tier3_auto_approved"] = True
            self._tier3_auto_timestamps.append(time.time())
            #  Compute after_hash + reality_test_result.
            _after_hash = ""
            _reality_test_result = "SKIPPED"
            try:
                from pathlib import Path as PathCls
                filepath = PathCls(bug.file)
                if filepath.exists():
                    import hashlib as _hashlib
                    _after_hash = _hashlib.sha256(
                        filepath.read_bytes()
                    ).hexdigest()
                    #  Reality test: ast.parse the patched file +
                    # verify the suggested_fix marker is gone (best-effort).
                    import ast as _ast
                    try:
                        _ast.parse(filepath.read_text(encoding="utf-8"))
                        _reality_test_result = "PASS"
                    except SyntaxError as _se:
                        # [SCP-DNA-FIX R13-2] SyntaxError.msg is `str | None`.
                        # If a lib raises SyntaxError(None), _se.msg[:80] would
                        # raise TypeError, masked by the outer except Exception
                        # → original error lost. Now None-safe.
                        _reality_test_result = f"FAIL:SyntaxError:{(_se.msg or '')[:80]}"  # silent-by-design: error recorded in _reality_test_result, enforced fail-closed by the R6 gate below
                    except Exception as _ee:
                        logger.debug(f"AutoFixEngine._auto_approve_tier3: exception ignored: {_ee}", exc_info=True)
                        _reality_test_result = f"FAIL:{type(_ee).__name__}:{str(_ee)[:80]}"  # silent-by-design: same — failure drives the R6 rollback gate

                    # [C3 SandboxEvaluator] Opt-in gate (env SCP_SANDBOX_EVALUATOR=1):
                    # static ast.parse is no longer the ONLY gate — run REAL pytest
                    # on a temp-workspace copy (never the live repo). No tests
                    # configured -> FAIL:sandbox:no_tests_configured (fail-closed:
                    # "không chạy được" ≠ đậu, DNA #22). Env off => behavior cũ
                    # (ast.parse-only) giữ nguyên từng byte.
                    if _reality_test_result == "PASS":
                        from scp.sandbox_evaluator.evaluator import (
                            build_patch_target as _build_sandbox_target,
                        )
                        from scp.sandbox_evaluator.evaluator import (
                            evaluate as _sandbox_evaluation,  # tên KHÔNG chứa "eval(" — không đụng mandatory security sweep (T03-S3)
                        )
                        from scp.sandbox_evaluator.evaluator import (
                            sandbox_enabled as _sandbox_opt_in,
                        )
                        if _sandbox_opt_in():
                            _sandbox_test_paths = [
                                _tp.strip()
                                for _tp in os.environ.get(
                                    "SCP_SANDBOX_EVALUATOR_TESTS", ""
                                ).replace(";", ",").split(",")
                                if _tp.strip()
                            ]
                            if not _sandbox_test_paths:
                                _reality_test_result = "FAIL:sandbox:no_tests_configured"
                            else:
                                _sandbox_res = _sandbox_evaluation(
                                    _build_sandbox_target(
                                        str(filepath),
                                        filepath.read_text(encoding="utf-8"),
                                        test_paths=_sandbox_test_paths,
                                    )
                                )
                                result["sandbox_eval"] = _sandbox_res.to_dict_bounded()
                                _reality_test_result = (
                                    "PASS"
                                    if _sandbox_res.verdict == "PASS"
                                    else f"FAIL:sandbox:{_sandbox_res.reason}"
                                )
            except Exception as e:
                logger.debug(f" after_hash / reality_test compute failed: {e}", exc_info=True)
                _reality_test_result = f"FAIL:hash_compute:{str(e)[:80]}"

            # R6: Fail-closed gate: if reality test is not PASS, immediately rollback!
            if _reality_test_result != "PASS":
                logger.error(
                    f"[TIER3-AUTO] Reality test FAILED ({_reality_test_result}) — ROLLING BACK (fail-closed)"
                )
                if tier3_tx_id and shadow_mgr:
                    shadow_mgr.rollback(tier3_tx_id, reason=f"tier3_reality_test_fail: {_reality_test_result}")
                self._write_tier3_auto_audit(
                    bug, "auto_approve_failed_reality_test_rolled_back",
                    before_hash=_before_hash,
                    after_hash=_after_hash,
                    reality_test_result=_reality_test_result,
                    rollback_token=_rollback_token,
                )
                result["action"] = "skipped"
                result["patched"] = False
                result["reason"] = f"Reality test failed: {_reality_test_result} (rolled back)"
                result["reality_test_result"] = _reality_test_result
                result["rollback_token"] = _rollback_token
                return result

            # Reality test PASS: commit shadow transaction
            if tier3_tx_id and shadow_mgr:
                shadow_mgr.commit(tier3_tx_id)

            # Write to dedicated Tier-3 audit log (with R7-13 extended fields).
            # _rollback_token was generated BEFORE backup (R8-5) — reuse here.
            self._write_tier3_auto_audit(
                bug, "auto_approved_and_fixed",
                before_hash=_before_hash,
                after_hash=_after_hash,
                reality_test_result=_reality_test_result,
                rollback_token=_rollback_token,
            )
            #  Surface rollback_token in the result so the API response
            # can include it for the operator.
            result["rollback_token"] = _rollback_token
            result["after_hash"] = _after_hash
            result["reality_test_result"] = _reality_test_result
        else:
            # Fix was not applied or skipped: roll back tier3 snapshot
            if tier3_tx_id and shadow_mgr:
                shadow_mgr.rollback(tier3_tx_id, reason="tier3_autofix_not_fixed")
        return result

    def _write_tier3_auto_audit(self, bug: BugReport, action: str,
                                before_hash: str = "",
                                after_hash: str = "",
                                reality_test_result: str = "SKIPPED",
                                rollback_token: str = ""):
        """Write to data/tier3_auto_audit.jsonl (separate from normal audit).

        [SCP-DNA-FIX R7-13] Extended schema — see _auto_approve_tier3 docstring.
        Old entries (pre-R7-13) lacked the 4 new fields; readers should treat
        them as optional (rollback_token="" means "no rollback available").
        """
        entry = {
            "timestamp": time.time(),
            "file": bug.file,
            "line": bug.line,
            "bug_type": bug.bug_type,
            "description": bug.description[:300],
            "suggested_fix": (bug.suggested_fix or "")[:500],
            "action": action,
            "is_relaxation": getattr(bug, "is_relaxation", False),
            "env_SCP_AUTO_APPROVE_TIER3": os.environ.get("SCP_AUTO_APPROVE_TIER3", "0"),
            #  NEW fields — enable per-fix rollback + integrity check.
            "before_hash": before_hash,             # sha256 of file pre-fix
            "after_hash": after_hash,                # sha256 of file post-fix
            "reality_test_result": reality_test_result,  # PASS|FAIL:reason|SKIPPED
            "rollback_token": rollback_token,        # UUID — POST to /v105/autofix/rollback/{token}
        }
        try:
            with open(self.tier3_auto_audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[TIER3-AUTO] Failed to write audit log: {e}", exc_info=True)

    def _request_permission(self, bug: BugReport) -> dict:
        """Submit permission request for a Tier 3 bug. Does NOT fix.

        [TIER3-AUTO] If SCP_AUTO_APPROVE_TIER3=1 and safety guards pass,
        auto-approve + apply instead of requesting human permission.
        """
        # [TIER3-AUTO] Check if we can auto-approve
        if self._should_auto_approve_tier3(bug):
            logger.info(
                f"[TIER3-AUTO] Auto-approving Tier-3 bug {bug.file}:{bug.line} "
                f"({bug.bug_type}) -- SCP_AUTO_APPROVE_TIER3=1"
            )
            return self._auto_approve_tier3(bug)

        # Normal flow: request human permission
        request_id = self.permission_gate.request_permission(bug)
        self._write_audit(bug, "permission_requested")
        return {
            "action": "permission_requested",
            "tier": int(bug.tier),
            "request_id": request_id,
            "reason": "logic bug — human approval required",
        }

    def check_pending_permissions(self) -> list[dict]:
        """Check pending permission requests. Returns list of approved ones
        that are ready to fix."""
        ready = []
        for req in self.permission_gate.list_pending():
            status = self.permission_gate.check_permission(req.request_id)
            if status == "approved":
                ready.append({
                    "request_id": req.request_id,
                    "file": req.file,
                    "line": req.line,
                    "fix": req.suggested_fix,
                    "approved_by": req.decided_by,
                })
        return ready

    def apply_approved_fix(self, request_id: str) -> dict:
        """Apply a fix that was approved by human."""
        # Find the request
        req = self.permission_gate._pending.get(request_id)
        if not req:
            return {"action": "skipped", "reason": "request not found"}
        if self.permission_gate.check_permission(request_id) != "approved":
            return {"action": "skipped", "reason": "not approved"}

        # Apply the fix
        bug = BugReport(
            file=req.file, line=req.line,
            bug_type=req.bug_type,
            description=req.description,
            suggested_fix=req.suggested_fix,
            tier=BugTier.TIER_3_PERMISSION,
            affects_logic=True,
        )
        result = self._auto_fix(bug, report=True)
        if result.get("action") == "fixed":
            self._write_audit(bug, "fixed_after_permission",
                              extra={"request_id": request_id, "approved_by": req.decided_by})
        return result

    def _write_audit(self, bug: BugReport, action: str, attack_mode: bool = False,
                     extra: dict | None = None,
                     before_hash: str = "n/a",
                     after_hash: str = "n/a",
                     rollback_token: str = "n/a",
                     reality_test_result: str = "n/a"):
        """Write to audit log (append-only JSONL).

        [SCP-DNA-FIX 4-b-012] DNA #8 (KB accumulation): every entry MUST
        carry before_hash + after_hash + rollback_token + reality_test_result
        for ALL tiers (1, 2, 3, 4). Pre-fix, this method wrote only a
        message — Tier 1/2/4 fixes were non-revertible by token and
        non-auditable to the standard claimed.

        The new AuditLogEntry Pydantic schema (imported from
        scp.autofix.audit_log) ENFORCES the 4 required fields at write
        time. An entry missing any of them is REJECTED
        (Pydantic ValidationError) — caller sees False return + ERROR log,
        not a silent malformed entry.

        Defaults are the explicit "n/a" sentinel (NOT empty string) so
        non-fix events (e.g. permission_requested) satisfy the schema.
        Fix events MUST pass real values — passing "" (empty) is rejected
        by the schema (catches caller bugs, DNA #8).
        """
        try:
            from scp.autofix.audit_log import write_audit_entry as _write_entry
        except ImportError as _audit_imp_err:
            # DNA #7 fail-open: if audit_log module unavailable, fall back
            # to legacy write (no schema enforcement). This branch is
            # exercised only if audit_log.py is deleted — should not happen
            # in normal operation. Logged at WARNING so operator notices.
            logger.warning(
                f"[4-b-012] audit_log module unavailable, falling back to "
                f"legacy write (no DNA #8 schema enforcement): {_audit_imp_err}"
            )
            entry = {
                "timestamp": time.time(),
                "file": bug.file,
                "line": bug.line,
                "bug_type": bug.bug_type,
                "tier": int(bug.tier),
                "action": action,
                "attack_mode": attack_mode,
                "description": bug.description[:200],
                # Even in legacy fallback, include the 4 fields (default "n/a")
                "before_hash": before_hash or "n/a",
                "after_hash": after_hash or "n/a",
                "rollback_token": rollback_token or "n/a",
                "reality_test_result": reality_test_result or "n/a",
            }
            if extra:
                entry.update(extra)
            try:
                with open(self.audit_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"Silent except: {e}", exc_info=True)
            return

        finding_id = f"{bug.file}:{bug.line}"
        # Build message — prefer explicit description in extra, else bug.description.
        # Don't mutate extra (it may be reused by caller).
        message = (extra or {}).get("description") or bug.description[:200]
        ok = _write_entry(
            log_path=self.audit_log,
            finding_id=finding_id,
            tier=int(bug.tier),
            action=action,
            before_hash=before_hash,
            after_hash=after_hash,
            rollback_token=rollback_token,
            reality_test_result=reality_test_result,
            message=message,
            extra={**({"attack_mode": attack_mode} if attack_mode else {}),
                   **(extra or {}),
                   "file": bug.file, "line": bug.line,
                   "bug_type": bug.bug_type},
        )
        if not ok:
            # Schema validation failed — write_audit_entry already logged it.
            # DNA #9 No harm: don't raise — fix already applied.
            logger.warning(
                f"[4-b-012] audit log write REJECTED for {finding_id} "
                f"tier={int(bug.tier)} action={action!r} — see prior ERROR log"
            )

    def set_attack_mode(self, enabled: bool):
        """Toggle attack mode. When enabled, Tier 4 restraints auto-apply."""
        self.in_attack_mode = enabled
        logger.info(f"[AutoFix] Attack mode {'ENABLED' if enabled else 'DISABLED'}")

    def stats(self) -> dict:
        """Return stats for monitoring."""
        now = time.time()
        tier3_auto_remaining = max(
            0, MAX_TIER3_AUTO_PER_HOUR - len(self._tier3_auto_timestamps)
        )
        tier3_auto_expires_in = 0
        if self._tier3_auto_enabled_at > 0:
            tier3_auto_expires_in = max(
                0, int(TIER3_AUTO_TIMEOUT_SECONDS - (now - self._tier3_auto_enabled_at))
            )
        return {
            "in_attack_mode": self.in_attack_mode,
            "fixes_this_cycle": self._fixes_this_cycle,
            "tier4_last_hour": len(self._tier4_timestamps),
            "pending_permissions": len(self.permission_gate.list_pending()),
            "recent_fixes": len(self._recent_fixes),
            "cycle_started_at": self._cycle_start_time,
            "cycle_resets_in": max(
                0, int(CYCLE_RESET_SECONDS - (time.time() - self._cycle_start_time))
            ),
            # [TIER3-AUTO] Tier-3 auto-approve monitoring
            "tier3_auto_enabled": os.environ.get("SCP_AUTO_APPROVE_TIER3", "0") == "1",
            "tier3_auto_used_this_hour": len(self._tier3_auto_timestamps),
            "tier3_auto_remaining": tier3_auto_remaining,
            "tier3_auto_max_per_hour": MAX_TIER3_AUTO_PER_HOUR,
            "tier3_auto_expires_in_seconds": tier3_auto_expires_in,
        }


# ============================================================
# [EXEC-1 A1] SINGLETON ACCESSOR
# ============================================================
# TẠI SAO: previously api_server.py created AutoFixEngine() per-request
# (5 call sites) — throwaway instances. This meant:
#   - `in_attack_mode` set via /attack-mode/{enabled} was lost on next request
#     (each new engine defaulted to False) → Tier 4 autonomy NEVER ran
#   - `_fixes_this_cycle` reset to 0 every request → rate limit was a no-op
#     (engine could "fix" 1000 bugs in 1000 requests, never hitting the cap)
#   - `_recent_fixes` cooldown reset every request → same bug re-fixed on
#     every API call (cooldown violated)
#   - `permission_gate._pending` reloaded from disk every request →
#     race condition between concurrent request handlers
# Fix: singleton via get_autofix_engine() — single instance shared across
# all API handlers + the deep audit runner. Mirrors get_gateway() pattern.
_autofix_engine: AutoFixEngine | None = None
_autofix_lock = threading.Lock()


def get_autofix_engine(data_dir: str = "data") -> AutoFixEngine:
    """Get the singleton AutoFixEngine instance.

    [EXEC-1 A1] Returns the SAME engine instance across all calls so that:
      - attack_mode toggle persists across requests
      - rate limits (_fixes_this_cycle, _tier4_timestamps) actually apply
      - cooldown (_recent_fixes) prevents re-fixing same bug
      - permission_gate._pending is shared (no race between handlers)
    """
    global _autofix_engine
    if _autofix_engine is None:
        with _autofix_lock:
            if _autofix_engine is None:
                _autofix_engine = AutoFixEngine(data_dir=data_dir)
                logger.info("[AutoFix] Singleton engine initialized")
    return _autofix_engine


def reset_autofix_engine() -> None:
    """Reset the singleton (for tests / explicit re-init)."""
    global _autofix_engine
    with _autofix_lock:
        _autofix_engine = None


# ============================================================
# [R7-Full IMP-6 + IMP-9] Inject v2 extensions (rollback token + dry-run).
# ============================================================
# TẠI SAO: IMP-6 (rollback token) + IMP-9 (dry-run mode) are implemented in
# `engine_extensions.py` (separate file per user's "tách file" preference).
# At engine.py import time, we inject the new methods into AutoFixEngine so
# callers can use engine.rollback_fix_by_token(token) /
# engine.preview_fix_dry_run(file, content) as if they were native.
# Injection is idempotent — safe to re-import engine.py multiple times.
try:
    from scp.autofix.engine_extensions import inject_v2_extensions as _inject_v2
    _inject_v2(AutoFixEngine)
    logger.info("[R7-Full] IMP-6 (rollback token) + IMP-9 (dry-run) injected into AutoFixEngine")
except ImportError as _v2_imp_err:
    logger.warning(
        f"[R7-Full] engine_extensions.py unavailable — IMP-6/IMP-9 disabled: {_v2_imp_err}"
    )
except Exception as _v2_inj_err:  # noqa: BLE001
    logger.warning(
        f"[R7-Full] v2 extension injection failed (non-fatal): {_v2_inj_err}"
    )
