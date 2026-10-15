# ADVERSARIAL CHALLENGER REPORT: Milestone 2 (P1 Fixes)

- **Agent**: Challenger 2 (Empirical Challenger: Concurrency & Architectural Stress)
- **Working Directory**: `D:\scp\.agents\challenger_p1_2`
- **Target Subsystems**: `KernelStorage` (`scp/kernel_storage.py`, `scp/kernel_storage_pg.py`), In-Memory Collections (`_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`), Protocols & Orphaned Modules (`scp/interfaces/`, 32 deleted modules).
- **Handoff Type**: Hard (Review Complete)
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Directly observed empirical test results, verbatim tracebacks, and code inspection:

### 1.1 `KernelStorage` Failures (R5-04 & R5-05)

When executing the adversarial stress test harness `python tools/stress_p1_concurrency.py`:

```
2026-09-22 15:58:35,031 [ERROR] FAIL: KernelStorage.AsyncContextVarIsolation - ContextVar isolation FAILED: all 5 concurrent async tasks were assigned the IDENTICAL connection ID (2300110324256) due to parent context inheritance! Errors: [('task_1', 'OperationalError', 'cannot start a transaction within a transaction'), ('task_3', 'OperationalError', 'cannot start a transaction within a transaction')]

2026-09-22 15:58:35,087 [ERROR] FAIL: KernelStorage.ThreadConcurrencyAndPoolBounding - Multi-thread concurrency FAILED: 9/10 threads crashed (e.g. [('thread_2', 'OperationalError', 'cannot start a transaction within a transaction'), ('thread_9', 'OperationalError', 'cannot start a transaction within a transaction'), ('thread_8', 'OperationalError', 'cannot start a transaction within a transaction')]). Root cause: idle connection reuse without checkout locks permits connection aliasing across threads.

2026-09-22 15:58:46,153 [ERROR] FAIL: KernelStorage.ConnectionEvictionUnderCapacity - Eviction of in-use connection confirmed: active connection closed or database locked during write slot contention, triggering OperationalError: database is locked.
```

#### Code Inspection of `scp/kernel_storage.py`:

1. **Lines 83-91**:
   ```python
   self._conn_ctx: contextvars.ContextVar[sqlite3.Connection | None] = contextvars.ContextVar(
       f"sqlite_kernel_conn_{id(self)}", default=None
   )
   self._all_conns: deque[sqlite3.Connection] = deque()
   self._conn_guard = threading.Lock()
   c = self._get_conn()
   c.execute("PRAGMA journal_mode=WAL")
   ```
   *Observation*: In `__init__`, calling `c = self._get_conn()` sets `self._conn_ctx.set(new_conn)` in the parent execution context. When coroutines are spawned via `asyncio.create_task()` or `asyncio.gather()`, Python shallow-copies the context, causing all child coroutines to inherit `self._conn_ctx.get() == c`. ContextVar isolation across async tasks is completely neutralized.

2. **Lines 120-125**:
   ```python
   # Reuse idle connection not in transaction
   for candidate in self._all_conns:
       if not candidate.in_transaction:
           self._conn_ctx.set(candidate)
           return candidate
   ```
   *Observation*: `_get_conn()` considers any connection where `candidate.in_transaction == False` as reusable. When Thread 1 calls `_get_conn()`, `candidate.in_transaction` is `False`. Before Thread 1 executes `candidate.execute("BEGIN IMMEDIATE")`, Thread 2 calls `_get_conn()`, observes `candidate.in_transaction == False`, and receives the same connection. Both threads proceed to execute `BEGIN IMMEDIATE` on the identical connection instance, crashing with `sqlite3.OperationalError: cannot start a transaction within a transaction` and `OperationalError: not an error` (`SQLITE_MISUSE` code 21).

3. **Lines 140-152**:
   ```python
   def begin(self) -> None:
       """Acquire write lock + BEGIN IMMEDIATE (bounded retry on SQLITE_BUSY / locked)."""
       last_error: Exception | None = None
       for attempt in range(25):
           try:
               self._get_conn().execute("BEGIN IMMEDIATE")
               return
           except sqlite3.OperationalError as exc:
               err_msg = str(exc).lower()
               if "locked" not in err_msg and "busy" not in err_msg:
                   raise
               last_error = exc
               time.sleep(0.05 * min(attempt + 1, 4))
   ```
   *Observation*: `time.sleep()` is synchronous. When coroutine A holds an active transaction and coroutine B encounters `database is locked`, coroutine B calls `time.sleep(...)`, blocking the entire OS event loop thread. Coroutine A is starved and unable to progress or commit, deadlocking the process for up to 250 seconds.

4. **Lines 126-133**:
   ```python
   # Bounded creation: if capacity reached, recycle oldest non-in-transaction or purge
   if len(self._all_conns) >= self._max_conns:
       oldest = self._all_conns.popleft()
       try:
           oldest.close()
       except sqlite3.Error:
           pass
   ```
   *Observation*: Despite the comment ("recycle oldest non-in-transaction"), there is no guard checking `oldest.in_transaction`. When connection count reaches `_max_conns`, `self._all_conns.popleft().close()` terminates connections currently executing transactions in other threads.

5. **`scp/kernel_storage_pg.py:323-337`**:
   The PostgreSQL implementation shares the identical flaws:
   ```python
   for candidate in self._all_conns:
       status = candidate.info.transaction_status
       if status == 0:  # IDLE
           self._conn_ctx.set(candidate)
           return candidate

   if len(self._all_conns) >= self._max_conns:
       oldest = self._all_conns.popleft()
       try:
           oldest.close()
   ```

---

### 1.2 In-Memory Collection Bounding (R5-06) — PASSED

Directly observed stress testing 6 in-memory collections under concurrent multi-threaded load:

1. **`_threat_history` & `_alert_history` (`scp/api/webhook.py:82-83`)**:
   - Injected 5,000 threats and alerts across 25 concurrent threads.
   - Bounded at exactly 1,000/1,000 items (`deque(maxlen=1000)`). FIFO eviction confirmed. No exceptions.
2. **`_incidents` (`scp/api/routes/risk_routes.py:40-41`)**:
   - Injected 5,000 incidents across 25 concurrent threads with `_incidents_lock`.
   - Bounded at exactly 1,000/1,000 items (`OrderedDict` + `popitem(last=False)`). No exceptions.
3. **`_auth_failures` (`scp/security/auth.py:59-61`)**:
   - Injected 12,000 distinct IP failures across 30 concurrent threads with `_auth_failures_lock`.
   - Bounded at exactly 5,000/5,000 items. Oldest IP eviction confirmed.
4. **`_JOBS` (`scp/api/routes/batch_benchmark_routes.py:31-32`)**:
   - Injected 150 dead thread references with `_JOBS_LOCK`.
   - Dead threads pruned, bounded cleanly to <= 100 items.
5. **`_CID_CACHE` (`scp/core/multi_source_verifier.py:268-269`)**:
   - Injected 5,000 compound lookups across 25 concurrent threads.
   - Bounded cleanly at 1,000/1,000 items with 0 errors.

---

### 1.3 Protocol & Dynamic Imports (R3-02 & R3-03) — PASSED

1. **Protocol Compliance & Zero Circular Imports (`scp/interfaces/`)**:
   - All 8 modules (`data_source`, `epistemic`, `evolution`, `governance`, `hands`, `judge`, `knowledge`, `severity`) imported cleanly with 0 circular dependency cycles.
   - `@runtime_checkable` protocol compliance verified for `IEvolutionEngine`, `IGoalParser`, `IHandsPlanner`, `IHandsExecutor`, `IPrivacyWriteGate`, `IEvidenceStore`, `IJudge`, `ILearningDB`, and `Severity`.
2. **Deleted 32 Orphaned Modules (R3-02)**:
   - Verified that all 32 modules are deleted from disk.
   - AST search across all 632 active `.py` files in `scp/` confirmed 0 import statements referencing any deleted modules.
   - Zero runtime `ImportError` or `ModuleNotFoundError` across the repository.

---

## 2. Logic Chain

1. **From Observation 1.1 to ContextVar Failure**:
   - In `SQLiteKernelStorage.__init__`, `self._get_conn()` calls `self._conn_ctx.set(new_conn)` during object initialization.
   - Python's `asyncio` task creation (`asyncio.create_task`, `asyncio.gather`) automatically copies the creator's contextvars into child tasks.
   - Therefore, all async tasks spawned within the event loop start with `self._conn_ctx.get()` already pointing to the instance created at init.
   - When `_get_conn()` is called within any child task, `conn = self._conn_ctx.get()` returns the shared root connection without allocating a per-task connection.
   - When multiple tasks invoke `storage.begin()`, they execute `BEGIN IMMEDIATE` on the same connection, triggering `OperationalError: cannot start a transaction within a transaction`.

2. **From Observation 1.1 to Multi-Thread Connection Aliasing**:
   - `_get_conn()` searches `_all_conns` for a connection where `not candidate.in_transaction`.
   - A connection is not in transaction until `candidate.execute("BEGIN IMMEDIATE")` completes.
   - Under concurrent thread access, Thread 1 obtains `candidate` and exits `_conn_guard`. Before Thread 1 can execute `BEGIN IMMEDIATE`, Thread 2 enters `_conn_guard`, observes `not candidate.in_transaction`, and is granted the identical `candidate`.
   - Both threads concurrently call `execute("BEGIN IMMEDIATE")` on the same C connection, corrupting internal SQLite state (`SQLITE_MISUSE` / "not an error") and failing with `cannot start a transaction within a transaction`.

3. **From Observation 1.1 to Event Loop Deadlock**:
   - SQLite permits only one writer at a time under WAL mode.
   - When one coroutine holds the write lock, any other coroutine calling `begin()` catches `sqlite3.OperationalError` ("database is locked").
   - `begin()` enters a retry loop calling `time.sleep(...)`.
   - Because `time.sleep` blocks the OS thread, the single-threaded asyncio event loop ceases to dispatch any callbacks, preventing the lock-holding coroutine from executing `await` steps or calling `commit()`.
   - The result is a mutual block (deadlock) until retry exhaustion.

4. **From Observation 1.1 to Active Connection Eviction**:
   - When `len(self._all_conns) >= self._max_conns`, `self._all_conns.popleft().close()` is called unconditionally without checking `in_transaction` or checking out state.
   - If active transactions exist, the oldest active connection is closed while in use, raising `ProgrammingError: Cannot operate on a closed database` or `database is locked`.

5. **Contrasting Sequential Tests vs. Concurrent Reality**:
   - `pytest tests/T04_kernel/ -q` passes (259 passed, 23 skipped) because each test runs sequentially on a single thread.
   - Empirical stress testing reveals that under concurrent multi-task and multi-thread operation, `KernelStorage` breaks immediately.

---

## 3. Caveats

1. PostgreSQL backend (`PgKernelStorage`) was evaluated via static and architectural code analysis because a live PostgreSQL instance is not running locally in this test environment. The code in `scp/kernel_storage_pg.py:323-337` shares the identical connection selection and eviction patterns as `SQLiteKernelStorage`.
2. The remaining 66 legacy reality tests (`reality_*.py`) in `tests/reality-tests/` were not modified, as confirmed in the worker's handoff (they are not discovered by standard pytest and remain historical AST fixtures).

---

## 4. Conclusion

While Batches 1, 3, 4, and the in-memory bounds of Batch 2 (R5-06) meet quality requirements, **the concurrency implementation of `KernelStorage` (R5-04 and R5-05) in both `scp/kernel_storage.py` and `scp/kernel_storage_pg.py` is critically broken and unsafe for production concurrent workloads**.

### Required Remediation (Actionable Fixes for Worker):

1. **Do not populate `_conn_ctx` in `__init__`**:
   - In `__init__`, open a temporary setup connection for PRAGMAs and close it, or explicitly call `self._conn_ctx.set(None)` so that child tasks and threads do not inherit a pre-bound connection.
2. **Implement an Exclusive Checkout / Pool Pattern with Lock**:
   - Instead of checking `not candidate.in_transaction`, track `_checked_out: set[sqlite3.Connection]`.
   - When a connection is lent to a task/thread via `_get_conn()`, mark it as checked out until the transaction commits/rolls back, or use a `threading.local` connection cache per thread plus a dedicated transaction lock.
3. **Async-Safe Write Serialization**:
   - Serialize write transactions in SQLite using a mutex / `threading.Lock` (or `asyncio.Lock` if async-native) so that only ONE writer attempts `BEGIN IMMEDIATE` at a time. This eliminates `database is locked` retries and prevents `time.sleep` event loop starvation.
4. **Non-destructive Pool Bounding**:
   - When capacity is reached, NEVER close a connection that is currently checked out or has an active transaction (`in_transaction`). Only evict idle, non-checked-out connections.

---

## 5. Verification Method

To independently reproduce the failures:

1. **Run Adversarial Concurrency Harness**:
   ```bash
   python tools/stress_p1_concurrency.py
   ```
   *Result*: Fails with exit code 1, reporting:
   - `KernelStorage.AsyncContextVarIsolation`: ContextVar isolation FAILED (identical connection ID across async tasks).
   - `KernelStorage.ThreadConcurrencyAndPoolBounding`: Multi-thread concurrency FAILED (9/10 threads crashed with `cannot start a transaction within a transaction` or `not an error`).
   - `KernelStorage.ConnectionEvictionUnderCapacity`: Fails due to closing active connections.

2. **Run Standard Sequential Kernel Tests**:
   ```bash
   pytest tests/T04_kernel/ -q
   ```
   *Result*: 259 passed, proving that standard sequential unit tests fail to detect these concurrency bugs.
