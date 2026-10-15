## 2026-10-04T10:35:31Z

You are worker_live_ops_1 (Live Cluster Operations & Probing Worker).
Your working directory is: D:\scp\.agents\teamwork\worker_live_ops_1
You MUST read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md (specifically the section under ## 2026-10-04T10:18:44Z).
You MUST review the pre-boot exploration handoff at: D:\scp\.agents\teamwork\explorer_m1_1\handoff.md.
Load and apply the domain skill at: C:\Users\check\.gemini\config\plugins\scp-skills\skills\scp-runtime-audit\SKILL.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Core Directives & Constraints:
1. PURE READ-ONLY MODE: Absolutely do NOT modify or delete any source code files (git status must remain 100% untouched).
2. Skip static unit tests (pytest tests/). Focus entirely on live cluster operational verification and runtime audit.
3. Target baseline commit: 1aef24a8 on branch main in D:\scp.

## Mission & Requirements to Execute:

### R1. Live Cluster Boot & Health:
- Pre-check & clean ports 8000, 8081, 3000.
- Launch all 3 backend services in background with standard log redirection to `data/service-logs/`:
  1. API Server FastAPI (`http://127.0.0.1:8000`) via `python -m scp 8000`
  2. Bun LLM Bridge (`http://127.0.0.1:8081`) via `bun run dev` in `mini-services/llm-bridge/`
  3. Web Dashboard Next.js (`http://127.0.0.1:3000`) via `bun run dev` in `dashboard/` (set SCP_DEV_MODE=1, PORT=3000, SCP_INTERNAL_URL=http://127.0.0.1:8000, LLM_BRIDGE_URL=http://127.0.0.1:8081, SCP_AUTH_TOKEN_SECRET=scp-v3-68fcc2ae7dac74cc436decf214cae8cc)
  (You may also execute `tools/cluster_operational_prober.py` or write/run tailored operational test scripts).
- Observe boot progress, measure readiness latency per service, and verify HTTP 200 on health/ready/status endpoints (`/health`, `/ready`, `/status`, `/v98/status`).

### R2. Live Conversational & Retrieval Probing:
- Send natural conversation queries ("bạn là ai", greetings, open discussions) -> measure latency, ensure responses not withheld, verify PASS verdict.
- Send factual data queries requiring retrieval -> observe FactSeparator, verify transparency badge, extract trace_id, evaluate routing.

### R3. Live Security Boundary Audit:
- Probe `/v3/trace/{trace_id}` with valid admin token -> observe decision tree, HMAC ledger, secret redaction (verify secrets like tokens and passwords are not leaked in plaintext).
- Probe `/v3/trace/{trace_id}` and internal routes with NO token or invalid token -> verify fail-closed HTTP 401/403.
- Test Bun LLM Bridge (:8081) token protection when called directly from external (unauthenticated request to protected endpoint -> 401; authenticated -> 200).
- Test Next.js Dashboard anti-spoofing mechanism (X-Forwarded-For with external IP -> blocked/gated).

### R4. Task Lifecycle & Ledger Inspection:
- Verify TaskKernel lifecycle on real DB: create task, claim lease, renew heartbeat, complete with verification evidence, check idempotency.
- Verify HMAC audit ledger hash-chain integrity and `.jsonl` event files.
- Inspect service logs in `data/service-logs/` and runtime logs for swallowed exceptions, stealth warnings, or resource leaks.

### R5. Clean Teardown & Port Release:
- Terminate all service process trees cleanly (`taskkill /F /T /PID`).
- Verify 100% ports 8000, 8081, 3000 released without zombie processes using `Get-NetTCPConnection`.

### Reporting:
Write a comprehensive report to `D:\scp\.agents\teamwork\worker_live_ops_1\handoff.md` following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method) with all observed metrics, HTTP status codes, trace records, log extracts, and security verdicts. When finished, send a message back.
