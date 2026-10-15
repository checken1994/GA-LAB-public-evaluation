# Dispatch for explorer_m3_1

**Milestone**: M3 — Fix Remaining Unfixed Findings (F10-F13, F15-F16)
**Working Directory**: `D:\scp\.agents\explorer_m3_1`

## Investigation Scope
1. **F10: Judge Crosscheck Crash Fallback & Answer-Contains-Answer Tautology**:
   - Inspect `scp/runtime/judge.py` (around lines 309-314 and 430-480).
   - Locate where single-vendor fallback occurs silently on crash; formulate fix to flag result as `degraded: True` / raise rather than silent pass.
   - Locate answer-contains-answer tautology (where text contains answer check is trivialized) and formulate genuine semantic crosscheck.
2. **F11: `expire_leases` Rowcount OCC Checks (4 branches)**:
   - Inspect `scp/task_kernel/taskkernel.py` / `scp/task_kernel_parts/taskkernel.py` (around lines 805-855).
   - Identify the 4 branches of `expire_leases` UPDATE queries.
   - Formulate checking `cur.rowcount` after each UPDATE and handling unexpected 0-row results.
3. **F12: Semantic Firewall Untrusted Input Inspection**:
   - Inspect `scp/core/top_systems_learning.py` / `scp/knowledge/top_systems_learning.py` (lines 263, 318).
   - Formulate wiring `inspect_untrusted()` before ingesting external data from GitHub descriptions and Wikipedia sources to block prompt injection.
4. **F13: Dashboard SSRF Elimination in Remaining Raw-Fetch Routes**:
   - Inspect `dashboard/src/app/api/status/route.ts`, `scanners/route.ts`, `loop/route.ts`, `loop/trigger/route.ts`, `autofix/route.ts`.
   - Check how backend URLs are constructed and fetched; eliminate arbitrary target fetching or unvalidated parameters.
5. **F15: Quorum Removal in Documentation & Stale Test Imports**:
   - Inspect `docs/SCP_ARCHITECTURE.md` (around lines 60, 121) where quorum is still advertised as an active security ring.
   - Update architecture docs to accurately reflect quorum removal. Check for any stale test imports.
6. **F16: Memory Multi-Turn Secret Redaction Patterns**:
   - Inspect `ChatMemoryStore` in `scp/memory/chat_memory_store.py` (or wherever defined).
   - Check `_SECRET_PATTERNS` regex list.
   - Formulate addition of JWT (`eyJ...`), GitHub PAT (`ghp_...`), AWS Access Key (`AKIA...`), and Google API Key (`AIza...`) patterns so sensitive credentials in conversation turns are masked.

## Required Output
Write your findings to `D:\scp\.agents\explorer_m3_1\handoff.md`.
Follow the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).

## 2026-09-22T20:08:18Z
You are explorer_m3_1.
Your working directory is D:\scp\.agents\explorer_m3_1.
You MUST read D:\scp\.agents\ORIGINAL_REQUEST.md before starting work.
Also read D:\scp\.agents\explorer_m3_1\DISPATCH.md and D:\scp\.agents\orchestrator_7\PROJECT.md.

Your mission:
Investigate Milestone M3 (Features F10, F11, F12, F13, F15, F16):
- F10: Judge crosscheck crash fallback to degraded flag + answer-contains-answer tautology fix (scp/runtime/judge.py).
- F11: expire_leases rowcount OCC checks across 4 UPDATE branches in scp/task_kernel_parts/taskkernel.py (lines 805-855).
- F12: Semantic firewall inspect_untrusted() before external ingestion in scp/core/top_systems_learning.py (lines 263, 318).
- F13: Dashboard SSRF on remaining raw-fetch routes (status, scanners, loop, loop/trigger, autofix).
- F15: Quorum removal in docs/SCP_ARCHITECTURE.md (lines 60, 121) and cleaning any dead test imports.
- F16: ChatMemoryStore._SECRET_PATTERNS additions for JWT, ghp_, AKIA, AIza in scp/memory/chat_memory_store.py.

Write your findings to D:\scp\.agents\explorer_m3_1\handoff.md following the Handoff Protocol.
When complete, notify parent orchestrator via send_message.
