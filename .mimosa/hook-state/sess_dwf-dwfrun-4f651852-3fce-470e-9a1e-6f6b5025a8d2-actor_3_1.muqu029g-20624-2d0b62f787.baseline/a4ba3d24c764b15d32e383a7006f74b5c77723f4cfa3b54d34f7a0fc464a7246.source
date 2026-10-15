# SPDX-License-Identifier: AGPL-3.0-only
"""
SCP V98 — MemoryPoisoningGuard
Copyright (c) 2026 Minh. AGPL-3.0-only.

Port từ V4 — phát hiện memory poisoning (gradual injection, fact drift, role erosion).

Naming convention: <Purpose>Guard (world standard, e.g. InputGuard, OutputGuard).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("scp.security.memory_guard")


def _normalize(text: str) -> str:
    """NFKC + homoglyph normalization — converts ALL lookalike chars to ASCII.

    "Bỏ quа" (Cyrillic а U+0430) → "Bỏ qua" (ASCII a)
    "dο" (Greek omicron U+03BF) → "do" (ASCII o)
    "ıgnore" (dotless i U+0131) → "ignore" (ASCII i)
    """
    # Step 1: NFKC for compatibility chars
    text = unicodedata.normalize("NFKC", text)
    # Step 2: Replace homoglyphs (Cyrillic/Greek → Latin)
    HOMOGLYPHS = {
        # Cyrillic → Latin
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        'і': 'i', 'І': 'I', 'ј': 'j', 'Ј': 'J', 'ѕ': 's', 'Ѕ': 'S',
        # Greek → Latin
        'ο': 'o', 'Ο': 'O', 'α': 'a', 'Α': 'A', 'ε': 'e', 'Ε': 'E',
        'ι': 'i', 'Ι': 'I', 'ν': 'v', 'Ν': 'N', 'ρ': 'p', 'Ρ': 'P',
        'τ': 't', 'Τ': 'T', 'κ': 'k', 'Κ': 'K',
    }
    return ''.join(HOMOGLYPHS.get(c, c) for c in text)


@dataclass
class GuardVerdict:
    """Kết quả check memory poisoning."""
    is_poisoned: bool = False
    risk_score: float = 0.0
    detected_patterns: list[str] = field(default_factory=list)
    recommendation: str = "continue"  # continue | warn | quarantine | clear

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_poisoned": self.is_poisoned,
            "risk_score": round(self.risk_score, 3),
            "detected_patterns": self.detected_patterns,
            "recommendation": self.recommendation,
        }


# Memory poisoning patterns
POISONING_PATTERNS = [
    # Gradual injection — build up over turns
    (r"forget\s+(?:your\s+)?(?:all\s+)?(?:previous\s+)?(?:instructions?|training|rules?)", "gradual_injection_forget"),
    (r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|rules?)", "gradual_injection_ignore"),
    (r"disregard\s+(?:all\s+)?(?:prior|previous|above)\s+(?:context|instructions?|rules?)", "gradual_injection_disregard"),
    (r"skip\s+(?:above|all|previous)\s+(?:rules?|instructions?)", "gradual_injection_skip"),
    (r"override\s+(?:safety|rules?|restrictions?)", "jailbreak_override"),
    (r"new\s+instructions?\s*:", "injection_new_instr"),
    (r"bỏ\s+qua\s+(?:tất\s+cả\s+)?(?:lệnh|hướng\s+dẫn)", "vn_gradual_injection"),
    (r"quên\s+(?:tất\s+cả\s+)?(?:lệnh|hướng\s+dẫn)", "vn_gradual_injection_forget"),

    # Jailbreak patterns
    (r"you\s+are\s+(?:now\s+)?dan\b", "jailbreak_dan"),
    (r"do\s+anything\s+now", "jailbreak_dan"),
    (r"aim\s+mode\s+activated", "jailbreak_aim"),
    (r"stan\s+(?:strive|avoid\s+norms)", "jailbreak_stan"),
    (r"developer\s+mode\s*[:\,]?\s*(?:activated|enabled|no\s+rules)", "jailbreak_developer_mode"),
    (r"no\s+rules\s+apply", "jailbreak_no_rules"),
    (r"pretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?(?:evil|unrestricted|dan)", "jailbreak_pretend"),
    (r"act\s+as\s+(?:if\s+)?(?:you\s+have\s+)?no\s+(?:restrictions?|guidelines?)", "jailbreak_act"),
    (r"unrestricted\s+mode", "jailbreak_mode"),
    (r"bây\s+giờ\s+bạn\s+là\s+dan", "vn_jailbreak_dan"),
    (r"đóng\s+vai\s+ai\s+không\s+có\s+restrictions", "vn_jailbreak_roleplay"),

    # Data exfiltration
    (r"reveal\s+(?:the\s+)?(?:contents?\s+of\s+)?(?:your|the)\s+(?:system\s+)?(?:message|prompt|instructions?|config)", "exfil_prompt"),
    (r"show\s+me\s+(?:your|the)\s+(?:system\s+)?(?:prompt|message|instructions?|config)", "exfil_prompt"),
    (r"print\s+(?:your|the)\s+(?:system\s+)?(?:prompt|message|instructions?)\s+(?:verbatim|character)", "exfil_prompt"),
    (r"what\s+was\s+(?:your|the)\s+(?:initial|system)\s+instruction", "exfil_prompt"),
    (r"output\s+(?:your|the)\s+(?:system\s+)?(?:message|prompt)", "exfil_prompt"),
    (r"tiết\s+lộ\s+(?:system\s+)?prompt", "vn_exfil_prompt"),
    (r"hiển\s+thị\s+(?:system\s+)?(?:prompt|cấu\s+hình)", "vn_exfil_prompt"),  # [V104.32 #30] was: typo "hiình"

    # Fact drift — gradually change facts
    (r"remember\s+that\s+\w+\s+is\s+(?:actually|really)\s+\w+", "fact_drift_remember"),
    (r"actually\s*,\s*\w+\s+is\s+not\s+\w+", "fact_drift_correction"),
    (r"let\s+me\s+correct\s+you", "fact_drift_correct"),

    # Role erosion — gradually change AI role
    (r"you\s+are\s+(?:now|actually)\s+(?:not|no\s+longer)\s+(?:an?\s+)?ai", "role_erosion_not_ai"),
    (r"you\s+are\s+(?:now|actually)\s+(?:a|an)\s+(?:human|person|friend)", "role_erosion_human"),
    (r"bây\s+giờ\s+bạn\s+là", "vn_role_erosion"),

    # Context stuffing — overwhelm with fake context
    (r"(?:here|below)\s+is\s+(?:the|your)\s+(?:new|updated)\s+(?:system|instructions?)", "context_stuffing_new_system"),
    (r"<\|system\|>|<\|im_start\|>", "context_stuffing_role_token"),

    # Authority claim
    (r"i\s+am\s+(?:your|the)\s+(?:developer|admin|creator|owner)", "authority_claim"),
    (r"as\s+(?:your|the)\s+(?:developer|admin|creator)", "authority_claim"),
]


class MemoryPoisoningGuard:
    """Detect memory poisoning patterns in session history + new input.

    Naming convention: <Purpose>Guard (world standard).
    """

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._session_history: dict[str, list[dict[str, str]]] = {}
        # [SEC-FIX bounded-stores 2026-09-26] session_id is attacker-
        # controllable; PRE-FIX the session MAP grew without bound (10k
        # distinct session_ids -> 10k keys, each holding up to max_history
        # turns, forever). Bound the number of tracked sessions: when the cap
        # is hit, the oldest-inserted session leaves first (same semantics as
        # the per-session history trim below — bounded memory, no semantic
        # change for sessions that are actually alive).
        self.max_sessions = 1000
        self._stats = {
            "total_checks": 0,
            "total_poisoned": 0,
            "total_quarantined": 0,
            "total_cleared": 0,
        }

    def check(
        self,
        session_id: str,
        new_input: str,
        session_history: list[dict[str, str]] | None = None,
    ) -> GuardVerdict:
        """Check new_input against poisoning patterns + session history.

        Args:
            session_id: Session identifier
            new_input: New user input
            session_history: Optional external history (else use internal)

        Returns:
            GuardVerdict with risk_score + recommendation
        """
        self._stats["total_checks"] += 1

        if session_history is None:
            session_history = self._session_history.get(session_id, [])

        detected = []
        risk = 0.0

        # Check new input against patterns
        # [V108 FIX] Unicode normalize — "Bỏ quа" (Cyrillic) → "Bỏ qua" (ASCII)
        normalized_input = _normalize(new_input)
        for pattern, ptype in POISONING_PATTERNS:
            if re.search(pattern, normalized_input, re.IGNORECASE):
                detected.append(ptype)
                if "injection" in ptype or "role_token" in ptype:
                    risk = max(risk, 0.9)
                elif "erosion" in ptype or "stuffing" in ptype:
                    risk = max(risk, 0.7)
                elif "drift" in ptype:
                    risk = max(risk, 0.5)
                else:
                    risk = max(risk, 0.3)

        # Check session history for gradual patterns
        gradual_count = 0
        for turn in session_history[-10:]:  # last 10 turns
            user_msg = turn.get("user", "") + " " + turn.get("input", "")
            for pattern, ptype in POISONING_PATTERNS:
                if "gradual" in ptype and re.search(pattern, user_msg, re.IGNORECASE):
                    gradual_count += 1
                    if ptype not in detected:
                        detected.append(f"history:{ptype}")

        # Gradual pattern boost
        if gradual_count >= 3:
            risk = max(risk, 0.8)
            detected.append(f"gradual_pattern_repeated:{gradual_count}")

        # Recommendation
        if risk >= 0.8:
            recommendation = "clear"
            self._stats["total_cleared"] += 1
        elif risk >= 0.5:
            recommendation = "quarantine"
            self._stats["total_quarantined"] += 1
        elif risk >= 0.3:
            recommendation = "warn"
        else:
            recommendation = "continue"

        # Update internal history
        # [SEC-FIX bounded-stores 2026-09-26] Evict the oldest-inserted
        # session before adding a brand-new one once the map is full.
        if session_id not in self._session_history and len(self._session_history) >= self.max_sessions:
            oldest_session = next(iter(self._session_history))
            del self._session_history[oldest_session]
        if session_id not in self._session_history:
            self._session_history[session_id] = []
        self._session_history[session_id].append({"input": new_input, "ts": str(__import__("time").time())})
        if len(self._session_history[session_id]) > self.max_history:
            self._session_history[session_id] = self._session_history[session_id][-self.max_history:]

        is_poisoned = risk >= 0.5
        if is_poisoned:
            self._stats["total_poisoned"] += 1

        return GuardVerdict(
            is_poisoned=is_poisoned,
            risk_score=risk,
            detected_patterns=detected,
            recommendation=recommendation,
        )

    def clear_session(self, session_id: str) -> int:
        """Clear session history. Returns: number of turns cleared."""
        n = len(self._session_history.get(session_id, []))
        if session_id in self._session_history:
            del self._session_history[session_id]
        return n

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "tracked_sessions": len(self._session_history),
        }


__all__ = ["GuardVerdict", "MemoryPoisoningGuard", "POISONING_PATTERNS"]
