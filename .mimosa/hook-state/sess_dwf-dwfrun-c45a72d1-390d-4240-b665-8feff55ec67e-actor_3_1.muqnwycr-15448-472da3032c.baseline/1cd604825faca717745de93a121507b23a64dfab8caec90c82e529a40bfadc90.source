import sys
from pathlib import Path
import sqlite3
import multiprocessing
import time
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scp.kernel_storage import SQLiteKernelStorage

DB_PATH = Path(__file__).resolve().parent / "probe_occ.db"

def worker(worker_id: int, iterations: int):
    storage = SQLiteKernelStorage(DB_PATH)
    for i in range(iterations):
        storage.begin()
        try:
            row = storage.fetchone("SELECT val FROM counter")
            current = row[0] if row else 0
            
            # Simulate some work to widen the race window
            time.sleep(0.001)
            
            storage.execute("UPDATE counter SET val = ?", (current + 1,))
            storage.commit()
        except Exception as e:
            storage.rollback()
            print(f"Worker {worker_id} iter {i} failed: {e}")
            raise

def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        
    storage = SQLiteKernelStorage(DB_PATH)
    storage.executescript("CREATE TABLE IF NOT EXISTS counter (val INTEGER); INSERT INTO counter (val) VALUES (0);")
    storage.close()
    
    workers_count = 10
    iterations = 50
    expected_total = workers_count * iterations
    
    print(f"Starting {workers_count} workers, {iterations} iterations each. Expected total: {expected_total}")
    
    start_time = time.time()
    
    processes = []
    for i in range(workers_count):
        p = multiprocessing.Process(target=worker, args=(i, iterations))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    end_time = time.time()
    
    storage = SQLiteKernelStorage(DB_PATH)
    final_val = storage.fetchone("SELECT val FROM counter")[0]
    storage.close()
    
    print(f"Final value: {final_val}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    if final_val == expected_total:
        print("PASS: No race condition detected. Multiprocess concurrency is safe without RLock.")
        sys.exit(0)
    else:
        print(f"FAIL: Race condition detected! Expected {expected_total}, got {final_val}.")
        sys.exit(1)

if __name__ == "__main__":
    main()
