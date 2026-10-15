import pytest

from scp.risk_intelligence import (
    AlertRouter,
    ContainmentCoordinator,
    EmergencyEvidenceBundle,
    IncidentState,
    IncidentStateMachine,
    RiskClassifier,
    RiskLevel,
    RiskSignal,
)
from scp.risk_intelligence.alert_router import FORBIDDEN_BROADCAST_OPERATIONS


def _signal(kind="social", lineage=None, fresh=True, located=False, direct=False, sid="s"):
    return RiskSignal(source_id=sid, kind=kind, lineage_id=lineage, fresh=fresh,
                      location_validated=located, observed_directly=direct)


def test_social_volume_alone_never_produces_pr4_or_pr5():
    classifier = RiskClassifier()
    signals = [_signal("social", lineage="lineage-1", sid=f"s{i}") for i in range(1000)]
    assessment = classifier.classify(signals, desired_level=RiskLevel.PR5)
    assert assessment.level not in (RiskLevel.PR4, RiskLevel.PR5)
    assert assessment.pending_verification is True
    assert assessment.independent_lineages <= 1


def test_official_source_qualifies_pr4():
    classifier = RiskClassifier()
    signals = [_signal("official", lineage="lineage-official", fresh=True, located=True, sid="official-1"), _signal("social", lineage="lineage-1", sid="s1"), _signal("social", lineage="lineage-1", sid="s2")]
    assessment = classifier.classify(signals, desired_level=RiskLevel.PR4)
    assert assessment.level == RiskLevel.PR4
    assert assessment.pending_verification is False


def test_two_independent_lineages_qualified_but_pr5_needs_official_confirmation():
    classifier = RiskClassifier()
    signals = [_signal("independent", lineage="lineage-A", fresh=True, located=True, sid="a"), _signal("independent", lineage="lineage-B", fresh=True, located=True, sid="b")]
    assessment = classifier.classify(signals, desired_level=RiskLevel.PR5)
    assert assessment.level == RiskLevel.PR4
    assert assessment.independent_lineages == 2


def test_stale_or_unlocated_evidence_caps_level_at_pr3():
    assessment = RiskClassifier().classify([_signal("official", lineage="lineage-official", fresh=False, located=True, sid="o1")], desired_level=RiskLevel.PR4)
    assert assessment.level in (RiskLevel.PR1, RiskLevel.PR2, RiskLevel.PR3)
    assert any("stale" in reason or "location" in reason for reason in assessment.reasons)


def test_owned_sensor_direct_observation_is_the_missing_source_exception():
    assessment = RiskClassifier().classify([_signal("owned_sensor", fresh=True, located=True, direct=True, sid="sensor-1")], desired_level=RiskLevel.PR4)
    assert assessment.level == RiskLevel.PR4


def test_emergency_evidence_bundle_requires_and_carries_the_owner_contract():
    bundle = EmergencyEvidenceBundle(incident_id="WATER-20260903-001", risk_type="WATER_CONTAMINATION", level="PR4", location="District A", claims=("water anomaly reported",), independent_lineages=3, contradictions=("old municipal page says normal",), unknowns=("source of contamination",), confidence=0.9, recommended_actions=("urgent human verification",), source_hashes=("sha256:abc",), official_confirmation=False)
    payload = bundle.to_dict()
    for field in ("incident_id", "risk_type", "independent_lineages", "contradictions", "unknowns", "official_confirmation", "recommended_actions"):
        assert field in payload
    with pytest.raises(ValueError):
        EmergencyEvidenceBundle(incident_id="", risk_type="X", level="PR4")
    with pytest.raises(ValueError):
        EmergencyEvidenceBundle(incident_id="I", risk_type="X", level="PR4", confidence=1.5)


def test_alert_router_never_sends_without_configuration_or_authority():
    bundle = EmergencyEvidenceBundle(incident_id="I-1", risk_type="CYBER", level="PR4")
    result = AlertRouter(channels={}).route(bundle)
    assert result["decision"] == "BUNDLE_ONLY" and result["deliveries"] == []
    result = AlertRouter(channels={"SOC": {"configured": True, "requires_approval": True}}).route(bundle)
    assert result["decision"] == "WAITING_APPROVAL" and result["deliveries"] == []
    result = AlertRouter(channels={"SOC": {"configured": True, "requires_approval": False, "pre_authorized": True}}).route(bundle)
    assert result["decision"] == "SUBMITTED"
    assert result["deliveries"][0]["kind"] == "bounded_incident_report"


def test_public_broadcast_operations_are_forbidden_even_on_pre_authorized_channels():
    router = AlertRouter(channels={"SOC": {"configured": True, "requires_approval": False, "pre_authorized": True}})
    bundle = EmergencyEvidenceBundle(incident_id="I-1", risk_type="CYBER", level="PR5")
    for operation in FORBIDDEN_BROADCAST_OPERATIONS:
        result = router.route(bundle, requested_operation=operation)
        assert result["decision"] == "DENY_FORBIDDEN_OPERATION"
        assert result["deliveries"] == []


def test_incident_state_machine_walks_and_refuses_illegal_jumps():
    machine = IncidentStateMachine("INC-1")
    for state in ("SUSPECTED", "CORROBORATING", "CONFIRMED", "CONTAINING", "ESCALATED", "MONITORING", "RESOLVED"):
        machine.transition(state)
    assert machine.state is IncidentState.RESOLVED
    fp = IncidentStateMachine("INC-2")
    fp.transition("SUSPECTED")
    fp.transition("CONTRADICTED")
    fp.transition("CLOSED_FALSE_POSITIVE")
    assert fp.state is IncidentState.CLOSED_FALSE_POSITIVE
    blocked = IncidentStateMachine("INC-3")
    with pytest.raises(ValueError):
        blocked.transition("CONFIRMED")


def test_containment_requires_capability_authority_not_direct_tool_call(tmp_path):
    from scp.security.capability_epoch import (
        CapabilityAuthority,
        CapabilityRevokedError,
    )

    classifier = RiskClassifier()
    router = AlertRouter(channels={})
    for forbidden_method in ("execute_tool", "run_action", "kill_process", "direct_containment"):
        assert not hasattr(classifier, forbidden_method)
        assert not hasattr(router, forbidden_method)

    bundle = EmergencyEvidenceBundle(incident_id="SEC-20260903-099", risk_type="DATA_EXFILTRATION_ATTEMPT", level="PR4", recommended_actions=("isolate_network_egress",), confidence=0.95)
    cap_auth = CapabilityAuthority(tmp_path / "capability_state.json")
    token = cap_auth.issue(subject="worker-egress")
    coordinator = ContainmentCoordinator(cap_auth)

    with pytest.raises(PermissionError):
        coordinator.contain(bundle, owned_scope=False)
    assert cap_auth.validate(token) is True

    result = coordinator.contain(bundle, owned_scope=True, actor="governance_authority")
    assert result["decision"] == "CAPABILITY_REVOKED"
    assert result["authority"] == "CapabilityAuthority"
    assert result["action"] == "isolate_network_egress"
    assert cap_auth.validate(token) is False
    with pytest.raises(CapabilityRevokedError):
        cap_auth.issue(subject="worker-egress")


def test_emergency_evidence_bundle_lineage_preservation_across_routing():
    router = AlertRouter(channels={"SOC": {"configured": True, "requires_approval": True}})
    bundle = EmergencyEvidenceBundle(incident_id="ENV-20260903-007", risk_type="CYBER", level="PR4", location="Server Room B", claims=("credential anomaly detected", "unusual outbound sweep"), independent_lineages=2, contradictions=("old audit log claimed access authorized",), unknowns=("scope of affected machines",), confidence=0.92, source_hashes=("sha256:sensor_feed_alpha", "sha256:sentinel_orbit_beta"), official_confirmation=False)
    routed = router.route(bundle)
    assert routed["decision"] == "WAITING_APPROVAL"
    assert routed["target"] == "SOC"
    assert routed["bundle_id"] == bundle.bundle_id
    assert routed["deliveries"] == []
    payload = bundle.to_dict()
    assert payload["source_hashes"] == ["sha256:sensor_feed_alpha", "sha256:sentinel_orbit_beta"]
    assert payload["independent_lineages"] == 2
    assert payload["contradictions"] == ["old audit log claimed access authorized"]
    assert payload["unknowns"] == ["scope of affected machines"]
    assert payload["location"] == "Server Room B"
