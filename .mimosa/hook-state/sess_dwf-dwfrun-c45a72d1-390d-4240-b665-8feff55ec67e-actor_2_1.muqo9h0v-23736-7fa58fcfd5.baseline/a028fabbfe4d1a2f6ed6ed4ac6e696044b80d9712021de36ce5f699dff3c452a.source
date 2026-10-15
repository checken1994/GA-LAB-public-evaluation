import os
import tempfile

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.task_kernel import TaskKernel


def test_subsystem_task_kernel_importable():
    """Task kernel: verify task lifecycle transitions and cryptographic journal verification."""
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "kernel_test.sqlite3")
        kernel = TaskKernel(db)
        try:
            kernel.create_task("t-1", "operator", "execute backup", "R0")
            assert kernel.get_task("t-1")["state"] == "CREATED"
            
            kernel.transition("t-1", "PLANNING", actor="planner", reason="begin plan")
            assert kernel.get_task("t-1")["state"] == "PLANNING"
            
            kernel.transition("t-1", "READY", actor="planner", reason="plan finalized")
            assert kernel.get_task("t-1")["state"] == "READY"
            
            # Verify journal hash chain integrity
            journal = kernel.verify_journal("t-1")
            assert journal["hash_chain_valid"] is True
            assert journal["event_count"] == 3
        finally:
            kernel.close()
