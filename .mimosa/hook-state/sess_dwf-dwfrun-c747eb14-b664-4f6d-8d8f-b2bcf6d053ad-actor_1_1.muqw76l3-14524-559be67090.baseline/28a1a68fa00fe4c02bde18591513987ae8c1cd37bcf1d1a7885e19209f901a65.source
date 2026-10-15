import os

import pytest

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.pc_control import CapabilityLevel, PCController


def test_subsystem_pc_control_importable():
    """PC Controller: verify status inspection and fail-closed token boundary."""
    ctrl = PCController()
    status = ctrl.status()
    assert status["controller"] == "online"
    assert "capabilityLevels" in status
    assert status["capabilityLevels"]["READ_ONLY"] == CapabilityLevel.READ_ONLY.value
    
    # Verify unauthenticated action is rejected fail-closed (FA-05)
    with pytest.raises(PermissionError):
        ctrl.clear_kill_switch(approved=True, capability_token=None)
