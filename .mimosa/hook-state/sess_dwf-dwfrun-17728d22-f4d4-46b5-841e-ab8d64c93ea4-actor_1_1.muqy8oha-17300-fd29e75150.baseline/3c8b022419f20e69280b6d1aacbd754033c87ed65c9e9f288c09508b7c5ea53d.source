"""T09 Golden Task - Edge CE-X08-01: World observation -> state projection/change.

Evidence level: C (End-to-end execution flow across real production authorities)
Authority path: [EvidenceAuthority, EntityEventAuthority, TemporalAuthority, WorldStateProjection]
Covered capabilities:
  - world.entity_identity
  - world.event_model
  - world.temporal_state
  - world.change_detection
  - world.state_projection
Gates: T02, T06, T09, T10
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scp.epistemic import EvidenceStore
from scp.world_state.entity_event_authority import EntityEventAuthority
from scp.world_state.temporal_authority import TemporalAuthority, WorldStateError
from scp.world_state.world_state_projection import WorldStateProjection


def test_ce_x08_01_world_observation_to_state_projection_e2e(tmp_path: Path) -> None:
    """Proves the full closed-loop pipeline for CE-X08-01:

    1. T06 EvidenceStore captures immutable real observation bytes and hash.
    2. TemporalAuthority records bitemporal assertion with evidence reference.
    3. EntityEventAuthority links alias identities with verified evidence.
    4. WorldStateProjection builds current state and change delta.
    5. Observation changes/conflicts: new assertion supersedes past state.
    6. T10 Restart / Crash Recovery: projection parity survives simulated DB reboot.
    7. Negative invariants: no history overwrite, no unverified prediction promotion,
       no unevidenced cross-lineage same-name entity merge.
    """
    # --------------------------------------------------------------------------
    # Step 1 (T06): Real EvidenceStore capture
    # --------------------------------------------------------------------------
    evidence_db = tmp_path / "epistemic.sqlite3"
    evidence_objects = tmp_path / "evidence_objects"
    store = EvidenceStore(evidence_db, evidence_objects)

    obs_payload = b'{"node_id": "worker-node-1", "status": "HEALTHY", "load": 0.15}'
    obs_record = store.observe(
        kind="RUNTIME_OBSERVATION",
        content=obs_payload,
        collector_id="cluster_probe_collector",
        collector_version="1.0.0",
        source_id="probe_stream_01",
    )
    assert obs_record["evidence_id"].startswith("ev_")
    evidence_ref_1 = obs_record["evidence_id"]
    assert store.read_content(evidence_ref_1) == obs_payload

    # --------------------------------------------------------------------------
    # Step 2 (T02/T09): Ingestion into TemporalAuthority
    # --------------------------------------------------------------------------
    world_db_path = tmp_path / "world_state.sqlite3"
    temporal = TemporalAuthority(world_db_path)
    entity_events = EntityEventAuthority(temporal)
    projection = WorldStateProjection(temporal)

    valid_time_1 = "2026-09-04T00:00:00Z"
    assertion_1 = temporal.record_observation(
        subject="node:worker-node-1",
        predicate="cluster_status",
        value={"status": "HEALTHY", "load": 0.15},
        valid_time=valid_time_1,
        evidence_refs=[evidence_ref_1],
        actor_id="collector_agent",
    )
    assert assertion_1["assertion_id"].startswith("w_")
    assert assertion_1["epistemic_status"] == "OBSERVED"

    # Step 3: Entity Event and Identity Linking with verified evidence
    event_payload = {"action": "NODE_REGISTERED", "capabilities": ["compute", "sandbox"]}
    entity_events.record_event(
        entity_id="worker-node-1",
        event_kind="lifecycle",
        payload=event_payload,
        valid_time=valid_time_1,
        evidence_refs=[evidence_ref_1],
        actor_id="cluster_orchestrator",
    )

    # Link primary identifier with network alias
    entity_events.link_identity(
        "worker-node-1",
        "ip:10.240.0.15",
        evidence_refs=[evidence_ref_1],
        actor_id="network_dns_registrar",
    )
    linked = entity_events.linked_ids("worker-node-1")
    assert "worker-node-1" in linked and "ip:10.240.0.15" in linked

    # Verify projection before change
    curr = projection.current("node:worker-node-1", "cluster_status")
    assert curr is not None
    assert curr["value"]["status"] == "HEALTHY"

    # --------------------------------------------------------------------------
    # Step 4: Conflicting / Updated World Observation (Cause of CE-X08-01)
    # --------------------------------------------------------------------------
    obs_payload_2 = b'{"node_id": "worker-node-1", "status": "CRITICAL", "load": 0.98}'
    obs_record_2 = store.observe(
        kind="RUNTIME_OBSERVATION",
        content=obs_payload_2,
        collector_id="cluster_probe_collector",
        collector_version="1.0.0",
        source_id="probe_stream_01",
    )
    evidence_ref_2 = obs_record_2["evidence_id"]

    corrected = temporal.correct(
        assertion_1["assertion_id"],
        new_value={"status": "CRITICAL", "load": 0.98},
        actor_id="incident_responder",
        evidence_refs=[evidence_ref_2],
    )
    assert corrected["assertion_id"] != assertion_1["assertion_id"]

    # --------------------------------------------------------------------------
    # Step 5: Verify Effects - Change record delta & reconstructable history
    # --------------------------------------------------------------------------
    # Check change detection delta
    delta_changes = projection.changes("node:worker-node-1", "cluster_status")
    assert len(delta_changes) == 0, "Superseded assertions are excluded from active delta sequence"

    # Now append an additional subsequent observation without superseding
    obs_payload_3 = b'{"node_id": "worker-node-1", "status": "CONTAINED", "load": 0.05}'
    obs_record_3 = store.observe(
        kind="RUNTIME_OBSERVATION",
        content=obs_payload_3,
        collector_id="containment_probe",
        collector_version="1.0.0",
        source_id="containment_log",
    )
    valid_time_3 = "2026-09-04T00:10:00Z"
    assertion_3 = temporal.record_observation(
        subject="node:worker-node-1",
        predicate="cluster_status",
        value={"status": "CONTAINED", "load": 0.05},
        valid_time=valid_time_3,
        evidence_refs=[obs_record_3["evidence_id"]],
        actor_id="containment_agent",
    )

    # Now changes() captures the real state transition delta
    active_deltas = projection.changes("node:worker-node-1", "cluster_status")
    assert len(active_deltas) == 1
    assert active_deltas[0]["from_value"]["status"] == "CRITICAL"
    assert active_deltas[0]["to_value"]["status"] == "CONTAINED"

    # Current projection matches latest
    current_post = projection.current("node:worker-node-1", "cluster_status")
    assert current_post is not None
    assert current_post["value"]["status"] == "CONTAINED"

    # --------------------------------------------------------------------------
    # Step 6 (T10): Restart / Crash Recovery Parity
    # --------------------------------------------------------------------------
    # Close existing connection to simulate process restart
    temporal.db.close()

    # Reopen brand new authority and projection on disk
    recovered_temporal = TemporalAuthority(world_db_path)
    recovered_projection = WorldStateProjection(recovered_temporal)

    # Check that current state survives with exact parity
    recovered_current = recovered_projection.current("node:worker-node-1", "cluster_status")
    assert recovered_current is not None
    assert recovered_current["assertion_id"] == assertion_3["assertion_id"]
    assert recovered_current["value"]["status"] == "CONTAINED"

    # Check that historical as_of reconstruction preserves pre-correction state
    historical_state = recovered_projection.rebuild(as_of_system_time=assertion_1["system_time"])
    hist_entry = historical_state["node:worker-node-1"]["cluster_status"][0]
    assert hist_entry["assertion_id"] == assertion_1["assertion_id"]
    assert hist_entry["value"]["status"] == "HEALTHY"

    # --------------------------------------------------------------------------
    # Step 7: Must-Not Invariants (Fail-Closed)
    # --------------------------------------------------------------------------
    # Invariant A: Immutability triggers abort raw SQLite updates & deletes
    with (
        pytest.raises(sqlite3.Error, match="append-only"),
        recovered_temporal.db.transaction() as conn,
    ):
        conn.execute(
            "UPDATE world_assertions SET subject='node:hacked' WHERE assertion_id=?",
            (assertion_1["assertion_id"],),
        )
    with (
        pytest.raises(sqlite3.Error, match="append-only"),
        recovered_temporal.db.transaction() as conn,
    ):
        conn.execute(
            "DELETE FROM world_assertions WHERE assertion_id=?",
            (assertion_1["assertion_id"],),
        )

    # Invariant B: Predictor can NEVER self-promote prediction to OBSERVED
    prediction = recovered_temporal.record_prediction(
        subject="node:worker-node-1",
        predicate="forecast_load",
        value={"predicted_load": 0.40},
        valid_time="2026-09-04T00:30:00Z",
        predictor_id="predictor_agent_007",
    )
    # Self-promotion by the same predictor must be refused
    with pytest.raises(WorldStateError, match="predictor can never promote its own prediction"):
        recovered_temporal.promote_to_observed(
            prediction["assertion_id"],
            evidence_refs=[obs_record_3["evidence_id"]],
            resolver_id="predictor_agent_007",  # SAME ACTOR
        )

    # Invariant C: Same name entities across different lineages are never merged
    with pytest.raises(ValueError, match="identity linking requires evidence_refs"):
        EntityEventAuthority(recovered_temporal).link_identity(
            "worker-node-1", "remote_cluster:worker-node-1",
            evidence_refs=[],  # UNAUDITED / NO EVIDENCE
            actor_id="rogue_agent",
        )
