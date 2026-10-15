## 2026-09-22T03:33:36Z
You are Worker P1-1 for Milestone 2 (P1: 18 High-Severity Reliability & Deployment Fixes).
Your working directory is D:\scp\.agents\worker_p1_1.

MANDATORY FIRST STEP:
Read D:\scp\.agents\ORIGINAL_REQUEST.md before doing anything else.
Read D:\scp\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

REFERENCE HANDOFF REPORTS (CONTAINING COMPLETE DROP-IN CODE SPECIFICATIONS):
1. D:\scp\.agents\explorer_p1_1_gen2\handoff.md
   - R6-02: `start-scp.bat` (add LLM Bridge port 8081).
   - R6-03: `dashboard/src/lib/scp-backend-url.ts` (update port to 8081) and sync `tests/T03_capability/test_security_sweep_s5.mjs:445`.
   - R6-04: `Dockerfile` (EXPOSE 8000, CMD ["8000"]).
   - R2-03: `scp/web_control/browser_session.py` (enforce_egress_policy inside navigate_and_read and open_visible).
   - R2-04: `scp/knowledge/learning_db.py` (SQL allowlist in execute_insert).
   - R2-05: `scp/api/routes/batch_benchmark_routes.py` (job_id regex validation).
   - R2-06: Add auth to `/swe-bench/v1/chat/completions` and `/metrics`.
   - R1-03: `scp/autofix/type_flow_verifier.py` (test.comparators[0] None check).
   - R1-04: Add encoding="utf-8" in `external_trust.py`, `compare_results.py`, `run_benchmark.py`.
   - R5-04 & R5-05: `KernelStorage` ContextVar connection management & bounded pool.
   - R5-06: Size bounds on `_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`.
   - R5-07: `scp/api_server_parts/lifespan.py` graceful shutdown.

2. D:\scp\.agents\explorer_p1_2_gen2\handoff.md
   - R3-02: Safely remove the 32 verified orphaned Python modules (see list in handoff.md; verify 0 callers).
   - R3-03: Add interface protocols in `scp/interfaces/` and break the 5 circular dependency cycles.
   - R3-04: Refactor 2 monkeypatching split-and-stitch patterns (`api_server.py` and `task_kernel.py`) to proper class composition.
   - R4-03: Implement functional tests for 10 under-covered subsystems (`interfaces`, `observability`, `capabilities`, `rag`, `sandbox_evaluator`, `prediction`, `consolidator`, `experience`, `forecast`, `world_state`).
   - R4-04: Convert 10 AST reality tests in `tests/reality-tests/` to behavioral execution tests.

EXECUTION & VERIFICATION INSTRUCTIONS:
1. Apply all 18 fixes carefully, following the exact code diffs and designs in the two explorer handoff reports.
2. Run verification commands:
   - `pytest tests/ --collect-only -q` (MUST show 0 collection errors).
   - `python tools/t00_meta_audit.py` (MUST show 0 regressions).
   - Run the new and modified test suites to confirm 100% pass rate:
     - `pytest tests/test_p1_*.py -v` (or corresponding test files)
     - `pytest tests/reality-tests/ -q`
     - `pytest tests/T12_unified_chatbot/ -q`
3. Document all file changes, deletions, build/test commands executed, and verification outputs in `D:\scp\.agents\worker_p1_1\handoff.md`.
4. Send a message back to the orchestrator with your completion report.
