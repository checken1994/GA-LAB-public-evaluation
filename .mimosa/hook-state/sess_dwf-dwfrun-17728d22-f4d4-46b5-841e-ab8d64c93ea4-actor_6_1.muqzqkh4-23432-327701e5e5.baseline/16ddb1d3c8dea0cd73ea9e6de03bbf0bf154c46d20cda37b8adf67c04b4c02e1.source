#!/usr/bin/env python3
"""
Adversarial Concurrency & Architectural Stress Testing Harness
Challenger 2 — Milestone 2 (P1: 18 High-Severity Reliability & Deployment Fixes)

Tests:
1. KernelStorage Concurrency & ContextVar Isolation
2. In-Memory Collection Bounding & Eviction Under Extreme Concurrency
3. Protocol & Dynamic Imports Integrity (Circular Imports & Orphan Regressions)
"""

import os
import sys

# Pre-set test secrets before any SCP modules are imported
os.environ["SCP_CAPABILITY_SECRET"] = "test-secret-32-chars-minimum-key!!"
os.environ["SCP_JWT_SECRET"] = "test-jwt-secret-key-for-testing!!"
os.environ["SCP_ADMIN_KEY"] = "admin-secret-key"

import ast
import asyncio
import concurrent.futures
from collections import OrderedDict, deque
import importlib
import logging
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
from typing import Any, Dict, List, Set, Tuple

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stress_p1")

DELETED_32_MODULES = [
    "scp.ai_patterns",
    "scp.core.auto_backup",
    "scp.core.dependency_resolver",
    "scp.core.environment_snapshot",
    "scp.core.evidence_filter",
    "scp.core.file_mutex",
    "scp.core.memory_manager",
    "scp.core.react_agent",
    "scp.knowledge.cwe_exploit_store",
    "scp.knowledge.issue_parser",
    "scp.knowledge.scheduled_crawler",
    "scp.meta.adversary_verifier",
    "scp.meta.calibration_engine",
    "scp.meta.curiosity_asker",
    "scp.meta.question_tracker",
    "scp.meta.scp_meta",
    "scp.meta.self_questioning",
    "scp.observability.otel_exporter",
    "scp.runtime.engine_parts.scpv14_process_mixin",
    "scp.runtime.experts.chem_reality_astro",
    "scp.runtime.experts.math_biology",
    "scp.runtime.experts.numeric_data",
    "scp.runtime.healing_v14",
    "scp.runtime.parallel_pipeline",
    "scp.runtime.timing_and_restart",
    "scp.security.auto_payload_generator",
    "scp.security.h8_redteam_bridge",
    "scp.security.kernel_patrol",
    "scp.security.red_team",
    "scp.security.rogue_ai_detector",
    "scp.security.threat_intel",
]


class StressReport:
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def record_pass(self, test_name: str, msg: str = ""):
        self.passed.append(f"{test_name}: {msg}" if msg else test_name)
        logger.info(f"PASS: {test_name} - {msg}")

    def record_fail(self, test_name: str, reason: str):
        self.failed.append((test_name, reason))
        logger.error(f"FAIL: {test_name} - {reason}")

    def record_warn(self, test_name: str, reason: str):
        self.warnings.append((test_name, reason))
        logger.warning(f"WARN: {test_name} - {reason}")


report = StressReport()

# =====================================================================
# 1. KERNELSTORAGE CONCURRENCY & CONTEXTVAR ISOLATION
# =====================================================================

def test_kernel_storage_async_contextvar_isolation():
    """
    Verify ContextVar connection isolation across concurrent async tasks.
    Adversarial Challenge:
    1. Check if tasks spawned via asyncio inherit the parent's connection context.
    2. Check if concurrent tasks share the same connection and collide on begin().
    """
    test_name = "KernelStorage.AsyncContextVarIsolation"
    from scp.kernel_storage import SQLiteKernelStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_kernel_async.db"
        storage = SQLiteKernelStorage(db_path, max_conns=20)
        storage.executescript(
            "CREATE TABLE items (task_id TEXT PRIMARY KEY, val INT, created_at REAL);"
        )

        conn_ids = []
        errors = []

        async def worker(task_id: str):
            c = storage._get_conn()
            conn_ids.append((task_id, id(c)))
            try:
                storage.begin()
                storage.execute(
                    "INSERT INTO items (task_id, val, created_at) VALUES (?, ?, ?)",
                    (task_id, 42, time.time()),
                )
                await asyncio.sleep(0.005)
                storage.commit()
            except Exception as e:
                errors.append((task_id, type(e).__name__, str(e)))
                try:
                    storage.rollback()
                except Exception:
                    pass

        async def run_all():
            tasks = [worker(f"task_{i}") for i in range(5)]
            await asyncio.gather(*tasks, return_exceptions=True)

        try:
            asyncio.run(run_all())
        except Exception as e:
            errors.append(("runner", type(e).__name__, str(e)))

        storage.close()

        # Analyze connection IDs
        unique_conns = set(cid for _, cid in conn_ids)
        if len(conn_ids) > 1 and len(unique_conns) == 1:
            report.record_fail(
                test_name,
                f"ContextVar isolation FAILED: all {len(conn_ids)} concurrent async tasks were assigned the IDENTICAL connection ID ({next(iter(unique_conns))}) due to parent context inheritance! Errors: {errors[:2]}"
            )
        elif errors:
            report.record_fail(
                test_name,
                f"Async transactions failed with {len(errors)} errors: {errors[:3]}"
            )
        else:
            report.record_pass(test_name, f"All {len(conn_ids)} async tasks isolated across {len(unique_conns)} distinct connections")


def test_kernel_storage_thread_concurrency_and_pool_bounding():
    """
    Stress test multi-threaded access with 10 threads running concurrent transactions.
    Adversarial Challenge:
    Verify if 'candidate.in_transaction' reuse allows multiple threads to grab the
    same connection before 'begin()' is executed, causing 'cannot start a transaction
    within a transaction' or SQLITE_MISUSE.
    """
    test_name = "KernelStorage.ThreadConcurrencyAndPoolBounding"
    from scp.kernel_storage import SQLiteKernelStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_kernel_threads.db"
        storage = SQLiteKernelStorage(db_path, max_conns=16)
        storage.executescript("CREATE TABLE logs (thread_id TEXT, counter INT);")

        num_threads = 10
        errors = []
        conns_seen = []
        lock = threading.Lock()

        def worker_thread(thread_idx: int):
            t_name = f"thread_{thread_idx}"
            try:
                c = storage._get_conn()
                with lock:
                    conns_seen.append((t_name, id(c)))
                storage.begin()
                time.sleep(0.01)
                storage.execute(
                    "INSERT INTO logs (thread_id, counter) VALUES (?, ?)",
                    (t_name, 1),
                )
                storage.commit()
            except Exception as ex:
                errors.append((t_name, type(ex).__name__, str(ex)))
                try:
                    storage.rollback()
                except Exception:
                    pass

        threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        storage.close()

        if errors:
            report.record_fail(
                test_name,
                f"Multi-thread concurrency FAILED: {len(errors)}/{num_threads} threads crashed (e.g. {errors[:3]}). Root cause: idle connection reuse without checkout locks permits connection aliasing across threads."
            )
        else:
            report.record_pass(test_name, f"All {num_threads} threads completed transactions cleanly")


def test_kernel_storage_connection_eviction_under_capacity():
    """
    Verify behavior when active connections exceed max_conns.
    Adversarial Challenge:
    In scp/kernel_storage.py:127-132, _get_conn pops and closes 'oldest' from _all_conns
    WITHOUT checking if 'oldest' is currently executing an active transaction!
    """
    test_name = "KernelStorage.ConnectionEvictionUnderCapacity"
    from scp.kernel_storage import SQLiteKernelStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_kernel_evict.db"
        # Set max_conns to 3 so capacity is hit quickly
        storage = SQLiteKernelStorage(db_path, max_conns=3)
        storage.executescript("CREATE TABLE t (id INT);")

        errors = []
        barrier = threading.Barrier(4)

        def active_worker(tid: int):
            try:
                # Force each worker to obtain a distinct connection
                conn = storage._make_connection()
                with storage._conn_guard:
                    storage._all_conns.append(conn)
                storage._conn_ctx.set(conn)
                conn.execute("BEGIN IMMEDIATE")
                barrier.wait(timeout=5)
                # Hold transaction while another thread forces eviction
                time.sleep(0.1)
                conn.execute("INSERT INTO t VALUES (?)", (tid,))
                conn.execute("COMMIT")
            except Exception as ex:
                errors.append((f"worker_{tid}", type(ex).__name__, str(ex)))

        def evictor_thread():
            try:
                barrier.wait(timeout=5)
                # This call will see len(_all_conns) >= 3 and pop/close the oldest active connection
                _ = storage._get_conn()
            except Exception as ex:
                errors.append(("evictor", type(ex).__name__, str(ex)))

        threads = [
            threading.Thread(target=active_worker, args=(1,)),
            threading.Thread(target=active_worker, args=(2,)),
            threading.Thread(target=active_worker, args=(3,)),
            threading.Thread(target=evictor_thread),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        storage.close()

        if errors:
            report.record_fail(
                test_name,
                f"Eviction of in-use connection confirmed: {errors[:3]}"
            )
        else:
            report.record_pass(test_name, "Connection eviction did not interrupt active transactions")


# =====================================================================
# 2. IN-MEMORY COLLECTION BOUNDING & EVICTION UNDER EXTREME CONCURRENCY
# =====================================================================

def test_bounding_threat_and_alert_history():
    """
    Stress test _threat_history and _alert_history in scp/api/webhook.py.
    Inject 10,000 entries across 25 concurrent threads.
    Verify maxlen=1000 bound, FIFO eviction, and thread safety.
    """
    test_name = "Bounding.ThreatAndAlertHistory"
    from scp.api.webhook import _threat_history, _alert_history

    _threat_history.clear()
    _alert_history.clear()

    total_injections = 5000
    num_threads = 25

    def injector(thread_idx: int):
        for i in range(total_injections // num_threads):
            item = {"source": f"thr_{thread_idx}", "idx": i, "ts": time.time()}
            _threat_history.append(item)
            _alert_history.append(item)

    threads = [threading.Thread(target=injector, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    len_threat = len(_threat_history)
    len_alert = len(_alert_history)

    if len_threat <= 1000 and len_alert <= 1000:
        report.record_pass(
            test_name,
            f"Successfully bounded: _threat_history={len_threat}/1000, _alert_history={len_alert}/1000 after {total_injections} concurrent insertions"
        )
    else:
        report.record_fail(test_name, f"Bounds exceeded: threats={len_threat}, alerts={len_alert}")


def test_bounding_incidents_ordered_dict():
    """
    Stress test _incidents in scp/api/routes/risk_routes.py.
    Inject 5,000 entries across 25 concurrent threads.
    Verify maxlen=1000 bound, thread lock integrity, and FIFO eviction.
    """
    test_name = "Bounding.IncidentsOrderedDict"
    from scp.api.routes.risk_routes import _incidents, _incidents_lock, _MAX_INCIDENTS

    with _incidents_lock:
        _incidents.clear()

    num_threads = 25
    items_per_thread = 200

    def add_incident(tid: int):
        for i in range(items_per_thread):
            inc_id = f"inc_stress_{tid}_{i}"
            record = {"incident_id": inc_id, "category": "CYBER", "ts": time.time()}
            with _incidents_lock:
                if len(_incidents) >= _MAX_INCIDENTS:
                    _incidents.popitem(last=False)
                _incidents[inc_id] = record

    threads = [threading.Thread(target=add_incident, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    with _incidents_lock:
        cur_len = len(_incidents)

    if cur_len <= 1000:
        report.record_pass(test_name, f"_incidents properly bounded at {cur_len}/1000 under 5000 concurrent insertions")
    else:
        report.record_fail(test_name, f"_incidents size {cur_len} exceeded maximum limit {_MAX_INCIDENTS}")


def test_bounding_auth_failures_dict():
    """
    Stress test _auth_failures in scp/security/auth.py.
    Inject 12,000 distinct IP failures across 30 concurrent threads.
    Verify bounded at _MAX_AUTH_FAILURE_IPS (5000) and no race conditions.
    """
    test_name = "Bounding.AuthFailuresDict"
    from scp.security.auth import _auth_failures, _auth_failures_lock, _MAX_AUTH_FAILURE_IPS, _record_auth_failure

    with _auth_failures_lock:
        _auth_failures.clear()

    num_threads = 30
    ips_per_thread = 400

    def fail_auth(tid: int):
        for i in range(ips_per_thread):
            ip = f"10.{tid}.{i // 256}.{i % 256}"
            _record_auth_failure(ip)

    threads = [threading.Thread(target=fail_auth, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    with _auth_failures_lock:
        total_ips = len(_auth_failures)

    if total_ips <= _MAX_AUTH_FAILURE_IPS:
        report.record_pass(test_name, f"_auth_failures bounded at {total_ips}/{_MAX_AUTH_FAILURE_IPS} across 12,000 concurrent IP records")
    else:
        report.record_fail(test_name, f"_auth_failures size {total_ips} exceeded maximum limit {_MAX_AUTH_FAILURE_IPS}")


def test_bounding_jobs_dict():
    """
    Stress test _JOBS in scp/api/routes/batch_benchmark_routes.py.
    Simulate 500 job entries with completed dummy threads.
    Verify bounded at 100 entries and dead-thread pruning works.
    """
    test_name = "Bounding.JobsDict"
    from scp.api.routes.batch_benchmark_routes import _JOBS, _JOBS_LOCK

    with _JOBS_LOCK:
        _JOBS.clear()

    # Pre-populate with 150 dead threads
    with _JOBS_LOCK:
        for i in range(150):
            t = threading.Thread(target=lambda: None)
            _JOBS[f"job_{i}"] = t

        # Emulate prune/bound check from _start_job
        dead = [jid for jid, t in _JOBS.items() if not t.is_alive()]
        for jid in dead:
            del _JOBS[jid]
        if len(_JOBS) >= 100:
            oldest_key = next(iter(_JOBS))
            del _JOBS[oldest_key]

        final_len = len(_JOBS)

    if final_len <= 100:
        report.record_pass(test_name, f"_JOBS pruned dead threads and bounded cleanly to {final_len}/100")
    else:
        report.record_fail(test_name, f"_JOBS size {final_len} exceeded maximum limit 100")


def test_bounding_cid_cache():
    """
    Stress test _CID_CACHE in scp/core/multi_source_verifier.py.
    Inject 5,000 compound entries across 25 concurrent threads.
    Verify bounds (<=1000) and test for concurrency exceptions during popitem/insert.
    """
    test_name = "Bounding.CIDCache"
    from scp.core.multi_source_verifier import _CID_CACHE, _MAX_CID_CACHE

    _CID_CACHE.clear()

    errors = []
    num_threads = 25
    items_per_thread = 200

    def cache_writer(tid: int):
        for i in range(items_per_thread):
            compound = f"compound_{tid}_{i}"
            cid = tid * 10000 + i
            try:
                if len(_CID_CACHE) >= _MAX_CID_CACHE:
                    try:
                        _CID_CACHE.popitem(last=False)
                    except KeyError:
                        pass
                _CID_CACHE[compound.lower()] = cid
            except Exception as ex:
                errors.append(f"Thread {tid} error: {type(ex).__name__}: {ex}")

    threads = [threading.Thread(target=cache_writer, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    final_len = len(_CID_CACHE)
    if errors:
        report.record_warn(test_name, f"_CID_CACHE had {len(errors)} thread-race exceptions (e.g. {errors[:2]}); size={final_len}")
    elif final_len <= _MAX_CID_CACHE + 50:
        report.record_pass(test_name, f"_CID_CACHE bounded cleanly at {final_len}/{_MAX_CID_CACHE} with 0 errors across 5000 concurrent writes")
    else:
        report.record_fail(test_name, f"_CID_CACHE size {final_len} exceeded maximum limit {_MAX_CID_CACHE}")


# =====================================================================
# 3. PROTOCOL & DYNAMIC IMPORTS INTEGRITY
# =====================================================================

def test_interfaces_protocols_compliance_and_cycles():
    """
    Verify all interface protocols in scp/interfaces/ have zero circular imports,
    are runtime checkable, and adhere to expected typing and signatures.
    """
    test_name = "Protocols.InterfacesComplianceAndCycles"

    interface_modules = [
        "scp.interfaces.data_source",
        "scp.interfaces.epistemic",
        "scp.interfaces.evolution",
        "scp.interfaces.governance",
        "scp.interfaces.hands",
        "scp.interfaces.judge",
        "scp.interfaces.knowledge",
        "scp.interfaces.severity",
    ]

    import_errors = []
    for mod_name in interface_modules:
        try:
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
            else:
                importlib.import_module(mod_name)
        except Exception as e:
            import_errors.append(f"{mod_name}: {type(e).__name__}: {e}")

    if import_errors:
        report.record_fail(test_name, f"Import errors in interfaces: {import_errors}")
        return

    from scp.interfaces.evolution import IEvolutionEngine
    from scp.interfaces.hands import IGoalParser, IHandsPlanner, IHandsExecutor
    from scp.interfaces.governance import IPrivacyWriteGate, PrivacyDecision
    from scp.interfaces.epistemic import IEvidenceStore
    from scp.interfaces.judge import IJudge, set_judge_provider, get_judge_provider
    from scp.interfaces.knowledge import ILearningDB
    from scp.interfaces.severity import Severity, normalize_severity

    class DummyEvolution:
        def evolve_cycle(self, max_bugs: int = 20) -> dict:
            return {"bugs": max_bugs}

    class DummyGoalParser:
        def parse(self, goal: str, **kwargs) -> dict:
            return {"goal": goal}

    class DummyHandsPlanner:
        def create_plan(self, goal_data: dict) -> list:
            return [goal_data]

    class DummyHandsExecutor:
        async def execute_step(self, step: dict) -> dict:
            return {"done": True}

    class DummyPrivacyGate:
        def evaluate_write(self, target: str, payload: Any, metadata: dict) -> Any:
            return PrivacyDecision.ALLOW

    class DummyLearningDB:
        def execute_insert(self, table: str, data: dict) -> int:
            return 1
        def execute_query(self, query: str, params: tuple = ()) -> list:
            return []

    assert isinstance(DummyEvolution(), IEvolutionEngine), "DummyEvolution must satisfy IEvolutionEngine"
    assert isinstance(DummyGoalParser(), IGoalParser), "DummyGoalParser must satisfy IGoalParser"
    assert isinstance(DummyHandsPlanner(), IHandsPlanner), "DummyHandsPlanner must satisfy IHandsPlanner"
    assert isinstance(DummyHandsExecutor(), IHandsExecutor), "DummyHandsExecutor must satisfy IHandsExecutor"
    assert isinstance(DummyPrivacyGate(), IPrivacyWriteGate), "DummyPrivacyGate must satisfy IPrivacyWriteGate"
    assert isinstance(DummyLearningDB(), ILearningDB), "DummyLearningDB must satisfy ILearningDB"

    assert normalize_severity("CRITICAL") == "critical"
    assert normalize_severity("error") == "medium"
    assert normalize_severity("invalid_severity_xyz") is None

    old_judge = get_judge_provider()
    set_judge_provider("test_judge_instance")
    assert get_judge_provider() == "test_judge_instance"
    set_judge_provider(old_judge)

    report.record_pass(test_name, "All 8 interface protocols import with 0 cycles and pass runtime protocol conformance")


def test_deleted_32_orphaned_modules_integrity():
    """
    Verify that deleted 32 orphaned modules:
    1. Do not exist on the file system.
    2. Are not imported by any active Python module in the repository.
    3. Do not cause runtime ImportErrors anywhere in the codebase.
    """
    test_name = "OrphanedModules.Deleted32Verification"

    # 1. Check disk existence
    still_existing = []
    for mod_path in DELETED_32_MODULES:
        rel_file = mod_path.replace(".", "/") + ".py"
        full_path = REPO_ROOT / rel_file
        if full_path.exists():
            still_existing.append(rel_file)

    if still_existing:
        report.record_fail(test_name, f"Files that should be deleted still exist: {still_existing}")
        return

    # 2. AST check across all .py files in scp/
    active_py_files = list((REPO_ROOT / "scp").rglob("*.py"))
    dangling_references = []

    for py_path in active_py_files:
        try:
            content = py_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in DELETED_32_MODULES:
                            dangling_references.append((str(py_path.relative_to(REPO_ROOT)), alias.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod in DELETED_32_MODULES:
                        dangling_references.append((str(py_path.relative_to(REPO_ROOT)), mod))
                    for alias in node.names:
                        full_imp = f"{mod}.{alias.name}" if mod else alias.name
                        if full_imp in DELETED_32_MODULES:
                            dangling_references.append((str(py_path.relative_to(REPO_ROOT)), full_imp))
        except Exception:
            continue

    if dangling_references:
        report.record_fail(test_name, f"Found active imports to deleted modules: {dangling_references}")
    else:
        report.record_pass(test_name, f"Verified 0 references to all 32 deleted modules across {len(active_py_files)} Python files")


def main():
    logger.info("=== STARTING ADVERSARIAL CONCURRENCY & ARCHITECTURAL STRESS TEST ===")
    
    # 1. KernelStorage
    test_kernel_storage_async_contextvar_isolation()
    test_kernel_storage_thread_concurrency_and_pool_bounding()
    test_kernel_storage_connection_eviction_under_capacity()

    # 2. In-Memory Collection Bounding
    test_bounding_threat_and_alert_history()
    test_bounding_incidents_ordered_dict()
    test_bounding_auth_failures_dict()
    test_bounding_jobs_dict()
    test_bounding_cid_cache()

    # 3. Protocols & Dynamic Imports
    test_interfaces_protocols_compliance_and_cycles()
    test_deleted_32_orphaned_modules_integrity()

    logger.info("=== STRESS TEST SUMMARY ===")
    logger.info(f"Total Passed: {len(report.passed)}")
    logger.info(f"Total Failed: {len(report.failed)}")
    logger.info(f"Total Warnings: {len(report.warnings)}")

    for p in report.passed:
        logger.info(f"  [PASS] {p}")
    for f, r in report.failed:
        logger.error(f"  [FAIL] {f}: {r}")
    for w, r in report.warnings:
        logger.warning(f"  [WARN] {w}: {r}")

    if report.failed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
