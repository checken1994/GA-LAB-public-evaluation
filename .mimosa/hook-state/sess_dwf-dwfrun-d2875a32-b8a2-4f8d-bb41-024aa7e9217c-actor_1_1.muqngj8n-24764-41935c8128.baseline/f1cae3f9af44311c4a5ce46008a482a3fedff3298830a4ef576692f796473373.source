import os

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.meta.constitution import get_default_constitution
from scp.meta.severity import CRITICAL_SEVERITIES, Severity, normalize_severity


def test_subsystem_meta_importable():
    """Meta reasoning: verify severity classification and constitution principles."""
    assert normalize_severity("critical") == Severity.CRITICAL
    assert normalize_severity("HIGH") == Severity.HIGH
    assert normalize_severity("unknown_text") is None
    assert Severity.CRITICAL in CRITICAL_SEVERITIES
    
    # Verify core philosophical principles
    constitution = get_default_constitution()
    principles = constitution.principles()
    assert len(principles) >= 10
    principle_names = [p.name for p in principles]
    assert "Accuracy" in principle_names
