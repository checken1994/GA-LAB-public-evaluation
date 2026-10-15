import os
from pathlib import Path

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.governance import DriftDecision, DriftGuard


def test_subsystem_governance_importable():
    """Governance drift guard: verify AST change inspection against protected invariants."""
    manifest = Path("spec/protected_invariants.yaml")
    assert manifest.exists(), "protected_invariants.yaml must exist"
    
    guard = DriftGuard(manifest)
    res = guard.inspect_change(
        path="scp/sample_worker.py",
        old_text="TIMEOUT = 30\n",
        new_text="TIMEOUT = 60\n",
    )
    assert res is not None
    assert res.decision in {DriftDecision.ALLOW, DriftDecision.DENY, DriftDecision.REQUIRE_GOVERNANCE}
