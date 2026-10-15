# Project: SCP (Secure Control Plane) Remediation of All 46 Audit Findings

## Architecture
- **Web & API Layer**: `scp/api/`, `scp/api_server.py`, `scp/api_server_parts/`
- **Security & Policies**: `scp/security/`, `scp/capabilities/`, `scp/policy/`
- **Core Orchestration & Traceability**: `scp/core/`, `scp/trace_ledger.py`
- **Runtime, Kernel & Judges**: `scp/runtime/`, `scp/task_kernel_parts/`, `scp/autofix/`
- **Persistence & Knowledge**: `scp/persistence/`, `scp/knowledge/`
- **Automation & External**: `scp/web_control/`, `scp/pc_control/`, `scp/llm_gateway/`
- **Testing & Tooling**: `tests/`, `tools/`, `scp/tests/`

## Feature Inventory (46 Findings Mapped to Milestones)
> **Governance Note (DNA #22 & GA.md § A1):** Status 'VERIFIED' is strictly bound to automated machine closure tests in `tests/` that exist on disk and pass in CI.

| # | Finding ID | Description | Milestone | Machine Closure Gate | Status |
|---|---|---|---|---|---|
| 1 | R2-01 | Add admin authentication to `/v3/trace/{trace_id}` in `api_server.py` | M1_P0 | `tests/T02_contract/test_trace_runtime_paths.py` | VERIFIED |
| 2 | R2-02 | Fix `redact_attributes()` in `trace_contract.py` for strings, tuples, missing keys | M1_P0 | `tests/test_p0_security_adversarial_challenger2.py` | VERIFIED |
| 3 | R3-01 | Commit untracked trace files and mount router in `api_server.py`, fix tests | M1_P0 | `tests/T02_contract/test_trace_runtime_paths.py` | VERIFIED |
| 4 | R1-01 | Implement lazy init for 6 stubbed `Judge` properties to fix 503 errors on admin v98 | M1_P0 | `tests/contract/test_judge_verifier_contract.py` | VERIFIED |
| 5 | R5-01 | Add thread lock and file lock around `ChatMemoryStore` append and prune | M1_P0 | `tests/test_p0_persistence_concurrency.py` | VERIFIED |
| 6 | R5-02 | Serialize `TraceLedger.append()` with exclusive lock, incremental tail read | M1_P0 | `tests/T02_contract/test_trace_ledger_oversize_get.py` | VERIFIED |
| 7 | R5-03 | Hold locks throughout query execution and fetching in `db_manager.py` | M1_P0 | `tests/test_p0_persistence_concurrency.py` | VERIFIED |
| 8 | R1-02 | Replace fake `EvidenceReplay.verify()` return with real verification logic | M1_P0 | `tests/T07_learning/test_evidence_replay_hardening.py` | VERIFIED |
| 9 | R4-01 | Replace 23+ import-only `test_subsystem_*.py` with functional tests | M1_P0 | `tests/test_subsystem_core.py` | VERIFIED |
| 10 | R4-02 | Replace `assert True` in `chaos_recovery.py` with real crash/recovery validation | M1_P0 | `tests/T10_recovery/test_kernel_chaos_recovery.py` | VERIFIED |
| 11 | R6-01 | Document all 165 missing environment variables in `.env.example` | M1_P0 | `spec/guardrail_policy.yaml` | VERIFIED |
| 12 | R6-02 | Update `start-scp.bat` to launch LLM Bridge on port 8081 | M2_P1 | None | IN_PROGRESS |
| 13 | R6-03 | Fix dashboard fallback URL to 8081 in `scp-backend-url.ts` | M2_P1 | None | IN_PROGRESS |
| 14 | R6-04 | Fix Dockerfile: EXPOSE 8000 and default CMD ["8000"] | M2_P1 | None | IN_PROGRESS |
| 15 | R2-03 | Enforce egress policy in `BrowserSession.navigate_and_read` and `open_visible` | M2_P1 | None | IN_PROGRESS |
| 16 | R2-04 | Fix SQL injection in `LearningDB.execute_insert()` with identifier allowlist | M2_P1 | None | IN_PROGRESS |
| 17 | R2-05 | Fix path traversal in `batch_benchmark_routes.py` with `job_id` regex validation | M2_P1 | None | IN_PROGRESS |
| 18 | R2-06 | Add authentication to `/swe-bench/v1/chat/completions` and `/metrics` | M2_P1 | None | IN_PROGRESS |
| 19 | R1-03 | Fix broken `None` comparison in `type_flow_verifier.py` | M2_P1 | None | IN_PROGRESS |
| 20 | R1-04 | Add explicit `encoding="utf-8"` to file operations missing it | M2_P1 | None | IN_PROGRESS |
| 21 | R5-04 | Fix async transaction collision in `KernelStorage` using asyncio-safe conns | M2_P1 | None | IN_PROGRESS |
| 22 | R5-05 | Fix connection pool leak in `KernelStorage._all_conns` with bounded cleanup | M2_P1 | None | IN_PROGRESS |
| 23 | R5-06 | Add size bounds to unbounded in-memory collections | M2_P1 | None | IN_PROGRESS |
| 24 | R5-07 | Fix graceful shutdown: await cancelled tasks, thread stops, WAL checkpoint | M2_P1 | None | IN_PROGRESS |
| 25 | R4-03 | Add functional tests for >=10 under-covered subsystems | M2_P1 | None | IN_PROGRESS |
| 26 | R4-04 | Convert >=10 AST-only reality tests to behavioral execution tests | M2_P1 | None | IN_PROGRESS |
| 27 | R3-02 | Remove at least 30 identified orphaned modules | M2_P1 | None | IN_PROGRESS |
| 28 | R3-03 | Break top 5 circular dependency cycles with interface protocols | M2_P1 | None | IN_PROGRESS |
| 29 | R3-04 | Refactor >=2 split-and-stitch monkeypatching patterns to composition | M2_P1 | None | IN_PROGRESS |
| 30 | R1-05 | Add logging to silent `except Exception: pass` in `Judge.domain_experts` | M3_P2 | None | PLANNED |
| 31 | R1-06 | Add error inspection to fire-and-forget fact-check task callback | M3_P2 | None | PLANNED |
| 32 | R1-07 | Fix Mojibake character corruption in API responses | M3_P2 | None | PLANNED |
| 33 | R2-07 | Add token verification to LLM Bridge microservice | M3_P2 | None | PLANNED |
| 34 | R2-08 | Move WebSocket auth to headers and validate before accept | M3_P2 | None | PLANNED |
| 35 | R3-05 | Remove stale `zero_cost_*` references from specs and scripts | M3_P2 | None | PLANNED |
| 36 | R3-06 | Move `scp/audit_r8` and `scp/audit_r9` to `docs/audit_history/` | M3_P2 | None | PLANNED |
| 37 | R3-07 | Move `scp/tests/` to `tests/internal/` and update pytest config | M3_P2 | None | PLANNED |
| 38 | R3-08 | Standardize file naming to PEP 8 where safe | M3_P2 | None | PLANNED |
| 39 | R4-05 | Replace >=20 hardcoded `time.sleep` calls with polling/event sync | M3_P2 | None | PLANNED |
| 40 | R4-06 | Document 14 permanently skipped tests and create tracking documentation | M3_P2 | None | PLANNED |
| 41 | R5-08 | Add lock synchronization to `ConversationManager` and `risk_routes` | M3_P2 | None | PLANNED |
| 42 | R5-09 | Track and cleanup spawned browser processes in `BrowserSession` | M3_P2 | None | PLANNED |
| 43 | R6-05 | Add missing 23 dependencies to `requirements.txt` | M3_P2 | None | PLANNED |
| 44 | R6-06 | Clean working tree and commit dirty files | M3_P2 | None | PLANNED |
| 45 | R3-02b | Remove remaining orphaned modules beyond the initial 30 | M3_P2 | None | PLANNED |
| 46 | R3-03b | Break remaining circular dependency cycles beyond top 5 | M3_P2 | None | PLANNED |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | P0 Critical Security & Data Integrity | 11 P0 findings (R2-01, R2-02, R3-01, R1-01, R5-01, R5-02, R5-03, R1-02, R4-01, R4-02, R6-01) | None | DONE |
| M2 | P1 High-Severity Reliability & Deployment | 18 P1 findings (R6-02 to R6-04, R2-03 to R2-06, R1-03 to R1-04, R5-04 to R5-07, R4-03 to R4-04, R3-02 to R3-04) | M1 | IN_PROGRESS |
| M3 | P2 Medium/Low Architectural Cleanup | 17 P2 findings (R1-05 to R1-07, R2-07 to R2-08, R3-05 to R3-08, R4-05 to R4-06, R5-08 to R5-09, R6-05 to R6-06, remaining orphans & cycles) | M2 | PLANNED |
| M4 | Final System Verification & Clean Commit | Run full test suite, meta-audit, collection check, verify all criteria, clean git status | M3 | PLANNED |

## Interface Contracts
- Admin endpoints require `verify_admin` FastAPI dependency.
- `redact_attributes(data)` must handle strings, dicts, lists, tuples `(key, val)`, redacting sensitive keys and values while preserving structure. True recursion cycle detection returns `[CIRCULAR_REFERENCE]` and depth limit returns `[MAX_DEPTH_EXCEEDED]`.
- `ChatMemoryStore` operations must use `RLock` and OS-level file locking on sidecar `.lock` file.
- `TraceLedger.append()` must hold thread lock and use incremental tail pointer without rewriting the file.
- `db_manager.py` must hold read/write lock for entire execute and fetch lifecycle.
- `EvidenceReplay.verify()` must execute real verification steps or fail-closed.

## Code Layout
- `scp/`: Core implementation packages
- `tests/`: Primary test suite
- `tools/`: Diagnostic and meta-audit tooling
- `docs/`: Documentation and historical audit logs
- `mini-services/`: Microservices (LLM Bridge, Loop Scheduler)
- `dashboard/`: Next.js web application
