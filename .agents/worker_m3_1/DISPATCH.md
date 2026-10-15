# Dispatch for worker_m3_1

## 2026-09-23T04:59:03Z

**Milestone**: M3 — Fix Remaining Unfixed Findings (F10-F13, F15-F16)
**Working Directory**: `D:\scp\.agents\worker_m3_1`

## Implementation Tasks
Read `D:\scp\.agents\explorer_m3_1\handoff.md` for exact line numbers, code snippets, and drop-in blueprints:

1. **F10: Judge Crosscheck Crash Fallback & Tautology Fix** (`scp/runtime/judge.py`):
   - In crosscheck fallback (lines 309-314): when secondary vendor fails or crashes, do NOT masquerade as consensus (`cross_model_agreement: True`). Set `degraded: True`, record `cross_model_agreement: False`, flag warning/error in metadata.
   - In `for_text_answer(ai_answer)`: eliminate the `ai_answer in ai_answer` tautology. Validate answer against question requirements or independent evaluation criteria.
2. **F11: `expire_leases` Rowcount OCC Checks** (`scp/task_kernel_parts/taskkernel.py:805-855`):
   - Across all 4 UPDATE branches and lease release in `expire_leases()`, check `cur.rowcount` and raise `OptimisticLockError` if rowcount is unexpected (e.g. 0 rows updated due to concurrent modification).
3. **F12: Semantic Firewall Untrusted Input Inspection** (`scp/core/top_systems_learning.py:263, 318`):
   - In `_fetch_github` and `_fetch_wikipedia`: call `inspect_untrusted()` on external content before ingestion into the learning pipeline, record SHA-256 provenance, and reject prompt injection payloads.
4. **F13: Dashboard SSRF Elimination in Remaining Raw-Fetch Routes** (`dashboard/src/app/api/`):
   - Update `status/route.ts`, `scanners/route.ts`, `loop/route.ts`, `loop/trigger/route.ts`, `autofix/route.ts` to use validated base URLs via `resolveInternalBackendBase()` and `resolveLoopSchedulerBase()`. Disallow arbitrary external URL fetches.
5. **F15: Quorum Removal in Documentation & Tool Import Cleanup**:
   - Update `docs/SCP_ARCHITECTURE.md` (lines 60, 121) to remove quorum references.
   - In `tools/stress_p1_concurrency.py`, remove stale `quorum_why` imports.
6. **F16: Memory Multi-Turn Secret Redaction Patterns** (`scp/core/chat_memory_store.py`):
   - Add compiled regex patterns to `_SECRET_PATTERNS`:
     - JWT: `r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"`
     - GitHub PAT: `r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b"`
     - AWS Access Key: `r"\bAKIA[0-9A-Z]{16}\b"`
     - Google API Key: `r"\bAIza[0-9A-Za-z\\-_]{35}\b"`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run tests:
1. `pytest tests/T07_learning/ tests/T04_kernel/ -q`
2. `pytest tests/ --collect-only -q`
3. `python tools/adversarial_goal3_probe.py`
4. If dashboard files are changed: `bun run --cwd dashboard build`

Write handoff report to `D:\scp\.agents\worker_m3_1\handoff.md` and notify parent orchestrator via `send_message`.
