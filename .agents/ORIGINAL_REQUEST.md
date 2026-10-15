# Original User Request

## 2026-09-08T12:26:38Z

# Teamwork Project Prompt — R2, R3, R6 Remediation

Dự án SCP (Agent OS) đang cần vá 3 lỗ hổng kiến trúc nghiêm trọng cuối cùng (R2, R3, R6) để đạt trạng thái Autonomous 24/7.

Working directory: c:\Users\check\Downloads\scp
Branch hiện tại: omega/gap-01-remediation (hoặc main tuỳ bạn checkout, hãy tạo nhánh mới nếu cần, ví dụ: remediation/R2-R3-R6).

MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13. You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

## Lỗ hổng cần vá

### R2: Execution Bypass (PCController)
- Vấn đề: `PCController` có các phương thức thực thi trực tiếp (VD: chạy command) mà thiếu boundary kiểm tra token hợp lệ từ Unified Broker.
- Yêu cầu: Thêm token boundary vào `PCController`. Bất kỳ request thực thi nào cũng phải có token (HMAC-SHA256 signature hợp lệ) được cấp phát đúng thẩm quyền. Chặn fail-closed nếu thiếu/sai token.

### R3: Provenance Forgery (Verifier receipts)
- Vấn đề: Các biên lai `verification.passed` (verifier receipts) đang thiếu độc lập (cryptographic provenance). Worker có thể tự giả mạo biên lai thành công để lừa Kernel.
- Yêu cầu: Thêm chữ ký số (cryptographic signature/HMAC) vào Receipt. Kernel phải verify chữ ký này trước khi commit trạng thái `COMPLETED`.

### R6: AutoFix Rollback (Cognitive loop perfect isolation)
- Vấn đề: Vòng lặp Cognitive/AutoFix thiếu cơ chế perfect isolation và rollback. Nếu AI áp dụng code lỗi, hệ thống bị hỏng (catastrophic corruption).
- Yêu cầu: Xây dựng cơ chế snapshot/rollback (có thể dùng `data/shadow/` hoặc git stash/restore) cho file trước khi AutoFix áp dụng patch. Tự động rollback nếu Reality Test (pytest) thất bại sau khi patch.

## Yêu cầu Bắt buộc (FA-12, FA-13)
- Vẽ Causal Graph và tạo file báo cáo `EMERGENCY_GAP_REPORT.md` (nếu phát hiện lỗ hổng lân cận).
- Phủ test cho toàn bộ nhân quả (Causal-Driven Test Generation) trong thư mục `tests/`. Chạy `pytest` phải xanh.
- Cuối cùng, tổng hợp kết quả (Fix steps, Test outcomes) vào artifact báo cáo.

## 2026-09-13T21:15:02Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

Hoàn thiện, kiểm thử và hợp nhất (commit) toàn bộ công việc của S26 (xóa 13.8k dòng code cũ) và S24 (logic Question Router T2-first) trong một lần một cách an toàn.

Working directory: `c:\Users\check\Downloads\scp`

## Requirements

### R1. Tích hợp S26 (Expert Unification)
Hoàn thành việc loại bỏ các file legacy (`judge_parts`, `slm_impls`, `slms.py`) theo đúng những gì S26 đã chuẩn bị. Đảm bảo code không bị gãy dependencies.

### R2. Tích hợp S24 (T2-first Routing)
Tích hợp file `question_router.py` và các đoạn code móc nối dở dang trong `ask_kernel_adapter.py`. 

### R3. Sửa lỗi Test (Khắc phục di chứng S22)
Sửa lại hàm `_disable_openrouter` trong bài test `test_ws_chat_fail_closed_when_no_answer_source_available` (thuộc T02) để tắt toàn bộ các LLM Provider mới (Groq, Cerebras, Gemini, Nvidia) vốn được thêm vào từ S22, giúp bài test này xanh trở lại.

## Acceptance Criteria

### Verification & Commit
- [ ] Chạy lệnh `pytest tests/T02_contract tests/T03_capability tests/T07_learning -q` trả về 0 failures.
- [ ] Các lỗi "đỏ" do test cũ gọi vào file đã bị xóa (FA-02) được báo cáo rõ hoặc có cơ chế bypass hợp lệ khi commit.
- [ ] Sau khi test pass, thực hiện chốt commit toàn bộ S24 và S26 vào nhánh hiện tại (`audit/runtime-guard-AUDIT-20260909`).

## 2026-09-21T17:02:21Z

Deep comprehensive audit of the entire SCP (Secure Control Plane) system — a large Python + TypeScript codebase covering a governed AI agent platform with LLM gateway, policy enforcement, backward traceability, knowledge management, and desktop/web dashboard.

Working directory: D:\scp
Integrity mode: development

## System Profile

- **Branch**: `feature/autonomous-mode-antigravity-v2` (HEAD: `6d6256f`)
- **Scale**: ~221,000 Python LOC, 1,142 .py files, 43 active subsystems, 1,937 tests
- **Stack**: Python 3.12 FastAPI backend, Next.js/React dashboard, Bun TypeScript microservices (LLM Bridge, Loop Scheduler)
- **Key subsystems** (by size): `core/` (71 files), `data_sources/` (69), `security/` (44), `meta/` (37), `autofix/` (35), `knowledge/` (26), `runtime/` (13), `api/` (8), `llm_gateway/` (5), `governance/` (4), plus 33 smaller modules
- **Test suites**: T00 (integrity), T01 (boot), T02 (contract), T03 (capability/integrity), T04 (kernel), T05 (gateway), T06 (verifier), T07 (learning), T08 (runtime), T09 (golden_task), T10 (recovery), T11 (release), T12 (unified_chatbot)
- **Existing audit tool**: `python tools/t00_meta_audit.py` — enforces test integrity against baseline
- **Existing test runner**: `pytest tests/ -q` — all 1,937 tests currently pass

## Requirements

### R1. Silent Bugs & Logic Errors

Identify code paths that silently produce incorrect results without raising errors. Focus areas:
- Functions that swallow exceptions or return default/empty values on failure without logging
- Conditional branches that can never be reached (dead branches)
- Type coercion or comparison bugs (e.g., `str` vs `int`, `None` equality)
- Off-by-one errors in slicing, pagination, or range operations
- Async/await misuse (missing `await`, unawaited coroutines, fire-and-forget)
- Mutable default arguments in function signatures
- Variable shadowing that changes semantics

### R2. Security & Secret Handling

Audit all security-sensitive code paths:
- Hardcoded secrets, API keys, tokens, or credentials in source files (not just `.env`)
- Secret leakage through logging, error messages, trace records, or API responses
- Authentication/authorization bypass possibilities in API endpoints
- Egress control gaps — can code send data to arbitrary external URLs?
- SQL injection vectors in any raw SQL construction
- Path traversal in file operations
- CORS/CSRF misconfiguration in the FastAPI server
- `.env` file containing production secrets committed to git
- The `redact_attributes()` function in `trace_contract.py` — verify its redaction coverage is complete

### R3. Architectural Integrity & Dead Code

Assess structural health:
- Modules that are imported nowhere (orphaned files)
- Functions/classes defined but never called
- Circular import chains
- God files (>500 LOC) that should be split
- Duplicate logic across subsystems (copy-paste code)
- Inconsistent naming conventions across subsystems
- Deprecated code still referenced (e.g., remnants of `zero_cost_guard`, `zero_cost_runtime`)
- Uncommitted files that appear to be part of the feature (`_trace_impl.py`, `trace_store.py`, changes to `trace_contract.py`) — should these be committed?

### R4. Test Coverage & Test Quality

Evaluate the test suite:
- Subsystems with zero or minimal test coverage
- Tests that assert trivially (e.g., `assert True`, `assert module is not None`)
- Tests that mock so heavily they don't test real behavior
- Tests that depend on external state (network, file system, specific ports)
- Missing edge case coverage for critical paths (ask flow, LLM gateway routing, governance checks)
- Test files that import from deleted modules
- Flaky test patterns (timing-dependent, order-dependent)

### R5. Runtime Correctness & Concurrency

Examine runtime behavior:
- Race conditions in shared mutable state (especially in `ChatMemoryStore`, `TraceLedger`, `KernelStorage`)
- Thread safety of SQLite operations (WAL mode, connection sharing)
- Resource leaks (unclosed file handles, database connections, HTTP sessions)
- Graceful shutdown handling — do all services clean up properly?
- Error propagation — do errors in subsystems surface correctly to the API layer?
- Memory growth patterns — any unbounded caches or growing data structures?

### R6. Configuration & Deployment Consistency

Check operational health:
- Environment variables referenced in code but not documented in `.env.example`
- Port conflicts or hardcoded port numbers that could collide
- Docker/compose configuration consistency with actual code
- Startup scripts (`start-scp.bat`, `start-scp.sh`) — do they match the actual required services?
- Dashboard build artifacts — is `.next/standalone` correctly gitignored?
- `requirements.txt` vs actual imports — missing or unused dependencies

## Acceptance Criteria

### Completeness
- [ ] Every one of the 43 active subsystems under `scp/` is covered in the audit
- [ ] All 6 requirement domains (R1-R6) are addressed with specific findings
- [ ] Each finding includes: file path, line number(s), severity, description, and evidence

### Severity Classification
- [ ] Findings are classified as CRITICAL / HIGH / MEDIUM / LOW / INFO
- [ ] CRITICAL: security vulnerabilities, data loss risk, or silent correctness bugs in production paths
- [ ] HIGH: bugs that would cause incorrect behavior under realistic conditions
- [ ] MEDIUM: code quality issues that increase maintenance risk or technical debt
- [ ] LOW: style inconsistencies, minor dead code, documentation gaps
- [ ] INFO: observations and improvement suggestions

### Evidence Quality
- [ ] Each finding cites specific file(s) and line number(s)
- [ ] Findings include a brief code snippet or grep evidence demonstrating the issue
- [ ] No speculative findings without concrete evidence from the actual codebase
- [ ] The report distinguishes between confirmed issues and potential risks

### Report Structure
- [ ] Executive summary with finding counts by severity
- [ ] Findings grouped by domain (R1-R6), then by severity within each domain
- [ ] A final section listing the top 10 most critical findings across all domains
- [ ] Output as a single structured markdown file

## Verification

### Programmatic Verification
- Run `pytest tests/ --collect-only -q` to confirm 0 collection errors (validates no broken imports exist)
- Run `python tools/t00_meta_audit.py` to confirm the existing meta-audit passes
- Use `grep -rn` to verify specific claims (e.g., "this function is never called" → grep confirms 0 callers)

### Agent-as-Judge Verification
- Each finding must be independently verifiable by reading the cited source file and line numbers
- The report should not contradict the actual test results (1,937 passing tests)
- No finding should claim a module doesn't exist if it actually does in the file system




## 2026-09-21T22:14:24Z

Fix all 46 findings from a comprehensive system audit of the SCP (Secure Control Plane) codebase. The audit report at `D:\scp\COMPREHENSIVE_AUDIT_REPORT.md` documents every finding with exact file paths, line numbers, severity classifications, code evidence, and a prioritized remediation roadmap (P0→P1→P2). All fixes must be implemented, tested, committed, and verified against the existing test infrastructure.

Working directory: D:\scp
Integrity mode: development

## Reference Material

- **Audit Report**: `D:\scp\COMPREHENSIVE_AUDIT_REPORT.md` (1,002 lines, 46 findings with evidence)
- **Branch**: `feature/autonomous-mode-antigravity-v2` (HEAD: `6d6256f`)
- **Codebase**: ~221K Python LOC, 43 subsystems, 1,937 existing tests

## Requirements

### R1. P0 — Critical Security & Data Integrity Fixes (11 findings)

Fix all 11 CRITICAL-severity findings:

1. **R2-01**: Add authentication to `/v3/trace/{trace_id}` endpoint in `api_server.py` — it must require admin verification before returning trace data.
2. **R2-02**: Fix `redact_attributes()` in `trace_contract.py` — must redact sensitive string values (not just keys), handle tuple headers like `("Authorization", "Bearer sk-...")`, add missing sensitive keys (`auth`, `dsn`, `connection_string`, `proxy`, `cert`), and restore string/list size limits.
3. **R3-01**: Commit untracked trace files (`_trace_impl.py`, `trace_store.py`, modified `trace_contract.py`), mount `_trace_impl.router` in `api_server.py`, and fix T12 tests that bypass the HTTP endpoint.
4. **R1-01**: Implement lazy initialization for the 6 stubbed `Judge` properties (`counter_response`, `canary_monitor`, `error_store`, `attack_memory`, `falsification`, `governance`) so the `/v98/` admin endpoints return real data instead of HTTP 503.
5. **R5-01**: Fix `ChatMemoryStore` race condition — add thread lock and OS file lock around file append and `_prune_if_needed()`.
6. **R5-02**: Fix `TraceLedger.append()` — serialize with exclusive lock, replace whole-file read with incremental tail reader.
7. **R5-03**: Fix `db_manager.py` — hold `_db_lock`/`_read_lock` throughout `conn.execute()` and row fetching, not just during connection retrieval.
8. **R1-02**: Replace the fake `EvidenceReplay.verify()` that returns hardcoded `{"ok": True}` with real verification logic or an explicit `NotImplementedError` with clear documentation.
9. **R4-01**: Replace at least the 23 `test_subsystem_*.py` import-only tests with functional tests that exercise actual subsystem behavior.
10. **R4-02**: Replace `assert True` in `chaos_recovery.py` with real crash injection and TaskKernel state recovery validation.
11. **R6-01**: Document all 165 missing environment variables in `.env.example` with descriptions, grouped by subsystem.

### R2. P1 — High-Severity Reliability & Deployment Fixes (18 findings)

Fix all 18 HIGH-severity findings:

1. **R6-02**: Update `start-scp.bat` to launch LLM Bridge on port 8081.
2. **R6-03**: Fix dashboard fallback URL from port 11434 to 8081 in `scp-backend-url.ts`.
3. **R6-04**: Fix Dockerfile — change `EXPOSE 8080` to `EXPOSE 8000`, change `CMD ["--help"]` to `CMD ["8000"]`.
4. **R2-03**: Add `enforce_egress_policy(url)` in `BrowserSession.navigate_and_read` and `open_visible`.
5. **R2-04**: Fix SQL injection in `LearningDB.execute_insert()` — validate table/column names against allowlist.
6. **R2-05**: Fix path traversal in `batch_benchmark_routes.py` — validate `job_id` with regex.
7. **R2-06**: Add authentication to `/swe-bench/v1/chat/completions` and `/metrics` endpoints.
8. **R1-03**: Fix broken `None` comparison in `type_flow_verifier.py` — check `test.comparators[0]`.
9. **R1-04**: Add explicit `encoding="utf-8"` to all file operations missing it across `external_trust.py`, `compare_results.py`, `run_benchmark.py`.
10. **R5-04**: Fix async transaction collision in `KernelStorage` — use asyncio-safe connection management instead of `threading.local()`.
11. **R5-05**: Fix connection pool leak in `KernelStorage._all_conns` — add bounded pool with proper cleanup.
12. **R5-06**: Add size bounds to all unbounded in-memory collections (`_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`).
13. **R5-07**: Fix graceful shutdown — await cancelled tasks, add thread stop events, close database connections, invoke `checkpoint_wal()`.
14. **R4-03**: Add meaningful tests for at least 10 of the 22 under-covered subsystems.
15. **R4-04**: Convert at least 10 AST-only "reality tests" to behavioral execution tests.
16. **R3-02**: Remove at least 30 of the 63 identified orphaned modules (prioritize the largest ones).
17. **R3-03**: Break at least the top 5 most critical circular dependency cycles using interface protocols.
18. **R3-04**: Refactor at least 2 of the "split-and-stitch" monkeypatching patterns to use proper class composition.

### R3. P2 — Medium/Low Architectural Cleanup (17 findings)

Fix the remaining MEDIUM, LOW, and INFO findings:

1. **R1-05**: Add logging to the silent `except Exception: pass` blocks in `Judge.domain_experts`.
2. **R1-06**: Add error inspection to the fire-and-forget fact-check task callback.
3. **R1-07**: Fix Mojibake character corruption in user-facing API responses.
4. **R2-07**: Add token verification to the LLM Bridge microservice.
5. **R2-08**: Move WebSocket auth from query params to headers; validate token before `websocket.accept()`.
6. **R3-05**: Remove stale `zero_cost_guard`/`zero_cost_runtime` references from spec files and maintenance scripts.
7. **R3-06**: Move `scp/audit_r8` and `scp/audit_r9` to `docs/audit_history/`.
8. **R3-07**: Move `scp/tests/` to `tests/internal/` and update `pytest.ini`.
9. **R3-08**: Standardize file naming to PEP 8 conventions where renaming won't break imports.
10. **R4-05**: Replace at least 20 of the 46 hardcoded `time.sleep` calls with polling or event sync.
11. **R4-06**: Document the 14 permanently skipped tests and create tracking issues.
12. **R5-08**: Add lock synchronization to `ConversationManager._sessions` and `risk_routes._incidents`.
13. **R5-09**: Track and cleanup spawned browser processes in `BrowserSession.open_visible`.
14. **R6-05**: Add missing 23 third-party dependencies to `requirements.txt`.
15. **R6-06**: Commit the dirty working tree files and ensure clean git status.
16. Remaining orphaned module removal (beyond R2's 30).
17. Remaining circular dependency breaks (beyond R2's top 5).

## Acceptance Criteria

### Test Suite Integrity
- [ ] `pytest tests/ -q` passes with 0 failures
- [ ] `python tools/t00_meta_audit.py` passes with 0 new regressions
- [ ] `pytest tests/ --collect-only -q` shows 0 collection errors
- [ ] Total test count increases (baseline: 1,937) — new functional tests must outnumber any removed stubs

### Security Fixes Verified
- [ ] `GET /v3/trace/{trace_id}` returns 401/403 without valid admin token
- [ ] `python -c "from scp.core.trace_contract import redact_attributes; print(redact_attributes([('Authorization', 'Bearer sk-12345')]))"` outputs `[REDACTED]` or equivalent masked value
- [ ] `grep -rn "enforce_egress_policy" scp/web_control/browser_session.py` returns at least 1 match
- [ ] `job_id` parameter in batch benchmark routes is validated against `^[a-zA-Z0-9_-]+$`

### Concurrency Fixes Verified
- [ ] `ChatMemoryStore` file operations are wrapped in both thread lock and file lock
- [ ] `TraceLedger.append()` uses exclusive lock and does not read the entire file
- [ ] `db_manager.py` holds lock throughout query execution, not just connection retrieval
- [ ] All unbounded in-memory collections have explicit size caps

### Architecture Verified
- [ ] `grep -rn "from scp.llm_gateway.zero_cost" scp/ tests/` returns 0 results
- [ ] At least 30 orphaned modules are removed
- [ ] `scp/audit_r8` and `scp/audit_r9` no longer exist in `scp/`
- [ ] No `types.FunctionType` rebinding patterns in at least 2 formerly "split-and-stitch" files

### Configuration Verified
- [ ] `.env.example` documents at least 150 environment variables (up from 32)
- [ ] `start-scp.bat` launches 4 services including LLM Bridge
- [ ] `Dockerfile` exposes port 8000 and defaults to starting the server
- [ ] `requirements.txt` includes all 23 previously missing dependencies

### Git Cleanliness
- [ ] All changes committed with descriptive messages
- [ ] `git status` shows clean working tree
- [ ] Pushed to `feature/autonomous-mode-antigravity-v2`

## Verification Resources

The codebase includes existing verification infrastructure:

1. **Test runner**: `pytest tests/ -q` — runs all 1,937 tests
2. **Meta-audit**: `python tools/t00_meta_audit.py` — enforces test integrity against baseline
3. **Collection check**: `pytest tests/ --collect-only -q` — validates all imports resolve
4. **Grep verification**: Use `grep -rn` to verify removal of dead references and presence of new guards

## 2026-09-22T12:50:00Z

Execute the next-stage development and verification cycle for SCP across three integrated goals: (1) Boot and verify the full SCP cluster live end-to-end (API Server port 8000, LLM Bridge port 8081, Web Dashboard port 3000) with backward-traceable chatbot interactions, shutting down all spawned server processes cleanly upon test completion, (2) Substantially expand subsystem functional test coverage and stress testing across core engines, and (3) Advance SCP Agent OS autonomous execution capabilities with bounded tool invocation and ledger-backed audit provenance.

Working directory: D:\scp
Integrity mode: development

## Reference Material

- **Branch**: `feature/autonomous-mode-antigravity-v2`
- **Recent Baseline**: 2,049 tests collected, 0 meta-audit regressions, 46 audit findings resolved
- **Audit Reports**: `D:\scp\COMPREHENSIVE_AUDIT_REPORT.md` and `D:\scp\BAO_CAO_KIEM_TOAN_TOAN_HE_THONG.md`

## Requirements

### R1. Live Cluster E2E Boot, Verification & Clean Shutdown
- Spawn the SCP cluster services (API server on port 8000, LLM Bridge on port 8081, and Web Dashboard on port 3000).
- Execute an end-to-end automated probe against the running cluster:
  - Submit a multi-turn chat prompt via WebSocket/HTTP.
  - Verify that the response contains backward-traceable metadata.
  - Query the secured `/v3/trace/{trace_id}` endpoint with valid admin credentials and confirm ledger provenance.
- Cleanly terminate all spawned server processes and child processes, ensuring no orphaned background tasks or ports remain bound.

### R2. Subsystem Functional & Stress Test Expansion
- Add new comprehensive behavioral test suites targeting under-tested subsystems (such as Epistemic Engine, TaskKernel, Self-Model, and Observability).
- Include concurrency stress tests that validate thread safety and data integrity under rapid sequential and parallel queries.
- Ensure all tests use real assertions and respect fail-closed invariants without simulated or import-only stubs.

### R3. SCP Agent OS & Autonomous Tool Execution Capabilities
- Extend the autonomous execution pipeline with bounded tools (e.g. system inspection, workspace analysis, safe command runner).
- Enforce capability boundaries and egress policies on all autonomous tool invocations.
- Ensure every autonomous execution step and tool output is recorded into the append-only audit ledger with cryptographic verification hashes.

## Acceptance Criteria

### Live System & Traceability
- [ ] Automated probe verifies HTTP 200 health on port 8000 and port 8081 during execution.
- [ ] Live chat exchange produces a valid trace ID, and querying `/v3/trace/{trace_id}` yields verified, redacted event records.
- [ ] Ports 8000, 8081, and 3000 are completely free and no zombie Python/Node processes remain after verification completes.

### Test Integrity & Coverage Expansion
- [ ] Total collected tests increase from the current baseline of 2,049 with 0 collection errors (`pytest tests/ --collect-only -q`).
- [ ] Meta-audit passes cleanly with 0 new regressions (`python tools/t00_meta_audit.py`).
- [ ] All new tests pass cleanly when run via pytest.

### Agent OS Autonomous Tooling
- [ ] Autonomous tool invocations correctly register in the ledger and enforce permission boundaries.
- [ ] Working tree is clean and all changes are committed with descriptive messages.

## Verification Resources

1. **Test Runner**: `pytest tests/ -q`
2. **Meta-Audit**: `python tools/t00_meta_audit.py`
3. **Port Check**: PowerShell `Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue`
4. **Trace Verification**: Direct automated HTTP client probe querying `/api/chat` and `/v3/trace/{trace_id}`

## 2026-09-22T18:07:00Z

Fix all findings from a comprehensive independent audit of the SCP `main` branch (HEAD `7344c1e`, post-merge of PR #47). The audit identified that security features written in the previous cycle are **well-coded libraries that are NOT wired into the production runtime** — tests call them but no production code path does. This "hardening trang trí" (decorative hardening) anti-pattern is the single most important thing to eliminate: every security module must either be wired into the actual execution path and proven to be called at runtime, or must be removed/documented as undeployed. Do NOT repeat the pattern of writing good code and leaving it unwired.

Working directory: D:\scp
Integrity mode: development
Branch: `main` (HEAD: `7344c1e`)

## Reference Material

- **Audit Report**: Provided verbatim below as Section 6 (user's audit findings)
- **Existing verification tools**: `pytest tests/ -q`, `python tools/t00_meta_audit.py`, `tools/adversarial_goal3_probe.py`
- **Repo context**: 1,651 files, 2,066+ test functions, Python + TypeScript (Next.js dashboard + LLM Bridge)

## Requirements

### R1. Fix the CRITICAL Security Chain (3 interlocking vulnerabilities + eval API)
The audit identified a chain where 3 bugs combine to allow unauthenticated admin access with governance bypass:
- Dashboard middleware fail-open with credential auto-minting
- Chatbot lane classification overriding governance KILL → ALLOW
- JWT guard accepting static admin key as JWT role:"admin" on all routes
- Evaluation API defaulting to verdict=PASS and echoing unvalidated LLM confidence

All four must be fixed so the chain is broken at every link, not just one.

### R2. Wire Unwired Security Modules into Production Runtime
Three well-coded security modules exist only as libraries called by tests, with zero production callers:
- `scp/capabilities/tools.py` (bounded tool runner) — runtime still uses old governor regex
- `scp/policy/egress.py` (fail-closed egress engine) — runtime still uses old url_safety
- `scp/core/autonomous_ledger.py` (cryptographic provenance) — zero callers

Each must be integrated into the actual planner→executor→governance path so they are exercised in production. If a module cannot be wired without breaking the runtime, document why explicitly and remove the misleading commit messages and docs that claim it is active.

### R3. Fix Remaining Unfixed Findings from Previous Audit
The audit tracked 10 previous findings; only TraceLedger was truly fixed. The remaining need resolution:
- Judge tautology (answer-contains-answer) and 0.85 hardcoded threshold
- `expire_leases` missing OCC rowcount checks (4 branches)
- Semantic firewall gaps (github-desc/wiki bypass)
- Dashboard SSRF on remaining raw-fetch routes (status, scanners, loop, loop/trigger)
- Egress dev-default open + DNS-rebinding gaps
- Quorum removal with docs still advertising it — fix the docs or restore the feature
- Memory multi-turn redaction gaps (JWT/ghp_/AKIA patterns not in regex set)

### R4. Restore Deleted Evidence and Fix Dangling References
Commit `87d78da` deleted 152,699 lines of audit evidence (closure records M01–M14, STATUS-LEDGER, witness reports) without creating a relocation manifest. 80+ references across the repo now point to non-existent files. Either restore the evidence to a documented location or create a summary manifest, and fix all dangling references.

### R5. Cleanup Debris and Hygiene
- Remove `prev_ask_impl.py` (876-line dead copy) and `sleeps.txt` (grep output) that were committed
- Fix `e2e_live_cluster_verifier.py:100` hardcoded fallback admin token
- Fix `SCP_ARCHITECTURE.md` claims about quorum (feature was deleted)
- Fix `domain_knowledge.py` FactSeparator "verified" = 2-token overlap tautology
- Ensure observability compose password and compose.test 0.0.0.0 binding are addressed

## Acceptance Criteria

### Security Chain Broken
- [ ] Dashboard middleware rejects requests without valid credentials (no auto-minting JWT admin)
- [ ] Governance KILL verdict on chatbot lane is NOT overridden to ALLOW — the kill must propagate
- [ ] `verify_jwt_token` does NOT accept static admin key as a valid JWT — static keys use a separate auth path
- [ ] `/v1/eval` and `/v1/systemone` do NOT default to PASS; LLM verdict is validated and confidence is clamped to [0,1]
- [ ] An integration test proves the full chain: unauthenticated request → rejection (not admin access)

### Wiring Verified at Runtime
- [ ] `grep -rn` for `from scp.capabilities.tools import` shows at least one production caller (not in tests/)
- [ ] `grep -rn` for `from scp.policy.egress import` shows at least one production caller (not in tests/)
- [ ] `grep -rn` for `from scp.core.autonomous_ledger import` shows at least one production caller (not in tests/)
- [ ] The old code paths (governor regex in planner.py, url_safety standalone calls) are updated to delegate through the new modules
- [ ] `autonomous_ledger.py` uses HMAC (keyed hash) instead of bare SHA-256, or documents why bare SHA-256 is acceptable for the threat model

### Previous Findings Resolved
- [ ] Judge crosscheck does NOT silently fallback to single-vendor on crash — it either retries or flags the result as degraded
- [ ] `expire_leases` checks rowcount after each UPDATE and raises on unexpected 0-row results
- [ ] `SCP_ARCHITECTURE.md` no longer references quorum as an active security ring

### Evidence Integrity
- [ ] Either a `docs/evidence-summary/` directory exists with relocated closure records, or a `RELOCATION_MANIFEST.md` documents where evidence went
- [ ] Zero dangling file references: `grep -rn` for deleted closure JSON filenames returns 0 hits in live code/docs
- [ ] `README.md` claims that cite specific numbers (e.g., "184,276 requests") link to verifiable evidence

### Test & Git Integrity
- [ ] `pytest tests/ --collect-only -q` shows 0 collection errors
- [ ] `python tools/t00_meta_audit.py` passes with 0 new regressions
- [ ] `prev_ask_impl.py` and `sleeps.txt` are removed from the repo
- [ ] Working tree is clean and all changes are committed with descriptive messages

## Verification Resources

1. **Test runner**: `pytest tests/ -q`
2. **Meta-audit**: `python tools/t00_meta_audit.py`
3. **Adversarial probe**: `python tools/adversarial_goal3_probe.py`
4. **Grep verification**: Use `grep -rn` to verify wiring, dangling refs, and removed debris
5. **Integration test**: Write and run a chain-break integration test proving the CRITICAL chain is severed

## Section 6: Full Audit Findings (Verbatim Reference)

The audit report is extensive (provided by the user). Key file paths and line numbers for each finding:

**CRITICAL chain files:**
- `dashboard/src/middleware.ts:6-7`
- `dashboard/src/app/ask/route.ts:15-34` (JWT admin auto-minting)
- `scp/api/routes/evaluation_routes.py:211-212,226-233,86-88` (eval API fake PASS)
- `scp/api/_ask_impl.py:646-648` + `scp/api/chat.py:501-502` (KILL→ALLOW)
- `scp/security/jwt_guard.py:37-42` (static key as JWT)

**Unwired modules:**
- `scp/capabilities/tools.py` — should replace `scp/runtime/engine_parts/hands_planner.py:486-495`
- `scp/policy/egress.py` — should replace standalone `scp/llm_gateway/egress_policy.py` + `scp/security/url_safety.py` calls
- `scp/core/autonomous_ledger.py` — should be called from executor paths

**Previous audit remnants:**
- `scp/runtime/judge.py:309-314` (crash fallback)
- `scp/task_kernel/taskkernel.py:805-855` (expire_leases OCC)
- `scp/knowledge/top_systems_learning.py:263,318` (semantic firewall)
- `docs/SCP_ARCHITECTURE.md:60,121` (quorum claims)
- `scp/knowledge/domain_knowledge.py:526-532` (FactSeparator tautology)

## 2026-09-27T07:01:04Z

Kiểm toán chuyên sâu toàn bộ mã nguồn và logic hệ thống SCP (Secure Control Plane) theo từng dòng code, đối chiếu với 26 nguyên lý SCP DNA và các bất biến Fail-Closed & Evidence-First. Chế độ thuần túy kiểm toán (Read-Only), tuyệt đối KHÔNG sửa mã nguồn ở lượt này.

Working directory: D:\scp
Integrity mode: development

## Requirements

### R1. Security Boundaries, Authentication & Secret Handling
- Rà soát toàn bộ ranh giới an ninh: Auth headers, JWT token validation, API key role segregation (`admin` vs `user`), Next.js dashboard middleware IP verification, và chống header spoofing (`X-Forwarded-For`, `X-Real-IP`).
- Rà soát lỗ hổng SSRF và Egress Policy enforcement trên toàn bộ các luồng network outbound (Python backend, BrowserSession, Next.js API routes).
- Rà soát ranh giới thực thi của `SafeCommandRunnerTool` (`cmd.run`) và cơ chế HumanConfirmationStore đối với các lệnh nhạy cảm (Level >= 3).
- Rà soát rò rỉ bí mật trong logging, error traces, chat memory store và trace payloads.

### R2. Core Logic, RealityJudge & LLM Gateway
- Rà soát logic trọng tài RealityJudge, cơ chế multi-LLM crosscheck, xử lý timeout/crash fallback và hàm tính toán độ tin cậy `_calibrate_confidence()`.
- Rà soát chatbot lane (`_ask_impl.py`), question router và đảm bảo không có bất kỳ bypass nào đối với phán quyết `KILL` từ Governance.
- Rà soát định tuyến LLM Gateway và xác nhận không còn tồn tại mã thừa sau khi phế truất zero-cost.

### R3. TaskKernel Architecture, Concurrency & Data Integrity
- Rà soát state machine của TaskKernel, xử lý leases (`expire_leases`), kiểm tra optimistic concurrency control (`rowcount > 0` và `OptimisticLockError`).
- Rà soát thread safety và file lock quanh SQLite (WAL mode) và các file append-only (.jsonl).
- Rà soát HMAC audit ledger: tính toàn vẹn của hash chain và domain-separated key.

### R4. Knowledge, Fact Separation & RAG
- Rà soát thuật toán phân tách sự thật (`FactSeparator`), Semantic Firewall trước các ký tự ẩn / homoglyphs.
- Rà soát retrieval pipeline và canonical corpus của hệ thống RAG.

### R5. Dashboard Frontend & Microservices
- Rà soát toàn bộ Next.js API routes (`dashboard/src/app/api/scp/**/*.ts`) đảm bảo không tự ý tiêm token nội bộ khi thiếu thông tin xác thực từ client.
- Rà soát Bun microservices (`mini-services/llm-bridge`) về cơ chế bảo vệ token endpoint.

### R6. Test Suite Quality, Tripwire & Dead Code
- Chạy phân tích tĩnh tự động (`tools/t00_meta_audit.py`, `tools/stale_code_tripwire.py`) để kiểm tra baseline metrics và phát hiện drift.
- Rà soát chất lượng các bộ test (T00 đến T12) để loại bỏ placebo assertions, mock giả lập kết quả `PASS` hời hợt.

## Acceptance Criteria

### Bằng Chứng & Độ Tin Cậy (Evidence Quality)
- [ ] 100% các phát hiện (findings) đều trích dẫn chính xác tệp nguồn (`file_path`), số dòng (`line_number`), đoạn mã minh họa (`code snippet`) và kịch bản rủi ro cụ thể.
- [ ] Không có nhận định suy đoán hoặc kết luận không được kiểm chứng bằng mã nguồn thực tế.

### Phân Loại Mức Độ Nghiêm Trọng (Severity Classification)
- [ ] Phân loại rõ ràng theo các cấp độ: **CRITICAL**, **HIGH**, **MEDIUM**, **LOW**, **INFO**.
- [ ] Đánh giá rõ tác động của từng phát hiện đối với tính ổn định và an ninh của hệ thống.

### Nguyên Tắc Bất Biến (Read-Only Enforcement)
- [ ] TUYỆT ĐỐI KHÔNG thực hiện thay đổi, chỉnh sửa hay xóa bất kỳ tệp mã nguồn nào trong suốt quá trình audit.
- [ ] Kết quả kiểm toán được lưu trữ thành file báo cáo tổng hợp Markdown hoàn chỉnh.
## 2026-09-27T07:43:49Z

Server vừa restart và làm gián đoạn tiến trình. Hãy tiếp tục nhiệm vụ kiểm toán chuyên sâu toàn bộ SCP: kiểm tra trạng thái và thu thập báo cáo từ các explorer (r1, r2, r3, r4, r5, worker_r6), hoàn thiện các phân tích còn lại và tổng hợp Báo Cáo Kiểm Toán Toàn Diện (Comprehensive Audit Report) đầy đủ chi tiết với dẫn chứng từng file:line, phân loại CRITICAL/HIGH/MEDIUM/LOW/INFO để báo cáo nghiệm thu. Chế độ Read-Only, không sửa code.