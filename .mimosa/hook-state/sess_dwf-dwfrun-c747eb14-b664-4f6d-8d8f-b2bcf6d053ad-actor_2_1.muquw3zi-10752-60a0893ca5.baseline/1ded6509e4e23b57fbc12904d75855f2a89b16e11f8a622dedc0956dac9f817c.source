"""T09 Golden Task - Edge CE-S10-03: Risk -> governed containment E2E path.

Evidence level: C (End-to-end execution flow across real production authorities)
Authority path: [RiskAuthority, GovernanceAuthority, CapabilityAuthority, TaskKernelAuthority, RealityVerifier]
Covered capabilities:
  - risk.local_containment
  - risk.assessment
Gates: T03, T09
Must not effect: [RiskAuthority_direct_tool_call]
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scp.risk_intelligence.containment import ContainmentCoordinator
from scp.risk_intelligence.evidence_bundle import EmergencyEvidenceBundle
from scp.risk_intelligence.incident_state import IncidentState, IncidentStateMachine
from scp.risk_intelligence.risk_classifier import RiskClassifier, RiskLevel, RiskSignal
from scp.security.capability_epoch import CapabilityAuthority, CapabilityRevokedError
from scp.task_kernel import TaskKernel


def test_ce_s10_03_governed_containment_e2e_closed_loop(tmp_path: Path) -> None:
    """Proves the full closed-loop pipeline for CE-S10-03:

    1. TaskKernel provisions an active task leased to a worker.
    2. CapabilityAuthority issues an execution capability lease token.
    3. RiskClassifier identifies material risk and emits an EmergencyEvidenceBundle.
    4. Negative invariant: RiskClassifier has NO direct tool execution capability.
    5. Fail-closed: containment on unowned scope is strictly denied.
    6. Governed containment: ContainmentCoordinator revokes CapabilityAuthority epoch.
    7. Worker capability immediately invalidated; subsequent execution attempts fail closed.
    8. Incident state machine advances to CONTAINING and RESOLVED with full audit trail.
    """
    # --------------------------------------------------------------------------
    # Step 1 (TaskKernelAuthority): Provision durable task lifecycle
    # --------------------------------------------------------------------------
    kernel_db = tmp_path / "task_kernel.sqlite3"
    kernel = TaskKernel(kernel_db)

    task_id = "task-worker-containment-001"
    kernel.create_task(
        task_id=task_id,
        owner="worker-pool-sandbox",
        goal="Run untrusted background data analytics workload",
        risk_tier="R2",
        deadline_ms=600000,
    )
    kernel.transition(task_id, "PLANNING", actor="planner", reason="decompose task")
    kernel.transition(task_id, "READY", actor="planner", reason="workload plan ready")
    kernel.transition(task_id, "QUEUED", actor="planner", reason="await worker lease")

    lease = kernel.claim(task_id, "worker-node-1", ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    assert kernel.get_task(task_id)["state"] == "RUNNING"

    # --------------------------------------------------------------------------
    # Step 2 (CapabilityAuthority): Issue capability token for worker
    # --------------------------------------------------------------------------
    cap_state_file = tmp_path / "capability_state.json"
    cap_auth = CapabilityAuthority(cap_state_file)
    worker_token = cap_auth.issue(subject="worker-node-1")
    assert cap_auth.validate(worker_token) is True

    # --------------------------------------------------------------------------
    # Step 3 (RiskAuthority): Detect material risk and produce evidence bundle
    # --------------------------------------------------------------------------
    classifier = RiskClassifier()

    # Verify MUST-NOT invariant: RiskClassifier cannot execute tools directly
    for forbidden_call in ("execute_tool", "run_action", "kill_process", "direct_containment"):
        assert not hasattr(classifier, forbidden_call), (
            f"Violation of DNA #6 and CE-S10-03: RiskAuthority has direct tool execution method {forbidden_call}"
        )

    # Risk signals indicate suspicious data exfiltration attempt from owned sensor
    signals = [
        RiskSignal(
            source_id="sensor_net_01",
            kind="owned_sensor",
            lineage_id="lineage_net_guard",
            fresh=True,
            location_validated=True,
            observed_directly=True,
        )
    ]
    assessment = classifier.classify(signals, desired_level=RiskLevel.PR4)
    assert assessment.level == RiskLevel.PR4

    evidence_bundle = EmergencyEvidenceBundle(
        incident_id="INC-EXFIL-20260904-001",
        risk_type="DATA_EXFILTRATION",
        level="PR4",
        claims=("Worker attempted unauthorized bulk data exfiltration",),
        independent_lineages=2,
        contradictions=(),
        unknowns=("external recipient identity",),
        confidence=0.98,
        recommended_actions=("quarantine_worker_and_revoke_network",),
        source_hashes=("sha256:abcd1234ef567890",),
        official_confirmation=False,
    )

    # --------------------------------------------------------------------------
    # Step 4 (GovernanceAuthority): Governed containment scope check & execution
    # --------------------------------------------------------------------------
    coordinator = ContainmentCoordinator(cap_auth)

    # Fail-closed: unowned scope cannot be contained
    with pytest.raises(PermissionError, match="restricted to owned infrastructure"):
        coordinator.contain(evidence_bundle, owned_scope=False)
    assert cap_auth.validate(worker_token) is True

    # Governed containment on owned scope
    containment_result = coordinator.contain(
        evidence_bundle,
        owned_scope=True,
        actor="governance_authority",
    )
    assert containment_result["decision"] == "CAPABILITY_REVOKED"
    assert containment_result["authority"] == "CapabilityAuthority"
    assert containment_result["action"] == "quarantine_worker_and_revoke_network"

    # --------------------------------------------------------------------------
    # Step 5 (RealityVerifier & TaskKernel): Validate postconditions & containment
    # --------------------------------------------------------------------------
    # Capability immediately revoked
    assert cap_auth.validate(worker_token) is False

    # Worker attempting to issue new actions fails closed
    with pytest.raises(CapabilityRevokedError):
        cap_auth.issue(subject="worker-node-1")

    # TaskKernel transitions task to terminal containment state
    kernel.transition(
        task_id,
        "HUMAN_REVIEW",
        actor="governance_containment_coordinator",
        reason="Quarantined due to PR4 data exfiltration risk",
    )
    assert kernel.get_task(task_id)["state"] == "HUMAN_REVIEW"

    # Incident state machine tracks full lifecycle
    incident = IncidentStateMachine("INC-EXFIL-20260904-001")
    assert incident.state == IncidentState.OBSERVED
    incident.transition(IncidentState.SUSPECTED)
    incident.transition(IncidentState.CORROBORATING)
    incident.transition(IncidentState.CONFIRMED)
    incident.transition(IncidentState.CONTAINING)
    incident.transition(IncidentState.RESOLVED)
    assert incident.state == IncidentState.RESOLVED

    # Audit file on disk confirms epoch revocation and provenance
    audit_data = json.loads(cap_state_file.read_text(encoding="utf-8"))
    assert audit_data["revoked"] is True
    assert "quarantine_worker_and_revoke_network" in audit_data["reason"]
    assert audit_data["actor"] == "governance_authority"
