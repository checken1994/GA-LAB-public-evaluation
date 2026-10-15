import sys, os, tempfile
sys.path.insert(0, ".")
from scp.task_kernel import TaskKernel
fd, db = tempfile.mkstemp(suffix=".sqlite3")
os.close(fd)
k = TaskKernel(db)
tid = "task_probe_failed"
k.create_task(tid, "probe-owner", "test_task")
k.transition(tid, "PLANNING")
k.transition(tid, "READY")
k.transition(tid, "QUEUED")
lease = k.claim_next("worker_1").lease_id
k.transition(tid, "RUNNING", lease_id=lease)
try:
    k.transition(tid, "FAILED", lease_id=lease, actor="probe", reason="bypass")
    print("RED: Transition to FAILED succeeded directly via transition()")
except Exception as e:
    print(f"GREEN: Blocked with {type(e).__name__}: {e}")
