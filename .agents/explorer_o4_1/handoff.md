# Exploration Report: Live Cluster E2E Boot, Verification & Clean Process Shutdown

## Summary
This investigation provides a comprehensive architectural and operational blueprint for executing Goal 1 of the SCP project: Booting the live full SCP cluster (API Server on port 8000, LLM Bridge on port 8081, Web Dashboard on port 3000), verifying multi-turn backward-traceable chat interactions against the secured `/v3/trace/{trace_id}` endpoint, and cleanly terminating all spawned processes with zero lingering zombie processes on Windows.

---

## 1. Observation

### 1.1 Cluster Launch Architecture & Scripts
1. **API Server (`port 8000`)**:
   - **Entrypoint**: `scp/__main__.py` (lines 96–128).
   - **Environment loading**: `_load_env_at_startup()` loads `.env` or `SCP_ENV_FILE` prior to any subsystem imports (lines 48–89).
   - **Production guard**: `enforce_production_safety()` in `scp/security/production_guard.py` (lines 18–54) checks that dangerous bypass flags (`SCP_DEV_MODE`, `SCP_SKIP_STARTUP_GATE`, etc.) are disabled when `SCP_PRODUCTION_MODE=1` is set, and validates password length $\ge 16$.
   - **Server startup**: Invokes `uvicorn.run("scp.api_server:app", host="127.0.0.1", port=8000, reload=False)`.
   - **Lifespan sequence**: Defined in `scp/api_server_parts/lifespan.py` (lines 53–507). Validates boot config via `validate_boot_config()` (`scp/core/config_contract.py`), immediately yields to bind port 8000, while deferring judge initialization, background schedulers (`ThreatSimulator`, `IntelCrawler`, `DoubtCron`), and deep audit loops to background threads/tasks.

2. **LLM Bridge (`port 8081`)**:
   - **Location**: `mini-services/llm-bridge/` (`package.json`, `index.ts`, `core.ts`).
   - **Entrypoint**: `bun run dev` (running `bun --hot index.ts`).
   - **Port Configuration**: `mini-services/llm-bridge/core.ts` line 177:
     ```typescript
     const PORT = Number(process.env.SCP_LLM_BRIDGE_PORT ?? process.env.ZAI_BRIDGE_PORT ?? 11434);
     const HOST = process.env.ZAI_BRIDGE_HOST ?? "127.0.0.1";
     ```
     When launched with `SCP_LLM_BRIDGE_PORT=8081`, it listens on `127.0.0.1:8081`.
   - **Model routing**: `resolveModel()` (lines 159–172) maps task types to per-task OpenRouter models (`OPENROUTER_MODEL_AUTOFIX`, `OPENROUTER_MODEL_JUDGE`, `OPENROUTER_MODEL_CHAT`, etc.).
   - **Endpoints**: `GET /` (status 200 HTML info), `GET /api/tags` (status 200 model list), `GET /api/version` (status 200), `POST /api/chat`, `POST /api/generate`.
   - **Noticeable gap**: `mini-services/llm-bridge/core.ts` line 1035 only handles `GET /`, `GET /api/tags`, and `GET /api/version`. `GET /health` is not routed and returns 404 (`ollamaError(404, "not found: GET /health")`).

3. **Web Dashboard (`port 3000`)**:
   - **Location**: `dashboard/` (`package.json`).
   - **Tech stack**: Next.js 16.1.1 with React 19, Tailwind CSS, Bun runtime.
   - **Scripts**: `dev`: `next dev -p 3000`, `build`: `next build && node scripts/copy-standalone-assets.js`, `start`: `bun .next/standalone/server.js`.
   - **Port configuration**: Listens on port 3000. For development/testing, `bun run dev` runs without requiring a pre-built `.next/standalone` directory.

4. **Loop Scheduler (`port 3030`)**:
   - **Location**: `mini-services/loop-scheduler/` (`package.json`, `index.ts`).
   - **Script**: `bun run dev`. Exposes dashboard/health on `127.0.0.1:3030`.

5. **Discrepancies in Existing Startup/Shutdown Scripts**:
   - `start-scp.bat`:
     - Lines 8–12: By default, immediately calls `powershell ... scripts\ops\start_scp_silent.ps1 -OpenBrowser true` unless `--windowed` is explicitly passed.
     - Lines 84–101: Windowed mode spawns 4 services: LLM Bridge (8081), Loop Scheduler (3030), SCP Python (8000), Dashboard (3000).
   - `scripts/ops/start_scp_silent.ps1`:
     - Lines 82, 92, 97, 113, 138: Still uses stale port `11434` for LLM Bridge (`$env:ZAI_BRIDGE_PORT = "11434"`, `@(11434, 3030, 8000, 3000)`), contradicting the updated 8081 port contract from R6-02.
   - `stop-scp.bat`:
     - Lines 13–17: Kills window titles `SCP-Loop-Scheduler*`, `SCP-Python*`, `SCP-Dashboard*`, `SCP-Desktop-App*`, but **omits** `SCP-LLM-Bridge*`.
     - Lines 20–31: Kills ports 3030, 8000, 3000, but **omits** port `8081`.
     - Lines 20–31: Uses `taskkill /f /pid %%a` without `/t` (process tree kill), leaving child processes orphaned.
   - `stop-scp.sh`:
     - Lines 56, 65: Kills port `11434` instead of `8081`.
   - `tests/T01_boot/test_startup_launcher_contract.py`:
     - Line 20: `assert 'SCP-LLM-Bridge' not in LAUNCHER, "FAIL: launcher vẫn spawn LLM-Bridge"` fails because commit `e40af00` correctly added LLM Bridge (8081) to `start-scp.bat` per audit requirement R6-02, but the unit test assertion was not updated.

---

### 1.2 Multi-Turn Chat Interactions & Authentication
1. **WebSocket Endpoint `/chat` (`scp/api/chat.py`)**:
   - **Connection**: `ws://127.0.0.1:8000/chat?token=<token>&session_id=<session_id>`.
   - **Authentication**: Lines 250–276 check `websocket.query_params.get("token")`. Verifies against `cfg.token` (`SCP_AUTH_TOKEN_SECRET`) or `cfg.password` (`SCP_AUTH_PASSWORD`) using `secrets.compare_digest`. Closes with code 1008 if invalid, or 1011 if unconfigured.
   - **Input Guards**: Line 49 (`MAX_CHAT_MESSAGE_CHARS = 8000`), line 52 (`MAX_CHAT_FRAME_CHARS = 32000`), lines 53–54 (`CHAT_RATE_LIMIT_MESSAGES = 20`, `CHAT_RATE_LIMIT_WINDOW_SECONDS = 60.0`). Closes with 1009 if oversized, 1008 if rate limit exceeded.
   - **Conversation Management**: `ConversationManager` (lines 176–236) manages session history in memory and persists to disk via `ChatMemoryStore` (`scp/core/chat_memory_store.py`) protected by `threading.RLock` and OS file lock.
   - **Candidate Generation & Verifier Adjudication**:
     - `_generate_candidate_answer` (lines 91–174) calls `llm_gateway.chat(..., task="chat")`, with fallback to `InternetSearch`.
     - `judge.judge(...)` (lines 462–476) executed via `asyncio.to_thread` with `v98_context`.
     - `FactSeparator.separate(...)` (lines 511–538) computes verified facts, LLM reasoning, and confidence badge.
   - **Ledger Recording**:
     - Line 355: `run = _CHAT_LEDGER.begin(SimpleNamespace(source="websocket_chat", domain="general", message=user_message))` generates `run_id` and `trace_id`, writing `request_received` and `request_started` events to `data/request_runs.jsonl`.
     - Line 581: `terminal_status, ledger_ok = _CHAT_LEDGER.finish(run, run_status, result=response)`.
     - Line 584: Response payload enriched with `run_id`, `trace_id`, `run_status`, `ledger_status`.

2. **HTTP Endpoint `POST /v1/chat/completions` (`scp/api/routes/openai_compat.py`)**:
   - **Authentication**: Line 36: `current_user: str = Depends(get_current_user)`.
   - In `scp/security/jwt_guard.py` (lines 36–58): `verify_jwt_token` inspects `Authorization: Bearer <token>`. Compares against `SCP_API_KEY`, `SCP_ADMIN_KEY`, and `SCP_AUTH_TOKEN_SECRET` with `secrets.compare_digest`. If not matched, decodes as HS256 JWT using `_get_jwt_secret()` (`SCP_JWT_SECRET`).
   - **Ledger Decorator**: Line 35: `@traced_request(_OPENAI_COMPAT_LEDGER, require_write=False, action="openai_chat")`. Automatically attaches `run_id`, `trace_id`, `run_status`, and `ledger_status` to the JSON response body and sets response headers `X-SCP-Trace-ID`, `X-SCP-Run-ID`, `X-SCP-Run-Status`, `X-SCP-Ledger-Status`.
   - **Execution**: Extracts user message, calls `judge.judge(...)` offloaded to `asyncio.to_thread`. Enforces KILL/FAIL/FLAGGED sanitization, returns standard OpenAI schema + `scp_metadata`.

3. **HTTP Endpoint `POST /swe-bench/v1/chat/completions` (`scp/api/routes/swe_bench_routes.py`)**:
   - **Authentication**: Line 8: `router = APIRouter(prefix="/swe-bench/v1", dependencies=[Depends(verify_admin)])`. Requires valid admin credentials via `verify_admin` (`scp/security/auth.py`).

4. **HTTP Endpoint `POST /api/chat` (`mini-services/llm-bridge/core.ts`)**:
   - **Port**: 8081.
   - **Authentication**: Lines 1039–1048 check `req.headers.get("authorization")` against `SHARED_SECRET` or `BEARER_TOKEN`.

---

### 1.3 Backward-Traceable Metadata & TraceLedger Storage
1. **Trace ID Generation**:
   - In `RequestRunLedger.begin()` (`scp/core/request_run_ledger.py` lines 166–167):
     ```python
     run_id = f"run-{uuid.uuid4().hex}"
     trace_id = f"trace-{uuid.uuid4().hex}"
     ```
   - In `TraceLedger.append()` (`scp/trace_ledger.py` line 106):
     ```python
     trace_id = fields.pop("trace_id", None) or "trace_" + secrets.token_hex(8)
     ```
   - In `TraceStore.record_trace()` (`scp/core/trace_store.py` line 70):
     ```python
     trace_id = str(trace_data.get("trace_id") or f"trace-{uuid.uuid4().hex}")
     ```

2. **Persistence Channels**:
   - **Primary SQLite Store (`data/trace_store.sqlite3`)**:
     - Managed by `TraceStore` (`scp/core/trace_store.py`). SQLite in WAL mode with `PRAGMA synchronous=NORMAL`.
     - Schema: `traces (trace_id PRIMARY KEY, timestamp, session_id, query, routing, retrieval, multi_llm_crosscheck, governance, final_decision, causal_graph)`.
     - Built-in `build_causal_graph()` produces a 5/6-stage DAG (`intake -> routing -> retrieval -> adjudication -> governance -> synthesis`).
   - **Cryptographic Hash-Chain Ledger (`data/trace_ledger.jsonl`)**:
     - Managed by `TraceLedger` (`scp/trace_ledger.py`).
     - Each line format:
       ```json
       {"fields": {...}, "hash": "sha256:...", "prev_hash": "...", "seq": 1, "trace_id": "trace-..."}
       ```
     - Uses O(1) binary reverse tail seek (`_read_tail()`) and exclusive lock (`_state.lock`). Appends with `f.flush()` and `os.fsync()`.
     - Verification method `verify()` traverses and validates unbroken SHA-256 chain integrity.
   - **Request Run Ledger (`data/request_runs.jsonl`)**:
     - Managed by `RequestRunLedger` (`scp/core/request_run_ledger.py`).
     - Records granular lifecycle events (`request_received`, `request_started`, `stage`, `request_finished`) indexed by `trace_id` and `run_id`.

---

### 1.4 GET `/v3/trace/{trace_id}` Implementation & Redaction
1. **Routing & Aliases**:
   - Implemented in `scp/api_server_parts/_trace_impl.py` (lines 20–26):
     ```python
     router = APIRouter(dependencies=[Depends(verify_admin)])

     @router.get("/api/scp/v3/trace/{trace_id}")
     @router.get("/api/v3/trace/{trace_id}")
     @router.get("/v3/trace/{trace_id}")
     async def get_trace_record(trace_id: str) -> dict[str, Any]:
     ```
   - Mounted directly in `api_server.py`.

2. **Admin Authentication**:
   - Gated by `verify_admin` (`scp/security/auth.py` lines 91–182).
   - Extracts `Authorization` header (`Bearer <token>`).
   - Requires match against `SCP_AUTH_TOKEN_SECRET` or `SCP_AUTH_PASSWORD` via timing-safe `secrets.compare_digest`.
   - Rate limited: max 5 failed attempts per IP per 60 seconds (returns 429).
   - If missing or wrong: returns HTTP 401 Unauthorized.

3. **Multi-Store Lookup Flow**:
   - Step 1: Queries SQLite `TraceStore`: `get_trace_store().get_trace(trace_id)`.
   - Step 2: If not found, falls back to legacy/current JSONL ledgers in order:
     `trace_ledger.jsonl`, `ask_task_kernel_trace.jsonl`, `trace.jsonl`, `request_runs.jsonl` using `TraceLedger(path).get_trace(trace_id)`.
   - Step 3: If still not found, raises `HTTPException(status_code=404, detail=f"Trace record not found: {trace_id}")`.

4. **Sensitive Attribute Redaction**:
   - Returns `redact_attributes(record)` from `scp/core/trace_contract.py` (lines 72–118).
   - Sensitive key mask: Redacts any key containing substring in:
     `"secret", "token", "password", "cookie", "api_key", "authorization", "private_key", "credential", "key", "bearer", "auth", "dsn", "connection_string", "proxy", "cert"`.
   - Regex string value mask (`_redact_string`): Masks Bearer tokens, `sk-` tokens, DSN passwords, private key PEM headers, and truncates strings $> 512$ characters.
   - Tuple headers: Transforms `("Authorization", "Bearer sk-...")` $\to$ `("Authorization", "[REDACTED]")`.
   - Graph cycle safety: Detects circular object references returning `[CIRCULAR_REFERENCE]` and caps depth at 20 (`[MAX_DEPTH_EXCEEDED]`).

5. **Dashboard Proxy Defect Observed**:
   - In `dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts` line 16:
     ```typescript
     const token = process.env.SCP_PC_CONTROLLER_TOKEN || process.env.SCP_AUTH_TOKEN_SECRET || ""
     if (token) {
       headers["X-SCP-PC-Token"] = token
     }
     ```
     The proxy sets `X-SCP-PC-Token` but **fails** to set `Authorization: Bearer ${token}`. Because `_trace_impl.py` enforces `verify_admin`, requests passing through the Next.js API route are rejected with 401 unless `Authorization` is attached.

---

### 1.5 Clean Process Termination & Windows Mechanics
1. **Windows Process Tree Behavior**:
   - In Windows, terminating a parent process (e.g. `cmd.exe`, `bun.exe`, `python.exe`) does not terminate child processes by default.
   - For example, `start-scp.bat` line 74 uses `taskkill /f /pid %%a`. Without the `/t` flag, child worker processes (e.g. Node/Bun worker threads, uvicorn subprocesses) continue running detached, keeping ports 8000, 8081, or 3000 bound.
2. **Standard Zero-Zombie Method**:
   - When spawning background processes, redirect stdout and stderr to log files (e.g. `data/service-logs/<service>.log`). If stdout/stderr pipes are unread, standard Windows pipe buffers (typically 4KB–64KB) fill up, freezing background server processes indefinitely.
   - Process termination must use `taskkill /F /T /PID <pid>` where `/T` forces the termination of the entire child process hierarchy.
   - Post-shutdown port sweep: Query `Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -State Listen` and execute tree kill on any remaining owning PIDs.
   - Final verification: Assert that all targeted ports return no active listener connections.

---

## 2. Logic Chain

```
[Observation 1.1: start-scp.bat & start_scp_silent.ps1 port divergence]
  ├─ start-scp.bat launches LLM Bridge on 8081 (R6-02 fix)
  ├─ start_scp_silent.ps1 still launches LLM Bridge on 11434 and checks port 11434
  ├─ stop-scp.bat and stop-scp.sh omit port 8081 and omit LLM Bridge from taskkill
  └─ CONCLUSION: Silent startup script and stop scripts must be aligned to port 8081 with process-tree taskkill (/t).

[Observation 1.2: Chat endpoints & RequestRunLedger]
  ├─ WebSocket /chat begins run in RequestRunLedger, writes to data/request_runs.jsonl
  ├─ HTTP /v1/chat/completions uses @traced_request, writes to data/request_runs.jsonl
  ├─ Both return trace_id in response body and/or headers
  └─ CONCLUSION: Live chat queries deterministically emit traceable trace_id values that exist in data/request_runs.jsonl.

[Observation 1.3 & 1.4: /v3/trace/{trace_id} & verify_admin]
  ├─ Endpoint requires Authorization: Bearer <SCP_AUTH_TOKEN_SECRET>
  ├─ Rejects unauthenticated requests with HTTP 401
  ├─ Searches SQLite TraceStore then falls back to JSONL ledgers via TraceLedger.get_trace()
  ├─ Redacts credentials, tokens, DSNs, and long strings via redact_attributes()
  └─ CONCLUSION: Querying /v3/trace/{trace_id} immediately verifies provenance, access control, and credential redaction.

[Observation 1.5: Windows process management]
  ├─ Windows background processes hang if stdout/stderr pipes are unbuffered/unread
  ├─ Killing parent PID without /t leaves orphan child processes on ports
  └─ CONCLUSION: An automated test runner must redirect logs to disk, track PIDs, apply taskkill /F /T /PID, and perform a post-kill netstat/TCP sweep.
```

---

## 3. Caveats
1. **LLM Bridge Health Endpoint**:
   `mini-services/llm-bridge/core.ts` currently responds to `GET /` and `GET /api/tags` with HTTP 200, but returns 404 on `GET /health`. The probe runner must query `GET /api/tags` or `GET /` unless a trivial alias `/health` is added to `core.ts`.
2. **Dashboard Standalone vs Dev**:
   `dashboard/` requires `bun run build` before `bun run start` (standalone) can run. In development or test environments where Next.js is not pre-built, `bun run dev` (running `next dev -p 3000`) should be used to avoid build latency.
3. **External LLM Cloud Connectivity**:
   If OpenRouter API keys are rate-limited, the system falls back to configured fallback providers (Groq, Cerebras) or SLM stubs; this does not affect cluster boot, port binding, WebSocket connectivity, or TraceLedger recording.

---

## 4. Conclusion & Concrete Recommendations

### 4.1 Required Launcher & Script Fixes
1. **Update `scripts/ops/start_scp_silent.ps1`**:
   - Replace port `11434` with `8081`:
     - Line 82: Change `@(11434, 3030, 8000, 3000)` $\to$ `@(8081, 3030, 8000, 3000)`.
     - Lines 92–98: Change port check and `$env:ZAI_BRIDGE_PORT = "11434"` $\to$ `$env:SCP_LLM_BRIDGE_PORT = "8081"`.
     - Lines 113, 138: Change `$env:LLM_BRIDGE_URL` $\to$ `"http://127.0.0.1:8081"`.
2. **Update `stop-scp.bat`**:
   - Add `taskkill /f /fi "WINDOWTITLE eq SCP-LLM-Bridge*" >nul 2>&1`.
   - Add port kill for port 8081:
     ```batch
     for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8081 " ^| findstr "LISTENING"') do (
         taskkill /f /t /pid %%a >nul 2>&1
     )
     ```
   - Add `/t` flag to all `taskkill /f /pid %%a` lines (`taskkill /f /t /pid %%a`).
   - Update verification line 42 to include `:8081 `:
     `netstat -aon | findstr ":8081 :3030 :8000 :3000 " | findstr "LISTENING"`.
3. **Update `stop-scp.sh`**:
   - Change `kill_port 11434` $\to$ `kill_port 8081`.
   - Update verification loop for ports `8081 3030 8000 3000`.
4. **Fix `tests/T01_boot/test_startup_launcher_contract.py`**:
   - Line 20 currently asserts `assert 'SCP-LLM-Bridge' not in LAUNCHER`. Update this to:
     `assert 'SCP-LLM-Bridge' in LAUNCHER` and verify that port 8081 is configured.
5. **Fix Dashboard Trace Proxy (`dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts`)**:
   - Line 16: Set `headers["Authorization"] = "Bearer " + token` in addition to `headers["X-SCP-PC-Token"] = token`.
6. **Add `/health` to LLM Bridge (`mini-services/llm-bridge/core.ts`)**:
   - Line 1035: Change `if (method === "GET" && path === "/") return handleInfo();` to:
     `if (method === "GET" && (path === "/" || path === "/health")) return handleInfo();`.

---

## 5. Design of the Automated Non-Hanging E2E Probe Runner

Create `tools/e2e_live_cluster_verifier.py` to automate the complete verification lifecycle with hard timeouts and zero zombie processes:

### Architecture of `tools/e2e_live_cluster_verifier.py`

```python
#!/usr/bin/env python3
"""
Automated Live Cluster E2E Boot, Verification & Clean Shutdown Runner
====================================================================
1. Pre-cleans ports 8000, 8081, 3000.
2. Boots LLM Bridge (8081), SCP API Server (8000), and Dashboard (3000) in background with log redirection.
3. Polls health endpoints with deadlines (max 45s).
4. Submits live chat query via HTTP /v1/chat/completions (and/or WebSocket /chat).
5. Verifies trace_id is present and queries GET /v3/trace/{trace_id} with admin auth.
6. Verifies 401 Unauthorized boundary without auth.
7. Executes tree-kill cleanup (taskkill /F /T /PID) and port sweep.
8. Confirms zero zombie processes and all ports completely free.
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "service-logs"
PORTS = [8081, 8000, 3000]

def kill_process_tree(pid: int):
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    else:
        import signal
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

def clean_ports():
    if sys.platform == "win32":
        cmd = "Get-NetTCPConnection -LocalPort 8000,8081,3000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $_.OwningProcess }"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            pid = line.strip()
            if pid.isdigit():
                kill_process_tree(int(pid))
    time.sleep(1)

def verify_ports_free():
    if sys.platform == "win32":
        cmd = "Get-NetTCPConnection -LocalPort 8000,8081,3000 -State Listen -ErrorAction SilentlyContinue"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        return len(res.stdout.strip()) == 0
    return True

async def run_e2e_verification():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    clean_ports()

    # Read .env for tokens
    env = dict(os.environ)
    env_file = ROOT / ".env"
    token = ""
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("SCP_AUTH_TOKEN_SECRET="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif not token and line.startswith("SCP_ADMIN_KEY="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")

    spawned_procs = []
    try:
        # 1. Spawn LLM Bridge on 8081
        bridge_log = open(LOG_DIR / "llm-bridge.log", "w", encoding="utf-8")
        b_env = dict(env, SCP_LLM_BRIDGE_PORT="8081")
        p_bridge = subprocess.Popen(["bun", "run", "dev"], cwd=str(ROOT / "mini-services" / "llm-bridge"), env=b_env, stdout=bridge_log, stderr=bridge_log)
        spawned_procs.append(p_bridge)

        # 2. Spawn SCP Python on 8000
        server_log = open(LOG_DIR / "scp-server.log", "w", encoding="utf-8")
        s_env = dict(env, SCP_PORT="8000", SCP_HOST="127.0.0.1")
        p_server = subprocess.Popen([sys.executable, "-m", "scp", "8000"], cwd=str(ROOT), env=s_env, stdout=server_log, stderr=server_log)
        spawned_procs.append(p_server)

        # 3. Spawn Dashboard on 3000
        dash_log = open(LOG_DIR / "dashboard.log", "w", encoding="utf-8")
        d_env = dict(env, PORT="3000", SCP_INTERNAL_URL="http://127.0.0.1:8000", LLM_BRIDGE_URL="http://127.0.0.1:8081")
        p_dash = subprocess.Popen(["bun", "run", "dev"], cwd=str(ROOT / "dashboard"), env=d_env, stdout=dash_log, stderr=dash_log)
        spawned_procs.append(p_dash)

        # 4. Wait for readiness
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Probe Bridge (8081)
            bridge_ready = False
            for _ in range(15):
                try:
                    r = await client.get("http://127.0.0.1:8081/api/tags")
                    if r.status_code == 200:
                        bridge_ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            assert bridge_ready, "LLM Bridge failed to reach HTTP 200 on port 8081"

            # Probe Server (8000)
            server_ready = False
            for _ in range(45):
                try:
                    r = await client.get("http://127.0.0.1:8000/health")
                    if r.status_code == 200:
                        server_ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            assert server_ready, "SCP API Server failed to reach HTTP 200 on port 8000"

            # Probe Dashboard (3000)
            dash_ready = False
            for _ in range(30):
                try:
                    r = await client.get("http://127.0.0.1:3000/")
                    if r.status_code == 200:
                        dash_ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
            assert dash_ready, "Web Dashboard failed to reach HTTP 200 on port 3000"

            # 5. Live Chat Query & Trace ID Extraction
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "model": "scp-standard",
                "messages": [{"role": "user", "content": "What is 2+2?"}]
            }
            chat_resp = await client.post("http://127.0.0.1:8000/v1/chat/completions", headers=headers, json=payload, timeout=30.0)
            assert chat_resp.status_code == 200, f"Chat failed with status {chat_resp.status_code}"
            chat_data = chat_resp.json()
            trace_id = chat_data.get("trace_id") or chat_resp.headers.get("X-SCP-Trace-ID")
            assert trace_id, "No trace_id found in chat response body or headers"

            # 6. Verify Trace Retrieval & Redaction
            trace_resp = await client.get(f"http://127.0.0.1:8000/v3/trace/{trace_id}", headers=headers)
            assert trace_resp.status_code == 200, f"Trace lookup failed: {trace_resp.status_code}"
            trace_record = trace_resp.json()
            assert trace_record.get("trace_id") == trace_id

            # Verify credential redaction: raw token must not appear in the trace response
            assert token not in trace_resp.text, "Sensitive token leaked in trace record response!"

            # 7. Verify Fail-Closed Security Boundary (Unauthenticated query)
            unauth_resp = await client.get(f"http://127.0.0.1:8000/v3/trace/{trace_id}")
            assert unauth_resp.status_code == 401, f"Expected 401 for unauth trace query, got {unauth_resp.status_code}"

    finally:
        # 8. Clean Shutdown (Zero-Zombie Guarantee)
        for p in spawned_procs:
            kill_process_tree(p.pid)
        clean_ports()
        assert verify_ports_free(), "Lingering zombie processes detected! Ports 8000, 8081, or 3000 still bound."

if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
    print("[PASS] Full SCP Cluster Live E2E Verification & Clean Shutdown Completed.")
```

---

## 6. Verification Method
1. **Launcher Contract Test**:
   `pytest tests/T01_boot/test_startup_launcher_contract.py -q`
   (Fails on line 20 until updated to reflect R6-02 LLM Bridge inclusion).
2. **Cluster Port Check**:
   PowerShell: `Get-NetTCPConnection -LocalPort 8000, 8081, 3000, 3030 -State Listen -ErrorAction SilentlyContinue`
3. **Trace Retrieval Security Gate**:
   `curl -i -X GET http://127.0.0.1:8000/v3/trace/test-id` returns HTTP 401 Unauthorized.
   `curl -i -H "Authorization: Bearer <SCP_AUTH_TOKEN_SECRET>" http://127.0.0.1:8000/v3/trace/test-id` returns HTTP 404 (or 200 if trace exists).
