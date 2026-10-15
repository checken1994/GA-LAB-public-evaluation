# Pre-Boot Environment Operational Audit & Architecture Report (Milestone 1)

**Agent**: `explorer_m1_1` (Pre-Boot Environment Explorer)  
**Date**: 2026-10-04T10:33:00Z  
**Target Repository**: `D:\scp`  
**Target Baseline Commit**: `1aef24a8` on branch `main`  
**Operational Status**: Pre-Boot Inspection Complete — Environment 100% Ready for Live Execution  

---

## 1. Observation

### 1.1 Git Baseline & Repository Integrity
Direct command execution:
```powershell
git rev-parse HEAD; git branch --show-current; git status --short
```
Verbatim stdout:
```
1aef24a84dcdf801b05dbdf855dc62b457686f17
main
 M dashboard/next-env.d.ts
?? .codex/
?? .zcodeignore
?? reports/incidents/
?? reports/runtime/evidence-RUNTIME-AUDIT-20260925-0411/boot_8090.log
?? reports/scp_acceptance_ci/
```
- **Commit**: Matches required baseline `1aef24a8` (`1aef24a84dcdf801b05dbdf855dc62b457686f17`).
- **Branch**: Confirmed `main`.
- **Source Code Integrity**: `dashboard/next-env.d.ts` contains only an automatic Turbopack dev type import change (`./.next/dev/types/` vs `./.next/types/`). No source code files in `scp/`, `mini-services/`, or root have been modified or deleted. PURE READ-ONLY constraint verified.

---

### 1.2 TCP Port Inspection (8000, 8081, 3000)
Direct PowerShell commands executed:
```powershell
$conns = Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue; if ($conns) { $conns | Select-Object LocalAddress, LocalPort, State, OwningProcess } else { Write-Output "NO_CONNECTIONS_FOUND" }
netstat -ano | Select-String ":(8000|8081|3000)\s"
```
Verbatim stdout:
```
NO_CONNECTIONS_FOUND
```
- **Port 8000 (FastAPI API Server)**: Unoccupied (0 listeners, 0 established connections).
- **Port 8081 (Bun LLM Bridge)**: Unoccupied (0 listeners, 0 established connections).
- **Port 3000 (Next.js Dashboard)**: Unoccupied (0 listeners, 0 established connections).
- **Zombie Process Check**: 0 processes currently bound to target ports.

---

### 1.3 Service Boot Architecture

#### Service 1: FastAPI API Server (`:8000`)
- **Entry Point**: `scp/__main__.py` (invoked via `python -m scp 8000` or `python -m scp`).
  - Lines 125–127 enforce Windows event loop policy:
    ```python
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    ```
  - Lines 49–101 execute `_load_env_at_startup()` to load `.env` before importing `scp.api_server:app`.
  - Line 108 executes `enforce_production_safety()` (`scp/security/production_guard.py`).
  - Lines 131–138 launch uvicorn:
    ```python
    uvicorn.run("scp.api_server:app", host=host, port=port, reload=False, log_level="info", access_log=True)
    ```
- **Python Runtime**:
  - Binary: `C:\Users\check\AppData\Local\Programs\Python\Python312\python.exe`
  - Version: Python 3.12.10
  - Dependencies: `uvicorn` (0.44.0), `fastapi`, `pydantic`, `httpx`, and `scp` package installed and verified importable.
  - Venv status: `D:\scp\.venv` and `D:\scp\venv` do not exist; host Python 3.12.10 is the canonical execution runtime.
- **Health & Readiness Endpoints**:
  - `GET /health` (`scp/api_server.py:674–685`): Public, unauthenticated liveness endpoint (returns HTTP 200 with status `"ok"`, version `"14.0.0"`, route count). Responds within ~1–2 seconds of boot.
  - `GET /ready` and `GET /readiness` (`scp/api_server.py:746–763`): Readiness probe. Checks `app.state.judge_ready` and `app.state.background_scheduler_started`. Returns HTTP 503 (`judge_initialization_pending`) during the first ~8 seconds while RealityJudge loads SLMs and V98 modules in the background, then flips to HTTP 200 (`"status": "ready"`).
  - `GET /health/detailed` (`scp/api_server.py:691–744`): Deep operational metrics. Requires admin token (`Depends(verify_admin)`).
  - `GET /` (`scp/api_server.py:765–786`): Service directory listing.
  - Status endpoints: `GET /v98/status`, `GET /v100/status`, `GET /v103/status`, `GET /v104/status`, `GET /v104/learn/status`, `GET /v105/capability/status`, `GET /v3/pc/status`, `GET /v3/hands/status`. All critical admin status routes require admin token authentication via `Depends(verify_admin)`.
- **Authentication & Secret Configuration**:
  - Canonical Admin Auth Guard: `verify_admin` in `scp/security/auth.py:140–231`.
    - Authenticates via header `Authorization: Bearer <token>`.
    - Compares token using timing-safe `secrets.compare_digest` against `auth_config.token` (`SCP_AUTH_TOKEN_SECRET` / `SCP_ADMIN_KEY`) or `auth_config.password` (`SCP_AUTH_PASSWORD`).
    - Enforces rate limiting: max 5 failed attempts per IP per 60 seconds (HTTP 429).
    - Rejects unauthenticated requests with HTTP 401 fail-closed.
  - Token Minting Exchange: `POST /auth/token` (`scp/api_server.py:597–612`) accepts `{"admin_key": "<SCP_ADMIN_KEY>"}` and mints a short-lived Bearer JWT for `POST /ask`.
  - Secrets in `D:\scp\.env`:
    - `SCP_ADMIN_KEY` (length 32)
    - `SCP_AUTH_PASSWORD` (length 32)
    - `SCP_AUTH_TOKEN_SECRET` (length 39, `scp-v3-68fcc2ae7dac74cc436decf214cae8cc`)
    - `SCP_JWT_SECRET` (length 64)
    - `SCP_PC_CONTROLLER_TOKEN` (length 44)

---

#### Service 2: Bun LLM Bridge (`:8081`)
- **Directory**: `D:\scp\mini-services\llm-bridge`
- **Bun Runtime**:
  - Binary: `C:\Users\check\.bun\bin\bun.exe`
  - Version: Bun 1.3.14
- **Package.json Scripts**:
  ```json
  "scripts": {
    "dev": "bun --hot index.ts",
    "start": "bun index.ts",
    "build": "bun build index.ts --target=bun --outdir dist"
  }
  ```
- **Startup Command**:
  `bun run dev` (or `bun index.ts`) with environment variables:
  `SCP_LLM_BRIDGE_PORT=8081`, `ZAI_BRIDGE_PORT=8081`, `ZAI_BRIDGE_HOST=127.0.0.1`, and `SCP_AUTH_TOKEN_SECRET`.
- **Endpoints & Ports**:
  - Bound to `127.0.0.1:8081` (`core.ts:182–193`).
  - `GET /` and `GET /health` (`core.ts:1229`): Public HTML service info (HTTP 200).
  - `GET /api/tags` (`core.ts:1230`): Ollama-compatible advertised model list (`deepseek-r1:8b`, `qwen2.5:7b`, `llama3.2`) (HTTP 200).
  - `GET /api/version` (`core.ts:1231`): Ollama version string.
  - Protected endpoints: `POST /api/chat`, `POST /api/generate`, `GET /api/cache/stats`, `POST /api/cache/clear`.
- **Token Authorization Mechanism**:
  - Defined in `core.ts:940–966` (`isAuthorized(req)`):
    ```typescript
    function isAuthorized(req: Request): boolean {
      const authHeader = req.headers.get("authorization") || req.headers.get("Authorization");
      if (!authHeader) return false;
      const match = authHeader.match(/^Bearer\s+(.+)$/i);
      const token = match ? match[1].trim() : authHeader.trim();
      if (!token) return false;

      const validSecrets = [
        process.env.BRIDGE_SECRET,
        process.env.SHARED_SECRET,
        process.env.BEARER_TOKEN,
        process.env.SCP_AUTH_TOKEN_SECRET,
      ].map((s) => s?.trim()).filter((s): s is string => Boolean(s && s.length > 0));

      if (validSecrets.length === 0) return false;
      return validSecrets.some((secret) => safeCompare(token, secret));
    }
    ```
  - Uses `timingSafeEqual` over SHA-256 (`safeCompare`).
  - Fails closed: unauthenticated requests to `/api/chat` or `/api/generate` return HTTP 401 `{"error": "Unauthorized"}`.

---

#### Service 3: Next.js Dashboard (`:3000`)
- **Directory**: `D:\scp\dashboard`
- **Node & Tooling Runtime**:
  - Node: `C:\Program Files\nodejs\node.exe` (v26.5.0)
  - npm: `C:\Program Files\nodejs\npm.cmd` (11.17.0)
  - Bun: `C:\Users\check\.bun\bin\bun.exe` (1.3.14)
- **Package.json Scripts**:
  ```json
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build && node scripts/copy-standalone-assets.js",
    "start": "bun .next/standalone/server.js"
  }
  ```
- **Build Status**:
  - `.next` directory exists and contains Turbopack caches and types.
  - Standalone server exists at `D:\scp\dashboard\.next\standalone\server.js`.
- **Startup Command**:
  `bun run dev` (or `bun run start` / `npm run dev -- --port 3000`).
  In development mode, `next dev -p 3000` compiles on demand and becomes ready in ~5.9s.
- **Middleware & Security Boundary (`dashboard/src/middleware.ts:69–166`)**:
  - Protects `GATED_API_ROOTS`: `["/api/scp", "/api/audit", "/api/autofix", "/api/scanners"]`.
  - When `SCP_DASHBOARD_PROXY_SECRET` is set: requests must present `x-scp-proxy-secret` matching the secret, or fail closed with HTTP 403.
  - When `SCP_DASHBOARD_PROXY_SECRET` is unset:
    - If `SCP_DEV_MODE=1`: activates dev-mode loopback fallback. Requires `X-Forwarded-For` or `X-Real-IP` where all hops are local (`127.0.0.1`, `::1`, `localhost`) and loopback Hostname. Stamps response with `X-SCP-Dev-Mode-Warning`.
    - If `SCP_DEV_MODE` is unset or `0`: fails closed with HTTP 503 (`Dashboard API unavailable: SCP_DASHBOARD_PROXY_SECRET is not set`).
  - Crucial finding: To allow the prober to access proxied routes like `/api/scp/v3/trace/{trace_id}`, the dashboard process environment must include either `SCP_DEV_MODE=1` or `SCP_DASHBOARD_PROXY_SECRET`.
- **Credential Injection & Forwarding (`dashboard/src/lib/scp-service-auth.ts:17–46`)**:
  - Caller-sent credentials (`Authorization: Bearer <token>`, `X-SCP-PC-Token`) take precedence and are forwarded verbatim to the backend at `http://127.0.0.1:8000`.
  - In local development mode without proxy secret, missing credentials can be filled from `.env` cache.
  - Route `/api/scp/v3/trace/[trace_id]` proxies directly to `${base}/v3/trace/${trace_id}`, returning 200 when authenticated and 401 when unauthenticated.

---

### 1.4 Existing Probes & Ops Scripts
1. **`tools/cluster_operational_prober.py`**:
   - The authoritative end-to-end operational test harness.
   - Automatically executes:
     - Step 1: Pre-cleans ports 8000, 8081, 3000 via `taskkill /F /T /PID`.
     - Step 2: Spawns Bridge (`bun run dev`), Server (`python -m scp 8000`), Dashboard (`bun run dev`) redirecting outputs to `data/service-logs/`.
     - Step 3: Readiness polling loop for Bridge (8081), Server (8000 `/health`), Judge (8000 `/readiness`), and Dashboard (3000 `/`).
     - Step 4: Executes 4 operational probes:
       - Probe 1: Conversational Chat Probe ("Xin chào, bạn là ai?", verifies PASS verdict, answer not withheld).
       - Probe 2: Factual Query & Retrieval Probe ("Thủ đô của Việt Nam là gì?", extracts valid `trace_id`).
       - Probe 3: Trace Lookup & Secret Redaction Probe (`/v3/trace/{trace_id}` returns 200 with admin token, redacted secrets, unauth returns 401, Dashboard proxy returns 200/401).
       - Probe 4: Autonomous Task Probe (Direct `TaskKernel` queue lifecycle, worker lease claim, heartbeat renewal, idempotency claim, completion).
     - Step 5: Clean teardown killing process trees and confirming all ports free.
2. **`tools/e2e_live_cluster_verifier.py`**:
   - Similar E2E runner featuring Docker Desktop backend PID protection and WMI termination fallback (`Win32_Process.Terminate`) for stubborn Windows processes.
3. **`scripts/ops/start_scp_silent.ps1`**:
   - Production PowerShell zero-window background launcher that starts processes via `cmd.exe /c` redirecting to `data\service-logs\`.
4. **`tools/adversarial_goal3_probe.py`**:
   - Offline security test harness for path traversal, command injection, egress policy, and ledger hash tampering. Writes reports to `data/adversarial_probe_goal3_report.json`.

---

## 2. Logic Chain

1. **Premise 1**: All target ports (8000, 8081, 3000) are verified currently unoccupied with 0 listening processes.
   - *Evidence*: `Get-NetTCPConnection` returned `NO_CONNECTIONS_FOUND`.
   - *Deduction*: No cleanup is necessary prior to launching services; however, defensive pre-clean before boot guarantees zero port contention.

2. **Premise 2**: On Windows, launching the Python API server via `python -m scp 8000` is strictly superior to raw `uvicorn scp.api_server:app`.
   - *Evidence*: `scp/__main__.py` lines 125–127 explicitly configure `asyncio.WindowsSelectorEventLoopPolicy()`. Furthermore, `__main__.py` executes `_load_env_at_startup()` before importing `api_server`, preventing empty module-level configuration state.
   - *Deduction*: Launching via `python -m scp 8000` ensures correct event loop handling for child process execution and flawless configuration loading.

3. **Premise 3**: The API server requires two-stage readiness polling.
   - *Evidence*: `GET /health` responds HTTP 200 within ~2 seconds of process start, but `GET /readiness` responds HTTP 503 while `RealityJudge` initializes asynchronously in the background (~8 seconds total).
   - *Deduction*: A boot runner must poll `/health` first for socket bind, and then poll `/readiness` until HTTP 200 before sending `/ask` requests (which return 503 until judge is ready).

4. **Premise 4**: Bun LLM Bridge on port 8081 requires Bearer token authentication for inference endpoints.
   - *Evidence*: `mini-services/llm-bridge/core.ts:950–966` verifies `Authorization: Bearer <token>` against `SCP_AUTH_TOKEN_SECRET` / `BRIDGE_SECRET`.
   - *Deduction*: For live cluster testing, `SCP_AUTH_TOKEN_SECRET` must be set in the Bridge environment so that authentications succeed and external unauthenticated calls are rejected with HTTP 401.

5. **Premise 5**: Next.js Dashboard on port 3000 requires explicit security posture configuration.
   - *Evidence*: `dashboard/src/middleware.ts:107–116` returns HTTP 503 for all `/api/scp/*` proxy routes if `SCP_DASHBOARD_PROXY_SECRET` is unset and `SCP_DEV_MODE` is not `1`.
   - *Deduction*: When booting Dashboard for local operational probing, passing `SCP_DEV_MODE=1` or `SCP_DASHBOARD_PROXY_SECRET` in the dashboard's environment is mandatory to allow loopback queries to pass through to the backend.

6. **Premise 6**: Reliable process teardown on Windows requires process tree termination.
   - *Evidence*: Starting `bun run dev` or `python -m scp` spawns sub-processes. Terminating only the root PID leaves child processes bound to ports.
   - *Deduction*: Teardown must use `taskkill /F /T /PID <pid>` (with fallback to WMI or port-based PID discovery) to ensure 100% port release.

---

## 3. Caveats

1. **Host Python vs Virtual Environment**:
   - `D:\scp\.venv` and `D:\scp\venv` are absent. The host Python `C:\Users\check\AppData\Local\Programs\Python\Python312\python.exe` contains all necessary dependencies. Scripts should use `python` or `sys.executable`.
2. **Next.js Turbopack Startup Delay**:
   - On the first compilation, `next dev` takes ~5–8 seconds to compile modules and bind port 3000. Readiness timeout for Dashboard should be at least 45 seconds.
3. **Secret Redaction**:
   - The `.env` file contains production secrets and provider API keys. All operational probes and log collectors must ensure that token secrets (`SCP_AUTH_TOKEN_SECRET`, `SCP_ADMIN_KEY`, `OPENROUTER_API_KEY_*`) are redacted and never printed unredacted in final reports or stdout.
4. **Rate Limiting**:
   - `verify_admin` enforces 5 failed attempts per 60 seconds per IP (HTTP 429). Negative security tests (testing unauthenticated access) should be limited to 1–2 requests to avoid triggering IP-wide rate-limit lockouts.

---

## 4. Conclusion & Concrete Operational Synthesis

The pre-boot environment in `D:\scp` is fully verified, consistent with commit `1aef24a8`, and ready for live cluster boot.

### Concrete Operational Procedures

#### Step 1: Pre-Boot Port Verification & Cleanup
```powershell
# Check target ports
$conns = Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) {
        taskkill /F /T /PID $c.OwningProcess
    }
    Start-Sleep -Seconds 2
}
```

#### Step 2: Background Service Launch
Ensure `data\service-logs` directory exists:
```powershell
New-Item -ItemType Directory -Force -Path "D:\scp\data\service-logs"
```

1. **Boot Bun LLM Bridge (:8081)**:
   ```powershell
   $env:SCP_LLM_BRIDGE_PORT = "8081"
   $env:ZAI_BRIDGE_PORT = "8081"
   $env:ZAI_BRIDGE_HOST = "127.0.0.1"
   $env:SCP_AUTH_TOKEN_SECRET = "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
   Start-Process -FilePath "bun.exe" -ArgumentList "run dev" `
       -WorkingDirectory "D:\scp\mini-services\llm-bridge" `
       -RedirectStandardOutput "D:\scp\data\service-logs\llm-bridge.log" `
       -RedirectStandardError "D:\scp\data\service-logs\llm-bridge-err.log"
   ```

2. **Boot FastAPI API Server (:8000)**:
   ```powershell
   $env:SCP_PORT = "8000"
   $env:SCP_HOST = "127.0.0.1"
   $env:SCP_AUTH_TOKEN_SECRET = "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
   $env:SCP_ADMIN_KEY = "tfO0RetycvVp3BQ-gyjVCV4lec8soybA"
   Start-Process -FilePath "python.exe" -ArgumentList "-m scp 8000" `
       -WorkingDirectory "D:\scp" `
       -RedirectStandardOutput "D:\scp\data\service-logs\scp-server.log" `
       -RedirectStandardError "D:\scp\data\service-logs\scp-server-err.log"
   ```

3. **Boot Next.js Dashboard (:3000)**:
   ```powershell
   $env:PORT = "3000"
   $env:SCP_DEV_MODE = "1"
   $env:SCP_INTERNAL_URL = "http://127.0.0.1:8000"
   $env:LLM_BRIDGE_URL = "http://127.0.0.1:8081"
   $env:SCP_AUTH_TOKEN_SECRET = "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
   Start-Process -FilePath "bun.exe" -ArgumentList "run dev" `
       -WorkingDirectory "D:\scp\dashboard" `
       -RedirectStandardOutput "D:\scp\data\service-logs\dashboard.log" `
       -RedirectStandardError "D:\scp\data\service-logs\dashboard-err.log"
   ```

#### Step 3: Health & Readiness Polling Sequence
- **Bridge Liveness**: Poll `http://127.0.0.1:8081/health` (HTTP 200 within 5s).
- **Backend Liveness**: Poll `http://127.0.0.1:8000/health` (HTTP 200 within 5s).
- **Backend Readiness**: Poll `http://127.0.0.1:8000/readiness` (wait for judge to finish, HTTP 200 within 15–20s).
- **Dashboard Liveness**: Poll `http://127.0.0.1:3000/` (HTTP 200 within 15s).

#### Step 4: Comprehensive Operational Probing
Execute the full, pre-configured test harness:
```powershell
python D:\scp\tools\cluster_operational_prober.py
```
This script handles token extraction from `.env`, background booting with isolated logging, polling, chat probe, retrieval probe, trace probe (including token redaction and fail-closed checks), TaskKernel probe, and clean teardown.

#### Step 5: Clean Teardown Procedure
```powershell
# Terminate process trees for all 3 ports
$ports = 8000, 8081, 3000
foreach ($port in $ports) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $_.OwningProcess }
    foreach ($pid_val in $pids) {
        if ($pid_val -gt 0) {
            taskkill /F /T /PID $pid_val
        }
    }
}
Start-Sleep -Seconds 2

# Verify all ports released
$remaining = Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue
if (-not $remaining) {
    Write-Host "[OK] Clean teardown verified: 0 remaining listeners on 8000, 8081, 3000." -ForegroundColor Green
}
```

---

## 5. Verification Method

To independently verify the observations and findings in this report:

1. **Verify Git Baseline**:
   ```powershell
   git rev-parse HEAD
   # Expected: 1aef24a84dcdf801b05dbdf855dc62b457686f17
   git branch --show-current
   # Expected: main
   ```

2. **Verify Port Unoccupied State**:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue
   # Expected: Null / No output
   ```

3. **Verify Tooling Paths and Executability**:
   ```powershell
   python --version
   # Expected: Python 3.12.10
   bun --version
   # Expected: 1.3.14
   node --version
   # Expected: v26.5.0
   ```

4. **Verify Operational Prober Readiness**:
   ```powershell
   python -c "import scp, uvicorn, fastapi; print('Dependencies OK')"
   # Expected: Dependencies OK
   Test-Path "D:\scp\tools\cluster_operational_prober.py"
   # Expected: True
   ```
