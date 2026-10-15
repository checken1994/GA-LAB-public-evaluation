import threading

from scp.autofix.evidence_replay import (
    EvidenceReplay,
)
from scp.core.chat_memory_store import ChatMemoryStore
from scp.core.db_manager import db_exec, db_query_all, db_query_one
from scp.trace_ledger import TraceLedger


def test_chat_memory_store_concurrent_append_prune(tmp_path):
    store = ChatMemoryStore(tmp_path / "chat.jsonl")

    def worker(wid):
        for i in range(25):
            assert store.append(session_id="sess_1", role="user", content=f"msg {wid}-{i}") is True

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    records = store.load("sess_1", limit=100)
    assert len(records) > 0


def test_trace_ledger_concurrent_hash_chain(tmp_path):
    ledger = TraceLedger(tmp_path / "trace.jsonl")

    def worker(wid):
        for i in range(20):
            ledger.append(worker=wid, i=i)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    result = ledger.verify()
    assert result["entries"] == 100
    assert result["hash_chain_valid"] is True
    assert len(result["errors"]) == 0


def test_db_manager_concurrent_reads_and_writes(tmp_path):
    test_db = str(tmp_path / "concurrency_test.db")
    db_exec("CREATE TABLE IF NOT EXISTS p0_test (id INTEGER PRIMARY KEY, val TEXT)", db_path=test_db)
    for i in range(10):
        db_exec("INSERT INTO p0_test (val) VALUES (?)", (f"v_{i}",), db_path=test_db)

    def reader():
        for _ in range(20):
            db_query_all("SELECT * FROM p0_test", db_path=test_db)

    def writer():
        for i in range(20):
            db_exec("INSERT INTO p0_test (val) VALUES (?)", (f"w_{i}",), db_path=test_db)

    threads = [threading.Thread(target=reader) for _ in range(4)] + [threading.Thread(target=writer) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    row = db_query_one("SELECT COUNT(*) as cnt FROM p0_test", db_path=test_db)
    assert row["cnt"] >= 50


def test_evidence_replay_fail_closed_and_real_exec():
    replay = EvidenceReplay()
    # Fail-closed when no evidence or test
    empty_res = replay.verify()
    assert empty_res["ok"] is False
    assert empty_res["status"] == "UNVERIFIED"

    # Real test execution
    exec_res = replay.verify(test_command='python -c "exit(0)"')
    assert exec_res["ok"] is True
    assert exec_res["status"] == "VERIFIED"

    fail_res = replay.verify(test_command='python -c "exit(1)"')
    assert fail_res["ok"] is False
    assert fail_res["status"] == "FAILED"
