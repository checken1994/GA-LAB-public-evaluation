"""
SCP V100 — Claim Extractor + Claim Verifier
=============================================
Trích xuất claims từ answer + verify từng claim against ground truth.

Claim Extraction:
  "Bitcoin giá 62000 USD hôm nay" →
    Claim(entity="bitcoin_price", value=62000, unit="USD", claim_type="numeric")
  "Hà Nội là thủ đô Việt Nam" →
    Claim(entity="hanoi", relation="capital_of", target="vietnam", claim_type="factual")
  "Nghiên cứu của Harvard 2023 chỉ ra..." →
    Claim(entity="harvard_research_2023", claim_type="citation", source="harvard")

Claim Verification:
  - Numeric claims → measure deviation vs ground truth
  - Citation claims → verify DOI/URL exists
  - Entity claims → verify against Wikidata/Wikipedia
  - Date claims → verify plausibility
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger("scp.knowledge.claims")


@dataclass
class Claim:
    """1 factual claim extracted from answer."""
    claim_id: str
    claim_type: str  # numeric | citation | entity | date | url | boolean
    text: str        # original text snippet
    entity: str = ""
    value: float | None = None
    unit: str = ""
    relation: str = ""    # for entity claims (capital_of, founded_in, ...)
    target: str = ""
    source_ref: str = ""  # DOI, URL, reference
    confidence: float = 0.5
    verified: bool | None = None
    verification_detail: str = ""
    evidence_ref: str = ""  #  which evidence piece verified this claim

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "text": self.text[:200],
            "entity": self.entity,
            "value": self.value,
            "unit": self.unit,
            "relation": self.relation,
            "target": self.target,
            "source_ref": self.source_ref,
            "confidence": self.confidence,
            "verified": self.verified,
            "verification_detail": self.verification_detail,
            "evidence_ref": self.evidence_ref,  #
        }


# ============================================================
# CLAIM EXTRACTOR
# ============================================================

# Vietnamese + English numeric patterns
_NUM_UNIT_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*"
    r"(tỷ|tỉ|ty|triệu|tr|nghìn|ngàn|nghin|ngan|billion|million|thousand|k|m|b|USD|VND|EUR|°C|°F|km|m|kg|%|percent)?",
    re.IGNORECASE,
)

_UNIT_MULTIPLIERS = {
    "tỷ": 1e9, "tỉ": 1e9, "ty": 1e9, "triệu": 1e6, "tr": 1e6,
    "nghìn": 1e3, "ngàn": 1e3, "nghin": 1e3, "ngan": 1e3,
    "billion": 1e9, "million": 1e6, "thousand": 1e3,
    "k": 1e3, "m": 1e6, "b": 1e9,
}

# URL pattern
_URL_RE = re.compile(r"https?://[^\s<>\"]+[^\s<>.]")

# DOI pattern
_DOI_RE = re.compile(r"10\.\d{4,}/[^\s]+")

# Date patterns
_DATE_RE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|năm\s+\d{4}|year\s+\d{4}|in\s+\d{4})\b",
    re.IGNORECASE,
)

# Citation patterns
_CITATION_RE = re.compile(
    r"(?:according\s+to|nghiên\s+cứu\s+của|theo|source:|reference:)\s+([A-Z][a-zA-Z\s]+?)(?:\s+\d{4})?",
    re.IGNORECASE,
)


class ClaimExtractor:
    """Extract factual claims from answer text.

    Naming convention: <Purpose>Extractor (world standard).
    """

    def extract(self, answer: str, question: str = "") -> list[Claim]:
        """Extract all claims from answer.

        Args:
            answer: Answer text to extract claims from
            question: Original question (for context)

        Returns:
            List of Claim objects
        """
        claims: list[Claim] = []
        claim_counter = 0

        # 1. Extract numeric claims
        for m in _NUM_UNIT_RE.finditer(answer):
            raw_num = m.group(1)
            unit = (m.group(2) or "").lower()
            try:
                # [V104.35 #52] TẠI SAO: "1,5" (Vietnamese decimal) → first try
                # replace(",","") gives "15" → float("15")=15.0 (SUCCESS, no ValueError)
                # → fallback (correct "1.5") never runs. Fix: detect delimiter convention.
                # If only "," and no "." → treat "," as decimal separator (Vietnamese/European)
                if "," in raw_num and "." not in raw_num:
                    # Vietnamese/European decimal: "1,5" → 1.5
                    value = float(raw_num.replace(",", "."))
                elif "," in raw_num and "." in raw_num:
                    # European thousands: "1.234,56" → 1234.56
                    value = float(raw_num.replace(".", "").replace(",", "."))
                else:
                    value = float(raw_num)
            except ValueError:
                logger.debug('ClaimExtractor.extract: ValueError ignored', exc_info=True)
                continue

            if unit in _UNIT_MULTIPLIERS:
                value *= _UNIT_MULTIPLIERS[unit]

            claim_counter += 1
            claims.append(Claim(
                claim_id=f"claim_{claim_counter:03d}",
                claim_type="numeric",
                text=m.group(0),
                value=value,
                unit=unit,
                confidence=0.7,
            ))

        # 2. Extract URL claims
        for m in _URL_RE.finditer(answer):
            claim_counter += 1
            claims.append(Claim(
                claim_id=f"claim_{claim_counter:03d}",
                claim_type="url",
                text=m.group(0),
                source_ref=m.group(0),
                confidence=0.6,
            ))

        # 3. Extract DOI claims
        for m in _DOI_RE.finditer(answer):
            claim_counter += 1
            claims.append(Claim(
                claim_id=f"claim_{claim_counter:03d}",
                claim_type="citation",
                text=m.group(0),
                source_ref=m.group(0),
                confidence=0.8,
            ))

        # 4. Extract date claims
        for m in _DATE_RE.finditer(answer):
            claim_counter += 1
            year_match = re.search(r"\d{4}", m.group(0))
            year = int(year_match.group(0)) if year_match else None
            claims.append(Claim(
                claim_id=f"claim_{claim_counter:03d}",
                claim_type="date",
                text=m.group(0),
                value=float(year) if year else None,
                unit="year",
                confidence=0.6,
            ))

        # 5. Extract citation references
        for m in _CITATION_RE.finditer(answer):
            claim_counter += 1
            claims.append(Claim(
                claim_id=f"claim_{claim_counter:03d}",
                claim_type="citation",
                text=m.group(0),
                entity=m.group(1).strip(),
                confidence=0.5,
            ))

        # 6. Extract entity claims (simple: "X là Y" / "X is Y")
        entity_patterns = [
            (r"(\w[\w\s]+?)\s+(?:là|is|are)\s+(?:thủ\s+đô\s+của|capital\s+of)\s+(\w[\w\s]+)", "capital_of"),
            (r"(?:thủ\s+đô\s+của|capital\s+of)\s+(\w[\w\s]+?)\s+(?:là|is|are)\s+(\w[\w\s]+)", "capital_of"),
            (r"(\w[\w\s]+?)\s+(?:được\s+thành\s+lập|was\s+founded|was\s+established)", "founded"),
            (r"(\w[\w\s]+?)\s+(?:thuộc|belongs?\s+to|is\s+in)\s+(\w[\w\s]+)", "part_of"),
            (r"(\w[\w\s]+?)\s+(?:có\s+diện\s+tích|has\s+an\s+area\s+of)\s+([^,.;]+)", "area"),
            (r"(\w[\w\s]+?)\s+(?:sôi\s+ở|boils\s+at)\s+([^,.;]+)", "property"),
        ]
        for pattern, relation in entity_patterns:
            for m in re.finditer(pattern, answer, re.IGNORECASE):
                claim_counter += 1
                claims.append(Claim(
                    claim_id=f"claim_{claim_counter:03d}",
                    claim_type="entity",
                    text=m.group(0),
                    entity=m.group(1).strip(),
                    relation=relation,
                    target=m.group(2).strip() if (m.lastindex is not None and m.lastindex >= 2) else "",
                    confidence=0.5,
                ))

        logger.debug(f"[ClaimExtractor] Extracted {len(claims)} claims from answer")
        return claims


# ============================================================
# CLAIM VERIFIER
# ============================================================

class ClaimVerifier:
    """Verify each claim against ground truth.

    Naming convention: <Purpose>Verifier (world standard).
    """

    # Severity thresholds (relative deviation)
    SEVERITY_LOW = 0.02
    SEVERITY_MEDIUM = 0.10
    SEVERITY_HIGH = 0.25

    def verify(
        self,
        claims: list[Claim],
        ground_truth: dict[str, Any],
        falsification_engine=None,
    ) -> list[Claim]:
        """Verify each claim against ground truth.

        Args:
            claims: List of Claim objects from ClaimExtractor
            ground_truth: Dict of {field: value} from DataSource
            falsification_engine: Optional FalsificationEngine for deviation measurement

        Returns:
            Same list of claims with verified + verification_detail set
        """
        for claim in claims:
            if claim.claim_type == "numeric" and claim.value is not None:
                claim = self._verify_numeric(claim, ground_truth)
            elif claim.claim_type == "url":
                claim = self._verify_url(claim)
            elif claim.claim_type == "date":
                claim = self._verify_date(claim, ground_truth)
            elif claim.claim_type == "citation":
                claim = self._verify_citation(claim)
            elif claim.claim_type == "entity":
                claim = self._verify_entity(claim, ground_truth)
            else:
                claim.verified = None  # cannot verify
                claim.verification_detail = "no verifier for this claim type"

        return claims

    def _verify_numeric(self, claim: Claim, ground_truth: dict[str, Any]) -> Claim:
        """Verify numeric claim against ground truth."""
        # Try to find matching field in ground truth
        best_delta = float("inf")
        best_field = ""
        best_ref = None

        for field_name, ref_value in ground_truth.items():
            ref_num = self._to_float(ref_value)
            if ref_num is None:
                continue
            if claim.value is None:
                continue
            if ref_num == 0:
                delta = abs(claim.value)
            else:
                delta = abs(claim.value - ref_num) / abs(ref_num)
            if delta < best_delta:
                best_delta = delta
                best_field = field_name
                best_ref = ref_num

        if best_ref is None:
            claim.verified = None
            claim.verification_detail = "no numeric ground truth available"
            return claim

        if best_delta < self.SEVERITY_LOW:
            claim.verified = True
            claim.verification_detail = f"matches {best_field} (delta={best_delta:.4f})"
        elif best_delta < self.SEVERITY_MEDIUM:
            claim.verified = True
            claim.verification_detail = f"close to {best_field} (delta={best_delta:.4f})"
        elif best_delta < self.SEVERITY_HIGH:
            claim.verified = False
            claim.verification_detail = f"deviation from {best_field} (delta={best_delta:.4f})"
        else:
            claim.verified = False
            claim.verification_detail = f"contradicts {best_field} (delta={best_delta:.4f})"

        return claim

    def _verify_url(self, claim: Claim) -> Claim:
        """Verify URL claim — check format (can't check live without HTTP)."""
        url = claim.source_ref
        if not url:
            claim.verified = False
            claim.verification_detail = "empty URL"
            return claim
        # Basic format check
        if url.startswith(("http://", "https://")) and "." in url:
            claim.verified = None  # format OK but can't verify without HTTP
            claim.verification_detail = "URL format valid — live check requires HTTP"
        else:
            claim.verified = False
            claim.verification_detail = "malformed URL"
        return claim

    def _verify_date(self, claim: Claim, ground_truth: dict[str, Any]) -> Claim:
        """Verify date claim — check plausibility."""
        if claim.value is None:
            claim.verified = None
            return claim
        year = int(claim.value)
        current_year = datetime.now().year  # [V104.34 #54] TẠI SAO: hardcoded 2026 → breaks in 2027+
        if year < 1 or year > current_year + 5:
            claim.verified = False
            claim.verification_detail = f"year {year} out of plausible range"
        elif year > current_year:
            claim.verified = False
            claim.verification_detail = f"year {year} is in the future"
        else:
            claim.verified = None
            claim.verification_detail = f"year {year} plausible"
        return claim

    def _verify_citation(self, claim: Claim) -> Claim:
        """Verify citation claim — check DOI format."""
        if claim.source_ref and claim.source_ref.startswith("10."):
            # DOI format check
            if re.match(r"10\.\d{4,}/[^\s]+", claim.source_ref):
                claim.verified = None
                claim.verification_detail = "DOI format valid — live check requires CrossRef API"
            else:
                claim.verified = False
                claim.verification_detail = "malformed DOI"
        else:
            claim.verified = None
            claim.verification_detail = "citation reference — needs external verification"
        return claim

    def _verify_entity(self, claim: Claim, ground_truth: dict[str, Any]) -> Claim:
        """Verify entity claim against ground truth."""
        if not claim.entity or not claim.target:
            claim.verified = None
            claim.verification_detail = "incomplete entity claim"
            return claim

        # [V104.35 #49] TẠI SAO: str(ground_truth).lower() produces "{'city': 'hanoi'}"
        # → substring match catches any sub-word. Short entity "an" matches "hanoi".
        # Fix: if ground_truth is a dict, match against its VALUES (not stringified dict).
        if isinstance(ground_truth, dict):
            gt_values = [str(v).lower() for v in ground_truth.values()]
            entity_found = any(claim.entity.lower() in v for v in gt_values if len(claim.entity) >= 3)
            target_found = any(claim.target.lower() in v for v in gt_values if len(claim.target) >= 3)
            # For short entity/target, require exact match against a value
            if len(claim.entity) < 3:
                entity_found = any(claim.entity.lower() == v for v in gt_values)
            if len(claim.target) < 3:
                target_found = any(claim.target.lower() == v for v in gt_values)
        else:
            gt_str = str(ground_truth).lower()
            entity_found = claim.entity.lower() in gt_str
            target_found = claim.target.lower() in gt_str

        if entity_found and target_found:
            claim.verified = True
            claim.verification_detail = f"{claim.entity} + {claim.target} found in ground truth"
        elif entity_found:
            claim.verified = None
            claim.verification_detail = f"{claim.entity} found but {claim.target} not in ground truth"
        else:
            claim.verified = None
            claim.verification_detail = "entity not in ground truth"
        return claim

    @staticmethod
    def _to_float(value: Any) -> float | None:
        """Convert any value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "").replace(" ", ""))
            except ValueError as e:
                logger.warning(f"Silent except: {e}")
        return None

    def summarize(self, claims: list[Claim]) -> dict[str, Any]:
        """Summarize verification results.

         Added 'unverified' alias for 'unknown' — used by judgecore_mixin
        governance logic (UPHOLD if >50% claims unverified).
        """
        total = len(claims)
        verified = sum(1 for c in claims if c.verified is True)
        refuted = sum(1 for c in claims if c.verified is False)
        unknown = sum(1 for c in claims if c.verified is None)
        return {
            "total_claims": total,
            "verified": verified,
            "refuted": refuted,
            "unknown": unknown,
            "unverified": unknown,  #  alias — "unknown" = "unverified"
            "verification_rate": round(verified / total, 2) if total > 0 else 0,
            "refutation_rate": round(refuted / total, 2) if total > 0 else 0,
            "details": [c.to_dict() for c in claims],
        }


__all__ = ["Claim", "ClaimExtractor", "ClaimVerifier"]
