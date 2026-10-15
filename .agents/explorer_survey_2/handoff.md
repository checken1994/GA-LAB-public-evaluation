# Audit Report: Security & Secret Handling (R2) and Runtime Correctness & Concurrency (R5)

**Explorer**: Security & Runtime Explorer (Survey Phase)  
**Working Directory**: `D:\scp\.agents\explorer_survey_2`  
**Project Root**: `D:\scp`  
**Date**: 2026-09-22  
**Integrity Mode**: Development / Survey  

---

## Executive Summary

A comprehensive, evidence-grounded audit of Requirement Domain **R2 (Security & Secret Handling)** and Domain **R5 (Runtime Correctness & Concurrency)** was conducted across the entire SCP codebase (~221,000 Python LOC, 1,142 `.py` files, TypeScript sidecars, and configuration files).

The audit identified **17 confirmed architectural, security, and concurrency findings**:
- **CRITICAL (5 findings)**: 
  - `R2-F01`: Public unauthenticated `/v3/trace/{trace_id}` endpoint with zero attribute redaction on the active route in `api_server.py`.
  - `R2-F02`: Multiple redaction blind spots in `trace_contract.py:redact_attributes` (leaking raw string values, missing sensitive keys, tuple headers, and removed size bounds).
  - `R5-F01`: Destructive race condition and data loss during un-locked `ChatMemoryStore._prune_if_needed` temporary file replacement.
  - `R5-F02`: Broken cryptographic hash chains and $O(N)$ memory/IO scaling in un-locked `TraceLedger.append()`.
  - `R5-F03`: SQLite database lock dropped before executing queries in `db_manager.py:db_query_one` and `db_query_all`, causing concurrent multi-threaded execution on an unprotected shared C connection.
- **HIGH (7 findings)**:
  - `R2-F03`: Egress policy bypass in `WebNavigator.browse_logged_in` and `BrowserSession.navigate_and_read` / `open_visible` under `SCP_EGRESS_MODE=deny`.
  - `R2-F04`: SQL injection vector in `LearningDB.execute_insert` through unescaped f-string table and column names.
  - `R2-F05`: Path traversal vector in `batch_benchmark_routes.py:_job_dir` allowing arbitrary directory creation outside `data/`.
  - `R2-F06`: Unauthenticated public exposure of SWE-Bench completions (`/swe-bench/v1/chat/completions`) and Prometheus metrics (`/metrics`).
  - `R5-F04`: Async transaction state collision across coroutines sharing thread-local connections in `KernelStorage`.
  - `R5-F05`: Monotonic connection pool leak in `KernelStorage._all_conns` and invalidation failures on `close()`.
  - `R5-F07`: Uncoordinated graceful shutdown leaving infinite daemon loops running (`_why_thread`) and unawaited cancelled async tasks.
- **MEDIUM (5 findings)**:
  - `R2-F07`: Unauthenticated local LLM Bridge microservice (`llm-bridge`) permitting quota exhaustion and prompt exfiltration.
  - `R2-F08`: Sensitive authentication tokens transmitted via URL query parameters in WebSocket `/chat` and dashboard HTML.
  - `R5-F06`: Multiple unbounded in-memory data structures (`_threat_history`, `_alert_history`, `_incidents`, `_auth_failures`, `_JOBS`, `_CID_CACHE`) causing slow memory leaks.
  - `R5-F08`: Unsynchronized shared mutable dictionaries in `ConversationManager` and `risk_routes.py` vulnerable to race conditions.
  - `R5-F09`: Unmanaged `subprocess.Popen` browser process spawning in `BrowserSession.open_visible`.

---

## 1. Observation

### Domain R2: Security & Secret Handling

#### Finding R2-F01 (CRITICAL) — Public Unauthenticated Trace Endpoint & Zero Redaction on Active Route
- **File**: `scp/api_server.py`
- **Lines**: 541–566
- **Observation**:
  The active FastAPI server registers `/v3/trace/{trace_id}` and `/api/v3/trace/{trace_id}` directly inside `api_server.py`. The endpoint specifies no security dependency (neither `verify_admin` nor `get_current_user`). Moreover, the implementation does not invoke `redact_attributes()`; it merges raw fields and returns them directly to any caller over HTTP.
  An alternative router with redaction exists in `scp/api_server_parts/_trace_impl.py`, but it is an uncommitted/untracked file and is never imported or mounted in `api_server.py`.
- **Verbatim Code**:
  ```python
  # scp/api_server.py:541-566
  @app.get("/v3/trace/{trace_id}")
  @app.get("/api/v3/trace/{trace_id}")
  async def get_trace_record(trace_id: str):
      """Retrieve backward-traceable causal graph and evidence for a specific trace_id."""
      from fastapi import HTTPException
      from pathlib import Path
      from scp.trace_ledger import TraceLedger
      data_dir = Path("data")
      if not data_dir.exists():
          data_dir = Path(__file__).resolve().parent.parent / "data"
      ledger = TraceLedger(data_dir / "trace_ledger.jsonl")
      record = ledger.get_trace(trace_id)
      if not record:
          record = TraceLedger(data_dir / "ask_task_kernel_trace.jsonl").get_trace(trace_id)
      if not record:
          record = TraceLedger(data_dir / "trace.jsonl").get_trace(trace_id)
      if not record:
          record = TraceLedger(data_dir / "request_runs.jsonl").get_trace(trace_id)
      if not record:
          raise HTTPException(status_code=404, detail=f"Trace record not found: {trace_id}")
      if isinstance(record.get("fields"), dict):
          merged = dict(record["fields"])
          merged.update({k: v for k, v in record.items() if k != "fields"})
          merged["_ledger_entry"] = record
          return merged
      return record
  ```

#### Finding R2-F02 (CRITICAL) — Multiple Redaction Blind Spots in `redact_attributes()`
- **File**: `scp/core/trace_contract.py`
- **Lines**: 19–30, 44–64
- **Observation**:
  1. **Value Blind Spot**: `redact_attributes` inspects only dictionary keys (`key_text = str(key)`). String values are never checked against `_SENSITIVE_PARTS`. An attribute like `{"url": "https://api.openai.com/v1?key=sk-12345"}` or `{"error": "Authorization failed with Bearer secret"}` passes unredacted.
  2. **Missing Sensitive Keys**: `_SENSITIVE_PARTS` includes `("secret", "token", "password", "cookie", "api_key", "authorization", "private_key", "credential", "key", "bearer")`. It omits `"auth"`, `"dsn"`, `"connection_string"`, `"proxy"`, `"cert"`, `"session"`, and `"pin"`.
  3. **Header Tuple Leakage**: In HTTP request representations using header tuples (e.g. `[("Authorization", "Bearer sk-12345")]`), the tuple elements are strings, not dict keys. The recursion treats them as sequence elements and returns them unmodified.
  4. **Removal of String & List Bounds**: An uncommitted change in `trace_contract.py` stripped the 512-character string truncation and 50-item list limit, returning unbounded raw objects.
- **Verbatim Code**:
  ```python
  # scp/core/trace_contract.py:44-64
  def redact_attributes(value: Any) -> Any:
      if isinstance(value, Mapping):
          result: dict[str, Any] = {}
          for key, item in value.items():
              key_text = str(key)
              if any(part in key_text.lower() for part in _SENSITIVE_PARTS):
                  result[key_text] = "[REDACTED]"
              else:
                  result[key_text] = redact_attributes(item)
          return result
      if isinstance(value, (list, tuple)):
          res = [redact_attributes(item) for item in value]
          return type(value)(res) if not isinstance(value, list) else res
      if isinstance(value, set):
          return {redact_attributes(item) for item in value}
      return value
  ```

#### Finding R2-F03 (HIGH) — Egress Policy Bypass in Web Control
- **File**: `scp/web_control/web_navigator.py` and `scp/web_control/browser_session.py`
- **Lines**: `web_navigator.py:129–137`, `browser_session.py:145–146`, `158–159`
- **Observation**:
  `web_navigator.py:browse_public` calls `enforce_egress_policy(url)`. However, `browse_logged_in` delegates directly to `browser.navigate_and_read(url)`. Both `BrowserSession.navigate_and_read` and `BrowserSession.open_visible` call only `self.validate_url(url)` (which checks private IP / SSRF only) and DO NOT call `enforce_egress_policy(url)`.
  When `SCP_EGRESS_MODE=deny` is set in production, an API call to `/v3/web/browse` with `useLoggedInBrowser=true` or `/v3/ai/ask` with `useBrowser=true` will successfully connect to external internet websites via the Chrome/Edge instance, completely bypassing the fail-closed egress policy.
- **Verbatim Code**:
  ```python
  # scp/web_control/web_navigator.py:129-137
  async def browse_logged_in(self, url: str) -> dict[str, Any]:
      return await self.browser.navigate_and_read(url)

  async def browse(self, url: str, use_logged_in_browser: bool = False) -> dict[str, Any]:
      if self._playwright_backend is not None:
          return await self._playwright_backend.browse(url)
      if use_logged_in_browser:
          return await self.browse_logged_in(url)
      return await self.browse_public(url)

  # scp/web_control/browser_session.py:145-146
  async def navigate_and_read(self, url: str, target: dict[str, Any] | None = None) -> dict[str, Any]:
      url = self.validate_url(url) # Missing enforce_egress_policy!
  ```

#### Finding R2-F04 (HIGH) — SQL Injection Vulnerability in `LearningDB.execute_insert()`
- **File**: `scp/knowledge/learning_db.py`
- **Lines**: 63–70
- **Observation**:
  In `LearningDB.execute_insert`, table names and dictionary keys are concatenated into the SQL statement using an f-string without parameterization or an identifier allowlist.
- **Verbatim Code**:
  ```python
  # scp/knowledge/learning_db.py:63-70
  def execute_insert(self, table: str, data: Dict[str, Any]):
      cols = ", ".join(data.keys())
      placeholders = ", ".join(["?"] * len(data))
      values = tuple(data.values())
      
      with sqlite3.connect(self.db_path) as conn:
          conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
  ```

#### Finding R2-F05 (HIGH) — Path Traversal in Benchmark Batch Directory Handling
- **File**: `scp/api/routes/batch_benchmark_routes.py`
- **Lines**: 40–43, 307–314
- **Observation**:
  `_job_dir(job_id: str)` concatenates `_root()` with `job_id` and executes `path.mkdir(parents=True, exist_ok=True)`. The endpoint `GET /batch/{job_id}` passes the user-controlled path parameter directly into `_job_dir(job_id)`. Without regex validation or path containment checks, directory traversal strings (e.g. `../../...`) permit arbitrary directory creation and reading outside `data/benchmark_batches`.
- **Verbatim Code**:
  ```python
  # scp/api/routes/batch_benchmark_routes.py:40-43
  def _job_dir(job_id: str) -> Path:
      path = _root() / job_id
      path.mkdir(parents=True, exist_ok=True)
      return path
  ```

#### Finding R2-F06 (HIGH) — Unauthenticated Public Exposure of SWE-Bench & Metrics Endpoints
- **File**: `scp/api/routes/swe_bench_routes.py` (lines 15–16), `scp/api_server.py` (lines 356–358)
- **Observation**:
  - `POST /swe-bench/v1/chat/completions` has no auth dependencies and accepts unauthenticated completions requests.
  - `GET /metrics` publishes internal Prometheus metrics (system counters, latency histograms, error rates, model call statistics) to unauthenticated network clients.
- **Verbatim Code**:
  ```python
  # scp/api/routes/swe_bench_routes.py:15-16
  @router.post("/chat/completions")
  async def chat_completions(req: ChatCompletionRequest):

  # scp/api_server.py:356-358
  @app.get("/metrics")
  async def metrics():
      return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
  ```

#### Finding R2-F07 (MEDIUM) — Unauthenticated Local LLM Bridge Microservice
- **File**: `mini-services/llm-bridge/core.ts`
- **Lines**: 1001–1055
- **Observation**:
  The Bun HTTP server on port 11435 enforces CORS for web browsers, but has zero token verification for HTTP requests. Any local script, rogue process, or loopback client can call `POST /api/chat`, `POST /api/generate`, or `POST /api/cache/clear` to exhaust OpenRouter API credits.
- **Verbatim Code**:
  ```typescript
  // mini-services/llm-bridge/core.ts:1038-1054
  if (method === "POST" && path === "/api/chat") return handleChat(req);
  if (method === "POST" && path === "/api/generate") return handleGenerate(req);
  if (method === "POST" && path === "/api/cache/clear") {
    _llmCache.clear();
    return jsonResponse({ cleared: true, cache_size: 0 });
  }
  ```

#### Finding R2-F08 (MEDIUM) — Token Transmission in URL Query Parameters
- **File**: `scp/api/chat.py` (lines 243–255), `scp/api/dashboard_html.py` (lines 203–216)
- **Observation**:
  WebSocket `/chat` and the embedded dashboard instruct users to transmit sensitive tokens via URL query strings (`?token=...`), which are stored in browser history, HTTP access logs, and proxy traces. Additionally, `scp/api/chat.py:243` executes `await websocket.accept()` prior to validating the token.
- **Verbatim Code**:
  ```python
  # scp/api/chat.py:243, 252
  await websocket.accept()
  ...
  client_token = str(websocket.query_params.get("token", "") or "")
  ```

---

### Domain R5: Runtime Correctness & Concurrency

#### Finding R5-F01 (CRITICAL) — Silent Data Loss & Race Condition in `ChatMemoryStore` Pruning
- **File**: `scp/core/chat_memory_store.py`
- **Lines**: 78–83, 115–146
- **Observation**:
  `append()` appends a line to `self.path` and immediately calls `_prune_if_needed()`. In `_prune_if_needed()`, if the file exceeds 2MB, lines are read, filtered, written to a temporary file, and replaced using `os.replace(temp_name, self.path)`.
  There is NO thread lock and NO file lock (`flock`/`msvcrt`). Under concurrent WebSocket chat sessions:
  1. If Session B appends a record while Session A is preparing the temp file, Session A's `os.replace` silently obliterates Session B's new record.
  2. On Windows, executing `os.replace` on a file actively opened by another thread raises `PermissionError: [WinError 32]`.
  3. Concurrent `load()` calls during `os.replace` encounter partial file reads leading to `json.JSONDecodeError`.
- **Verbatim Code**:
  ```python
  # scp/core/chat_memory_store.py:78-83, 138
  with self.path.open("a", encoding="utf-8", newline="\n") as handle:
      handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
      handle.flush()
      os.fsync(handle.fileno())
  self._prune_if_needed()
  ...
  os.replace(temp_name, self.path)
  ```

#### Finding R5-F02 (CRITICAL) — Corrupted Hash Chain in Concurrent `TraceLedger.append()`
- **File**: `scp/trace_ledger.py`
- **Lines**: 28–34, 35–47
- **Observation**:
  `append()` executes:
  `lines = self.path.read_text().splitlines()`
  `prev = json.loads(lines[-1])`
  `seq = len(lines) + 1`
  `prev_hash = prev.get("hash")`
  There is NO lock around this read-modify-write cycle. When two requests append concurrently:
  - Both read the identical last line.
  - Both assign the exact same `seq` and `prev_hash`.
  - Both append to the file.
  Subsequent execution of `TraceLedger.verify()` fails with sequence and hash chain errors (`seq:X`, `prev_hash:X`), permanently corrupting audit provenance. Furthermore, reading the entire file on every append yields an unacceptable $O(N)$ CPU and I/O scaling bottleneck.
- **Verbatim Code**:
  ```python
  # scp/trace_ledger.py:28-34
  def append(self, **fields: Any) -> dict[str, Any]:
      lines=self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
      prev=json.loads(lines[-1]) if lines else None
      entry={"trace_id":fields.pop("trace_id",None) or "trace_"+secrets.token_hex(8),"seq":len(lines)+1,"prev_hash":prev.get("hash") if prev else None,"fields":_redact(fields)}
      entry["hash"]=_hash(entry)
      with self.path.open("a",encoding="utf-8") as f:f.write(json.dumps(entry,ensure_ascii=False,sort_keys=True)+"\n")
      return entry
  ```

#### Finding R5-F03 (CRITICAL) — Lock Dropped Before Query Execution in `db_manager.py`
- **File**: `scp/core/db_manager.py` (lines 139–158), `scp/core/db_manager_parts/get_db.py` (line 28)
- **Observation**:
  In `db_query_all` and `db_query_one`, `_db_lock` or `_read_lock` is acquired ONLY to retrieve the connection reference (`conn = _get_path_conn(db_path)` or `conn = get_db()`). The lock exits immediately before executing `conn.execute(sql, params)`.
  The shared connection is instantiated with `check_same_thread=False`. As a result, concurrent worker threads execute queries directly on the exact same underlying C-level `sqlite3.Connection` simultaneously without holding any lock, conflicting directly with write transactions in `db_exec()` and causing `database is locked` or data corruption.
- **Verbatim Code**:
  ```python
  # scp/core/db_manager.py:149-158
  def db_query_one(sql: str, params=(), db_path: Optional[str] = None) -> Optional[dict]:
      if db_path:
          with _db_lock:
              conn = _get_path_conn(db_path)
      else:
          with _read_lock:
              conn = get_db()
      row = conn.execute(sql, params).fetchone()  # Executed OUTSIDE the lock!
      return dict(row) if row else None
  ```

#### Finding R5-F04 (HIGH) — Async Transaction State Collision in `KernelStorage`
- **File**: `scp/kernel_storage.py` (lines 97–123, 124–146), `scp/kernel_storage_pg.py` (lines 276–350)
- **Observation**:
  `SQLiteKernelStorage` and `PgKernelStorage` manage connections via `self._conn_local = threading.local()`. In FastAPI/asyncio, all coroutines on the main thread share the single event loop thread.
  When two coroutines interleave across `await` points:
  - Coroutine A calls `storage.begin()`.
  - Coroutine B calls `storage.begin()` or `storage.commit()` on the same thread-local connection.
  - SQLite raises `OperationalError: cannot start a transaction within a transaction`, or Coroutine B prematurely commits or rolls back Coroutine A's active write slot.
- **Verbatim Code**:
  ```python
  # scp/kernel_storage.py:115-122
  def _get_conn(self) -> sqlite3.Connection:
      conn = getattr(self._conn_local, "conn", None)
      if conn is None:
          conn = self._make_connection()
          self._conn_local.conn = conn
  ```

#### Finding R5-F05 (HIGH) — Monotonic Connection Leak in `KernelStorage._all_conns`
- **File**: `scp/kernel_storage.py` (lines 115–123, 166–175), `scp/kernel_storage_pg.py` (lines 303–310)
- **Observation**:
  `_get_conn()` appends every newly created per-thread connection to `self._all_conns`. Under dynamic thread pools (FastAPI `run_in_threadpool`), `_all_conns` grows monotonically without any eviction or connection pooling.
  Furthermore, calling `close()` closes the connections in `_all_conns` but does not invalidate connection references in surviving thread locals, causing subsequent thread queries to crash with `ProgrammingError: Cannot operate on a closed database`.
- **Verbatim Code**:
  ```python
  # scp/kernel_storage.py:120-122
  with self._conn_guard:
      self._all_conns.append(conn) # Unbounded list growth
  ```

#### Finding R5-F06 (HIGH) — Multiple Unbounded In-Memory Collections
- **Files & Lines**:
  - `scp/api/webhook.py:80-82, 144, 150`: `_threat_history` and `_alert_history` append indefinitely on every threat or alert with no maximum size or eviction.
  - `scp/api/routes/risk_routes.py:37, 124`: `_incidents` dict retains all created incidents in memory.
  - `scp/security/auth.py:58, 76`: `_auth_failures` dict retains client IP entries forever without key deletion.
  - `scp/api/routes/batch_benchmark_routes.py:30, 265`: `_JOBS` dict stores completed thread objects indefinitely.
  - `scp/core/multi_source_verifier.py:267, 295`: `_CID_CACHE` caches all chemistry query results without eviction.
  - `scp/autofix/concurrent_runner.py:43, 51`: `_file_locks` retains locks for every unique file path processed.
- **Verbatim Code**:
  ```python
  # scp/api/webhook.py:80-82
  _registered_systems: dict[str, dict] = {}
  _threat_history: list[dict] = []
  _alert_history: list[dict] = []
  ```

#### Finding R5-F07 (HIGH) — Uncoordinated Graceful Shutdown & Unawaited Tasks
- **File**: `scp/api_server_parts/lifespan.py`
- **Lines**: 312–334, 448–477
- **Observation**:
  1. `_why_thread` executes `while True` with no `threading.Event` stop signal and is never joined or terminated during shutdown.
  2. Background asyncio tasks (`_scheduler_bootstrap_task`, `_evolution_bootstrap_task`, etc.) are cancelled via `_task.cancel()` but are never awaited (`await asyncio.gather`), triggering event loop closed warnings and prematurely aborting in-flight cleanups.
  3. No database connections in `db_manager` or `KernelStorage` are closed on shutdown, nor is `checkpoint_wal()` invoked.
- **Verbatim Code**:
  ```python
  # scp/api_server_parts/lifespan.py:314, 460-462
  def _why_verify_loop():
      while True: # Unbounded loop with no stop event
          ...
  for _task in (_scheduler_bootstrap_task, _evolution_bootstrap_task, ...):
      if _task is not None and (not _task.done()):
          _task.cancel() # Never awaited!
  ```

#### Finding R5-F08 (MEDIUM) — Unsynchronized Shared Mutable State in Singletons
- **Files & Lines**: `scp/api/chat.py:175–213`, `scp/api/routes/risk_routes.py:111–124`
- **Observation**:
  - `ConversationManager._sessions` in `chat.py` lacks synchronization locks. Concurrent calls to `add_message()` when `len >= max_sessions` can race on `del self._sessions[oldest]`, causing `KeyError` or dictionary iteration modification errors.
  - `open_incident()` in `risk_routes.py` computes `incident_id = ... or f"inc_{len(_incidents) + 1:04d}"` without a lock, producing colliding incident IDs under concurrent requests.
- **Verbatim Code**:
  ```python
  # scp/api/chat.py:197-200
  if len(self._sessions) >= self._max_sessions:
      oldest = next(iter(self._sessions))
      del self._sessions[oldest]
  ```

#### Finding R5-F09 (MEDIUM) — Unmanaged Process Spawning in `BrowserSession.open_visible`
- **File**: `scp/web_control/browser_session.py`
- **Line**: 171
- **Observation**:
  `subprocess.Popen([browser, "--new-window", url], ...)` creates external browser processes without tracking their process IDs or handles, without process count caps, and without termination on shutdown.
- **Verbatim Code**:
  ```python
  # scp/web_control/browser_session.py:171
  subprocess.Popen([browser, "--new-window", url], creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
  ```

---

## 2. Logic Chain

1. **R2-F01 & R2-F02**:
   - *Observation*: `api_server.py:541` binds `/v3/trace/{trace_id}` without security dependencies and returns raw ledger fields. `trace_contract.py:44` checks only mapping keys and misses tuple elements and string values.
   - *Logic*: An unauthenticated remote client can enumerate `trace_id` values and inspect execution traces containing unredacted authorization header tuples, prompt inputs, and sensitive operational parameters.
   - *Conclusion*: CRITICAL vulnerability violating Fail-Closed & Evidence-First authentication and sensitive attribute containment.

2. **R2-F03**:
   - *Observation*: `web_navigator.py:130` routes `browse_logged_in` to `browser_session.py:navigate_and_read`, which calls `validate_url` but omits `enforce_egress_policy`.
   - *Logic*: `SCP_EGRESS_MODE=deny` is intended to halt all non-loopback outbound traffic. Because `validate_url` only filters private IPs, browser navigation requests bypass egress enforcement and reach external servers.
   - *Conclusion*: HIGH security gap invalidating the egress fail-closed policy.

3. **R2-F04 & R2-F05**:
   - *Observation*: `learning_db.py:69` formats `table` and dictionary keys directly into SQL strings. `batch_benchmark_routes.py:41` joins `_root()` with raw `job_id`.
   - *Logic*: Injection of unvalidated strings directly into query syntax or filesystem path construction creates SQL injection and path traversal vectors.
   - *Conclusion*: HIGH severity security vulnerabilities.

4. **R5-F01 & R5-F02**:
   - *Observation*: `ChatMemoryStore._prune_if_needed` rewrites `chat_memory.jsonl` using `tempfile.mkstemp` and `os.replace` without locks. `TraceLedger.append` reads the whole file to compute sequence and hash before appending without locks.
   - *Logic*: Under concurrent requests, read-modify-write operations without mutual exclusion lead to lost updates, clobbered records, file sharing violations on Windows, and broken cryptographic sequence chains.
   - *Conclusion*: CRITICAL concurrency hazards risking data loss and corrupted audit trails.

5. **R5-F03 & R5-F04**:
   - *Observation*: `db_manager.py` releases locks before calling `conn.execute()`. `KernelStorage` stores connections in `threading.local()`.
   - *Logic*: Releasing locks prior to execution exposes shared SQLite connections to concurrent thread execution. In asyncio, coroutines share the same thread, causing conflicting transactions on the same connection.
   - *Conclusion*: CRITICAL and HIGH database concurrency defects causing `database is locked` errors and transaction contamination.

6. **R5-F06 & R5-F07**:
   - *Observation*: Module-level lists and dicts append on every event without limits. `lifespan.py` cancels async tasks without awaiting them and spawns `while True` threads with no stop event.
   - *Logic*: Unbounded memory growth eventually results in Out-Of-Memory termination. Uncoordinated shutdown causes unhandled exceptions and abruptly terminated I/O.
   - *Conclusion*: HIGH runtime reliability risks for long-running autonomous deployments.

---

## 3. Caveats

1. **Test Environment vs Production**:
   Under single-threaded test execution (e.g. running unit tests sequentially with `pytest`), race conditions in `ChatMemoryStore`, `TraceLedger`, and `db_manager` do not easily manifest because tests run sequentially. These issues surface primarily under concurrent multi-user load or real-time WebSocket traffic.
2. **Postgres vs SQLite Backend**:
   `PgKernelStorage` was analyzed statically; behavior under a live distributed PostgreSQL cluster was not benchmarked.
3. **Third-Party Sidecars**:
   `mini-services/loop-scheduler` and `llm-bridge` run as Bun/TypeScript processes alongside the Python API server. Their behavior was audited from source code inspection.

---

## 4. Conclusion

The SCP codebase exhibits sophisticated governance, validation, and audit tooling, but possesses critical vulnerabilities in **secret redaction**, **authentication gating on ancillary endpoints**, and **concurrency protection in shared storage components**:
- The `/v3/trace/{trace_id}` endpoint must be placed behind `Depends(verify_admin)` and wired to a hardened `redact_attributes()` function that handles values, tuples, and custom types.
- Browser navigation in `BrowserSession` and `WebNavigator` must enforce `enforce_egress_policy()` before executing navigation commands.
- `ChatMemoryStore` and `TraceLedger` must adopt robust file/thread locking (e.g. `filelock` or process-level mutexes) to prevent silent data loss and hash chain corruption during pruning and appending.
- `db_manager.py` must hold `_db_lock` throughout the entirety of `conn.execute()` and row fetching, not merely during connection retrieval.
- Unbounded in-memory collections must be replaced with bounded LRU caches or rotating ring buffers.

---

## 5. Verification Method

### Independent Verification Commands

1. **Verify Unauthenticated `/v3/trace/{trace_id}` Endpoint**:
   - Inspect `scp/api_server.py:541-566`.
   - Confirm lack of `Depends(verify_admin)` or `Depends(get_current_user)`.
   - Confirm return of `merged` or `record` without calling `redact_attributes()`.

2. **Verify Redaction Blind Spots**:
   - Inspect `scp/core/trace_contract.py:44-64`.
   - Run Python probe:
     ```bash
     python -c "from scp.core.trace_contract import redact_attributes; print(redact_attributes([('Authorization', 'Bearer sk-12345')]))"
     ```
     *Expected Output*: `[('Authorization', 'Bearer sk-12345')]` (unredacted).

3. **Verify Database Lock Dropped in `db_manager.py`**:
   - Inspect `scp/core/db_manager.py:149-158`.
   - Confirm `conn = _get_path_conn(db_path)` or `conn = get_db()` is inside `with _db_lock:`, but `conn.execute(...)` is outside the lock block.

4. **Verify SQL Injection in `LearningDB.execute_insert`**:
   - Inspect `scp/knowledge/learning_db.py:63-70`.
   - Confirm raw f-string formatting: `f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"`.

5. **Verify Egress Bypass in Web Control**:
   - Inspect `scp/web_control/browser_session.py:145-146`.
   - Confirm `navigate_and_read` calls only `validate_url`, omitting `enforce_egress_policy`.

6. **Verify Test Suite Integrity**:
   - Run collection check:
     ```bash
     pytest tests/ --collect-only -q
     ```
     *Output*: 1,937 tests collected in ~3.7s, 0 collection errors.
