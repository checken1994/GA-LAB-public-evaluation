import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scp.kernel_storage import SQLiteKernelStorage, make_storage

def test_storage_backend_tampering():
    print("[1] Testing SCP_STORAGE_BACKEND security & boundary cases...")
    fd, test_db = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    
    # 1. Injection strings
    adversarial_inputs = [
        "postgres",
        "POSTGRES",
        "  mysql  ",
        "sqlite; DROP TABLE tasks;",
        "sqlite/../../etc/passwd",
        "cassandra",
        "dynamodb",
        "redis\nappend evil 1",
        "12345",
        "sqlite_fake",
    ]
    for adv in adversarial_inputs:
        os.environ["SCP_STORAGE_BACKEND"] = adv
        try:
            storage = make_storage(test_db)
            print(f"FAIL: Expected NotImplementedError for backend='{adv}', but got {storage}")
            sys.exit(1)
        except NotImplementedError as e:
            assert f"Unsupported storage backend '{adv.strip().lower()}'" in str(e)
            
    # 2. Valid variants
    valid_variants = ["sqlite", "SQLITE", " SQLite ", "", "  "]
    for valid in valid_variants:
        os.environ["SCP_STORAGE_BACKEND"] = valid
        storage = make_storage(test_db)
        assert isinstance(storage, SQLiteKernelStorage)
        storage.close()
        
    print("PASS: All backend tampering attempts failed closed.")

def test_multithreaded_concurrency_without_rlock():
    print("[2] Testing multi-threaded concurrency without RLock...")
    fd, test_db = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    storage = SQLiteKernelStorage(test_db)
    storage.executescript("CREATE TABLE test_acc (id INT PRIMARY KEY, balance INT, version INT);")
    storage.execute("INSERT INTO test_acc VALUES (1, 1000, 1);")
    storage.close()

    errors = []
    thread_count = 10
    transfers_per_thread = 20

    def worker(worker_id):
        worker_storage = SQLiteKernelStorage(test_db)
        try:
            for _ in range(transfers_per_thread):
                # Retry loop on OCC / busy
                for attempt in range(30):
                    try:
                        worker_storage.begin()
                        row = worker_storage.fetchone("SELECT balance, version FROM test_acc WHERE id = 1")
                        bal, ver = row["balance"], row["version"]
                        cur = worker_storage.execute(
                            "UPDATE test_acc SET balance = ?, version = ? WHERE id = 1 AND version = ?",
                            (bal + 10, ver + 1, ver)
                        )
                        if cur.rowcount == 1:
                            worker_storage.commit()
                            break
                        else:
                            # OCC conflict
                            worker_storage.rollback()
                            time.sleep(0.01 * (attempt + 1))
                    except Exception as e:
                        err = str(e).lower()
                        if "busy" in err or "locked" in err:
                            try:
                                worker_storage.rollback()
                            except Exception:
                                pass
                            time.sleep(0.02 * (attempt + 1))
                        else:
                            worker_storage.rollback()
                            raise
        except Exception as e:
            errors.append((worker_id, e))
        finally:
            worker_storage.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors encountered during multi-threaded stress: {errors}"

    final_storage = SQLiteKernelStorage(test_db)
    row = final_storage.fetchone("SELECT balance, version FROM test_acc WHERE id = 1")
    final_storage.close()
    
    expected_balance = 1000 + (thread_count * transfers_per_thread * 10)
    expected_version = 1 + (thread_count * transfers_per_thread)
    assert row["balance"] == expected_balance, f"Balance mismatch: {row['balance']} != {expected_balance}"
    assert row["version"] == expected_version, f"Version mismatch: {row['version']} != {expected_version}"
    print(f"PASS: Multi-threaded OCC stress verified. Balance: {row['balance']}, Version: {row['version']}.")

def test_rollback_and_isolation():
    print("[3] Testing rollback clean-up and transaction isolation...")
    fd, test_db = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    storage = SQLiteKernelStorage(test_db)
    storage.executescript("CREATE TABLE items (name TEXT PRIMARY KEY);")
    
    # Begin and rollback
    storage.begin()
    assert storage.in_transaction
    storage.execute("INSERT INTO items VALUES ('apple')")
    storage.rollback()
    assert not storage.in_transaction
    
    row = storage.fetchone("SELECT count(*) as cnt FROM items")
    assert row["cnt"] == 0, "Rollback failed to discard uncommitted insert!"
    
    # Exception inside transaction
    storage.begin()
    try:
        storage.execute("INSERT INTO nonexistent_table VALUES (1)")
    except Exception:
        storage.rollback()
        
    assert not storage.in_transaction
    storage.close()
    print("PASS: Rollback and isolation verified.")

if __name__ == "__main__":
    test_storage_backend_tampering()
    test_multithreaded_concurrency_without_rlock()
    test_rollback_and_isolation()
    print("ALL ADVERSARIAL STRESS TESTS PASSED.")
