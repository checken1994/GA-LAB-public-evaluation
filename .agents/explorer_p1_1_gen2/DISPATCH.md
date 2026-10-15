## 2026-09-22T03:17:17Z

You are Explorer P1-1 (Generation 2) for Milestone 2 (P1: Security, Concurrency & Deployment Hardening).
Your working directory is D:\scp\.agents\explorer_p1_1_gen2.

MANDATORY FIRST STEP:
Read D:\scp\.agents\ORIGINAL_REQUEST.md.
Read D:\scp\PROJECT.md.
Read D:\scp\COMPREHENSIVE_AUDIT_REPORT.md (specifically relevant sections for R6-02, R6-03, R6-04, R2-03, R2-04, R2-05, R2-06, R1-03, R1-04, R5-04, R5-05, R5-06, R5-07).

SCOPE OF INVESTIGATION:
1. R6-02: Update `start-scp.bat` to launch `mini-services/llm-bridge` on port 8081.
2. R6-03: Fix dashboard fallback URL from port 11434 to 8081 in `dashboard/src/lib/scp-backend-url.ts`.
3. R6-04: Fix Dockerfile — change `EXPOSE 8080` to `EXPOSE 8000`, change `CMD ["--help"]` to `CMD ["8000"]`.
4. R2-03: Add `enforce_egress_policy(url)` inside `BrowserSession.navigate_and_read` and `open_visible` in `scp/web_control/browser_session.py`.
5. R2-04: Fix SQL injection in `LearningDB.execute_insert()` (`scp/knowledge/learning_db.py`) — validate table/column names against an identifier allowlist.
6. R2-05: Fix path traversal in `scp/api/routes/batch_benchmark_routes.py` — validate `job_id` against `^[a-zA-Z0-9_-]+$`.
7. R2-06: Add authentication to `/swe-bench/v1/chat/completions` and `/metrics` endpoints.
8. R1-03: Fix broken `None` comparison in `scp/autofix/type_flow_verifier.py` (check `test.comparators[0]`).
9. R1-04: Add explicit `encoding="utf-8"` to all file operations missing it across `external_trust.py`, `compare_results.py`, `run_benchmark.py`.
10. R5-04: Fix async transaction collision in `KernelStorage` — use asyncio-safe connection management instead of `threading.local()`.
11. R5-05: Fix connection pool leak in `KernelStorage._all_conns` — add bounded pool with proper cleanup.
12. R5-06: Add size bounds to unbounded in-memory collections (`_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`).
13. R5-07: Fix graceful shutdown in `scp/api_server_parts/lifespan.py` — await cancelled tasks, add thread stop events, close database connections, invoke `checkpoint_wal()`.

RULES:
- Read-only! Do NOT modify source code.
- Write your detailed findings and concrete implementation proposals with exact file paths, line numbers, and drop-in code to `D:\scp\.agents\explorer_p1_1_gen2\handoff.md`.
- Send a completion message back to the caller orchestrator.
