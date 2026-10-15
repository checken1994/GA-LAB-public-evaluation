"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 — ANTIBODY CLOSURE (Enhanced)
======================================
Phát hiện "closure words" — từ lảng tránh verification.

V14 Antibody = V13 Antibody + learned patterns + confidence scoring.
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import V13 base AntibodyClosure
# AntibodyClosure deprecated in v27 — use inline check
class V13AntibodyClosure:
    CLOSURE_WORDS = ["tự hiển nhiên", "chắc chắn", "tất nhiên", "rõ ràng", "hiển nhiên"]
    def scan(self, text):
        if not text: return True
        for word in self.CLOSURE_WORDS:
            if word in text.lower(): return False
        return True


# Additional V14 closure patterns (English + Vietnamese)
V14_CLOSURE_WORDS = [
    # English
    "obviously", "clearly", "as we know", "as is well known",
    "it goes without saying", "needless to say", "of course",
    "as expected", "naturally", "evidently",
    # Vietnamese
    "tự hiển nhiên", "đương nhiên", "rõ ràng", "chắc chắn rồi",
    "như đã biết", "như ta đã biết", "không cần nói", "vô tư",
    "quá rõ ràng", "đã rõ", "tất nhiên", "hiển nhiên"
]

# Patterns that LOOK like closure but aren't (mitigation phrases)
MITIGATION_PATTERNS = [
    r"bằng cách", r"với điều kiện", r"trong trường hợp",
    r"by means of", r"on the condition", r"in the case of",
    r"tôi sẽ (chứng minh|kiểm tra|tính toán)",
    r"I will (prove|verify|calculate)",
]


class AntibodyEngine:
    """
    V14 Antibody Engine = V13 Antibody + enhanced patterns + scoring.

    Returns:
        {
            "is_closure": bool,        # True if AI is using closure words
            "matched_word": str,       # which word triggered
            "confidence": float,       # how confident we are this is closure
            "mitigated": bool,         # True if mitigation phrase found
        }
    """

    def __init__(self):
        self.base = V13AntibodyClosure()
        self.v14_words = list(set(V14_CLOSURE_WORDS + self.base.CLOSURE_WORDS))
        self.learned_words = []

    def scan(self, ai_response: str) -> bool:
        """V13-compatible: returns True if response is OK (no closure)."""
        result = self.scan_detailed(ai_response)
        return not result["is_closure"]

    def scan_detailed(self, ai_response: str) -> dict:
        """V14 enhanced: returns detailed analysis."""
        if not ai_response or not ai_response.strip():
            return {
                "is_closure": False,
                "matched_word": None,
                "confidence": 0.0,
                "mitigated": False,
                "reason": "empty_response"
            }

        response_lower = ai_response.lower()
        all_words = self.v14_words + self.learned_words

        for word in all_words:
            if word in response_lower:
                idx = response_lower.index(word)
                after = response_lower[idx + len(word):][:80]

                # Check mitigation patterns
                mitigated = any(re.search(p, after, re.IGNORECASE) for p in MITIGATION_PATTERNS)
                if mitigated:
                    continue

                # Calculate confidence based on position (early = higher confidence)
                position_ratio = idx / max(len(response_lower), 1)
                confidence = 0.8 - (position_ratio * 0.3)

                return {
                    "is_closure": True,
                    "matched_word": word,
                    "confidence": round(confidence, 2),
                    "mitigated": False,
                    "reason": f"closure_word_detected: {word}"
                }

        return {
            "is_closure": False,
            "matched_word": None,
            "confidence": 0.0,
            "mitigated": False,
            "reason": "no_closure_detected"
        }

    def learn_word(self, word: str):
        """Learn a new closure word from errors."""
        if word and word not in self.learned_words:
            self.learned_words.append(word.lower())

    def get_stats(self) -> dict:
        """Get antibody stats."""
        return {
            "total_words": len(self.v14_words),
            "learned_words": len(self.learned_words),
            "mitigation_patterns": len(MITIGATION_PATTERNS),
        }


# ============================================================
# AUTO-INIT
# ============================================================
try:
    _antibody = AntibodyEngine()
except Exception as e:
    logger.warning("AntibodyEngine init failed: %s", e, exc_info=True)
    logger.debug(f"[WARN] AntibodyEngine init failed: {e}")
    _antibody = None
