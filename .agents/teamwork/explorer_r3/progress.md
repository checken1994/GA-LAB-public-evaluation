# Progress — Explorer R3

Last visited: 2026-09-27T07:15:00Z

## Status
Investigating findings across all 5 areas. Deep inspection conducted on:
- `scp/task_kernel_parts/taskkernel.py` & `definitions.py`
- `scp/task_kernel_parts/idempotency.py`
- `scp/kernel_storage.py`
- `scp/core/autonomous_ledger.py`
- `scp/core/trace_store.py`
- `scp/trace_ledger.py`
- `scp/history/evidence_ledger.py`
- `scp/persistence/db.py`
- `scp/capabilities/vector_db.py`
- `scp/security/confirmation_store.py`
- `scp/core/chat_memory_store.py`
- `scp/core/learning_run_ledger.py`
- `scp/core/request_run_ledger.py`
- `scp/brain/error_store.py`

## Discovered Critical Issues So Far:
1. `expire_leases` OCC rowcount validation gap: `UPDATE leases` (line 860) and `UPDATE queue_accounts` (line 862) execute without checking `cur.rowcount > 0` or raising `OptimisticLockError`.
2. `expire_leases` lease hijacking: Branches 1, 2, and 3 do NOT check `task['active_lease_id'] == lease['lease_id']`. If an old lease expires after a task was already re-queued/resumed under a new active lease, `expire_leases` sweeps and forcibly evicts the active worker's new lease.
3. `expire_leases` batch abort: If any lease in the expired loop encounters an `OptimisticLockError`, the entire batch transaction is rolled back, causing watchdog starvation.
4. `rebuild_projection` projection impossibility: If `tasks` row is deleted/lost, `rebuild_projection` raises `NotFound(task_id)` and fails. Moreover, `TASK_CREATED` event does not store task metadata (owner, goal, risk_tier, deadline, etc.), so tasks are NOT rebuildable from the journal.
5. `definitions.py` state machine inconsistency: `WAITING_APPROVAL` is defined in `ALLOWED_TRANSITIONS` but missing from `STATES`, causing ad-hoc bypass checks (`to_state not in STATES and to_state != "WAITING_APPROVAL"`).
6. `TaskKernel` event journal uses unkeyed SHA-256 (`stable_hash`), not HMAC. Journal can be rewritten without secret key.
7. `AutonomousAuditLedger` active production callers check: Called in `scp/hands/hands_executor.py` (`commit_intent` and `commit_result`). However, if initialized without HMAC key and `require_hmac=False`, it falls back to unkeyed SHA-256 and `verify_provenance()` skips HMAC signature verification completely.
8. Append-only `.jsonl` files lack locking:
   - `scp/history/evidence_ledger.py` (`history_evidence.jsonl`) called on every chat response has zero locks, reads whole file on every append, and has race conditions leading to forked hash chains.
   - `scp/hands/hands_executor.py` (`audit.jsonl` and `checkpoints.jsonl`) has zero locks and no fsync.
   - `scp/core/learning_run_ledger.py` has zero locks and no fsync.
   - `scp/brain/error_store.py` (`_atomic_append`) has zero locks despite the name, and `_rewrite_jsonl` crashes on Windows on open handles.
9. SQLite concurrency & missing WAL/timeout pragmas across multiple DBs:
   - `VectorStore` (`data/vectors.db`) has no WAL, no busy_timeout.
   - `KnowledgeControlDB` has no WAL, no busy_timeout.
   - `LearningDB` has no WAL, no busy_timeout.
   - `FoundationDB` has no busy_timeout set.
   - `KernelStorage`: in asyncio tasks, child tasks inherit `ContextVar` and share the same `sqlite3.Connection` without locking, and `begin()` uses synchronous `time.sleep` blocking the event loop.

## Next Steps
- Verify meta-audit task completion
- Structure detailed findings with exact file paths, line numbers, code snippets, severity, risk scenarios, and DNA principle citations
- Write comprehensive handoff report `handoff.md`
