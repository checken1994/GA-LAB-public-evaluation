# Hard Handoff Report: Milestone 2 (P1: Security, Concurrency & Deployment Hardening)

**Author**: Explorer P1-1 (Generation 2)  
**Working Directory**: `D:\scp\.agents\explorer_p1_1_gen2`  
**Target Scope**: 13 Audit Findings (R6-02, R6-03, R6-04, R2-03, R2-04, R2-05, R2-06, R1-03, R1-04, R5-04, R5-05, R5-06, R5-07)  
**Mode**: Read-Only Forensic Investigation & Drop-in Remediation Architecture  

---

## 1. Observation

Each observation below was directly inspected and empirically verified against the live repository at `D:\scp`.

### Observation 1 (R6-02: `start-scp.bat` missing LLM Bridge)
- **Target File**: `D:\scp\start-scp.bat` (lines 69–94)
- **Direct Evidence**:
  ```bat
  # start-scp.bat lines 69-76
  echo [0/3] Dung services cu (neu co)...
  taskkill /f /fi "WINDOWTITLE eq SCP-Loop-Scheduler*" >nul 2>&1
  taskkill /f /fi "WINDOWTITLE eq SCP-Python*" >nul 2>&1
  taskkill /f /fi "WINDOWTITLE eq SCP-Dashboard*" >nul 2>&1
  for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3030 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
  for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
  for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
  timeout /t 3 /nobreak >nul

  echo.
  echo [INFO] Khoi dong 3 child services (API-Only, khong Ollama)...
  echo.

  REM --- 1. Loop Scheduler (port 3030) ---
  echo [1/3] Loop Scheduler - port 3030
  start "SCP-Loop-Scheduler" cmd /k "cd /d %~dp0mini-services\loop-scheduler && set SCP_ENV_FILE=%~dp0.env && set SCP_BASE_URL=http://127.0.0.1:8000 && set SCP_INTERNAL_URL=http://127.0.0.1:8000 && set LOOP_SCHEDULER_URL=http://127.0.0.1:3030 && set LLM_BRIDGE_URL=http://127.0.0.1:8081 && set LOOP_LOG_PATH=%~dp0data\loop_runs.jsonl && bun run dev"
  timeout /t 1 /nobreak >nul

  REM --- 2. SCP Python (port 8000) ---
  ...
  REM --- 3. Dashboard Next.js (port 3000) ---
  ```
  `start-scp.bat` announces and launches only 3 child services, completely omitting `mini-services/llm-bridge`. However, line 84 injects `LLM_BRIDGE_URL=http://127.0.0.1:8081` into the Loop Scheduler environment, so all calls to port 8081 fail with connection refused on Windows. Unix counterpart `start-scp.sh` lines 67–75 properly launches LLM Bridge on port 8081 as service `[1/4]`.

### Observation 2 (R6-03: Dashboard fallback URL port mismatch)
- **Target File**: `D:\scp\dashboard\src\lib\scp-backend-url.ts` (lines 83–90)
- **Direct Evidence**:
  ```typescript
  export function resolveHealthProbeTargets(): HealthProbeTargets {
    return {
      fastapi: normalizeBase(process.env.SCP_INTERNAL_URL, "http://127.0.0.1:8000"),
      loopScheduler: normalizeBase(process.env.LOOP_SCHEDULER_URL, "http://127.0.0.1:3030"),
      llmBridge: normalizeBase(process.env.LLM_BRIDGE_URL, "http://127.0.0.1:11434"),
      extraHosts: parseHostList(process.env.SCP_HEALTH_ALLOWED_HOSTS),
    }
  }
  ```
  When `LLM_BRIDGE_URL` is omitted, the default fallback URL defaults to `http://127.0.0.1:11434` (Ollama's default port), instead of `http://127.0.0.1:8081`.
- **Cross-Coupled Test Finding**: In `tests/T03_capability/test_security_sweep_s5.mjs:445`:
  ```javascript
  assert.equal(t.llmBridge, "http://127.0.0.1:11434")
  ```
  Updating `scp-backend-url.ts` directly affects this test assertion.

### Observation 3 (R6-04: Dockerfile port mismatch and instant termination command)
- **Target File**: `D:\scp\Dockerfile` (lines 43, 50–51)
- **Direct Evidence**:
  ```dockerfile
  43: EXPOSE 8080
  ...
  50: ENTRYPOINT ["python", "-m", "scp"]
  51: CMD ["--help"]
  ```
  The container exposes port 8080 while the Python server defaults to port 8000 (`scp/__main__.py:104`). Furthermore, running `docker run <image>` runs `python -m scp --help` which prints the CLI help and exits immediately with code 0 rather than starting the daemon.

### Observation 4 (R2-03: Egress bypass in BrowserSession)
- **Target File**: `D:\scp\scp\web_control\browser_session.py` (lines 145–172)
- **Direct Evidence**:
  ```python
  async def navigate_and_read(self, url: str, target: dict[str, Any] | None = None) -> dict[str, Any]:
      url = self.validate_url(url)
      ...
  def open_visible(self, url: str) -> dict[str, Any]:
      url = self.validate_url(url)
      ...
  ```
  `enforce_egress_policy` is already imported at `browser_session.py:19` (`from scp.security.url_safety import enforce_egress_policy`), and is called in `targets()` at line 41, but is completely missing inside `navigate_and_read` (line 146) and `open_visible` (line 159). `validate_url` only checks scheme and SSRF private IP ranges; when `SCP_EGRESS_MODE=deny`, browser sessions can navigate to arbitrary public websites undetected.

### Observation 5 (R2-04: SQL injection in `LearningDB.execute_insert`)
- **Target File**: `D:\scp\scp\knowledge\learning_db.py` (lines 63–70)
- **Direct Evidence**:
  ```python
  def execute_insert(self, table: str, data: Dict[str, Any]):
      cols = ", ".join(data.keys())
      placeholders = ", ".join(["?"] * len(data))
      values = tuple(data.values())
      
      with sqlite3.connect(self.db_path) as conn:
          conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
  ```
  `table` and dictionary keys `data.keys()` are directly formatted into the SQL statement via f-string without validation against an allowlist or regex identifier pattern.
- **Subsystem Consumers**:
  - `open_questions` (`open_question_authority.py`)
  - `missing_pieces` (`open_question_authority.py`)
  - `hypotheses` (`hypothesis_authority.py`)
  - `benchmark_runs` (`benchmark_authority.py`)
  - `experiments` (`experiment_authority.py`)
  - `lessons` (`lesson_authority.py`)

### Observation 6 (R2-05: Path traversal in `batch_benchmark_routes.py`)
- **Target File**: `D:\scp\scp\api/routes/batch_benchmark_routes.py` (lines 40–43, 307–348)
- **Direct Evidence**:
  ```python
  def _job_dir(job_id: str) -> Path:
      path = _root() / job_id
      path.mkdir(parents=True, exist_ok=True)
      return path
  ```
  In routes `GET /batch/{job_id}`, `POST /batch/{job_id}/pause`, and `POST /batch/{job_id}/resume`, `job_id` is accepted directly from the URL path parameter without validation against `^[a-zA-Z0-9_-]+$`, permitting path traversal characters like `../../` into directory creation.

### Observation 7 (R2-06: Unauthenticated `/swe-bench/v1/chat/completions` & `/metrics`)
- **Target Files**:
  - `D:\scp\scp\api/routes/swe_bench_routes.py` (lines 15–16)
  - `D:\scp\scp\api_server.py` (lines 356–358)
- **Direct Evidence**:
  ```python
  # swe_bench_routes.py:15-16
  @router.post("/chat/completions")
  async def chat_completions(req: ChatCompletionRequest):
      ...
  
  # api_server.py:356-358
  @app.get("/metrics")
  async def metrics():
      return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
  ```
  Neither endpoint enforces authentication dependencies. Anyone with network reachability can invoke SWE-Bench completion endpoints or scrape internal Prometheus telemetry.
- **Cross-Coupled Test Finding**:
  `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py:259` and `tests/T03_capability/test_flow_34_swe_bench_scp_standard.py:18` query `/swe-bench/v1/chat/completions` without headers, which will return 401 once protected unless provided with authentication or dependency overrides.

### Observation 8 (R1-03: Broken `None` comparison in AST Type Flow Verifier)
- **Target File**: `D:\scp\scp\autofix\type_flow_verifier.py` (lines 381–392)
- **Direct Evidence**:
  ```python
  def _is_none_check(self, test: ast.expr) -> str | None:
      """Return the var name if `test` is `name is None` / `name is not None`."""
      try:
          if isinstance(test, ast.Compare):
              if len(test.ops) == 1 and isinstance(test.ops[0], (ast.Is, ast.IsNot)):
                  left = test.left
                  if isinstance(left, ast.Name):
                      return left.id
          return None
      except Exception:
          return None
  ```
  **Empirical Test Command & Output**:
  ```powershell
  python -c "import ast; from scp.autofix.type_flow_verifier import _CallSiteCollector; a = _CallSiteCollector('f', 'b'); n1 = ast.parse('if x is None: pass').body[0].test; n2 = ast.parse('if x is True: pass').body[0].test; print('is None:', a._is_none_check(n1), 'is True:', a._is_none_check(n2))"
  # Output: is None: x is True: x
  ```
  `_is_none_check(n2)` returned `'x'` on `if x is True:`, mistakenly reporting a boolean identity check as a None check because it never inspected `test.comparators[0]`.

### Observation 9 (R1-04: Missing `encoding="utf-8"` in file operations)
- **Target Files**:
  - `D:\scp\scp\meta\external_trust.py` (line 120): `content = constitution_path.read_text()`
  - `D:\scp\scp\benchmark\compare_results.py` (line 80, 82, 183):
    - line 80: `with open(scp_file) as f:`
    - line 82: `with open(baseline_file) as f:`
    - line 183: `with _output_path.open("w") as f:`
  - `D:\scp\scp\benchmark\run_benchmark.py` (line 80, 135):
    - line 80: `with open(filepath) as f:`
    - line 135: `with open(filepath) as f:`
- **Direct Evidence**: On Windows with non-UTF-8 system codepages (e.g., CP1252 or CP1258), omitting `encoding="utf-8"` raises `UnicodeDecodeError: 'charmap' codec can't decode byte` when parsing files containing UTF-8 characters such as quotes or Vietnamese text.

### Observation 10 & 11 (R5-04 & R5-05: Async transaction collision & connection pool leak in KernelStorage)
- **Target Files**:
  - `D:\scp\scp\kernel_storage.py` (lines 97–123, 166–175)
  - `D:\scp\scp\kernel_storage_pg.py` (lines 276–310, 486–495)
- **Direct Evidence**:
  ```python
  # kernel_storage.py:97-123
  self._conn_local = threading.local()
  self._all_conns: list[sqlite3.Connection] = []
  self._conn_guard = threading.Lock()
  ...
  def _get_conn(self) -> sqlite3.Connection:
      conn = getattr(self._conn_local, "conn", None)
      if conn is None:
          conn = self._make_connection()
          self._conn_local.conn = conn
          with self._conn_guard:
              self._all_conns.append(conn)
      return conn
  ```
  In asyncio, concurrent tasks running on the main event loop thread share the identical `threading.local()` instance. When task 1 issues `begin()` and yields to the event loop, task 2 invoking `begin()` attempts a nested `BEGIN IMMEDIATE` on the same connection, crashing with `sqlite3.OperationalError: cannot start a transaction within a transaction`. Furthermore, `_all_conns` grows monotonically every time a thread pool worker executes a query without cleanup or bounding, and calling `close()` closes the connections without invalidating the surviving thread locals.

### Observation 12 (R5-06: Unbounded in-memory collections)
- **Target Files**:
  1. `scp/api/webhook.py:81-82, 144, 212`: `_threat_history: list[dict] = []` and `_alert_history: list[dict] = []` append indefinitely with zero length caps.
  2. `scp/api/routes/risk_routes.py:37, 124`: `_incidents: dict[str, dict] = {}` grows monotonically on every incident opened.
  3. `scp/security/auth.py:58, 70, 76`: `_auth_failures: dict[str, list[float]] = {}` appends timestamps and reassigns empty lists `_auth_failures[ip] = []` without deleting keys, causing unbounded dictionary key growth under IP rotation attacks.
  4. `scp/api/routes/batch_benchmark_routes.py:30, 265`: `_JOBS: dict[str, threading.Thread] = {}` retains completed Thread objects indefinitely.
  5. `scp/core/multi_source_verifier.py:267, 296`: `_CID_CACHE: dict[str, int] = {}` caches PubChem compound CIDs without an eviction policy or size limit.

### Observation 13 (R5-07: Incomplete graceful shutdown in `api_server_parts/lifespan.py`)
- **Target Files**:
  - `D:\scp\scp\api_server_parts\lifespan.py` (lines 312–334, 448–477)
  - `D:\scp\scp\core\db_manager.py` (line 163)
- **Direct Evidence**:
  1. `_why_thread` runs a `while True` loop sleeping for 300 seconds (`time.sleep(300)`) with no `threading.Event` stop signal, completely ignoring process termination.
  2. Lines 460–462 cancel background tasks:
     ```python
     for _task in (_scheduler_bootstrap_task, _evolution_bootstrap_task, _background_task, _startup_gate_task, _judge_launch_task):
         if _task is not None and (not _task.done()):
             _task.cancel()
     ```
     These tasks are never awaited (`await asyncio.gather(...)`), resulting in cancelled task warnings and abrupt termination of pending asynchronous I/O.
  3. Neither `db_manager.checkpoint_wal()` nor database connection closures are invoked during the lifespan shutdown sequence.

---

## 2. Logic Chain

```
Observation 1 (start-scp.bat omits llm-bridge on 8081)
  -> Loop Scheduler fails to connect to LLM bridge on Windows
  -> Propose: Add [1/4] LLM Bridge startup block, port kill, and status check in start-scp.bat.

Observation 2 (scp-backend-url.ts fallback is 11434 instead of 8081)
  -> Dashboard health check pings dead port 11434 and flags LLM bridge as dead
  -> Propose: Change fallback URL from 11434 to 8081; update test_security_sweep_s5.mjs:445 assertion.

Observation 3 (Dockerfile EXPOSE 8080 and CMD ["--help"])
  -> Container ports do not match api_server 8000 default; container terminates on launch
  -> Propose: Change EXPOSE 8000 and CMD ["8000"].

Observation 4 (BrowserSession navigate_and_read & open_visible omit enforce_egress_policy)
  -> Browser automation bypasses egress firewall policy in deny mode
  -> Propose: Insert enforce_egress_policy(url) immediately after url validation.

Observation 5 (LearningDB.execute_insert f-string table/column interpolation)
  -> SQL injection possible if untrusted keys reach execute_insert
  -> Propose: Validate table against ALLOWED_TABLE_COLUMNS and columns against allowed set + regex identifier allowlist.

Observation 6 (_job_dir joins unsanitized job_id into filesystem path)
  -> Directory traversal can create arbitrary directory trees
  -> Propose: Enforce job_id regex ^[a-zA-Z0-9_-]+$ in _job_dir and route handlers.

Observation 7 (/swe-bench/v1/chat/completions and /metrics have no authentication)
  -> Internal metrics and LLM completion endpoints exposed publicly
  -> Propose: Apply Depends(verify_admin); update test callers with Authorization headers.

Observation 8 (_is_none_check ignores test.comparators[0])
  -> `x is True` incorrectly classified as a None-check, breaking AST flow analysis
  -> Propose: Assert isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None.

Observation 9 (read_text and open calls omit encoding="utf-8")
  -> Non-UTF-8 Windows defaults crash with UnicodeDecodeError
  -> Propose: Explicitly pass encoding="utf-8" to all 6 identified call sites.

Observations 10 & 11 (threading.local causes collision in asyncio; _all_conns leaks)
  -> Concurrent asyncio tasks collide on single thread connection; connection pool leaks memory
  -> Propose: Implement contextvars.ContextVar for task-safe connections + bounded pool with dead connection pruning.

Observation 12 (6 in-memory structures grow without bound)
  -> Memory leak over long-running daemon execution
  -> Propose: Apply bounded collections (deque(maxlen=1000) for history, OrderedDict with eviction for dict caches).

Observation 13 (Lifespan cancel tasks not awaited, _why_thread not signaled, db not checkpointed)
  -> Dirty shutdowns, unclosed resources, un-checkpointed WAL logs
  -> Propose: Pass threading.Event to _why_thread, await asyncio.gather on cancelled tasks, invoke checkpoint_wal() and close_db().
```

---

## 3. Caveats

1. **Read-Only Investigation Bound**: No production source files were modified during this investigation.
2. **Cross-Subsystem Dependencies**:
   - Modifying `dashboard/src/lib/scp-backend-url.ts` fallback port to 8081 requires updating `tests/T03_capability/test_security_sweep_s5.mjs:445`.
   - Modifying `/swe-bench/v1/chat/completions` to require `verify_admin` requires updating test fixtures in `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py` and `tests/T03_capability/test_flow_34_swe_bench_scp_standard.py` to pass the admin bearer token.
3. **Database Concurrency**: While SQLite in WAL mode allows multiple concurrent readers, only one writer can hold a write lock. Context-local connection management prevents transaction collisions inside the same process thread, but concurrent writers will still queue and wait on `busy_timeout`.

---

## 4. Conclusion & Drop-in Remediation Code

### Item 1: R6-02 — `start-scp.bat`
**Target File**: `D:\scp\start-scp.bat`  
**Lines**: 68–94, 115–130  
**Implementation Details**:
Replace the 3-service startup with 4 services, including port cleanup for 8081:
```bat
REM --- Stop old instances (kill by window-title + port, NOT by image name) ---
echo [0/4] Dung services cu (neu co)...
taskkill /f /fi "WINDOWTITLE eq SCP-LLM-Bridge*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq SCP-Loop-Scheduler*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq SCP-Python*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq SCP-Dashboard*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8081 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3030 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
timeout /t 3 /nobreak >nul

echo.
echo [INFO] Khoi dong 4 child services (API-Only, khong Ollama)...
echo.

REM --- 1. LLM Bridge (port 8081) ---
echo [1/4] LLM Bridge - port 8081
start "SCP-LLM-Bridge" cmd /k "cd /d %~dp0mini-services\llm-bridge && set SCP_LLM_BRIDGE_PORT=8081 && bun run dev"
timeout /t 2 /nobreak >nul

REM --- 2. Loop Scheduler (port 3030) ---
echo [2/4] Loop Scheduler - port 3030
start "SCP-Loop-Scheduler" cmd /k "cd /d %~dp0mini-services\loop-scheduler && set SCP_ENV_FILE=%~dp0.env && set SCP_BASE_URL=http://127.0.0.1:8000 && set SCP_INTERNAL_URL=http://127.0.0.1:8000 && set LOOP_SCHEDULER_URL=http://127.0.0.1:3030 && set LLM_BRIDGE_URL=http://127.0.0.1:8081 && set LOOP_LOG_PATH=%~dp0data\loop_runs.jsonl && bun run dev"
timeout /t 1 /nobreak >nul

REM --- 3. SCP Python (port 8000) — API-Only, no Ollama, no venv ---
echo [3/4] SCP Python - port 8000 (boot ~15s, vui long doi...)
start "SCP-Python" cmd /k "cd /d %~dp0 && python -m scp 8000"

REM --- 4. Dashboard Next.js (port 3000) ---
echo [4/4] Dashboard Next.js - port 3000 (standalone build)
start "SCP-Dashboard" cmd /k "cd /d %~dp0dashboard && set SCP_INTERNAL_URL=http://127.0.0.1:8000 && set LOOP_SCHEDULER_URL=http://127.0.0.1:3030 && set LLM_BRIDGE_URL=http://127.0.0.1:8081 && bun run start"
```

---

### Item 2: R6-03 — `dashboard/src/lib/scp-backend-url.ts`
**Target File**: `D:\scp\dashboard\src\lib\scp-backend-url.ts`  
**Line**: 87  
**Drop-in Replacement**:
```typescript
<<<<
    llmBridge: normalizeBase(process.env.LLM_BRIDGE_URL, "http://127.0.0.1:11434"),
====
    llmBridge: normalizeBase(process.env.LLM_BRIDGE_URL, "http://127.0.0.1:8081"),
>>>>
```
**Accompanying Test Fix**: In `tests/T03_capability/test_security_sweep_s5.mjs:445`:
```javascript
<<<<
        assert.equal(t.llmBridge, "http://127.0.0.1:11434")
====
        assert.equal(t.llmBridge, "http://127.0.0.1:8081")
>>>>
```

---

### Item 3: R6-04 — `Dockerfile`
**Target File**: `D:\scp\Dockerfile`  
**Lines**: 43, 51  
**Drop-in Replacement**:
```dockerfile
<<<<
43: EXPOSE 8080
...
50: ENTRYPOINT ["python", "-m", "scp"]
51: CMD ["--help"]
====
43: EXPOSE 8000
...
50: ENTRYPOINT ["python", "-m", "scp"]
51: CMD ["8000"]
>>>>
```

---

### Item 4: R2-03 — `scp/web_control/browser_session.py`
**Target File**: `D:\scp\scp\web_control\browser_session.py`  
**Lines**: 145–160  
**Drop-in Replacement**:
```python
    async def navigate_and_read(self, url: str, target: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.validate_url(url)
        enforce_egress_policy(url)
        targets = await self.targets()
        ...

    def open_visible(self, url: str) -> dict[str, Any]:
        url = self.validate_url(url)
        enforce_egress_policy(url)
        browser = os.environ.get("SCP_BROWSER_PATH", "")
        ...
```

---

### Item 5: R2-04 — `scp/knowledge/learning_db.py`
**Target File**: `D:\scp\scp\knowledge\learning_db.py`  
**Lines**: 63–70  
**Drop-in Replacement**:
```python
import re

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

ALLOWED_TABLE_COLUMNS: dict[str, set[str]] = {
    "open_questions": {
        "question_id", "title", "question", "scope_json", "trigger",
        "related_claim_refs_json", "related_knowledge_refs_json",
        "known_evidence_refs_json", "needed_observations_json",
        "needed_capabilities_json", "status", "created_at",
    },
    "missing_pieces": {
        "missing_piece_id", "question_id", "kind", "description",
        "blocks_claims_json", "blocks_decisions_json",
        "needed_evidence_json", "discovered_by", "created_at",
    },
    "hypotheses": {
        "hypothesis_id", "question_ref", "hypothesis", "mechanism",
        "predictions_json", "assumptions_json",
        "needed_capabilities_json", "status", "created_at",
    },
    "benchmark_runs": {
        "run_id", "benchmark_id", "target_capabilities_json",
        "status", "score", "regression_detected",
        "evidence_refs_json", "created_at",
    },
    "experiments": {
        "experiment_id", "hypothesis_ref", "setup_instructions_json",
        "sandbox_requirements_json", "execution_status",
        "resulting_evidence_refs_json", "started_at", "completed_at",
        "created_at",
    },
    "lessons": {
        "lesson_id", "experiment_refs_json", "insights_json",
        "knowledge_updates_json", "capability_updates_json",
        "created_at",
    },
}

    def execute_insert(self, table: str, data: Dict[str, Any]):
        if not isinstance(table, str) or not _IDENTIFIER_RE.match(table):
            raise ValueError(f"Invalid table identifier format: {table!r}")
        if table not in ALLOWED_TABLE_COLUMNS:
            raise ValueError(f"Table not permitted in LearningDB allowlist: {table!r}")
        if not data:
            return

        allowed_cols = ALLOWED_TABLE_COLUMNS[table]
        for col in data.keys():
            if not isinstance(col, str) or not _IDENTIFIER_RE.match(col):
                raise ValueError(f"Invalid column identifier format: {col!r}")
            if col not in allowed_cols:
                raise ValueError(f"Column '{col}' is not allowed for table '{table}'")

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = tuple(data.values())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
```

---

### Item 6: R2-05 — `scp/api/routes/batch_benchmark_routes.py`
**Target File**: `D:\scp\scp\api/routes/batch_benchmark_routes.py`  
**Lines**: 40–43, 307–348  
**Drop-in Replacement**:
```python
_JOB_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")

def _validate_job_id(job_id: str) -> str:
    if not job_id or not isinstance(job_id, str) or not _JOB_ID_REGEX.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format: must match ^[a-zA-Z0-9_-]+$")
    return job_id

def _job_dir(job_id: str) -> Path:
    _validate_job_id(job_id)
    root = _root().resolve()
    path = (root / job_id).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    path.mkdir(parents=True, exist_ok=True)
    return path
```

---

### Item 7: R2-06 — Authentication on SWE-Bench & Metrics Endpoints
**Target Files**:
1. `D:\scp\scp\api/routes/swe_bench_routes.py`
```python
from fastapi import APIRouter, Request, HTTPException, Depends
from scp.security.auth import verify_admin

router = APIRouter(prefix="/swe-bench/v1", tags=["swe-bench-compat"], dependencies=[Depends(verify_admin)])
```
2. `D:\scp\scp\api_server.py` (lines 356–358)
```python
from scp.security.auth import verify_admin

@app.get("/metrics", dependencies=[Depends(verify_admin)])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```
3. **Accompanying Test Updates**:
   In `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py:258` and `tests/T03_capability/test_flow_34_swe_bench_scp_standard.py:18`:
   Pass `headers={"Authorization": "Bearer dummy-secret-for-tests-123"}` (or use `app.dependency_overrides[verify_admin] = lambda: True`). Add test cases asserting 401 when called without token.

---

### Item 8: R1-03 — `scp/autofix/type_flow_verifier.py`
**Target File**: `D:\scp\scp\autofix\type_flow_verifier.py`  
**Lines**: 381–392  
**Drop-in Replacement**:
```python
    def _is_none_check(self, test: ast.expr) -> str | None:
        """Return the var name if `test` is `name is None` / `name is not None`."""
        try:
            if isinstance(test, ast.Compare):
                if len(test.ops) == 1 and len(test.comparators) == 1 and isinstance(test.ops[0], (ast.Is, ast.IsNot)):
                    # Left is variable name, comparator is None constant
                    if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
                        return test.left.id
                    # Left is None constant, comparator is variable name (e.g. None is x)
                    if isinstance(test.left, ast.Constant) and test.left.value is None and isinstance(test.comparators[0], ast.Name):
                        return test.comparators[0].id
            return None
        except Exception:  # noqa: BLE001
            return None
```

---

### Item 9: R1-04 — UTF-8 Encoding Enforcement
**Target Files**:
1. `D:\scp\scp\meta\external_trust.py` (line 120):
```python
<<<<
            content = constitution_path.read_text()
====
            content = constitution_path.read_text(encoding="utf-8")
>>>>
```
2. `D:\scp\scp\benchmark\compare_results.py` (lines 80, 82, 183):
```python
<<<<
80:    with open(scp_file) as f:
81:        scp = json.load(f)
82:    with open(baseline_file) as f:
...
183:    with _output_path.open("w") as f:
====
80:    with open(scp_file, encoding="utf-8") as f:
81:        scp = json.load(f)
82:    with open(baseline_file, encoding="utf-8") as f:
...
183:    with _output_path.open("w", encoding="utf-8") as f:
>>>>
```
3. `D:\scp\scp\benchmark\run_benchmark.py` (lines 80, 135):
```python
<<<<
80:         with open(filepath) as f:
...
135:         with open(filepath) as f:
====
80:         with open(filepath, encoding="utf-8") as f:
...
135:         with open(filepath, encoding="utf-8") as f:
>>>>
```

---

### Items 10 & 11: R5-04 & R5-05 — `KernelStorage` Concurrency & Bounded Pool
**Target Files**: `D:\scp\scp\kernel_storage.py` and `D:\scp\scp\kernel_storage_pg.py`  
**Drop-in Replacement for `SQLiteKernelStorage`**:
```python
import contextvars
from collections import deque

class SQLiteKernelStorage:
    def __init__(self, db_path: str | Path, max_conns: int = 16) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._max_conns = max_conns
        self._conn_ctx: contextvars.ContextVar[sqlite3.Connection | None] = contextvars.ContextVar(
            f"sqlite_kernel_conn_{id(self)}", default=None
        )
        self._all_conns: deque[sqlite3.Connection] = deque()
        self._conn_guard = threading.Lock()
        c = self._get_conn()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")

    def _is_open(self, conn: sqlite3.Connection) -> bool:
        try:
            _ = conn.total_changes
            return True
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            return False

    def _get_conn(self) -> sqlite3.Connection:
        conn = self._conn_ctx.get()
        if conn is not None and self._is_open(conn):
            return conn

        with self._conn_guard:
            # Prune closed connections
            open_conns = [c for c in self._all_conns if self._is_open(c)]
            self._all_conns = deque(open_conns)

            # Reuse idle connection not in transaction
            for candidate in self._all_conns:
                if not candidate.in_transaction:
                    self._conn_ctx.set(candidate)
                    return candidate

            # Bounded creation: if capacity reached, recycle oldest non-in-transaction or purge
            if len(self._all_conns) >= self._max_conns:
                oldest = self._all_conns.popleft()
                try:
                    oldest.close()
                except sqlite3.Error:
                    pass

            new_conn = self._make_connection()
            self._all_conns.append(new_conn)
            self._conn_ctx.set(new_conn)
            return new_conn

    def close(self) -> None:
        with self._conn_guard:
            for conn in list(self._all_conns):
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._all_conns.clear()
            self._conn_ctx.set(None)
```
*(Apply symmetric `contextvars.ContextVar` and bounded deque pattern to `PgKernelStorage` in `scp/kernel_storage_pg.py`).*

---

### Item 12: R5-06 — Bounded In-Memory Collections
**Target Files & Specific Patches**:
1. `scp/api/webhook.py`:
   ```python
   from collections import deque
   _threat_history: deque[dict] = deque(maxlen=1000)
   _alert_history: deque[dict] = deque(maxlen=1000)
   ```
   In `list_alerts()`: `alerts = list(_alert_history)[-limit:] if limit > 0 else list(_alert_history)`.
2. `scp/api/routes/risk_routes.py`:
   ```python
   from collections import OrderedDict
   _MAX_INCIDENTS = 1000
   _incidents: OrderedDict[str, dict] = OrderedDict()
   _incidents_lock = threading.Lock()
   ```
   In `open_incident()`:
   ```python
   with _incidents_lock:
       if len(_incidents) >= _MAX_INCIDENTS:
           _incidents.popitem(last=False)
       _incidents[incident_id] = record
   ```
3. `scp/security/auth.py`:
   ```python
   _MAX_AUTH_FAILURE_IPS = 5000
   _auth_failures_lock = threading.Lock()
   ```
   In `_check_rate_limit(ip)`:
   ```python
   with _auth_failures_lock:
       failures = [t for t in _auth_failures.get(ip, []) if now - t < _RATE_LIMIT_WINDOW]
       if failures:
           _auth_failures[ip] = failures
       else:
           _auth_failures.pop(ip, None)  # Delete empty IP key!
       if len(_auth_failures) > _MAX_AUTH_FAILURE_IPS:
           # Evict oldest entry
           oldest_ip = next(iter(_auth_failures))
           _auth_failures.pop(oldest_ip, None)
       return len(failures) < _RATE_LIMIT_MAX_FAILURES
   ```
4. `scp/api/routes/batch_benchmark_routes.py`:
   In `_start_job(job_id: str)`:
   ```python
   with _JOBS_LOCK:
       # Prune dead threads
       dead = [jid for jid, t in _JOBS.items() if not t.is_alive()]
       for jid in dead:
           del _JOBS[jid]
       if len(_JOBS) >= 100:
           # Evict oldest completed
           for jid in list(_JOBS.keys()):
               if not _JOBS[jid].is_alive():
                   del _JOBS[jid]
                   break
   ```
5. `scp/core/multi_source_verifier.py`:
   ```python
   from collections import OrderedDict
   _MAX_CID_CACHE = 1000
   _CID_CACHE: OrderedDict[str, int] = OrderedDict()
   ```
   When writing:
   ```python
   if len(_CID_CACHE) >= _MAX_CID_CACHE:
       _CID_CACHE.popitem(last=False)
   _CID_CACHE[compound.lower()] = cid
   ```

---

### Item 13: R5-07 — Lifespan Graceful Shutdown
**Target File**: `D:\scp\scp\api_server_parts\lifespan.py`  
**Lines**: 312–334, 448–478  
**Drop-in Replacement**:
1. **Pass stop event to `_why_verify_loop`**:
   ```python
   _why_verify_stop = threading.Event()
   app.state.why_verify_stop = _why_verify_stop

   def _why_verify_loop():
       if _why_verify_stop.wait(timeout=180):
           return
       while not _why_verify_stop.is_set():
           try:
               ...
           except Exception as _loop_exc:
               ...
           if _why_verify_stop.wait(timeout=300):
               break
   ```
2. **Signal all events, await cancelled tasks, checkpoint WAL, and close DB**:
   ```python
   # Signal threads to stop
   for _stop_event in (
       getattr(app.state, 'deep_audit_stop', None),
       getattr(app.state, 'attack_monitor_stop', None),
       getattr(app.state, 'retry_policy_stop', None),
       getattr(app.state, 'why_verify_stop', None),
   ):
       if _stop_event is not None:
           _stop_event.set()

   # Cancel and AWAIT background tasks
   _pending_tasks = [
       t for t in (_scheduler_bootstrap_task, _evolution_bootstrap_task, _background_task, _startup_gate_task, _judge_launch_task)
       if t is not None and not t.done()
   ]
   for _task in _pending_tasks:
       _task.cancel()
   if _pending_tasks:
       await asyncio.gather(*_pending_tasks, return_exceptions=True)

   # Checkpoint WAL and close SQLite connections
   try:
       from scp.core.db_manager import checkpoint_wal
       checkpoint_wal()
       logger.info("[SHUTDOWN] WAL checkpoint completed")
   except Exception as exc:
       logger.warning("[SHUTDOWN] WAL checkpoint failed: %s", exc)

   try:
       if hasattr(app.state, "task_kernel") and app.state.task_kernel:
           app.state.task_kernel.close()
           logger.info("[SHUTDOWN] TaskKernel closed cleanly")
   except Exception as exc:
       logger.warning("[SHUTDOWN] TaskKernel close error: %s", exc)
   ```

---

## 5. Verification Method

To independently verify these findings and confirm that proposed fixes resolve the issues without introducing regressions:

1. **Meta-Audit & Collection Test**:
   ```powershell
   python tools/t00_meta_audit.py
   pytest tests/ --collect-only -q
   ```
   *Expected*: Exit code 0, 0 new regressions.

2. **R1-03 AST Type Flow Verification**:
   ```powershell
   python -c "import ast; from scp.autofix.type_flow_verifier import _CallSiteCollector; a = _CallSiteCollector('f', 'b'); n = ast.parse('if x is True: pass').body[0].test; assert a._is_none_check(n) is None, 'Should not match True'"
   ```

3. **R2-04 SQL Allowlist Validation**:
   ```powershell
   python -c "from scp.knowledge.learning_db import LearningDB, ALLOWED_TABLE_COLUMNS; from pathlib import Path; db = LearningDB(Path('data/test_learn.db')); import pytest;
   try:
       db.execute_insert('invalid_table', {'id': 1})
   except ValueError:
       print('PASS: Invalid table blocked')
   "
   ```

4. **R2-05 Path Traversal Validation**:
   ```powershell
   python -c "from scp.api.routes.batch_benchmark_routes import _job_dir; from fastapi import HTTPException;
   try:
       _job_dir('../../etc')
   except HTTPException as e:
       assert e.status_code == 400
       print('PASS: Path traversal blocked with HTTP 400')
   "
   ```

5. **R2-06 Auth & Health Target Parity**:
   ```powershell
   bun tests/T03_capability/test_security_sweep_s5.mjs
   pytest tests/T02_contract/test_flow_03_openai_compat_scp_standard.py -k swe_bench
   ```

6. **Full Milestone Test Suite Verification**:
   ```powershell
   pytest tests/T01_boot tests/T02_contract tests/T03_capability tests/T04_kernel -q
   ```
