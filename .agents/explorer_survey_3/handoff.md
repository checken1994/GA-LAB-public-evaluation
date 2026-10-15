# Comprehensive Audit Report: Domains R1, R4, R6

**Auditor Role**: Quality & Deployment Explorer (Survey Phase)  
**Agent Workspace**: `D:\scp\.agents\explorer_survey_3`  
**Target Repository**: `D:\scp`  
**Git Branch**: `feature/autonomous-mode-antigravity-v2` (`6d6256f`)  
**Audit Scope**: Domain R1 (Silent Bugs & Logic Errors), Domain R4 (Test Coverage & Test Quality), Domain R6 (Configuration & Deployment Consistency)  
**Date**: 2026-09-21T17:15:00Z  

---

## Executive Summary

A deep systematic audit was executed across the entire SCP codebase (~221,000 Python LOC, 1,142 `.py` files, 43 active subsystems under `scp/`, and 1,937 tests). The audit used Python AST parsing, cross-subsystem import tracing, git diff/history analysis, and manual line-by-line verification.

### Finding Counts by Severity

| Domain | CRITICAL | HIGH | MEDIUM | LOW | INFO | Total |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Domain R1: Silent Bugs & Logic Errors** | 2 | 2 | 2 | 1 | 0 | **7** |
| **Domain R4: Test Coverage & Test Quality** | 2 | 2 | 2 | 0 | 1 | **7** |
| **Domain R6: Configuration & Deployment Consistency** | 1 | 3 | 1 | 1 | 0 | **6** |
| **TOTAL** | **5** | **7** | **5** | **2** | **1** | **20** |

---

## Top 10 Most Critical Findings Across Domains R1, R4, R6

1. **[R1 - CRITICAL] Hardcoded Stubbed Properties in Judge Permanently Break 4 Public API Endpoints (HTTP 503)**  
   `scp/runtime/judge.py:101-111` & `scp/api/routes/admin_v98.py:74-117`
2. **[R4 - CRITICAL] Blatant Manufactured Green in Chaos Recovery Test (FA-04 Violation)**  
   `scp/tests/chaos_recovery.py:1-8`
3. **[R1 - CRITICAL] Simulated Green in AutoFix Evidence Replay Engine (FA-04 Violation)**  
   `scp/autofix/evidence_replay.py:28-42` & `scp/autofix/runner_phases/post_fix_verify.py:415-498`
4. **[R4 - CRITICAL] Massive Test Inflation: 38 Test Files Only Assert Module Importability Without Testing Functionality**  
   `tests/test_subsystem_*.py` (23 files) & `tests/T03_capability/test_flow_19_*.py` through `test_flow_33_*.py` (15 files)
5. **[R6 - CRITICAL] 84% Environment Variable Drift: 165 of 197 Env Vars Undocumented in `.env.example`**  
   `.env.example:1-45` vs 197 `os.environ`/`os.getenv` keys in `scp/`
6. **[R6 - HIGH] Windows Startup Script (`start-scp.bat`) Completely Omits LLM Bridge Service While Binding to Port 8081**  
   `start-scp.bat:69-94` vs `start-scp.sh:66-81`
7. **[R6 - HIGH] Dashboard Health Probe Default Port Mismatch (Port 11434 vs 8081)**  
   `dashboard/src/lib/scp-backend-url.ts:87` vs `mini-services/loop-scheduler/index.ts:350`
8. **[R4 - HIGH] Systemic Under-Coverage: 22 Out of 43 Subsystems (>51%) Have Minimal (<=2) or Zero Test Coverage**  
   `scp/interfaces/` (0 tests), `scp/foundation/`, `scp/observability/`, `scp/history/`, `scp/consolidator/`, etc.
9. **[R1 - HIGH] Flawed `None` Check in AST Type Flow Verifier**  
   `scp/autofix/type_flow_verifier.py:381-391`
10. **[R1 - HIGH] Unencoded File Operations Raising `UnicodeDecodeError` on Windows (CP1252/CP1258)**  
    `scp/meta/external_trust.py:120`, `scp/benchmark/compare_results.py:80, 82`, `scp/benchmark/run_benchmark.py:80, 135`

---

# Section 1: Domain R1 — Silent Bugs & Logic Errors

### Finding R1-01: Hardcoded `return None` in Judge Properties Silently Breaks 4 Public Admin Endpoints
- **Severity**: CRITICAL
- **File**: `scp/runtime/judge.py:101-111`
- **File**: `scp/api/routes/admin_v98.py:74-77, 84-87, 94-97, 104-107, 114-117`
- **Description**:
  In `scp/runtime/judge.py`, six core properties (`falsification`, `error_store`, `governance`, `counter_response`, `canary_monitor`, `attack_memory`) are hardcoded to `return None`. 
  In `scp/api/routes/admin_v98.py`, four public endpoints depend on these properties and raise `HTTPException(status_code=503)` if they are None:
  - `GET /v98/counter/stats` -> checks `judge.counter_response` -> **Guaranteed 503**
  - `GET /v98/canary/triggers` -> checks `judge.canary_monitor` -> **Guaranteed 503**
  - `GET /v98/error-store/stats` -> checks `judge.error_store` -> **Guaranteed 503**
  - `GET /v98/attack-memory/stats` -> checks `judge.attack_memory` -> **Guaranteed 503**
  Furthermore, `GET /v98/status` reports `"falsification": False`, `"error_store": False`, `"governance": False`.
- **Evidence**:
  `scp/runtime/judge.py:100-111`:
  ```python
      @property
      def falsification(self): return None
      @property
      def error_store(self): return None
      @property
      def governance(self): return None
      @property
      def counter_response(self): return None
      @property
      def canary_monitor(self): return None
      @property
      def attack_memory(self): return None
  ```
  `scp/api/routes/admin_v98.py:84-87`:
  ```python
      judge = get_judge()
      if not judge.counter_response:
          raise HTTPException(status_code=503, detail="CounterResponseEngine not available")
      return judge.counter_response.stats()
  ```

---

### Finding R1-02: Manufactured Green in AutoFix Evidence Replay (FA-04 Violation)
- **Severity**: CRITICAL
- **File**: `scp/autofix/evidence_replay.py:28-42`
- **File**: `scp/autofix/runner_phases/post_fix_verify.py:421-498`
- **Description**:
  `scp/autofix/evidence_replay.py` is an unconditional simulation mock. `EvidenceReplay.verify()` unconditionally returns `{"ok": True, "status": "VERIFIED"}`. `EvidenceReplay.classify_evidence()` returns a mock object where `role = EvidenceRole.VERIFIER` and `discriminating = True`.
  Additionally, in `GoldDataset.get_entry()`:
  ```python
  def get_entry(self, signature: str):
      if os.environ.get("SCP_SEED_GOLD_EVIDENCE") == "1":
          return {"test_command": "pytest", "buggy_source": "", "gold_source": ""}
      return None
  ```
  Unless `SCP_SEED_GOLD_EVIDENCE="1"` is exported, `get_entry()` always returns `None`, forcing `post_fix_verify.py:489-498` to mark Phase 6 as `UNVERIFIED` and escalate to Tier-3 review. If the env var is set, it returns a stub mock that never executes pytest.
- **Evidence**:
  `scp/autofix/evidence_replay.py:28-39`:
  ```python
      def verify(self, *args, **kwargs):
          return {"ok": True, "status": "VERIFIED"}
          
      def classify_evidence(self, *args, **kwargs):
          class MockResult:
              role = EvidenceRole.VERIFIER
              discriminating = True
              def to_dict(self):
                  return {}
              def __str__(self):
                  return "mock reason"
          return MockResult()
  ```

---

### Finding R1-03: Broken `None` Check in AST Type Flow Verifier
- **Severity**: HIGH
- **File**: `scp/autofix/type_flow_verifier.py:381-391`
- **Description**:
  `_is_none_check(self, test: ast.expr)` is intended to detect when a condition checks whether a variable is `None` (e.g. `x is None` or `x is not None`).
  However, the function checks only that `test.ops[0]` is an `Is` or `IsNot` operator, and that `test.left` is an `ast.Name`. It **never checks `test.comparators[0]`**!
  As a result, conditions such as `if status is True:`, `if code is 1:`, or `if val is "ACTIVE":` are incorrectly treated as `None` checks and return the variable name, skewing type flow inference and post-fix validation.
- **Evidence**:
  `scp/autofix/type_flow_verifier.py:381-391`:
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
          except Exception:  # noqa: BLE001
              return None
  ```

---

### Finding R1-04: Unencoded File Reads Crashing with `UnicodeDecodeError` on Windows
- **Severity**: HIGH
- **File**: `scp/meta/external_trust.py:120`
- **File**: `scp/benchmark/compare_results.py:80, 82`
- **File**: `scp/benchmark/run_benchmark.py:80, 135`
- **Description**:
  On Windows operating systems, Python's `open()` and `Path.read_text()` default to the system code page (such as CP1252 or CP1258). 
  In `scp/meta/external_trust.py:120`:
  `content = constitution_path.read_text()`
  `scp/meta/constitution.py` contains UTF-8 non-ASCII characters. When `read_text()` is called without `encoding="utf-8"`, Python crashes with:
  `UnicodeDecodeError: 'charmap' codec can't decode byte ... in position ...: character maps to <undefined>`.
  This breaks external trust verification at startup on non-UTF-8 Windows environments.
- **Evidence**:
  `scp/meta/external_trust.py:117-121`:
  ```python
          constitution_path = self._resolve_expected_path("meta/constitution.py")
          constitution_approved = False
          if constitution_path.exists():
              content = constitution_path.read_text()
              constitution_approved = self._is_constitution_human_approved(content)
  ```

---

### Finding R1-05: Silent Best-Effort Exception Swallowing in Expert Subsystem Discovery
- **Severity**: MEDIUM
- **File**: `scp/runtime/judge.py:86-98`
- **Description**:
  In `Judge.domain_experts`, dynamic loading of expert modules iterates through `scp/runtime/experts/`. Both module importation (`importlib.import_module`) and class instantiation (`instance = obj()`) are wrapped in broad `except Exception: pass` blocks without logging.
  If an expert module contains an unhandled syntax error, import error, or initialization failure, it is silently dropped. The system continues running with that expert absent, leaving no log trace for developers or operators.
- **Evidence**:
  `scp/runtime/judge.py:90-98`:
  ```python
                                  try:
                                      instance = obj()
                                      self._experts[instance.domain] = instance
                                  except Exception:
                                      # silent-by-design: best-effort expert discovery — a broken expert module is skipped, the rest still load
                                      pass
                      except Exception:
                          # silent-by-design: same best-effort expert discovery contract as above
                          pass
  ```

---

### Finding R1-06: Fire-and-Forget Background Fact-Check Task Without Error Propagation
- **Severity**: MEDIUM
- **File**: `scp/api_server_parts/_ask_impl.py:682-689`
- **Description**:
  In `_ask_impl.py`, after generating a PASS verdict, a background asyncio task is spawned for fact-checking:
  ```python
  _fc_task = asyncio.create_task(_async_fact_check(_api_final_answer, req.question, v98_context.get('session_id', '')))
  _async_factcheck_tasks.add(_fc_task)
  _fc_task.add_done_callback(_async_factcheck_tasks.discard)
  ```
  `add_done_callback` only discards the task from the set. It does not inspect `task.exception()`. If an unhandled exception occurs in `_async_fact_check`, it produces an unretrieved task exception warning and silently abandons the fact-check and subsequent retraction queue.
- **Evidence**:
  `scp/api_server_parts/_ask_impl.py:682-689`:
  ```python
      if v.verdict == 'PASS' and _api_final_answer and (len(_api_final_answer) > 20):
          try:
              _fc_task = asyncio.create_task(_async_fact_check(_api_final_answer, req.question, v98_context.get('session_id', '')))
              _async_factcheck_tasks.add(_fc_task)
              _fc_task.add_done_callback(_async_factcheck_tasks.discard)
          except Exception as e:
              logger.debug(f'[V104.37] api_server.py: e={e}')
  ```

---

### Finding R1-07: Mojibake Character Corruption in User-Facing API Responses and Docstrings
- **Severity**: LOW
- **File**: `scp/api_server_parts/_ask_impl.py:96, 287`
- **File**: `scp/api/chat.py:3, 5, 238, 424`
- **File**: `scp/api/webhook.py:2, 8-11, 103, 177`
- **Description**:
  Across more than 20 files, UTF-8 strings containing Vietnamese text and box-drawing symbols have been corrupted into Mojibake sequences (e.g. `│Ă¢â€\x9aÂ¬Ă¢â‚¬Â\x9d`).
  Critically, in `_ask_impl.py:287`, this corrupted string is embedded into `AskResponse.final_answer`, directly returning garbled text to end users when a jailbreak is blocked:
  `final_answer='[SCP: Answer withheld │Ă¢â€\x9aÂ¬Ă¢â‚¬Â\x9d multimodal jailbreak detected]'`.
- **Evidence**:
  `scp/api_server_parts/_ask_impl.py:287`:
  ```python
  return AskResponse(verdict='FAIL', final_answer='[SCP: Answer withheld │Ă¢â€\x9aÂ¬Ă¢â‚¬Â\x9d multimodal jailbreak detected]', confidence=0.0, domain='security', elapsed_ms=0, session_id=v98_context['session_id'])
  ```

---

# Section 2: Domain R4 — Test Coverage & Test Quality

### Enumeration of Test Suites (T00 through T12)

| Test Suite | Directory | Py Files | Focus Area |
|---|---|:---:|---|
| **T00** | `tests/T00_integrity/` | 8 | Meta-audit, guardrails, code tampering prevention, skip/xfail tracking |
| **T01** | `tests/T01_boot/` | 3 | FastAPI lifespan, startup config validation, doubt cron, background jobs |
| **T02** | `tests/T02_contract/` | 24 | API contracts, route profiles, request ledgers, asking contracts |
| **T03** | `tests/T03_capability/` | 54 | Sandbox execution, browser, network egress, token signing, capability levels |
| **T04** | `tests/T04_kernel/` | 26 | TaskKernel state transitions, PostgreSQL/SQLite storage parity, event bus |
| **T05** | `tests/T05_gateway/` | 16 | LLM gateway routing, model failover, egress policy, provider health |
| **T06** | `tests/T06_verifier/` | 6 | Realtime verifier, claim extraction, indictment, fact checking |
| **T07** | `tests/T07_learning/` | 12 | AutoFix engine, shadow rollback, epistemic evolution, knowledge store |
| **T08** | `tests/T08_runtime/` | 3 | Runtime lifecycle, timing and restart, execution workers |
| **T09** | `tests/T09_golden_task/` | 6 | End-to-end golden verification tasks, epistemic loops, system maps |
| **T10** | `tests/T10_recovery/` | 3 | Crash recovery, lease expiry, worker recovery, checkpoint restore |
| **T11** | `tests/T11_release/` | 8 | Release gate, skill DNA contract, dependency integrity, deployment checks |
| **T12** | `tests/T12_unified_chatbot/` | 6 | Unified chatbot, 4-tier reasoning cascade, boundary test suite |
| *Auxiliary* | `tests/reality-tests/` | 76 | AST/regex static checks on source files |
| *Auxiliary* | `tests/diagnostics/` | 5 | Environment diagnostics and port probes |
| *Auxiliary* | `tests/contract/` | 1 | Schema contract verification |
| *Auxiliary* | `tests/external_audit/` | 1 | Security audit wrapper |

---

### Finding R4-01: Test Inflation — 38 Test Files Only Assert Module Importability (Zero Functional Testing)
- **Severity**: CRITICAL
- **File**: `tests/test_subsystem_*.py` (23 files)
- **File**: `tests/T03_capability/test_flow_19_*.py` through `test_flow_33_*.py` (15 files)
- **Description**:
  There are 38 separate test files across `tests/` that contain no functional assertions whatsoever. Each file consists of 13 to 16 lines doing:
  ```python
  try:
      import scp.<subsystem>
      _AVAILABLE = True
  except ImportError:
      _AVAILABLE = False

  def test_<subsystem>_isolated_flow():
      assert _AVAILABLE, "<subsystem> must be importable and connected"
  ```
  These files artificially inflate the passing test count by 38 tests, creating an illusion of comprehensive test coverage across 23 subsystems without validating a single function or state transition.
- **Evidence**:
  `tests/T03_capability/test_flow_19_audit_engine_scp_standard.py:1-16`:
  ```python
  import os
  import pytest
  try:
      import scp.audit_engine
      _AVAILABLE = True
  except ImportError:
      _AVAILABLE = False

  def test_audit_engine_isolated_flow():
      '''FA-13: Cover audit_engine flow'''
      assert _AVAILABLE, "audit_engine must be importable and connected"
  ```
  `tests/test_subsystem_observability.py:8-13`:
  ```python
  def test_subsystem_observability_importable():
      """Observability: module phải import được không lỗi."""
      import importlib
      mod = importlib.import_module("scp.observability")
      assert mod is not None, f"FAIL: scp.observability không import được!"
  ```

---

### Finding R4-02: Manufactured Green in Chaos Recovery Test (FA-04 Violation)
- **Severity**: CRITICAL
- **File**: `scp/tests/chaos_recovery.py:1-8`
- **Description**:
  The test file `scp/tests/chaos_recovery.py` contains a test function `test_chaos_recovery()` that purports to test crash recovery in the TaskKernel. 
  In reality, it executes two `print()` calls followed by `assert True`. It performs zero crash simulation, zero state validation, and zero kernel reconciliation. This is a direct violation of FA-04 (Manufactured Green).
- **Evidence**:
  `scp/tests/chaos_recovery.py:1-8`:
  ```python
  # -*- coding: utf-8 -*-
  """P1: Chaos Recovery Test.
  Simulates a random crash and verifies task kernel can reconcile and resume.
  """
  def test_chaos_recovery():
      print("Simulating Chaos Crash...")
      print("Recovery verified.")
      assert True
  ```

---

### Finding R4-03: Systemic Under-Coverage: 22 Out of 43 Subsystems Have Minimal or Zero Test Coverage
- **Severity**: HIGH
- **File**: `scp/interfaces/` (0 tests)
- **File**: `scp/observability/`, `scp/foundation/`, `scp/history/`, `scp/consolidator/`, `scp/experience/`, `scp/learning/`, `scp/forecast/`, `scp/audit_engine/`, `scp/audit_r8/`, `scp/audit_r9/`, `scp/capabilities/`, `scp/mcp_server/`, `scp/rag/`, `scp/sandbox_evaluator/` (Only 1 test each)
- **Description**:
  Analysis of all test files in the repository revealed that out of 43 active subsystems under `scp/`:
  - **2 subsystems** (`interfaces`, `tests`) have **0 test references**.
  - **13 subsystems** have **only 1 test reference** (which is the import-smoke test identified in R4-01).
  - **7 subsystems** have **only 2 test references**.
  In total, **22 out of 43 subsystems (>51%)** have zero functional test coverage.
- **Evidence**:
  Subsystem test reference counts mapped from AST import analysis:
  `interfaces: 0`, `observability: 1`, `foundation: 1`, `history: 1`, `consolidator: 1`, `experience: 1`, `learning: 1`, `forecast: 1`, `audit_engine: 1`, `audit_r8: 1`, `audit_r9: 1`, `capabilities: 1`, `mcp_server: 1`, `rag: 1`, `sandbox_evaluator: 1`.

---

### Finding R4-04: Static AST/Regex File Scans Masquerading as Runtime "Reality Tests"
- **Severity**: HIGH
- **File**: `tests/reality-tests/` (76 test files, e.g. `reality_4-a-003.py`, `reality_4-a-005.py`, `reality_4-a-006.py`, `reality_4-b-005.py`)
- **Description**:
  The 76 test files in `tests/reality-tests/` claim to be "reality verification" tests. However, an AST audit of these tests revealed that dozens of them never execute the code under test. Instead, they read source `.py` files as text or parse them into ASTs, checking whether a specific function name or AST node is present.
  If the target function has fatal runtime bugs, invalid SQL statements, or unhandled exceptions, these tests still pass with 100% green.
- **Evidence**:
  `tests/reality-tests/reality_4-a-005.py:107-110`:
  ```python
  assert api_utils_src is not None, "FAIL: api_utils.py not found"
  assert fwr_body is not None, "FAIL: fetch_with_retry not found in api_utils.py"
  ```
  `tests/reality-tests/reality_4-b-005.py:87`:
  ```python
  assert classify_node is not None, "FAIL: classify_threat function not found in source"
  ```

---

### Finding R4-05: Flaky Test Patterns — 46 Hardcoded Sleep Calls Up to 30 Seconds
- **Severity**: MEDIUM
- **File**: `tests/reality-tests/reality_4-a-010.py:77` (`time.sleep(30)`)
- **File**: `tests/reality-tests/reality_4-d-007.py:128, 175` (`time.sleep(3)`, `time.sleep(2.5)`)
- **File**: `tests/T01_boot/test_flow_01_boot_background_scp_standard.py:180, 329` (`time.sleep(1.5)`, `time.sleep(1.2)`)
- **Description**:
  The test suite contains 46 explicit `time.sleep` calls. In `reality_4-a-010.py:77`, the test sleeps for **30 seconds** to simulate a slow fetcher.
  Hardcoded sleeps introduce timing flakiness on congested CI runners and significantly increase test run times.
- **Evidence**:
  `tests/reality-tests/reality_4-a-010.py:75-78`:
  ```python
      def _slow_fetch(entity):
          slow_calls["count"] += 1
          time.sleep(30)
          return "slow-result"
  ```

---

### Finding R4-06: Pervasive Test Skipping Masking Unimplemented Infrastructure
- **Severity**: MEDIUM
- **File**: `spec/guardrail_policy.yaml` (Baseline debt tracking)
- **File**: `tests/T04_kernel/test_pg_boot_runtime.py`, `test_pg_event_bus.py`, `test_pg_migration.py`, `test_pg_storage_chaos.py`, `test_pg_storage_parity.py`
- **File**: `tests/T03_capability/test_os_sandbox.py`, `test_playwright_backend.py`
- **Description**:
  14 test cases in the test suite are permanently skipped in standard development environments:
  - 6 PostgreSQL kernel tests skip whenever a local PostgreSQL database is absent.
  - Windows Job Object sandbox tests skip due to missing Windows OS sandbox privileges.
  - Playwright browser tests skip because Chromium is not installed.
  Because these tests are tracked as baseline debt in `tools/t00_meta_audit.py`, CI remains green while critical production infrastructure remains completely untested.
- **Evidence**:
  `tools/t00_meta_audit.py` output:
  ```
  [DEBT] FA-01: tests/T04_kernel/test_pg_boot_runtime.py -> pytest.skip() in pg_dsn (2 historical instances)
  [DEBT] FA-01: tests/T04_kernel/test_pg_storage_parity.py -> pytest.skip() in pg_storage (2 historical instances)
  [DEBT] FA-01: tests/T03_capability/test_os_sandbox.py -> pytest.skip() in test_sandbox_executes_command_inside_job_object (1 historical instances)
  ```

---

### Finding R4-07: Test Suite Mocking Intensity
- **Severity**: INFO
- **File**: `tests/T00_integrity/test_meta_audit.py` (12 mocks)
- **File**: `tests/T01_boot/test_flow_01_boot_background_scp_standard.py` (12 mocks)
- **File**: `tests/T03_capability/test_flow_11_admin_import_scp_standard.py` (9 mocks)
- **Description**:
  Several integration suites employ heavy mock patching (`unittest.mock.patch` / `monkeypatch`). While mocking external LLM APIs is expected, in boot and kernel tests it occasionally replaces internal state machines and storage engines, bypassing real concurrency and disk persistence logic.

---

# Section 3: Domain R6 — Configuration & Deployment Consistency

### Finding R6-01: 84% Environment Variable Drift (165 of 197 Env Vars Undocumented)
- **Severity**: CRITICAL
- **File**: `.env.example:1-45`
- **File**: `scp/` (197 distinct `os.environ`/`os.getenv` keys)
- **Description**:
  The codebase references 197 distinct environment variables. However, `.env.example` documents only 32 variables.
  **165 environment variables are completely missing from `.env.example`**. 
  Crucial security, authentication, and persistence keys are among the undocumented variables:
  - Security & Auth: `SCP_ADMIN_KEY`, `SCP_JWT_SECRET`, `SCP_CAPABILITY_SECRET`, `SCP_AUTH_PASSWORD`, `SCP_INTERNAL_SECRET`, `SCP_ENCRYPTION_KEY`, `SCP_EGRESS_ALLOWLIST`
  - Persistence & Backend: `SCP_STORAGE_BACKEND`, `SCP_KERNEL_BACKEND`, `SCP_KERNEL_PG_DSN`, `SCP_EVENT_BUS_DSN`, `SCP_DATA_DIR`
  - Model Providers: `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`, `GITHUB_TOKEN`, `HF_TOKEN`, `OPENROUTER_MODEL_LOGICAL_AUDITOR`
  - Autonomous Modes: `SCP_AUTONOMOUS_MODE`, `SCP_AUTOFIX_MODE`, `SCP_API_PROFILE`
  An operator deploying SCP from `.env.example` will deploy an insecure or broken system.
- **Evidence**:
  Grep / AST scan comparison:
  - Code uses: 197 variables
  - `.env.example` documents: 32 variables
  - Undocumented count: 165 (83.8% missing)

---

### Finding R6-02: Windows Startup Script (`start-scp.bat`) Omits LLM Bridge Service
- **Severity**: HIGH
- **File**: `start-scp.bat:69-94`
- **File**: `start-scp.sh:66-81`
- **Description**:
  The Unix startup script `start-scp.sh` starts 4 services:
  1. LLM Bridge (`port 8081`)
  2. Loop Scheduler (`port 3030`)
  3. SCP Python (`port 8000`)
  4. Dashboard (`port 3000`)
  In contrast, the Windows startup script `start-scp.bat` only starts 3 services (Loop Scheduler, SCP Python, Dashboard), **omitting LLM Bridge entirely**.
  However, line 84 of `start-scp.bat` explicitly sets:
  `set LLM_BRIDGE_URL=http://127.0.0.1:8081`
  Because LLM Bridge is never launched, any service attempting to contact `LLM_BRIDGE_URL` on Windows fails immediately with a connection refused error.
- **Evidence**:
  `start-scp.bat:82-94`:
  ```bat
  REM --- 1. Loop Scheduler (port 3030) ---
  start "SCP-Loop-Scheduler" cmd /k "cd /d %~dp0mini-services\loop-scheduler && ... set LLM_BRIDGE_URL=http://127.0.0.1:8081 ... && bun run dev"

  REM --- 2. SCP Python (port 8000) ---
  start "SCP-Python" cmd /k "cd /d %~dp0 && python -m scp 8000"

  REM --- 3. Dashboard Next.js (port 3000) ---
  start "SCP-Dashboard" cmd /k "cd /d %~dp0dashboard && ... bun run start"
  ```

---

### Finding R6-03: Dashboard Health Probe Default Port Mismatch (Port 11434 vs 8081)
- **Severity**: HIGH
- **File**: `dashboard/src/lib/scp-backend-url.ts:87`
- **File**: `dashboard/src/app/api/scp/health/route.ts:8`
- **File**: `mini-services/loop-scheduler/index.ts:350`
- **File**: `start-scp.bat:93`
- **Description**:
  In `dashboard/src/lib/scp-backend-url.ts:87`:
  `llmBridge: normalizeBase(process.env.LLM_BRIDGE_URL, "http://127.0.0.1:11434")`
  The default fallback port for `llmBridge` is hardcoded to port **11434** (the standard Ollama port).
  However, SCP's own LLM Bridge (`mini-services/llm-bridge`) runs on port **8081**.
  In `start-scp.bat:93`, the dashboard is started with:
  `set SCP_INTERNAL_URL=http://127.0.0.1:8000 && set LOOP_SCHEDULER_URL=http://127.0.0.1:3030 && bun run start`
  `LLM_BRIDGE_URL` is **not passed** to the dashboard. The dashboard therefore probes `127.0.0.1:11434`, fails to connect, and falsely marks LLM Bridge as DEAD / OFFLINE on the UI control panel.
- **Evidence**:
  `dashboard/src/lib/scp-backend-url.ts:83-89`:
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

---

### Finding R6-04: Dockerfile Port Mismatch and Immediate Exit Default Command
- **Severity**: HIGH
- **File**: `Dockerfile:43, 50-51`
- **File**: `scp/api_server.py:108-111`
- **Description**:
  1. `Dockerfile` exposes port **8080** (`EXPOSE 8080`), whereas the native application (`api_server.py:108`, `start-scp.sh:98`, `start-scp.bat:89`) runs on port **8000**.
  2. In `scp/api_server.py:111`, running on port 8080 causes the server to determine its mode as:
     `_mode = "production" if _port == 8000 else "test" if _port == 8001 else "unknown"` -> sets `_mode = "unknown"`.
  3. `Dockerfile` sets:
     `ENTRYPOINT ["python", "-m", "scp"]`
     `CMD ["--help"]`
     Running `docker run scp-image` without arguments simply prints the help text and immediately terminates the container instead of starting the server.
- **Evidence**:
  `Dockerfile:43-51`:
  ```dockerfile
  EXPOSE 8080
  ...
  ENTRYPOINT ["python", "-m", "scp"]
  CMD ["--help"]
  ```

---

### Finding R6-05: Missing Production Dependencies in `requirements.txt`
- **Severity**: MEDIUM
- **File**: `scp/requirements.txt:1-109`
- **File**: `scp/security/image_voice_detector.py:101, 264`
- **File**: `scp/capabilities/browser.py:15`
- **Description**:
  23 third-party modules imported in active code paths under `scp/` are missing from `requirements.txt`.
  Key missing packages:
  - `openai-whisper` & `edge-tts`: required by voice endpoints and multimodal jailbreak detection (`scp/security/image_voice_detector.py:264`)
  - `pytesseract` & `pillow`: required by image endpoints and OCR jailbreak detection (`scp/security/image_voice_detector.py:101`)
  - `playwright`: required by browser automation (`scp/capabilities/browser.py:15`)
  - `websockets`: required by WebSocket chat handlers (`scp/api/chat.py`)
  - `sentence-transformers`: required for vector semantic search
  Without these packages installed, invoking these endpoints causes unhandled runtime `ImportError` or silent detection bypass.
- **Evidence**:
  `scp/security/image_voice_detector.py:113`:
  `result.error = "pytesseract not installed — pip install pytesseract pillow"`
  `scp/security/image_voice_detector.py:267`:
  `result.error = "whisper not installed — pip install openai-whisper"`

---

### Finding R6-06: Dirty Git Working Tree with Untracked Feature Files
- **Severity**: LOW
- **File**: `scp/api_server_parts/_trace_impl.py` (Untracked)
- **File**: `scp/core/trace_store.py` (Untracked)
- **File**: `scp/core/trace_contract.py` (Modified)
- **Description**:
  `git status` confirms that the working tree on branch `feature/autonomous-mode-antigravity-v2` is in a dirty state. Crucial implementation files for the trace ledger feature (`_trace_impl.py`, `trace_store.py`) exist as untracked files, and `trace_contract.py` has uncommitted modifications.
- **Evidence**:
  `git status`:
  ```
  Changes not staged for commit:
      modified:   scp/core/trace_contract.py
  Untracked files:
      scp/api_server_parts/_trace_impl.py
      scp/core/trace_store.py
  ```

---

# Section 4: Handoff Protocol Specification

## 1. Observation
- Inspected 1,142 Python source files under `scp/` across all 43 subsystems using custom AST parsers (`audit_r1.py`, `deep_r1_audit.py`, `audit_dead_branches.py`, `audit_unencoded_opens.py`).
- Mapped test suites T00 through T12 and evaluated 23 `test_subsystem_*.py` files and 35 `test_flow_*.py` files under `tests/`.
- Verified execution of `tools/t00_meta_audit.py` (0 regressions against baseline debt).
- Verified environment variables (197 code usages vs 32 documented in `.env.example`).
- Compared startup scripts (`start-scp.bat` vs `start-scp.sh`) and Docker configuration (`Dockerfile`).
- Verified all findings against literal file contents with exact line numbers.

## 2. Logic Chain
1. **Observation**: `scp/runtime/judge.py:101-111` returns `None` for `counter_response`, `canary_monitor`, `error_store`, and `attack_memory`.
   **Inference**: `admin_v98.py:84-117` checks these properties and raises 503 if None.
   **Conclusion**: These 4 public endpoints are permanently broken in production.
2. **Observation**: `scp/tests/chaos_recovery.py` contains only `print` statements and `assert True`.
   **Inference**: The test does not exercise the TaskKernel or simulate crash recovery.
   **Conclusion**: It is a manufactured test violating FA-04.
3. **Observation**: 38 test files (`test_subsystem_*.py` and `test_flow_19` through `test_flow_33`) consist purely of `import scp.<subsystem>` followed by `assert mod is not None` or `assert _AVAILABLE`.
   **Inference**: A passing test run does not prove that the internal logic of any of these 23 subsystems works.
   **Conclusion**: Test coverage metrics are artificially inflated.
4. **Observation**: `start-scp.sh` boots LLM Bridge on 8081, while `start-scp.bat` does not boot it at all. Furthermore, `dashboard/src/lib/scp-backend-url.ts:87` falls back to port 11434.
   **Inference**: When booted via `start-scp.bat` on Windows, LLM Bridge is not running, and the dashboard probes port 11434 instead of 8081.
   **Conclusion**: LLM Bridge functionality and dashboard status indicators are broken on Windows.

## 3. Caveats
- The 1,937 passing tests currently pass because tests either mock dependencies or assert shallow conditions (such as importability). A green test run must not be mistaken for proof of operational stability.
- External dependencies such as PostgreSQL, Playwright Chromium, and Windows Job Objects were skipped in the local test run as tracked debt.
- No source code modifications were performed during this audit (strictly read-only).

## 4. Conclusion
While the SCP system exhibits sophisticated architectural design (TaskKernel, 4-tier reasoning cascade, why-gates, deterministic worker), it suffers from significant **"Manufactured Green" drift** and **operational configuration mismatches**:
- **Domain R1**: Core API endpoints are stubbed out with `return None`, causing 503 errors; AutoFix evidence replay is a fake stub; and type flow checking has broken comparisons.
- **Domain R4**: Test coverage is hollowed out by 38 import-only smoke tests and AST-only "reality tests", leaving more than 50% of active subsystems functionally untested.
- **Domain R6**: Severe configuration drift (84% of env vars undocumented), startup script omissions on Windows, port conflicts (8080 vs 8000 vs 8081 vs 11434), and missing multimodal dependencies prevent smooth production deployment.

## 5. Verification Method
1. **Verify Stubbed Judge Endpoints**:
   Inspect lines 101-111 of `scp/runtime/judge.py` and lines 80-118 of `scp/api/routes/admin_v98.py`.
2. **Verify Fake Chaos Recovery Test**:
   Inspect lines 1-8 of `scp/tests/chaos_recovery.py`.
3. **Verify Test Inflation**:
   Inspect `tests/test_subsystem_observability.py` and `tests/T03_capability/test_flow_19_audit_engine_scp_standard.py`.
4. **Verify Windows Startup Script Omission**:
   Compare `start-scp.bat` lines 82-94 against `start-scp.sh` lines 66-81.
5. **Verify Environment Variable Drift**:
   Run `.agents/explorer_survey_3/audit_r6.py` and compare against `.env.example`.
