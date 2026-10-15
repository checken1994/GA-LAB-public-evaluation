# BRIEFING — 2026-09-21T22:25:00Z

## Mission
Investigate and design concrete fixes for P0 concurrency, persistence, and replay findings: R5-01 (ChatMemoryStore), R5-02 (TraceLedger), R5-03 (db_manager), and R1-02 (EvidenceReplay).

## 🔒 My Identity
- Archetype: explorer
- Roles: read-only investigation, concurrency & replay analysis, synthesis, proposal design
- Working directory: D:\scp\.agents\explorer_p0_2
- Original parent: 2b5b039d-ad9c-4525-8dd0-7eec0014e1fc
- Milestone: Milestone 1 (P0 Critical Security & Data Integrity)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code directly
- Must adhere to Fail-Closed & Evidence-First principles (FA-01 through FA-13)
- Windows compatibility (cross-platform file locking, msvcrt / portalocker / fcntl fallback, no WinError 32)
- All proposed changes delivered via handoff.md in working directory

## Current Parent
- Conversation ID: 2b5b039d-ad9c-4525-8dd0-7eec0014e1fc
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `scp/core/chat_memory_store.py`
  - `scp/trace_ledger.py`
  - `scp/core/db_manager.py` & `scp/core/db_manager_parts/*.py`
  - `scp/autofix/evidence_replay.py` & `scp/autofix/runner_phases/post_fix_verify.py`
  - Git history of `evidence_replay.py` (discovered pre-existing BSG-VA architecture in commit `fb9e70a`)
  - `tools/t00_meta_audit.py` FA-04 checking logic
- **Key findings**:
  - R5-01: `ChatMemoryStore` lacks mutex & file locking. `_prune_if_needed()` uses `os.replace` which raises `WinError 32` if the target is open, and concurrent writes are dropped. Designed `ReentrantFileLock` combining in-memory `RLock` and OS file lock (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX) on `.lock` sidecar.
  - R5-02: `TraceLedger.append()` reads whole file on every write ($O(N)$) and lacks synchronization. Empirically reproduced race condition: 5 threads x 10 writes -> 49 entries (1 dropped) and 22 hash chain errors. Designed process-wide `_LedgerState` with $O(1)$ reverse-seeking tail reader and `RLock`. Verified that fixed implementation yields 50/50 entries and 100% valid hash chain.
  - R5-03: `db_manager.py` drops `_db_lock`/`_read_lock` before executing `conn.execute()`. Single `sqlite3.Connection` (`_persistent_conn`) is not thread-safe for concurrent statement execution. Designed holding `_db_lock` throughout `conn.execute()` and row fetching (`.fetchall()` / `.fetchone()`).
  - R1-02: `EvidenceReplay.verify()` returns hardcoded `{"ok": True, "status": "VERIFIED"}` causing FA-04 violation in `t00_meta_audit.py`. `compute_bug_signature` returns `"mock_signature"`. Restoring full BSG-VA implementation from commit `fb9e70a` and wiring `verify()` to run real test execution or fail-closed eliminates fake stubs and FA-04 debt.
- **Unexplored areas**: None. All 4 target areas thoroughly inspected and verified with live code and empirical tests.

## Key Decisions Made
- Use sidecar `.lock` file with `ReentrantFileLock` for `ChatMemoryStore` so that `os.replace` on the primary data file never collides with open lock handles.
- Use reverse binary seek for `TraceLedger` tail reading to achieve true $O(1)$ append overhead and maintain sequence cache in memory.
- Hold `_db_lock` and `_read_lock` across the entire execute and fetch cycle in `db_query_one` and `db_query_all`.
- Reconstruct complete BSG-VA framework for `EvidenceReplay` and replace fake return with real test execution and fail-closed handling.

## Artifact Index
- `D:\scp\.agents\explorer_p0_2\DISPATCH.md` — Inbound instructions from orchestrator
- `D:\scp\.agents\explorer_p0_2\BRIEFING.md` — Persistent agent memory and tracking
- `D:\scp\.agents\explorer_p0_2\progress.md` — Liveness and step tracking
- `D:\scp\.agents\explorer_p0_2\handoff.md` — Comprehensive handoff report for implementer
