# Comprehensive Security & Architecture Audit Report: Stream R3
**Target**: TaskKernel Architecture, Concurrency & Data Integrity  
**Auditor**: Explorer R3  
**Project Root**: `D:\scp`  
**Working Directory**: `D:\scp\.agents\teamwork\explorer_r3`  
**Date**: 2026-09-27  
**Mode**: Pure Read-Only Audit  

---

## Executive Summary

Stream R3 conducted an in-depth audit of TaskKernel state transitions, lease management and OCC rowcount validation, SQLite locking and WAL concurrency, append-only file atomicity, and cryptographic ledger provenance across the SCP kernel and storage modules.

---

## Severity Summary Table

| Finding ID | Title | File Path & Lines | Severity | SCP DNA Principle |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-R3-01** | `expire_leases` OCC Rowcount Validation Gap & Watchdog Starvation | `scp/task_kernel_parts/taskkernel.py:805-865` | **CRITICAL** | DNA #2 (Vòng lặp khép kín)<br>DNA #9 (No harm) |
| **SEC-R3-02** | Lease Hijacking in `expire_leases` Active Lease Eviction | `scp/task_kernel_parts/taskkernel.py:820-850` | **CRITICAL** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #26 (Reality có quyền cuối cùng) |
| **SEC-R3-03** | Task Rebuild Impossibility from Event Journal Alone | `scp/task_kernel_parts/taskkernel.py:2032-2081` | **HIGH** | DNA #8 (KB accumulation)<br>DNA #23 (Quay về điểm bắt đầu) |
| **SEC-R3-04** | State Machine Inconsistency: `WAITING_APPROVAL` Missing from `STATES` | `scp/task_kernel_parts/definitions.py:25-55` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #16 (Học nói phạm vi) |
| **SEC-R3-05** | Unkeyed SHA-256 in Event Journal & Audit Ledger Provenance Skip | `scp/task_kernel_parts/taskkernel.py:195-210`<br>`scp/core/autonomous_ledger.py:90-135` | **HIGH** | DNA #6 (Gốc tin cậy bên ngoài)<br>DNA #22 (PASS ≠ TRUE) |
| **SEC-R3-06** | Unlocked Concurrent Appends & Windows File Handle Crashes in `.jsonl` Files | `scp/history/evidence_ledger.py:71`<br>`scp/hands/hands_executor.py:108,114`<br>`scp/brain/error_store.py:100-155` | **HIGH** | DNA #2 (Vòng lặp khép kín)<br>DNA #9 (No harm) |
| **SEC-R3-07** | Missing SQLite WAL Mode & Busy Timeout Across 5 Subsystem Databases | `scp/capabilities/vector_db.py:45`<br>`scp/persistence/db.py:30-50`<br>`scp/kernel_storage.py:120-140` | **MEDIUM** | DNA #9 (No harm)<br>DNA #26 (Reality có quyền cuối cùng) |

---

## Detailed Findings & Code Evidence

### SEC-R3-01: `expire_leases` OCC Rowcount Validation Gap & Watchdog Starvation (CRITICAL)
- **File**: `scp/task_kernel_parts/taskkernel.py:805-865`
- **Code Snippet**:
```python
860: cur.execute("UPDATE leases SET status='EXPIRED', updated_at=? WHERE lease_id=?", (now_iso(), lease_id))
861: # MISSING: if cur.rowcount <= 0: raise OptimisticLockError(...)
862: cur.execute("UPDATE queue_accounts SET in_flight = in_flight - 1 WHERE account_id=?", (account_id,))
863: # MISSING: if cur.rowcount <= 0: raise OptimisticLockError(...)
```
- **Risk / Exploit Scenario**:
While task state updates verify rowcount, lines 860 and 862 update `leases` and `queue_accounts` without verifying `cur.rowcount > 0`. If a lease was concurrently modified or removed, the query silently updates 0 rows without raising `OptimisticLockError`. Furthermore, because all expired leases in a cycle are processed in a single transaction block, if any task encounters an OCC conflict, the entire batch transaction rolls back, preventing any expired leases from being cleared (watchdog starvation).
- **DNA Violation**: DNA #2 (Vòng lặp khép kín), DNA #9 (No harm).

### SEC-R3-02: Lease Hijacking in `expire_leases` Active Lease Eviction (CRITICAL)
- **File**: `scp/task_kernel_parts/taskkernel.py:820-850`
- **Code Snippet**:
```python
825: # Branches 1, 2, 3 sweep expired leases from the 'leases' table
826: # BUT they fail to check: task["active_lease_id"] == lease["lease_id"]
827: cur.execute("UPDATE tasks SET state='QUEUED', active_lease_id=NULL WHERE task_id=?", (task_id,))
```
- **Risk / Exploit Scenario**:
If worker A's lease expires after task T has already been reclaimed and leased to worker B under a new active lease ID, the background `expire_leases` sweeper matches the old expired lease record and unconditionally sets `active_lease_id=NULL` and `state='QUEUED'` on task T. This forcibly hijacks and invalidates the healthy running task of worker B.
- **DNA Violation**: DNA #6 (Gốc tin cậy bên ngoài), DNA #26 (Reality có quyền cuối cùng).

### SEC-R3-03: Task Rebuild Impossibility from Event Journal Alone (HIGH)
- **File**: `scp/task_kernel_parts/taskkernel.py:2032-2081`
- **Code Snippet**:
```python
2046: task = self._task(task_id)  # Raises NotFound(task_id) if row missing in 'tasks' table!
...
2067: cur.execute('UPDATE tasks SET state=?, version=version+1... WHERE task_id=? AND version=?', ...)
```
- **Risk / Exploit Scenario**:
The architectural claim that the `tasks` table is an expendable, rebuildable projection of the event journal is false. `rebuild_projection()` assumes the row already exists in `tasks` and issues an `UPDATE`. If the `tasks` table row is lost or corrupted, `rebuild_projection()` crashes with `NotFound`. Moreover, `TASK_CREATED` event payloads omit initial metadata (task owner, goal, risk tier, deadline), making complete projection reconstruction impossible from events alone.
- **DNA Violation**: DNA #8 (KB accumulation), DNA #23 (Quay về điểm bắt đầu).

### SEC-R3-04: State Machine Inconsistency: `WAITING_APPROVAL` Missing from `STATES` (HIGH)
- **File**: `scp/task_kernel_parts/definitions.py:25-55`
- **Code Snippet**:
```python
# definitions.py
STATES = {"SUBMITTED", "QUEUED", "LEASED", "RUNNING", "WAITING_TOOL", "VERIFYING", "COMPLETED", "FAILED", ...}
# WAITING_APPROVAL is present in ALLOWED_TRANSITIONS but absent from STATES set!
```
- **Risk / Exploit Scenario**:
`WAITING_APPROVAL` is defined in state transition maps but missing from the canonical `STATES` set. To prevent transition rejections, ad-hoc patches were introduced (`if to_state not in STATES and to_state != "WAITING_APPROVAL"`). This divergent state definition breaks static state validation and can cause unhandled transition errors in queue dispatchers.
- **DNA Violation**: DNA #6 (Gốc tin cậy bên ngoài), DNA #16 (Học nói phạm vi).

### SEC-R3-05: Unkeyed SHA-256 in Event Journal & Audit Ledger Provenance Skip (HIGH)
- **File**: `scp/task_kernel_parts/taskkernel.py:195-210`, `scp/core/autonomous_ledger.py:90-135`
- **Code Snippet**:
```python
# taskkernel.py: event journal hash chain
202: return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()  # Bare unkeyed hash!

# autonomous_ledger.py
115: if not self.hmac_key and not self.require_hmac:
116:     # Falls back to unkeyed SHA-256 and skips HMAC validation in verify_provenance()
```
- **Risk / Exploit Scenario**:
The TaskKernel event journal hash chain relies on unkeyed SHA-256. Anyone with write access to SQLite can rewrite historical event payloads and recompute matching hashes without detection. Similarly, if `AutonomousAuditLedger` runs without `SCP_LEDGER_HMAC_KEY`, it downgrades to bare SHA-256 and disables cryptographic signature verification.
- **DNA Violation**: DNA #6 (Gốc tin cậy bên ngoài), DNA #22 (PASS ≠ TRUE).

### SEC-R3-06: Unlocked Concurrent Appends & Windows File Handle Crashes in `.jsonl` Files (HIGH)
- **File**: `scp/history/evidence_ledger.py:71`, `scp/hands/hands_executor.py:108,114`, `scp/brain/error_store.py:100-155`
- **Code Snippet**:
```python
# evidence_ledger.py: called on every chat turn
71: with target.open("a", encoding="utf-8", newline="\n") as handle:
72:     handle.write(line)  # ZERO LOCKS, reads entire file on append -> race condition & forked chain

# brain/error_store.py:
155: os.replace(tmp_path, target_path)  # PermissionError on Windows if handle held open!
```
- **Risk / Exploit Scenario**:
Multiple append-only audit files (`history_evidence.jsonl`, `audit.jsonl`, `checkpoints.jsonl`, `learning_runs.jsonl`) operate without file locks or fsync calls. Under concurrent requests, writes interleave and corrupt JSON lines. In `error_store.py`, `_rewrite_jsonl` calls `os.replace` on open files, raising `PermissionError` on Windows.
- **DNA Violation**: DNA #2 (Vòng lặp khép kín), DNA #9 (No harm).

### SEC-R3-07: Missing SQLite WAL Mode & Busy Timeout Across 5 Subsystem Databases (MEDIUM)
- **File**: `scp/capabilities/vector_db.py:45`, `scp/persistence/db.py:30-50`, `scp/kernel_storage.py:120-140`
- **Code Snippet**:
```python
# vectors.db, KnowledgeControlDB, LearningDB
conn = sqlite3.connect(self.db_path)
# Neither PRAGMA journal_mode=WAL nor PRAGMA busy_timeout=5000 is executed!
```
- **Risk / Exploit Scenario**:
Databases default to rollback journal mode without busy timeouts. Concurrent access by background schedulers and FastAPI workers triggers immediate `sqlite3.OperationalError: database is locked`. In `KernelStorage`, child asyncio tasks share connection handles via `ContextVar` without serialization locks.
- **DNA Violation**: DNA #9 (No harm), DNA #26 (Reality có quyền cuối cùng).
