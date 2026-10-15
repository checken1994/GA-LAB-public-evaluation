import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.contracts import EventEnvelope, EvidenceLevel, Maturity, Verdict


def test_subsystem_contracts_importable():
    """Core contracts: verify EventEnvelope instantiation and invariant checks."""
    envelope = EventEnvelope(
        event_type="task.dispatched",
        actor_type="orchestrator",
        actor_id="worker_01",
        payload={"task_id": "task_100", "action": "code_eval"},
    )
    assert envelope.event_type == "task.dispatched"
    assert envelope.actor_id == "worker_01"
    assert envelope.payload["task_id"] == "task_100"
    assert envelope.event_id is not None


def test_subsystem_contracts_enums():
    """Verify contract maturity levels and verdict states."""
    assert Verdict.VERIFIED.value == "VERIFIED"
    assert Verdict.CONTRADICTED.value == "CONTRADICTED"
    assert EvidenceLevel.A.value == "A"
    assert Maturity.M4_RUNTIME_VERIFIED.name == "M4_RUNTIME_VERIFIED"
