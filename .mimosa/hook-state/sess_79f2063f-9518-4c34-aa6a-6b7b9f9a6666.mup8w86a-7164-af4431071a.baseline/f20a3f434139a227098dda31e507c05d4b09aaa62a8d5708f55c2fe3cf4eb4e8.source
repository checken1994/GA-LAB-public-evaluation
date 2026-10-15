import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from scp.task_kernel import TaskKernel, OptimisticLockError

def run_real_db_test():
    db_path = PROJECT_ROOT / 'data' / 'ask_task_kernel.sqlite3'
    if not db_path.exists():
        print(f"FAILED: Real DB not found at {db_path}")
        sys.exit(1)
        
    print(f"SUCCESS: Connected to LIVE database: {db_path}")
    kernel = TaskKernel(str(db_path))
    
    task_id = 'e2e-live-race-test'
    try:
        kernel.conn.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
        kernel.conn.execute("DELETE FROM events WHERE task_id=?", (task_id,))
        kernel._commit()
        
        kernel.create_task(task_id, 'admin', 'E2E Race Test', 'R0')
        kernel.transition(task_id, 'PLANNING', actor='system')
        
        base_task = kernel.get_task(task_id)
        base_version = int(base_task['version'])
        print(f"SUCCESS: Created task in live DB: id={task_id}, version={base_version}, state={base_task['state']}")
        
        results = []
        barrier = threading.Barrier(2)

        def worker_thread(name: str) -> None:
            k = TaskKernel(str(db_path))
            try:
                barrier.wait(timeout=5)
                k.rebuild_projection(task_id, expected_version=base_version)
                results.append((name, "SUCCESS"))
            except OptimisticLockError:
                results.append((name, "OCC_ERROR (BLOCKED BY FIX!)"))
            except Exception as e:
                results.append((name, f"ERROR: {e}"))
            finally:
                k.close()

        print("WARNING: Launching 2 concurrent hackers into the live TaskKernel...")
        t1 = threading.Thread(target=worker_thread, args=("Hacker_A",))
        t2 = threading.Thread(target=worker_thread, args=("Hacker_B",))
        t1.start(); t2.start()
        t1.join(); t2.join()
        
        print(f"RESULTS: {results}")
        
    finally:
        kernel.close()

if __name__ == '__main__':
    run_real_db_test()
