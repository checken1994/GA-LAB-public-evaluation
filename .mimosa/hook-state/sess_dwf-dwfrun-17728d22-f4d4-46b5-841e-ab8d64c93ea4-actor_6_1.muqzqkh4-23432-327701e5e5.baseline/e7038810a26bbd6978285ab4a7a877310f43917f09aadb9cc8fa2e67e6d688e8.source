"""
LAYER 1: METAFALSIFIER — "Plan có thiếu kiểu phản bác nào?"

Meta-Falsification — kiểm tra chính VerificationPlan.

WHY Engine tạo plan → MetaFalsifier hỏi:
    "Plan này có thiếu kiểu phản bác nào không?"

VD: Plan cho "giá BTC" chỉ check "≥3 exchanges agree"
→ MetaFalsifier phát hiện thiếu:
    - Temporal check (price at what time?)
    - Exchange location check (US vs Asian exchanges?)
    - Volume-weighted check (low-volume exchange skews?)

Extracted from `meta/cognitive_engine.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetaFalsificationResult:
    """Result từ MetaFalsifier — kiểm tra VerificationPlan."""
    plan_complete: bool
    missing_attack_vectors: list[str]
    suggested_additions: list[str]
    reasoning: str
    revised_plan: dict | None = None


class MetaFalsifier:
    """
    Meta-Falsification — kiểm tra chính VerificationPlan.

    WHY Engine tạo plan → MetaFalsifier hỏi:
        "Plan này có thiếu kiểu phản bác nào không?"

    VD: Plan cho "giá BTC" chỉ check "≥3 exchanges agree"
    → MetaFalsifier phát hiện thiếu:
        - Temporal check (price at what time?)
        - Exchange location check (US vs Asian exchanges?)
        - Volume-weighted check (low-volume exchange skews?)
    """

    # Attack vectors mà mọi plan nên có
    REQUIRED_ATTACK_VECTORS = {
        "numeric_value": [
            "source_agreement",       # ≥N sources agree?
            "temporal_freshness",     # data stale?
            "tolerance_check",        # within tolerance?
        ],
        "string_value": [
            "source_agreement",
            "exact_match",            # exact string vs fuzzy?
            "language_check",         # correct language?
        ],
        "boolean_value": [
            "deterministic_check",    # reproducible?
            "boundary_check",         # edge cases?
        ],
        "entity_fact": [
            "source_agreement",
            "temporal_check",         # still true?
            "authority_check",        # source authoritative?
        ],
        #  Domain-specific attack vectors for V46 domains
        "medical_fact": [
            "source_agreement",
            "medical_guideline_currency",  # hướng dẫn điều trị còn hiệu lực?
            "dosage_range_check",          # liều lượng trong ngưỡng an toàn?
            "authority_check",             # source is medical authority (WHO, FDA)?
        ],
        "legal_fact": [
            "source_agreement",
            "jurisdiction_check",          # luật áp dụng ở đâu (VN/US/EU)?
            "effective_date_check",        # luật còn hiệu lực?
            "authority_check",             # source is government/official?
        ],
        "art_attribution": [
            "source_agreement",
            "attribution_consensus",       # nhiều nguồn cùng công nhận tác giả?
            "period_consistency",          # phong cách khớp thời kỳ?
            "provenance_check",            # lịch sử sở hữu rõ ràng?
        ],
        "sports_record": [
            "source_agreement",
            "temporal_check",              # kỷ lục còn đứng không?
            "official_record_check",       # nguồn là governing body (FIFA, IOC)?
        ],
        "tech_fact": [
            "source_agreement",
            "version_check",               # phiên bản công nghệ còn current?
            "authority_check",             # source is official docs?
        ],
    }

    # [Fix 4-b-008 · Phase 4-A] Domain inference table — derive a domain hint
    # from `evidence_type` (which the WHY engine LLM classifier DOES populate).
    # Previously: the lookup `f"{answer_type}_value"` only worked for the 3
    # generic types (numeric_value / string_value / boolean_value). Domain
    # vectors (medical_fact / legal_fact / art_attribution / sports_record /
    # tech_fact) were DEAD CODE because answer_type ∈ {numeric, string,
    # boolean, temporal} — none of these produce `f"{answer_type}_value"` =
    # "medical_fact" etc. Caller-supplied `domain` attribute on the plan is
    # also honored if present (lets future callers opt into domain vectors
    # directly without changing the WHY-engine classifier output).
    _EVIDENCE_TYPE_TO_DOMAIN: dict[str, str | None] = {
        "real_time_weather_api": None,   # weather — no domain-specific vector
        "real_time_market_data": None,   # crypto/fiat — handled via numeric_value
        "central_bank_rates": None,
        "geographic_database": None,
        "historical_records": None,
        "biographical_records": None,
        "biological_database": "biological",  # not in REQUIRED_ATTACK_VECTORS
        "chemical_database": "chemical",      # not in REQUIRED_ATTACK_VECTORS
        "codata_constants": None,
        "deterministic_calculation": None,
        "deterministic_evaluation": None,
    }

    # [Fix 4-b-008] Keys that map a caller-provided `domain` attribute
    # (e.g. "medical", "legal") to the canonical key in REQUIRED_ATTACK_VECTORS
    # (e.g. "medical_fact", "legal_fact"). This makes the domain vectors
    # reachable: callers can now set `plan.domain = "medical"` (or pass
    # `expected_answer_type = "medical_fact"` directly).
    _DOMAIN_TO_VECTOR_KEY: dict[str, str] = {
        "medical": "medical_fact",
        "medical_fact": "medical_fact",
        "legal": "legal_fact",
        "legal_fact": "legal_fact",
        "art": "art_attribution",
        "art_attribution": "art_attribution",
        "sports": "sports_record",
        "sports_record": "sports_record",
        "tech": "tech_fact",
        "tech_fact": "tech_fact",
        "technology": "tech_fact",
        "entity": "entity_fact",
        "entity_fact": "entity_fact",
    }

    def _resolve_required_vectors(self, answer_type: str, evidence_type: str,
                                  plan) -> list[str]:
        """Resolve the required attack vectors for this plan.

        [Fix 4-b-008] Pre-fix: `self.REQUIRED_ATTACK_VECTORS.get(
        f"{answer_type}_value", default)` — only matched the 3 generic
        keys. Post-fix: try multiple key formats + honor caller-supplied
        `domain` attribute + infer domain from `evidence_type` if possible.
        The domain vectors (medical_fact / legal_fact / art_attribution /
        sports_record / tech_fact) are now REACHABLE — they were dead code
        before (DNA #22 PASS≠TRUE: the falsifier claimed to check medical
        dosage range but never did; DNA #19: observation mechanism couldn't
        see these attack vectors).
        """
        # Step 1: caller-supplied domain hint (highest priority — explicit
        # caller opt-in to domain vectors).
        domain = getattr(plan, "domain", None) or getattr(plan, "domain_hint", None)
        if domain:
            key = self._DOMAIN_TO_VECTOR_KEY.get(str(domain).lower().strip())
            if key and key in self.REQUIRED_ATTACK_VECTORS:
                return list(self.REQUIRED_ATTACK_VECTORS[key])

        # Step 2: try answer_type directly — handles callers that pass
        # the full key (e.g. expected_answer_type="medical_fact").
        if answer_type in self.REQUIRED_ATTACK_VECTORS:
            return list(self.REQUIRED_ATTACK_VECTORS[answer_type])

        # Step 3: try `f"{answer_type}_value"` — original behavior, handles
        # numeric / string / boolean (→ numeric_value / string_value /
        # boolean_value keys).
        key_value = f"{answer_type}_value"
        if key_value in self.REQUIRED_ATTACK_VECTORS:
            return list(self.REQUIRED_ATTACK_VECTORS[key_value])

        # Step 4: try `f"{answer_type}_fact"` — handles callers passing
        # "medical" / "legal" / "tech" (→ medical_fact / legal_fact /
        # tech_fact keys). This was the missing case in the original lookup.
        key_fact = f"{answer_type}_fact"
        if key_fact in self.REQUIRED_ATTACK_VECTORS:
            return list(self.REQUIRED_ATTACK_VECTORS[key_fact])

        # Step 5: try `f"{answer_type}_attribution"` — handles "art".
        key_attr = f"{answer_type}_attribution"
        if key_attr in self.REQUIRED_ATTACK_VECTORS:
            return list(self.REQUIRED_ATTACK_VECTORS[key_attr])

        # Step 6: try `f"{answer_type}_record"` — handles "sports".
        key_rec = f"{answer_type}_record"
        if key_rec in self.REQUIRED_ATTACK_VECTORS:
            return list(self.REQUIRED_ATTACK_VECTORS[key_rec])

        # Step 7: infer from evidence_type as last resort — if the question
        # is about medical/chemical data, escalate to the domain vector.
        inferred = self._EVIDENCE_TYPE_TO_DOMAIN.get(evidence_type)
        if inferred:
            inferred_key = self._DOMAIN_TO_VECTOR_KEY.get(inferred)
            if inferred_key and inferred_key in self.REQUIRED_ATTACK_VECTORS:
                return list(self.REQUIRED_ATTACK_VECTORS[inferred_key])

        # Step 8: fallback to entity_fact (original default behavior).
        return list(self.REQUIRED_ATTACK_VECTORS["entity_fact"])

    def falsify_plan(self, plan) -> MetaFalsificationResult:
        """
        Check if VerificationPlan is missing attack vectors.

        [V37 FIX] Skip irrelevant vectors for deterministic domains.
        Math/logic don't need source_agreement or temporal_freshness.
        """
        missing = []
        suggestions = []

        # Get required vectors for this answer type
        answer_type = getattr(plan, 'expected_answer_type', 'string')
        evidence_type = getattr(plan, 'evidence_type', '')

        # [V37 FIX] For deterministic domains, skip temporal/source checks
        is_deterministic = evidence_type in (
            "deterministic_calculation", "deterministic_evaluation",
            "codata_constants", "biological_database"
        )

        required = self._resolve_required_vectors(answer_type, evidence_type, plan)

        # [V37 FIX] Filter out irrelevant vectors for deterministic
        if is_deterministic:
            required = [v for v in required if v in ("deterministic_check", "boundary_check")]
            if not required:
                required = ["deterministic_check"]  # At least check reproducibility

        # Check plan's proof_criteria + falsification_criteria
        proof = getattr(plan, 'proof_criteria', '').lower()
        falsify = getattr(plan, 'falsification_criteria', '').lower()
        combined = f"{proof} {falsify}"

        for vector in required:
            # Check if vector is covered
            if vector == "source_agreement" and "agree" not in combined and "source" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify ≥2 independent sources agree")
            elif vector == "temporal_freshness" and "time" not in combined and "fresh" not in combined and "stale" not in combined:
                missing.append(vector)
                suggestions.append("Add: check data is not stale (timestamp < TTL)")
            elif vector == "tolerance_check" and "toleran" not in combined and "within" not in combined:
                missing.append(vector)
                suggestions.append("Add: define acceptable tolerance range")
            elif vector == "exact_match" and "exact" not in combined and "match" not in combined:
                missing.append(vector)
                suggestions.append("Add: require exact string match (not fuzzy)")
            elif vector == "language_check" and "language" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify answer language matches question language")
            elif vector == "deterministic_check" and "deterministic" not in combined and "reproduc" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify result is reproducible")
            elif vector == "boundary_check" and "boundary" not in combined and "edge" not in combined:
                missing.append(vector)
                suggestions.append("Add: test boundary/edge cases")
            elif vector == "temporal_check" and "still" not in combined and "current" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify fact is still true (not historical)")
            elif vector == "authority_check" and "authorit" not in combined and "official" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify source is authoritative for this domain")
            # [Fix 4-b-008] Domain-specific vectors (medical / legal / art /
            # sports / tech) are now REACHABLE — the loop must check them
            # or the resolver's work is undone. Pre-fix these branches
            # were dead code (vectors never appeared in `required`).
            elif vector == "medical_guideline_currency" and "guideline" not in combined and "currency" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify medical guideline is current (not superseded)")
            elif vector == "dosage_range_check" and "dosage" not in combined and "dose" not in combined and "range" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify dosage is within safe range (min/max)")
            elif vector == "jurisdiction_check" and "jurisdiction" not in combined and "jurisdic" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify which jurisdiction's law applies (VN/US/EU)")
            elif vector == "effective_date_check" and "effective" not in combined and "in force" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify law is still in force (not repealed)")
            elif vector == "attribution_consensus" and "attribut" not in combined and "consensus" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify multiple sources agree on attribution")
            elif vector == "period_consistency" and "period" not in combined and "style" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify artistic style matches claimed period")
            elif vector == "provenance_check" and "provenance" not in combined and "ownership" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify provenance chain is documented")
            elif vector == "official_record_check" and "official" not in combined and "governing" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify record comes from governing body (FIFA, IOC, etc.)")
            elif vector == "version_check" and "version" not in combined and "current" not in combined:
                missing.append(vector)
                suggestions.append("Add: verify technology version is current (not EOL)")

        plan_complete = len(missing) == 0

        return MetaFalsificationResult(
            plan_complete=plan_complete,
            missing_attack_vectors=missing,
            suggested_additions=suggestions,
            reasoning=f"Plan covers {len(required) - len(missing)}/{len(required)} required attack vectors"
                      + (" — COMPLETE" if plan_complete else f" — MISSING: {missing}"),
        )
