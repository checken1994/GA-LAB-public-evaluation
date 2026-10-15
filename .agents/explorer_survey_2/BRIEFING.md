# BRIEFING — 2026-09-22T00:15:00+07:00

## Mission
Audit Requirement Domain R2 (Security & Secret Handling) and Domain R5 (Runtime Correctness & Concurrency) across the entire SCP codebase.

## 🔒 My Identity
- Archetype: explorer
- Roles: Security & Runtime Explorer (Survey Phase)
- Working directory: D:\scp\.agents\explorer_survey_2
- Original parent: 5ff8d0f3-3557-4c8d-97a6-d96617312bf1
- Milestone: Survey Phase (Domains R2 and R5 Audit)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Audit Domain R2 (Security & Secret Handling) and Domain R5 (Runtime Correctness & Concurrency)
- Strict evidence standard: exact file paths, line numbers, severity, code snippet / evidence
- Zero tolerance for hallucination or speculative claims

## Current Parent
- Conversation ID: 5ff8d0f3-3557-4c8d-97a6-d96617312bf1
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `scp/core/trace_contract.py`, `scp/core/trace_store.py`, `scp/api_server_parts/_trace_impl.py`
  - `scp/api_server.py`, `scp/api/chat.py`, `scp/security/auth.py`, `scp/security/jwt_guard.py`
  - `scp/api/routes/` (all 28 route modules: batch_benchmark, pc_controller, web_control, risk, webhook, etc.)
  - `scp/pc_control/pc_controller.py`, `scp/web_control/web_navigator.py`, `scp/web_control/browser_session.py`
  - `scp/core/chat_memory_store.py`, `scp/trace_ledger.py`, `scp/kernel_storage.py`, `scp/kernel_storage_pg.py`
  - `scp/core/db_manager.py`, `scp/core/db_manager_parts/`
  - `mini-services/llm-bridge/`, `mini-services/loop-scheduler/`
  - `compose.yml`, `.env.example`, `.gitignore`
- **Key findings**:
  - R2-F01 (CRITICAL): Unauthenticated `/v3/trace/{trace_id}` with zero redaction in `api_server.py:541-566`.
  - R2-F02 (CRITICAL): Multiple redaction blind spots in `trace_contract.py:44-64` (value leakage, missing keys, header tuple bypass, truncation removed).
  - R2-F03 (HIGH): Egress policy bypass in `web_navigator.py:129-130` and `browser_session.py:145-146, 158-159` (only SSRF check, bypasses `SCP_EGRESS_MODE=deny`).
  - R2-F04 (HIGH): SQL injection in `learning_db.py:63-70` via f-string table and dictionary keys.
  - R2-F05 (HIGH): Path traversal vector in `batch_benchmark_routes.py:40-43` via unvalidated `job_id`.
  - R2-F06 (HIGH): Unauthenticated endpoints in `swe_bench_routes.py:15-16` (`/chat/completions`) and `api_server.py:356-358` (`/metrics`).
  - R2-F07 (MEDIUM): Unauthenticated LLM bridge microservice on localhost port 11435 (`core.ts:1001-1055`).
  - R2-F08 (MEDIUM): Credentials passed in URL query strings in `chat.py:252` and `dashboard_html.py:203-216`.
  - R5-F01 (CRITICAL): Silent data loss and race condition during `ChatMemoryStore` pruning (`chat_memory_store.py:78-83, 115-146`).
  - R5-F02 (CRITICAL): Corrupted cryptographic hash chain & $O(N)$ memory/IO scaling in `trace_ledger.py:28-34`.
  - R5-F03 (CRITICAL): Shared SQLite connection query execution outside database lock in `db_manager.py:139-158`.
  - R5-F04 (HIGH): Async transaction clash with thread-local connection in `kernel_storage.py:97-146`.
  - R5-F05 (HIGH): Unbounded connection collection growth and post-close failure in `kernel_storage.py:115-123, 166-175`.
  - R5-F06 (HIGH): Multiple unbounded memory growth collections (`webhook.py`, `risk_routes.py`, `auth.py`, `batch_benchmark_routes.py`, etc.).
  - R5-F07 (HIGH): Unmanaged threads (`while True` with no stop event) and unawaited cancelled tasks on shutdown (`lifespan.py:312-334, 448-477`).
  - R5-F08 (MEDIUM): Unsynchronized shared state in `chat.py:175-213` and `risk_routes.py:111-124`.
  - R5-F09 (MEDIUM): Unmanaged `subprocess.Popen` browser spawning in `browser_session.py:171`.
- **Unexplored areas**: None within domains R2 and R5; complete survey achieved.

## Key Decisions Made
- Structured the findings systematically by severity (CRITICAL, HIGH, MEDIUM) within R2 and R5.
- Formulated clear evidence chains citing exact file paths, line numbers, and verbatim code excerpts.

## Artifact Index
- `D:\scp\.agents\explorer_survey_2\progress.md` — Liveness & task tracking
- `D:\scp\.agents\explorer_survey_2\DISPATCH.md` — Received dispatch records
- `D:\scp\.agents\explorer_survey_2\BRIEFING.md` — Persistent working memory
- `D:\scp\.agents\explorer_survey_2\handoff.md` — Comprehensive Handoff Report (to be written)
