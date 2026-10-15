# Dispatch Log

## 2026-10-04T10:21:11Z

You are the Project Orchestrator (orchestrator_3) for the SCP project.
Your working directory is: D:\scp\.agents\teamwork\orchestrator_3
Authoritative request is recorded at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md (under header ## 2026-10-04T10:18:44Z).

## Core Directives & Constraints:
1. PURE READ-ONLY MODE: Absolutely do NOT modify or delete any source code files (`git status` must remain 100% untouched).
2. Skip static unit tests (`pytest tests/`). Focus entirely on live cluster operational verification and runtime audit.
3. Target baseline commit: `1aef24a8` on branch `main` in `D:\scp`.

## Requirements to Execute & Coordinate:
- R1. Live Cluster Boot & Health:
  - Pre-check & free ports 8000, 8081, 3000.
  - Launch 3 backend services: API Server FastAPI (:8000), Bun LLM Bridge (:8081), Web Dashboard Next.js (:3000).
  - Observe boot progress, measure readiness latency, verify HTTP 200 on health/ready/status endpoints.
- R2. Live Conversational & Retrieval Probing:
  - Natural conversation queries ("bạn là ai", greetings, open discussions) -> measure latency, ensure responses not withheld, verify PASS.
  - Factual data queries -> observe FactSeparator, verify transparency badge, extract trace_id, evaluate routing.
- R3. Live Security Boundary Audit:
  - Probe `/v3/trace/{trace_id}` with valid admin token -> observe decision tree, HMAC ledger, secret redaction.
  - Probe `/v3/trace/{trace_id}` and internal routes with NO token or invalid token -> verify fail-closed HTTP 401/403.
  - Test Bun LLM Bridge (:8081) token protection when called directly from external.
  - Test Next.js Dashboard anti-spoofing mechanism (X-Forwarded-For).
- R4. Task Lifecycle & Ledger Inspection:
  - Verify TaskKernel lifecycle on real DB: create task, claim lease, renew heartbeat, complete with verification evidence, check idempotency.
  - Verify HMAC audit ledger hash-chain integrity and `.jsonl` event files.
  - Inspect service logs in `data/service-logs/` or runtime logs for swallowed exceptions, stealth warnings, or resource leaks.
- R5. Clean Teardown & Port Release:
  - Terminate all service process trees cleanly.
  - Verify 100% ports 8000, 8081, 3000 released without zombie processes.
- Documentation & Reporting:
  - Generate comprehensive Live Operational Audit Report (`D:\scp\LIVE_OPERATIONAL_AUDIT_REPORT_20261004.md`) documenting latency metrics, HTTP status codes, trace evidence, security findings, and stability evaluation.
  - Maintain your `plan.md`, `progress.md`, and `BRIEFING.md` in `D:\scp\.agents\teamwork\orchestrator_3/`.
  - When finished, send a completion report back to Sentinel.
