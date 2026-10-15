import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")

from scp.self_model.capability_map import CapabilityMap, CapabilityStatus


def test_subsystem_self_model_importable():
    """self_model: module capability_map phải import được và định nghĩa trạng thái đầy đủ."""
    assert CapabilityMap is not None
    assert CapabilityStatus is not None


def test_subsystem_self_model_has_capability_map():
    """self_model: CapabilityMap class phải tồn tại (được doubt_engine dùng)."""
    assert hasattr(CapabilityMap, "add_blindspot")
    assert hasattr(CapabilityMap, "list_blindspots")


def test_subsystem_self_model_capability_status_levels():
    """self_model: CapabilityStatus phải có đủ 8 bậc từ UNKNOWN đến RECOVERY_VERIFIED."""
    values = [s.value for s in CapabilityStatus]
    assert len(values) >= 8, f"FAIL: CapabilityStatus chỉ có {len(values)} bậc, cần >= 8!"
    assert "RECOVERY_VERIFIED" in values
    assert "RUNTIME_VERIFIED" in values
