import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')


from scp.audit_engine.gate import PromotionGate
from scp.audit_engine.models import (
    AuditChallenge,
    EvidenceBundle,
    EvidenceRecord,
    OracleVerdict,
)


def test_audit_engine_isolated_flow():
    """FA-13: Cover audit_engine flow with genuine behavioral execution.

    Verifies fail-closed rejection for empty bundles, tamper detection, and
    multi-record requirement before promotion.
    """
    gate = PromotionGate()

    # Empty records -> fail-closed rejection
    bundle_empty = EvidenceBundle(
        bundle_id="b-empty",
        challenge=AuditChallenge(challenge_id="c-1", required_profile="std", target_contract_hash="hash1"),
        records=[],
    )
    decision = gate.evaluate_bundle(bundle_empty)
    assert not decision.promoted
    assert "No evidence records" in decision.reason

    # Single record -> fail-closed (multiple verifications required)
    bundle_single = EvidenceBundle(
        bundle_id="b-single",
        challenge=AuditChallenge(challenge_id="c-2", required_profile="std", target_contract_hash="hash2"),
        records=[
            EvidenceRecord(record_id="r-1", verdict=OracleVerdict.NOT_FALSIFIED, challenge_id="c-2", observer_coverage_hash="cov1"),
        ],
    )
    decision_single = gate.evaluate_bundle(bundle_single)
    assert not decision_single.promoted
    assert "Cannot promote from a single record" in decision_single.reason

    # Valid multi-record bundle -> promoted
    bundle_valid = EvidenceBundle(
        bundle_id="b-valid",
        challenge=AuditChallenge(challenge_id="c-3", required_profile="std", target_contract_hash="hash3"),
        records=[
            EvidenceRecord(record_id="r-1", verdict=OracleVerdict.NOT_FALSIFIED, challenge_id="c-3", observer_coverage_hash="cov1"),
            EvidenceRecord(record_id="r-2", verdict=OracleVerdict.NOT_FALSIFIED, challenge_id="c-3", observer_coverage_hash="cov2"),
        ],
    )
    decision_valid = gate.evaluate_bundle(bundle_valid)
    assert decision_valid.promoted
    assert decision_valid.bundle_id == "b-valid"

    # Tampered gate -> fail-closed
    gate.tamper()
    decision_tampered = gate.evaluate_bundle(bundle_valid)
    assert not decision_tampered.promoted
    assert "Gate is contaminated" in decision_tampered.reason
