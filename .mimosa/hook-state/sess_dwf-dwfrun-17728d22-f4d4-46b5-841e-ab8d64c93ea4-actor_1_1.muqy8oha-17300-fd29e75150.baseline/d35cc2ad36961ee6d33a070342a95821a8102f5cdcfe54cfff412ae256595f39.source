import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.hands import ActionDefinition, ActionRegistry


def test_subsystem_hands_importable():
    """Hands apparatus: verify action registry registration and policy definitions."""
    registry = ActionRegistry()
    actions = registry.list()
    assert len(actions) >= 20, "Hands must expose standard system actions"
    
    # Verify exact action definition retrieval
    action = registry.get("pc.directory_tree")
    assert action is not None
    assert isinstance(action, ActionDefinition)
    assert action.domain == "pc"
    assert action.risk == "low"
    assert action.mutates_state is False
