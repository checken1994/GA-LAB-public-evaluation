import sys
import threading
from pathlib import Path

# Load SCP module thuc te
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from scp.task_kernel import TaskKernel, OptimisticLockError

def run_reality_probe():
    db_path = PROJECT_ROOT / 'data' / 'reality_probe_kernel.sqlite3'
    if db_path.exists():
        db_path.unlink()
        
    print(f"[OK] Khoi tao Kernel DB thuc tren dia cung: {db_path}")
    kernel = TaskKernel(str(db_path))
    
    task_id = 'reality-race-task'
    try:
        kernel.create_task(task_id, 'admin', 'E2E Reality Test', 'R0')
        kernel.transition(task_id, 'PLANNING', actor='system')
        
        base_task = kernel.get_task(task_id)
        base_version = int(base_task['version'])
        print(f"[OK] Tinh trang Database that: id={task_id}, version={base_version}, state={base_task['state']}")
        
        results = []
        barrier = threading.Barrier(2)

        def hacker_thread(name: str) -> None:
            k = TaskKernel(str(db_path))
            try:
                barrier.wait(timeout=5)
                k.rebuild_projection(task_id, expected_version=base_version)
                results.append((name, "SUCCESS (Ghi de thanh cong)"))
            except OptimisticLockError:
                results.append((name, "OCC_ERROR (Bi Database block!)"))
            except Exception as e:
                results.append((name, f"ERROR: {e}"))
            finally:
                k.close()

        print("\n[WARNING] Kich hoat 2 luong hacker tan cong dong thoi vao cung file SQLite...")
        t1 = threading.Thread(target=hacker_thread, args=("Hacker_A",))
        t2 = threading.Thread(target=hacker_thread, args=("Hacker_B",))
        t1.start(); t2.start()
        t1.join(); t2.join()
        
        print(f"\n[RESULTS] KET QUA THUC TE TREN DIA CUNG:")
        for r in results:
            print(f"   - {r[0]}: {r[1]}")
            
    finally:
        kernel.close()

if __name__ == '__main__':
    run_reality_probe()
