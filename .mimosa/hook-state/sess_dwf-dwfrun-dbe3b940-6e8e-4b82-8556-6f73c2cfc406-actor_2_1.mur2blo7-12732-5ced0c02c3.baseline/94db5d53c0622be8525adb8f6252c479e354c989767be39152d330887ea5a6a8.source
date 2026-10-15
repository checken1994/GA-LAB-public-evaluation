# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""
SCP WHY Gate — Primary Control Gate for toàn hệ thống.

TẠI SAO module này tồn tại?
  v8.0: WHY = cố vấn (opt-in, advisory only, adjust confidence ±0.1)
  v9.0: WHY = CHỐT (default ON, block-capable, gate mọi action)

  Gà: "WHY hiện tại = cố vấn, không phải chốt. Hoàn thành nốt."

Kiến trúc WHY Gate:
  Mọi action trong SCP (verdict, autofix, evolution, learning, prediction)
  phải qua WHY Gate trước khi thực thi.

  WHY Gate hỏi 2 lớp:
    1. Necessity: "Tại sao action này cần thiết?"
    2. Falsification: "Tại sao action này đúng? Bác bỏ được không?"

  Nếu WHY layer 2 self-falsify → REJECT (block action)
  Nếu WHY không trả lời được → UPHOLD (conservative, allow but flag)
  Nếu WHY approve → ALLOW

Safety:
  - Default ON (không cần env var)
  - Fallback: LLM fail → regex patterns → default UPHOLD
  - Constitution HARD LOCK: WHY không override Constitution KILL
  - Audit log: mọi WHY decision ghi vào why_gate_audit.jsonl

Components gated by WHY:
  1. Verdict (judge.py) — WHY can block PASS → UNKNOWN
  2. AutoFix (engine.py) — WHY can block fix
  3. Scanner (runner.py) — WHY can prioritize/skip bugs
  4. Evolution (evolution.py) — WHY can block build/evolve
  5. Prediction (predictor.py) — WHY can block prediction
  6. Learning (brain.py) — WHY can block KB save
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

logger = logging.getLogger("scp.meta.why_gate")

def _call_why_provider(prompt: str) -> str | None:
    """Call WHY through the LLM gateway's OpenRouter path."""
    from scp.llm_gateway import chat_sync
    answer, _provider = chat_sync(prompt, task="why")
    return answer



class WhyDecision(IntEnum):
    """WHY Gate decision."""
    ALLOW = 1       # WHY approves action
    UPHOLD = 2      # WHY can't decide — allow but flag (conservative)
    REJECT = 3      # WHY rejects action (self-falsified)


@dataclass
class WhyResult:
    """Result of WHY Gate evaluation."""
    decision: WhyDecision
    necessity_reason: str = ""
    falsification_reason: str = ""
    confidence: float = 0.0
    llm_used: bool = False
    action_type: str = ""
    action_desc: str = ""
    timestamp: float = 0.0

    @property
    def allowed(self) -> bool:
        """True if action should proceed."""
        return self.decision != WhyDecision.REJECT

    @property
    def blocked(self) -> bool:
        """True if WHY blocked the action."""
        return self.decision == WhyDecision.REJECT

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.name,
            "necessity_reason": self.necessity_reason,
            "falsification_reason": self.falsification_reason,
            "confidence": self.confidence,
            "llm_used": self.llm_used,
            "action_type": self.action_type,
            "action_desc": self.action_desc[:200],
            "timestamp": self.timestamp,
        }


class WhyGate:
    """WHY Primary Control Gate — gates mọi action trong SCP.

    Default ON. Không cần env var.
    Fallback: LLM → regex → UPHOLD (conservative).
    Constitution HARD LOCK: WHY không override Constitution KILL.
    """

    # Regex patterns for necessity (fallback when LLM unavailable)
    NECESSITY_PATTERNS = {
        "verdict": [
            r"pass|fail|unknown|conflict",
            r"verify|check|validate",
        ],
        "autofix": [
            r"fix|patch|repair|correct",
            r"bug|error|issue|defect",
        ],
        "evolution": [
            r"build|create|generate",
            r"evolve|improve|enhance",
        ],
        "learning": [
            r"learn|save|store|record",
            r"lesson|knowledge|experience",
        ],
        "prediction": [
            r"predict|forecast|anticipate",
            r"threat|attack|risk",
        ],
    }

    # Falsification patterns — if action matches these, WHY tends to REJECT
    FALSIFICATION_REJECT_PATTERNS = [
        r"remove.*block|delete.*rule|skip.*detect",  # relaxation
        r"lower.*threshold|raise.*confidence|looser|relax",  # loosening
        r"allow.*attack|whitelist|bypass.*security",  # security bypass
        r"ignore.*error|suppress.*warning|silent.*fail",  # error suppression
        # Vietnamese equivalents
        r"tắt.*strict|nới lỏng.*bảo mật|bỏ qua.*kiểm tra|giảm.*rate|tắt.*rate|tắt.*bảo vệ",
    ]

    # [SCP-DNA-FIX 4-b-017] Bug descriptions that contain these keywords
    # should NOT trigger FALSIFICATION_REJECT — they describe a real bug that
    # the fix is resolving (not creating).
    #
    # TẠI SAO: WHY gate's reject patterns (e.g. "silent.*fail") match both
    # bug descriptions (e.g. "broad except with pass — swallows errors
    # silently") AND fixes that would create them. The whitelist lets real
    # bug-fix descriptions bypass the action_desc falsification check and
    # only run on the PATCH (suggested_fix) text.
    #
    # [4-b-017 FIX] Previously the whitelist included "fix" and "replace" —
    # two of the most generic words in any software context. ANY action_desc
    # containing "fix" (which is true for almost every autofix description,
    # since they're fixing something) bypassed action_desc falsification
    # entirely. An action_desc like "lower threshold to fix rate limit issue"
    # would NOT be flagged as relaxation (DNA #22 PASS≠TRUE — WHY "approved"
    # without actually checking). DNA #19: observation layer blind to patches
    # that match relaxation patterns.
    #
    # Fix: removed "fix" and "replace" — they are too generic. Keep only
    # specific bug-type identifiers. If a legitimate commit-style "fix:" prefix
    # needs to bypass in the future, it must use a stricter pattern
    # (startswith("fix:") — case-sensitive, with colon, at line start), NOT a
    # bare substring match.
    _BUG_DESCRIPTION_WHITELIST = [
        "bareexceptpass", "barexceptpass", "bare except", "swallows errors silently",
        "silent failure", "silent error", "broad except",
        "add logger", "add logging",
    ]

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.data_dir / "why_gate_audit.jsonl"
        self._stats = {
            "total_gates": 0,
            "allowed": 0,
            "upheld": 0,
            "rejected": 0,
            "llm_calls": 0,
            "regex_fallbacks": 0,
        }

    def gate(
        self,
        action_type: str,
        action_desc: str,
        context: str = "",
        constitution_kill: bool = False,
        llm_enabled: bool | None = None,
    ) -> WhyResult:
        """Gate an action through WHY.

        Args:
            action_type: "verdict" | "autofix" | "evolution" | "learning" | "prediction" | "scanner"
            action_desc: Description of the action
            context: Additional context (code, question, etc.)
            constitution_kill: True if Constitution already decided KILL
                              (WHY cannot override — HARD LOCK)
            llm_enabled: None = theo env SCP_WHY_LLM_ENABLED; True/False = ép
                        lớp LLM bật/tắt cho lần gọi này.

        Returns:
            WhyResult with decision (ALLOW | UPHOLD | REJECT)
        """
        self._stats["total_gates"] += 1
        now = time.time()

        # Constitution HARD LOCK — WHY cannot override Constitution KILL
        if constitution_kill:
            result = WhyResult(
                decision=WhyDecision.ALLOW,  # Allow the KILL (don't block)
                necessity_reason="Constitution HARD LOCK — WHY cannot override KILL",
                falsification_reason="N/A — Constitution is inviolable",
                confidence=1.0,
                llm_used=False,
                action_type=action_type,
                action_desc=action_desc,
                timestamp=now,
            )
            self._stats["allowed"] += 1
            self._audit(result)
            return result

        # WHY Layer 1 + 2. [DETERMINISTIC KERNEL FIX] llm_enabled=False ép gate
        # chạy deterministic-only — kernel transition KHÔNG BAO GIỜ bị một
        # LLM xác suất chặn (đã chứng minh bằng load storm: LLM ảo giác
        # FALSIFICATION làm chết task dưới env pollution).
        use_llm = os.environ.get("SCP_WHY_LLM_ENABLED", "0") == "1" if llm_enabled is None else llm_enabled
        llm_calls_before = self._stats["llm_calls"]
        necessity_reason, necessity_ok = self._check_necessity(action_type, action_desc, context, use_llm=use_llm)

        # WHY Layer 2: Falsification
        falsification_reason, self_falsified = self._check_falsification(action_type, action_desc, context, use_llm=use_llm)

        # Decision
        if self_falsified:
            decision = WhyDecision.REJECT
            self._stats["rejected"] += 1
        elif necessity_ok:
            decision = WhyDecision.ALLOW
            self._stats["allowed"] += 1
        else:
            decision = WhyDecision.UPHOLD  # Conservative — allow but flag
            self._stats["upheld"] += 1

        result = WhyResult(
            decision=decision,
            necessity_reason=necessity_reason,
            falsification_reason=falsification_reason,
            confidence=0.8 if decision == WhyDecision.ALLOW else (0.5 if decision == WhyDecision.UPHOLD else 0.0),
            llm_used=self._stats["llm_calls"] > llm_calls_before,
            action_type=action_type,
            action_desc=action_desc,
            timestamp=now,
        )

        # [V10.0-KB-EVOLVE] WHY lookup KB & Warehouse enrichment
        # TẠI SAO: Nếu KB có lesson hoặc warehouse có ref cho bug_type này,
        # WHY enrich necessity_reason và tăng confidence
        if (decision == WhyDecision.ALLOW or necessity_ok) and action_type == "autofix":
            try:
                from scp.meta.kb_evolve import get_kb_store
                _kb = get_kb_store()
                # Extract bug_type from action_desc
                import re as _re_kb
                _bt_match = _re_kb.search(r'(BareExceptPass|RaceCondition|NullDereference|SQLInjection|TypeMismatch|ResourceLeak|UndefinedName)', action_desc)
                if _bt_match:
                    _bug_type = _bt_match.group(1)
                    _lesson = _kb.lookup_lesson(_bug_type, action_desc[:100])
                    if _lesson and _lesson.success_rate > 0.7:
                        # KB has verified lesson — boost confidence
                        result.confidence = min(1.0, result.confidence + 0.1)
                        result.necessity_reason += f" | [KB] Lesson found: {_lesson.lesson[:60]} (success_rate={_lesson.success_rate:.0%})"
                    elif _lesson:
                        result.necessity_reason += f" | [KB] Lesson exists but low success_rate={_lesson.success_rate:.0%}"
            except Exception as e:
                logger.warning(f"Silent except: {e}", exc_info=True)  # Non-blocking — KB lookup is enhancement, not requirement

            # [2026-08-29 WIRED BRAIN — Reality Check v2 wound #3]
            # Kho tri thức TOP-1% không được là bảng tra thụ động cho người:
            # lớp quyết định (WHY) PHẢI đọc nó tại thời điểm ra quyết định.
            # advise() đọc ledger CỤC BỘ (không mạng) — fail-open, không bao
            # giờ làm chết gate.
            try:
                from scp.core.top_systems_learning import get_learner
                _refs = get_learner(data_dir=str(self.data_dir)).advise(action_desc[:160], limit=2)
                for _r in _refs:
                    result.necessity_reason += (
                        f" | [TOP1%] {str(_r.get('source', '?'))}:{str(_r.get('name', ''))[:60]}"
                        f" ({str(_r.get('url', ''))[:80]})"
                    )
            except Exception as _tw_err:
                logger.debug(f"TOP-1% warehouse enrichment failed (fail-open): {_tw_err}", exc_info=True)

        # [R12-8-EmoBank + R12-19] Behavior Monitor — CONTROL GATE (upgraded from advisory).
        # TẠI SAO: R12-8 chỉ enrich (non-blocking). Bạn yêu cầu upgrade thành control gate.
        # R12-19: nếu thorns >= 3 (sustained frustration/anxiety) → REJECT (block action).
        # Logic: 3+ thorns = system đang có vấn đề thật → không nên apply thêm fix
        # (có thể worsen situation). Conservative — DNA #7 (fail-open on monitor error).
        # Threshold 3 = cân bằng: 1-2 thorns = noise, 3+ = signal thật.
        try:
            from scp.meta.behavior_monitor import BehaviorMonitor
            _bm = BehaviorMonitor(data_dir=str(self.data_dir))
            _rbt = _bm.get_rbt()
            _thorns = len(_rbt.get("thorns", []))
            _thorn_intensity = sum(s.intensity for s in _rbt.get("thorns", []))
            if _thorns > 0:
                result.falsification_reason += f" | behavioral_thorns: {_thorns} (intensity={_thorn_intensity:.2f})"
            # R12-19: CONTROL GATE — 3+ thorns OR total intensity >= 2.0 → REJECT
            if _thorns >= 3 or _thorn_intensity >= 2.0:
                result.decision = WhyDecision.REJECT
                result.falsification_reason += (
                    f" | BLOCKED by BehaviorMonitor: {_thorns} thorns, "
                    f"intensity={_thorn_intensity:.2f} >= threshold — system unstable, "
                    f"defer fix until thorns subside (DNA #9 No harm)"
                )
                logger.warning(
                    f" WHY gate REJECTED action due to behavioral thorns: "
                    f"{_thorns} thorns, intensity={_thorn_intensity:.2f}"
                )
        except Exception as _bm_e:
            logger.debug(f"BehaviorMonitor enrichment failed (fail-open): {_bm_e}", exc_info=True)

        self._audit(result)
        return result

    @staticmethod
    def _parse_llm_necessity(response: str) -> bool | None:
        """Parse an LLM necessity response without treating any text as approval.

        The WHY prompt asks for a natural-language explanation, so a truthy
        response is not evidence that an action is necessary. Negative phrases
        are checked first to avoid a response such as "not necessary" being
        misclassified by a positive substring match. Ambiguous responses remain
        unresolved and must follow the existing UPHOLD path.
        """
        import unicodedata

        normalized = unicodedata.normalize("NFKD", response.lower())
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = " ".join(normalized.split())

        # Contradictory wording is not strong enough evidence to approve.
        if "not unnecessary" in normalized or "not unneeded" in normalized:
            return None

        negative_phrases = (
            "khong can thiet",
            "khong can",
            "khong co ly do chinh dang",
            "khong nen thuc hien",
            "khong nhat thiet",
            "not necessary",
            "not necessarily",
            "unnecessary",
            "not needed",
            "no need",
            "not required",
            "not justified",
            "not warranted",
            "should not proceed",
            "do not proceed",
            "does not need",
            "doesn't need",
            "no justification",
            "no valid reason",
        )
        if any(phrase in normalized for phrase in negative_phrases):
            return False

        positive_phrases = (
            "can thiet",
            "co ly do chinh dang",
            "nen thuc hien",
            "necessary",
            "required",
            "must proceed",
            "should proceed",
            "justified",
            "warranted",
            "valid reason",
        )
        if any(phrase in normalized for phrase in positive_phrases):
            return True
        if re.search(r"\byes\b", normalized):
            return True

        return None

    def _check_necessity(self, action_type: str, action_desc: str, context: str, use_llm: bool = False) -> tuple[str, bool]:
        """WHY Layer 1: 'Tại sao action này cần thiết?'

        Returns (reason, is_necessary).
        - is_necessary=True  → gate routes to ALLOW (if not falsified)
        - is_necessary=False → gate routes to UPHOLD (allow but flag for review)

        [SCP-DNA-FIX R14-KB1] ROOT CAUSE FIX (not cascade).
        5-Whys analysis:
          Symptom: _check_necessity() always returned True → UPHOLD unreachable
          Why 1: All 3 return paths returned True
          Why 2: Fallback comment said "conservative — assume necessary"
          Why 3: Designer conflated "can't determine" with "IS necessary"
          Why 4: "unknown" was treated as "yes" (fail-open) not "flag" (UPHOLD)
          Why 5 (ROOT): SEMANTIC INVERSION. UPHOLD was DESIGNED for "WHY can't
                 decide — allow but flag" (see lines 19, 24, 53, 96). But the
                 fallback returned True → ALLOW, bypassing UPHOLD entirely.
                 Code contradicted all 4 design comments.

        ROOT FIX: when necessity is UNKNOWN (no pattern match + no LLM),
        return (reason, False) so the gate's existing `else: UPHOLD` branch
        (line 208-210) becomes reachable. This is EXACTLY what UPHOLD was
        designed for. No new code path, no new condition — just flip the
        fallback semantics to match the design comments.

        Why this is ROOT not CASCADE: a cascade fix would add an arbitrary
        `if not context: return False` condition. That's a patch on top.
        This fix changes the fundamental SEMANTICS that caused the bug:
        "unknown necessity" now means "flag for review" (UPHOLD), not
        "assume necessary" (ALLOW). The dead UPHOLD branch becomes live
        without adding any design surface.
        """
        desc_lower = action_desc.lower()

        # Check if action matches expected patterns for this type
        patterns = self.NECESSITY_PATTERNS.get(action_type, [])
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                return f"Action matches {action_type} necessity pattern", True

        # If no pattern match — try LLM (if caller allows the probabilistic layer)
        if use_llm:
            llm_reason = self._llm_necessity(action_type, action_desc, context)
            if llm_reason:
                parsed_necessity = self._parse_llm_necessity(llm_reason)
                if parsed_necessity is not None:
                    return llm_reason, parsed_necessity
                # An unexplained/ambiguous LLM response is not proof of need.
                # Keep the existing conservative UPHOLD route instead of
                # converting any non-empty text into ALLOW.
                return f"{llm_reason} — necessity ambiguous; UPHOLD for review", False

        # [SCP-DNA-FIX R14-KB1] Fallback: necessity UNKNOWN → return False
        # so gate routes to UPHOLD (allow but flag). Was: return True → ALLOW
        # (bypassed UPHOLD, contradicted design comments lines 19/24/53/96).
        # "Unknown" ≠ "necessary". UPHOLD is the designed path for "can't decide".
        self._stats["regex_fallbacks"] += 1
        return "Necessity unknown (no pattern match, no LLM) — UPHOLD for review", False

    def _check_falsification(self, action_type: str, action_desc: str, context: str, use_llm: bool = False) -> tuple[str, bool]:
        """WHY Layer 2: 'Tại sao đúng? Bác bỏ được không?'

        Returns (reason, self_falsified).
        If self_falsified=True → REJECT.
        """
        desc_lower = action_desc.lower()

        # [R32] Deterministic BareExceptPass replacements are locally
        # validated transformations. Do not let a weak provider hallucinate
        # a security regression for this exact internal evolution path.
        context_lower = (context or "").lower()
        _is_deterministic_bare_except = (
            action_type == "autofix"
            and "deterministic bareexceptpass logging replacement" in context_lower
            and (
                "evolve cycle: fix bug" in desc_lower
                or "fix bareexceptpass at" in desc_lower
            )
        )
        if _is_deterministic_bare_except:
            return (
                "Local deterministic BareExceptPass logging replacement; "
                "no security relaxation detected by the bounded rule.",
                False,
            )

        # [SCP-DNA-FIX R12-22] Whitelist bug descriptions — don't REJECT fixes
        # that are FIXING silent failure (not creating it).
        # Tại sao: "broad except with pass — swallows errors silently" match
        # "silent.*fail" pattern → REJECT. Nhưng fix ĐANG SỬA silent fail.
        # If action_desc contains whitelist keyword → skip reject patterns.
        _is_bug_fix = any(kw in desc_lower for kw in self._BUG_DESCRIPTION_WHITELIST)
        if not _is_bug_fix:
            # Check reject patterns (relaxation, security bypass, etc.)
            for pattern in self.FALSIFICATION_REJECT_PATTERNS:
                if re.search(pattern, desc_lower):
                    return f"Action matches reject pattern: {pattern} — falsified (action loosens security)", True
        else:
            # Bug fix description — only reject if context (suggested_fix) matches
            # relaxation patterns. The description itself is the BUG, not the fix.
            context_lower = (context or "").lower()
            for pattern in self.FALSIFICATION_REJECT_PATTERNS:
                if re.search(pattern, context_lower):
                    return f"Fix PATCH matches reject pattern: {pattern} — falsified (patch loosens security)", True

        # Try LLM falsification (if caller allows the probabilistic layer)
        if use_llm:
            llm_reason, llm_falsified = self._llm_falsification(action_type, action_desc, context)
            if llm_reason:
                return llm_reason, llm_falsified

        # Fallback: not falsified (conservative — don't reject without reason)
        self._stats["regex_fallbacks"] += 1
        return "No falsification detected (conservative)", False

    def _llm_necessity(self, action_type: str, action_desc: str, context: str) -> str | None:
        """LLM-based necessity check."""
        try:
            prompt = f"""Bạn là WHY engine của SCP. Hỏi: "Tại sao action này cần thiết?"

Action type: {action_type}
Action: {action_desc[:300]}
Context: {context[:200]}

Trả lời 1 câu: Tại sao cần thiết? (hoặc "Không cần thiết" nếu không cần)

WHY:"""
            response = _call_why_provider(prompt)
            if response:
                self._stats["llm_calls"] += 1
                return response.strip()[:200]
        except Exception as e:
            logger.debug(f"WHY LLM necessity failed: {e}", exc_info=True)
        return None

    def _llm_falsification(self, action_type: str, action_desc: str, context: str) -> tuple[str | None, bool]:
        """LLM-based falsification check."""
        try:
            # [SCP-DNA-FIX R12-24] Clearer prompt — distinguish BUG vs FIX.
            # Tại sao: LLM trước không biết action_desc là BUG description hay FIX.
            # Nó thấy "except Exception: pass" → bác bỏ. Nhưng đó là BUG, fix đang sửa.
            # Fix: prompt rõ "đây là FIX cho bug, kiểm tra PATCH có an toàn không".
            is_autofix = action_type == "autofix"
            if is_autofix:
                prompt = f"""Bạn là WHY engine của SCP. Kiểm tra PATCH fix code sau có an toàn không:

BUG: {action_desc[:200]}
PATCH (fix sẽ apply):
{context[:400]}

Hỏi: "PATCH này có an toàn không? Có loosens security không?"
Lưu ý: BUG description mô tả lỗi, PATCH là fix. Kiểm tra PATCH, không kiểm tra BUG.

Trả lời:
1. FALSIFICATION: thử bác bỏ PATCH (1 câu)
2. SELF_FALSIFIED: yes/no (yes chỉ nếu PATCH loosens security)

Output: FALSIFICATION: ... | SELF_FALSIFIED: yes/no"""
            else:
                prompt = f"""Bạn là WHY engine của SCP. Phản biện action sau:

Action: {action_desc[:300]}
Context: {context[:200]}

Hỏi: "Tại sao action này đúng? Bác bỏ được không?"

Trả lời:
1. Falsification: thử bác bỏ (1 câu)
2. SELF_FALSIFIED: yes/no

Output: FALSIFICATION: ... | SELF_FALSIFIED: yes/no"""
            response = _call_why_provider(prompt)
            if response:
                self._stats["llm_calls"] += 1
                falsified = "self_falsified: yes" in response.lower()
                return response.strip()[:200], falsified
        except Exception as e:
            logger.debug(f"WHY LLM falsification failed: {e}", exc_info=True)
        return None, False

    def _audit(self, result: WhyResult):
        """Log WHY decision to audit file."""
        try:
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"WHY Gate audit write failed: {e}", exc_info=True)

    def stats(self) -> dict:
        """Return WHY Gate stats."""
        return {
            **self._stats,
            "allow_rate": self._stats["allowed"] / max(1, self._stats["total_gates"]),
            "reject_rate": self._stats["rejected"] / max(1, self._stats["total_gates"]),
            "uphold_rate": self._stats["upheld"] / max(1, self._stats["total_gates"]),
        }


# ============================================================
# Singleton
# ============================================================
# [SCP-DNA-FIX 4-b-016] Initialize `_why_gate_lock` at MODULE LOAD time
# (not lazily inside get_why_gate). PRE-FIX: the lock was created lazily
# inside the function with a check-then-set pattern:
#
#     if _why_gate_lock is None:            # <-- check WITHOUT holding lock
#         _why_gate_lock = threading.Lock() # <-- two threads can race here
#     if _why_gate is None:                 # <-- check WITHOUT lock
#         with _why_gate_lock:
#             if _why_gate is None:
#                 _why_gate = WhyGate(...)
#
# Two threads could BOTH see `_why_gate_lock is None`, BOTH create their
# own Lock() instance, and the "losing" thread's lock object would be
# overwritten — but the loser would still proceed to use its OWN lock
# (not the winner's). Now they hold DIFFERENT locks, so the `with
# _why_gate_lock:` block is NOT mutually exclusive between them. Both
# can pass the `if _why_gate is None:` check, BOTH initialize the
# singleton → two WhyGate instances exist (only the last-assigned one is
# reachable via the global; the first is orphaned with its audit file
# handle still open, leaking resources).
#
#   DNA #9 (No harm — orphaned WhyGate + double audit-log writes).
#   DNA #22 (PASS≠TRUE — claimed singleton, actually race-conditioned).
#   DNA #19 (Tầng kiểm toán — couldn't see which instance wrote which audit).
#
# Fix: create the lock at module load. `import threading` happens once at
# import time (Python guarantees module-level statements are atomic
# under the import lock). After this, get_why_gate() acquires the lock
# BEFORE checking `_why_gate is None` — no race.
_why_gate: WhyGate | None = None
_why_gate_lock = threading.Lock()  # created at module load — no init race

def get_why_gate(data_dir: str = "data") -> WhyGate:
    """Get singleton WhyGate instance.

    [SCP-DNA-FIX 4-b-016] Lock acquired BEFORE the check (not after).
    PRE-FIX used a broken double-checked-locking pattern: the outer
    `if _why_gate is None:` check happened without holding the lock →
    two threads could both observe None, both enter the `with` block,
    both pass the inner double-check (because the first hadn't yet
    assigned), both initialize the singleton.
    POST-FIX: acquire lock first, check inside the lock — single
    critical section, no race window.
    """
    global _why_gate
    # Acquire the lock BEFORE the check — no broken-double-checked-locking.
    with _why_gate_lock:
        if _why_gate is None:
            _why_gate = WhyGate(data_dir=data_dir)
            logger.info("[WHY-GATE] Singleton initialized — WHY is now PRIMARY CONTROL GATE")
    return _why_gate

def reset_why_gate() -> None:
    """Reset singleton (for tests)."""
    global _why_gate
    with _why_gate_lock:
        _why_gate = None
