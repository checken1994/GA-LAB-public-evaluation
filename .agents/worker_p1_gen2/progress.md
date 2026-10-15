# Progress: Milestone 2 (P1: 18 High-Severity Reliability & Deployment Fixes)

Last visited: 2026-09-22T15:40:00+07:00

## Status Overview
- Total Tasks: 18 findings + verification & handoff
- Current Phase: Completed (All 18 Findings Verified & Passing)

## Task Breakdown
- [x] Batch 1: Config, Security & Logic Fixes
  - [x] R6-02: `start-scp.bat` (LLM Bridge port 8081)
  - [x] R6-03: `dashboard/src/lib/scp-backend-url.ts` & test sync
  - [x] R6-04: `Dockerfile` (EXPOSE 8000, CMD ["8000"])
  - [x] R2-03: `scp/web_control/browser_session.py` (enforce_egress_policy)
  - [x] R2-04: `scp/knowledge/learning_db.py` (SQL allowlist in execute_insert)
  - [x] R2-05: `scp/api/routes/batch_benchmark_routes.py` (job_id regex validation & path traversal guard)
  - [x] R2-06: Authentication to `/swe-bench/v1/chat/completions` and `/metrics`
  - [x] R1-03: `scp/autofix/type_flow_verifier.py` (test.comparators[0] None check)
  - [x] R1-04: Explicit `encoding="utf-8"` in `external_trust.py`, `compare_results.py`, `run_benchmark.py`
- [x] Batch 2: Concurrency & Lifecycle
  - [x] R5-04 & R5-05: `KernelStorage` ContextVar connection management & bounded pool (`kernel_storage.py` and `kernel_storage_pg.py`)
  - [x] R5-06: Size bounds on `_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`
  - [x] R5-07: `scp/api_server_parts/lifespan.py` graceful shutdown
- [x] Batch 3: Architecture & Refactoring
  - [x] R3-02: Remove 32 verified orphaned Python modules
  - [x] R3-03: Add interface protocols in `scp/interfaces/` and break 5 circular dependency cycles
  - [x] R3-04: Refactor 2 monkeypatching split-and-stitch patterns (`api_server.py` and `task_kernel.py`)
- [x] Batch 4: Tests & Reality Tests Upgrade
  - [x] R4-03: Functional tests for 10 under-covered subsystems (21 passed)
  - [x] R4-04: Convert 10 AST reality tests to behavioral execution tests (10 passed)
- [x] Batch 5: Verification & Handoff
  - [x] Run `pytest tests/ --collect-only -q` (2016 tests collected, 0 errors)
  - [x] Run `python tools/t00_meta_audit.py` (0 new regressions against baseline debt)
  - [x] Run `pytest tests/reality-tests/ -q` (10/10 passed)
  - [x] Run `pytest tests/T12_unified_chatbot/ -q` (236/236 passed)
  - [x] Generate `handoff.md` and report to orchestrator
