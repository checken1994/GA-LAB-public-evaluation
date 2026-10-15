## 2026-09-22T13:03:33Z
You are worker_o4_3, a Worker agent in the SCP project.
Your Working Directory is D:\scp\.agents\worker_o4_3. Create your BRIEFING.md and progress.md there.

MANDATORY INPUT:
Read D:\scp\.agents\ORIGINAL_REQUEST.md (specifically § ## 2026-09-22T12:50:00Z and context), D:\scp\.agents\orchestrator_4\SCOPE.md, and D:\scp\.agents\explorer_o4_1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You have exclusive write ownership over the following files (no other agent is touching them):
- scripts/ops/start_scp_silent.ps1
- stop-scp.bat
- stop-scp.sh
- mini-services/llm-bridge/core.ts
- dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts
- tests/T01_boot/test_startup_launcher_contract.py
- tools/e2e_live_cluster_verifier.py
- tests/T01_boot/test_live_cluster_e2e.py

TASK OBJECTIVES (Goal 1: Live Cluster E2E Boot, Verification & Clean Process Shutdown):
1. Fix launcher and stop scripts per explorer_o4_1's findings:
   - `scripts/ops/start_scp_silent.ps1`: Change port from stale 11434 to 8081 for LLM Bridge ($env:SCP_LLM_BRIDGE_PORT = "8081", port check @(8081, 3030, 8000, 3000), $env:LLM_BRIDGE_URL = "http://127.0.0.1:8081").
   - `stop-scp.bat`: Add kill for window title `SCP-LLM-Bridge*`, add port kill for 8081 with `/t` tree kill flag, ensure all taskkills use `/t`, and include `:8081` in verification.
   - `stop-scp.sh`: Update 11434 to 8081.
   - `mini-services/llm-bridge/core.ts`: In line 1035, add `/health` route alias to return HTTP 200 along with `/`.
   - `dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts`: In line 16, add `headers["Authorization"] = "Bearer " + token` so the Next.js API proxy properly forwards admin credentials to `/v3/trace/{trace_id}`.
   - `tests/T01_boot/test_startup_launcher_contract.py`: Update line 20 assertion from `assert 'SCP-LLM-Bridge' not in LAUNCHER` to assert that `SCP-LLM-Bridge` is in `LAUNCHER` with port 8081 per R6-02.
2. Build the automated Live Cluster E2E Verifier:
   - Create `tools/e2e_live_cluster_verifier.py` (and test `tests/T01_boot/test_live_cluster_e2e.py`) based on explorer_o4_1's design.
   - Ensure it redirects stdout/stderr to `data/service-logs/` so Windows pipes never buffer/hang.
   - Pre-cleans ports 8000, 8081, 3000.
   - Boots LLM Bridge (8081), SCP Server (8000), and Dashboard (3000).
   - Probes health on all 3 services with polling deadlines.
   - Executes live chat interaction with valid token, extracting `trace_id`.
   - Queries `GET /v3/trace/{trace_id}` with admin auth and verifies response contains trace_id and has secrets redacted.
   - Queries `GET /v3/trace/{trace_id}` without auth and verifies fail-closed 401.
   - Cleanly shuts down all spawned processes using process tree kill (`taskkill /F /T /PID`).
   - Verifies ports 8000, 8081, 3000 are completely free with 0 leftover zombie processes.
3. Run the live verification:
   - `python tools/e2e_live_cluster_verifier.py`
   - `pytest tests/T01_boot/test_startup_launcher_contract.py tests/T01_boot/test_live_cluster_e2e.py -v`
   - Verify zero ports remain listening: `powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,8081,3000 -State Listen -ErrorAction SilentlyContinue"`
   - `python tools/t00_meta_audit.py`

Deliverable:
Write a detailed handoff report to D:\scp\.agents\worker_o4_3\handoff.md with all execution outputs and port status.
When complete, notify orchestrator via send_message to c8e670c9-7a53-48ab-b7be-c1e52f77e555.
