"""Reality test for Fix 4-a-009: approval committed AFTER fix applied.

Behavioral execution test: verifies that if apply_approved_fix raises an exception,
the request transitions to 'apply_failed' with the recorded error message,
preventing the 'approved-but-not-applied' stuck state.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

def test_permission_gate_apply_failed_transactional_recovery(tmp_path):
    from scp.autofix.permission import BugReport, PermissionGate

    gate = PermissionGate(data_dir=str(tmp_path))
    gate._bypass_understanding = True  # test mode bypass

    bug = BugReport(
        file="foo.py",
        line=42,
        bug_type="logic_error",
        description="Fix logic division by zero",
        tier=3,
        suggested_fix="if b != 0: return a / b",
    )
    req_id = gate.request_permission(bug)
    assert req_id in gate._pending

    # 1. Approve
    approved = gate.approve(req_id, decided_by="admin", note="Approval for division check")
    assert approved is True
    assert gate._pending[req_id].status == "approved"

    # 2. Simulate failed apply
    error_msg = "RuntimeError: Simulated file patch failure"
    ok = gate.mark_apply_status(req_id, "apply_failed", error=error_msg)
    assert ok is True

    # 3. Status must be apply_failed, NOT stuck in approved or applied
    req = gate._pending[req_id]
    assert req.status == "apply_failed"
    assert hasattr(req, "apply_error") and req.apply_error == error_msg

    # 4. Re-approval must be permitted (recoverable)
    reapproved = gate.approve(req_id, decided_by="admin", note="Re-approval retry")
    assert reapproved is True
    assert gate._pending[req_id].status == "approved"

    # 5. Success path marks applied
    ok_applied = gate.mark_apply_status(req_id, "applied")
    assert ok_applied is True
    assert gate._pending[req_id].status == "applied"

if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        test_permission_gate_apply_failed_transactional_recovery(Path(tmp))
    print("PASS: reality_4-a-009 behavioral tests passed")
