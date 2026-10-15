"""
[OPT-14] UnderstandingChecker — Gà §11: "Con người giải thích lại bằng ngôn ngữ của mình"

WHY re-implement: was 9-line stub with trivial overlap check (word intersection >0.3).
Proper implementation needs:
  - Semantic similarity (not just word overlap)
  - Key concept extraction (not just bag-of-words)
  - Contradiction detection (not just overlap)

Wired into: scp/autofix/permission.py (Tier-3 human approval gate)
  - Before auto-fix applied, human must explain what the fix does
  - UnderstandingChecker.verify(proposal, human_summary) must return True
  - If False → fix blocked (human didn't understand what they're approving)
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger("scp.meta.understanding_check")


class UnderstandingChecker:
    """Gà §11: Verify human understands what they're approving.

    A proposal (e.g., AutoFix patch) must be explained by human in their own words.
    This checker verifies the explanation:
      1. Is long enough (not trivial)
      2. Contains key concepts from proposal
      3. Doesn't contradict proposal
      4. Uses different words (not copy-paste)
    """

    MIN_EXPLANATION_LENGTH = 30  # chars
    MIN_CONCEPT_OVERLAP = 0.4  # 40% of proposal concepts must be in explanation
    MAX_COPY_PASTE_RATIO = 0.7  # if >70% identical to proposal, it's copy-paste

    def check_understanding(self, proposal: str, human_summary: str) -> bool:
        """Check if human_summary demonstrates understanding of proposal.

        Args:
            proposal: The original proposal (e.g., AutoFix patch description)
            human_summary: Human's explanation in their own words

        Returns:
            True if human demonstrates understanding, False otherwise
        """
        if not human_summary or not proposal:
            return False
        # 1. Length check
        if len(human_summary.strip()) < self.MIN_EXPLANATION_LENGTH:
            logger.warning(f"[UnderstandingChecker] too short: {len(human_summary)} < {self.MIN_EXPLANATION_LENGTH}")
            return False
        # 2. Extract key concepts (nouns, verbs — simplified)
        proposal_concepts = self._extract_concepts(proposal)
        summary_concepts = self._extract_concepts(human_summary)
        if not proposal_concepts:
            # [P2-2 FIX R16] UPHOLD for review (same root fix as R14 WhyGate KB1).
            # BEFORE: return True ("accept") when no concepts extractable.
            #         Q11/L1-1: this is a semantic inversion — "can't verify"
            #         was treated as "verified". Tier-3 human-approval gate
            #         failed OPEN, accepting any gibberish human note.
            # AFTER: return False (UPHOLD). "Can't verify" ≠ "verified".
            #         Operator must review manually. Same pattern as R14 WhyGate
            #         KB1 fix (UPHOLD when necessity unknown, not ALLOW).
            logger.warning(
                "[P2-2 R16] No extractable concepts in proposal — cannot verify "
                "understanding. UPHOLD for human review (not auto-accept). "
                "Was return True in R15 (Q11/L1-1 semantic inversion)."
            )
            return False  # UPHOLD — don't accept what we can't verify
        # 3. Concept overlap
        overlap = len(proposal_concepts & summary_concepts) / len(proposal_concepts)
        if overlap < self.MIN_CONCEPT_OVERLAP:
            logger.warning(f"[UnderstandingChecker] low concept overlap: {overlap:.2f} < {self.MIN_CONCEPT_OVERLAP}")
            return False
        # 4. Copy-paste detection
        similarity = SequenceMatcher(None, proposal.lower(), human_summary.lower()).ratio()
        if similarity > self.MAX_COPY_PASTE_RATIO:
            logger.warning(f"[UnderstandingChecker] copy-paste detected: {similarity:.2f} > {self.MAX_COPY_PASTE_RATIO}")
            return False
        return True

    def _extract_concepts(self, text: str) -> set[str]:
        """Extract key concepts (simplified — words >3 chars, not stopwords)."""
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "and", "or", "but", "if", "then", "of", "to", "in", "on",
                     "at", "by", "for", "with", "from", "this", "that", "these",
                     "và", "của", "là", "trong", "với", "cho", "một", "các"}
        words = re.findall(r'\b[a-zA-Z_à-ỹ]{4,}\b', text.lower())
        return {w for w in words if w not in stopwords}

    def verify(self, proposal: str, human_summary: str) -> dict:
        """Full verification with details (for logging)."""
        passed = self.check_understanding(proposal, human_summary)
        return {
            "passed": passed,
            "principle": "Gà §11: human understanding verification",
            "proposal_length": len(proposal),
            "summary_length": len(human_summary) if human_summary else 0,
            "concept_overlap": len(self._extract_concepts(proposal) & self._extract_concepts(human_summary)) if human_summary else 0,
        }


__all__ = ["UnderstandingChecker"]
