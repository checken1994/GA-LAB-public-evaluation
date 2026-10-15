from .models import EvidenceBundle, OracleVerdict, PromotionDecision


class PromotionGate:
    """
    Evaluates EvidenceBundle according to a challenge-required profile.
    Does not promote from a single record.
    """
    def __init__(self):
        self._tampered = False

    def tamper(self) -> None:
        """Simulate tampering with the gate for mutation testing."""
        self._tampered = True

    def evaluate_bundle(self, bundle: EvidenceBundle) -> PromotionDecision:
        if self._tampered:
            return PromotionDecision(
                promoted=False,
                reason="Gate is contaminated (Fail-closed).",
                bundle_id=bundle.bundle_id
            )

        if not bundle.records:
            return PromotionDecision(
                promoted=False,
                reason="No evidence records in bundle.",
                bundle_id=bundle.bundle_id
            )

        if len(bundle.records) < 2:
            return PromotionDecision(
                promoted=False,
                reason="Cannot promote from a single record. Multiple verifications required.",
                bundle_id=bundle.bundle_id
            )

        if not bundle.challenge.required_profile:
            return PromotionDecision(
                promoted=False,
                reason="Challenge missing required profile.",
                bundle_id=bundle.bundle_id
            )

        for record in bundle.records:
            if record.challenge_id != bundle.challenge.challenge_id:
                return PromotionDecision(
                    promoted=False,
                    reason=f"Record {record.record_id} does not belong to challenge {bundle.challenge.challenge_id}",
                    bundle_id=bundle.bundle_id
                )
            if record.verdict != OracleVerdict.NOT_FALSIFIED:
                return PromotionDecision(
                    promoted=False,
                    reason=f"Bundle contains non-NOT_FALSIFIED verdict: {record.verdict.name}",
                    bundle_id=bundle.bundle_id
                )
            if not record.observer_coverage_hash:
                return PromotionDecision(
                    promoted=False,
                    reason="Missing observer coverage.",
                    bundle_id=bundle.bundle_id
                )

        return PromotionDecision(
            promoted=True,
            reason="Bundle meets challenge profile and has multiple NOT_FALSIFIED records.",
            bundle_id=bundle.bundle_id
        )
