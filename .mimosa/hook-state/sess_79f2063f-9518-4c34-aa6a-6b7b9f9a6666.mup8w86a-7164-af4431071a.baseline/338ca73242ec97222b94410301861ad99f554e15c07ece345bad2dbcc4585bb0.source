import sys, os, tempfile, sqlite3
sys.path.insert(0, ".")
from scp.task_kernel import TaskKernel

fd, db = tempfile.mkstemp(suffix=".sqlite3")
os.close(fd)
k = TaskKernel(db)
tid = "task_probe_11"
k.create_task(tid, "probe-owner", "test_task")
k.transition(tid, "PLANNING")
k.transition(tid, "READY")
k.transition(tid, "QUEUED")
lease = k.claim_next("worker_1").lease_id
k.transition(tid, "RUNNING", lease_id=lease)
k.transition(tid, "VERIFYING", lease_id=lease)
try:
    k.transition(tid, "COMPLETED", lease_id=lease, actor="probe", reason="bypass")
    print("RED: Transition to COMPLETED succeeded without evidence!")
    state = k.get_task(tid)["state"]
    print(f"Task state is now: {state}")
except Exception as e:
    print(f"GREEN: Blocked with {type(e).__name__}: {e}")
finally:
    k.close()

# Empirical SQLite inspection (FA-12)
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
task_row = dict(conn.execute("SELECT task_id, state, version, active_lease_id FROM tasks WHERE task_id=?", (tid,)).fetchone())
events = [dict(r) for r in conn.execute("SELECT seq, type, from_state, to_state, actor FROM events WHERE task_id=? ORDER BY seq", (tid,)).fetchall()]
conn.close()
try:
    os.remove(db)
except OSError:
    pass

print(f"RAW_SQLITE_TASKS_ROW: {task_row}")
print(f"RAW_SQLITE_EVENTS_COUNT: {len(events)}")
for ev in events:
    print(f"RAW_SQLITE_EVENT: seq={ev['seq']} type={ev['type']} from={ev['from_state']} to={ev['to_state']} actor={ev['actor']}")
