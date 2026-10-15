import os
from pathlib import Path

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.world_state.temporal_authority import TemporalAuthority


def test_world_state_isolated_flow(tmp_path: Path):
    """FA-13: Cover world_state flow with genuine behavioral execution.

    Verifies TemporalAuthority SQLite schema persistence, observation recording,
    prediction tracking (PREDICTED status), and promotion to OBSERVED via evidence resolution.
    """
    db_file = tmp_path / "temporal_world.db"
    auth = TemporalAuthority(db_file)

    try:
        # 1. Behavioral: Record an empirical observation with actor and evidence refs
        obs = auth.record_observation(
            subject="cluster-node-01",
            predicate="health_status",
            value={"status": "healthy", "load_pct": 28.5},
            valid_time="2026-09-27T10:00:00Z",
            evidence_refs=["probe-health-01"],
            actor_id="daemon-monitor",
        )
        assert obs["assertion_id"].startswith("w_")
        assert obs["epistemic_status"] == "OBSERVED"
        assert obs["subject"] == "cluster-node-01"

        # 2. Behavioral: Record a forward-looking prediction
        pred = auth.record_prediction(
            subject="cluster-node-01",
            predicate="health_status",
            value={"status": "degraded", "predicted_load": 92.0},
            valid_time="2026-09-27T12:00:00Z",
            predictor_id="ml-forecast-agent",
        )
        assert pred["epistemic_status"] == "PREDICTED"
        pred_id = pred["assertion_id"]

        # 3. Behavioral: Promote prediction to OBSERVED when verified by ground truth evidence
        promoted = auth.promote_to_observed(
            pred_id,
            evidence_refs=["telemetry-ground-truth-1200"],
            resolver_id="eval-judge",
        )
        assert promoted["assertion_id"].startswith("w_")
        assert promoted["assertion_id"] != pred_id
        assert promoted["epistemic_status"] == "OBSERVED"

        # 4. Behavioral: History query retrieves recorded assertions
        history_records = auth.history("cluster-node-01")
        assert len(history_records) >= 2
    finally:
        auth.close()
