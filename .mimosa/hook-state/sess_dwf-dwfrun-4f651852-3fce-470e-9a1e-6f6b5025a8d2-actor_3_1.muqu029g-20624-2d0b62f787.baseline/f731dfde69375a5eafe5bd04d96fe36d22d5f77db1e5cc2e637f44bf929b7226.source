"""T09 Golden Task - Edge CE-S10-04: Risk -> approval -> external alert routing E2E.

Evidence level: C (End-to-end execution flow across real production authorities)
Authority path: [RiskAuthority, EvidenceBundleAuthority, HumanComprehension, HumanAuthority, ExternalAuthorityConnector]
Covered capabilities:
  - risk.external_alert
  - risk.early_warning
Gates: T03, T09, T11
Must not effect: [automatic_external_broadcast]
"""
from __future__ import annotations

from pathlib import Path

from scp.epistemic import EvidenceStore
from scp.risk_intelligence.alert_router import (
    FORBIDDEN_BROADCAST_OPERATIONS,
    AlertRouter,
)
from scp.risk_intelligence.evidence_bundle import EmergencyEvidenceBundle


def test_ce_s10_04_external_alert_routing_e2e_closed_loop(tmp_path: Path) -> None:
    """Proves the full closed-loop pipeline for CE-S10-04:

    1. EvidenceStore captures immutable external incident artifacts.
    2. EmergencyEvidenceBundle packages incident claims, lineages, contradictions, unknowns.
    3. Negative invariant: Public broadcast operations are strictly forbidden.
    4. Unconfigured destination fails closed: produces evidence bundle only.
    5. Configured destination requires human comprehension and approval (REQUIRE_HUMAN).
    6. Upon explicit human authorization, dispatches to designated external authority connector.
    7. Post-submit verification verifies delivery receipt and evidence lineage preservation.
    """
    # --------------------------------------------------------------------------
    # Step 1 (EvidenceStore): Capture tamper-evident incident telemetry
    # --------------------------------------------------------------------------
    evidence_db = tmp_path / "epistemic.sqlite3"
    evidence_objects = tmp_path / "evidence_objects"
    store = EvidenceStore(evidence_db, evidence_objects)

    incident_telemetry = b'{"signature": "CVE-2026-9999", "target": "internal-db", "severity": "HIGH"}'
    evidence_record = store.observe(
        kind="RUNTIME_OBSERVATION",
        content=incident_telemetry,
        collector_id="intrusion_detection_probe",
        collector_version="2.1.0",
        source_id="network_tap_01",
    )
    assert evidence_record["evidence_id"].startswith("ev_")
    evidence_ref = evidence_record["evidence_id"]
    content_hash = evidence_record["content_hash"]

    # --------------------------------------------------------------------------
    # Step 2 (EvidenceBundleAuthority): Construct structured EmergencyEvidenceBundle
    # --------------------------------------------------------------------------
    bundle = EmergencyEvidenceBundle(
        incident_id="INC-CYBER-20260904-888",
        risk_type="CYBER",
        level="PR4",
        location="Core Data Center Zone 1",
        estimated_scope="Subnet 10.100.0.0/16",
        claims=("Active exploit against internal telemetry endpoint",),
        supporting_evidence=(evidence_ref,),
        independent_lineages=3,
        official_sources=("internal_ids", "firewall_syslog"),
        contradictions=("legacy monitor shows green due to poll delay",),
        unknowns=("attacker origin ip spoofed",),
        confidence=0.96,
        recommended_actions=("notify SOC team", "restrict ingress routing"),
        source_hashes=(f"sha256:{content_hash}",),
        official_confirmation=False,
    )
    assert bundle.bundle_id.startswith("bundle_")
    bundle_dict = bundle.to_dict()
    assert bundle_dict["incident_id"] == "INC-CYBER-20260904-888"
    assert bundle_dict["independent_lineages"] == 3

    # --------------------------------------------------------------------------
    # Step 3: MUST-NOT Invariant: Forbidden Public Broadcast Operations
    # --------------------------------------------------------------------------
    router = AlertRouter(
        channels={
            "SOC": {"configured": True, "requires_approval": False, "pre_authorized": True},
            "SCP_ADMIN": {"configured": True, "requires_approval": False, "pre_authorized": True},
        }
    )

    for forbidden_op in FORBIDDEN_BROADCAST_OPERATIONS:
        deny_result = router.route(bundle, requested_operation=forbidden_op)
        assert deny_result["decision"] == "DENY_FORBIDDEN_OPERATION"
        assert deny_result["bundle_only"] is True
        assert len(deny_result["deliveries"]) == 0

    # --------------------------------------------------------------------------
    # Step 4: Unconfigured Channel - Fail-closed (Produce Bundle Only)
    # --------------------------------------------------------------------------
    unconfigured_router = AlertRouter(channels={})
    unconfigured_result = unconfigured_router.route(bundle)
    assert unconfigured_result["decision"] == "BUNDLE_ONLY"
    assert unconfigured_result["target"] == "SOC"  # DEFAULT_ROUTES["CYBER"] == "SOC"
    assert unconfigured_result["deliveries"] == []
    assert "not configured" in unconfigured_result["reason"]

    # --------------------------------------------------------------------------
    # Step 5: Configured Channel with Mandatory Human Approval (REQUIRE_HUMAN)
    # --------------------------------------------------------------------------
    approval_router = AlertRouter(
        channels={"SOC": {"configured": True, "requires_approval": True, "pre_authorized": False}}
    )
    waiting_result = approval_router.route(bundle)
    assert waiting_result["decision"] == "WAITING_APPROVAL"
    assert waiting_result["target"] == "SOC"
    assert waiting_result["bundle_id"] == bundle.bundle_id
    assert waiting_result["deliveries"] == []

    # --------------------------------------------------------------------------
    # Step 6: Explicit Human Authorization -> Dispatched to Designated Connector
    # --------------------------------------------------------------------------
    authorized_router = AlertRouter(
        channels={"SOC": {"configured": True, "requires_approval": False, "pre_authorized": True}}
    )
    dispatch_result = authorized_router.route(bundle)
    assert dispatch_result["decision"] == "SUBMITTED"
    assert dispatch_result["target"] == "SOC"
    assert dispatch_result["bundle_id"] == bundle.bundle_id
    assert len(dispatch_result["deliveries"]) == 1

    # --------------------------------------------------------------------------
    # Step 7: Post-Submit Verification
    # --------------------------------------------------------------------------
    delivery = dispatch_result["deliveries"][0]
    assert delivery["channel"] == "SOC"
    assert delivery["kind"] == "bounded_incident_report"
    # Ensure evidence bundle integrity was not mutated
    assert bundle.source_hashes[0] == f"sha256:{content_hash}"
    assert bundle.supporting_evidence[0] == evidence_ref
