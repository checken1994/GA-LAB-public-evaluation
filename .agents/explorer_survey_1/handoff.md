# Comprehensive Architectural Survey & Domain R3 Audit Report

**Audit Phase**: Survey Phase  
**Auditor Role**: Architecture & Subsystems Explorer (`explorer_survey_1`)  
**Target Repository**: `D:\scp`  
**Git Branch**: `feature/autonomous-mode-antigravity-v2` (HEAD: `6d6256f`)  
**Date**: 2026-09-22  

---

## 1. Observation

### 1.1 Executive Architectural Inventory

A comprehensive AST and filesystem analysis of the SCP codebase reveals the following system profile:
- **Repository Python Scale**: 1,201 `.py` files across the repository (~221,000 Python LOC).
- **Core Library Scale (`scp/`)**: 655 `.py` files containing 162,118 LOC.
- **Active Subsystem Count**: Exactly **43 directories** directly under `D:\scp\scp\` (excluding hidden cache directories `.pytest_cache`, `.ruff_cache`, and `__pycache__`).
- **Standalone Root Files**: 12 `.py` modules situated directly in `scp/` root (e.g., `api_server.py`, `ask_kernel_adapter.py`, `task_kernel.py`).
- **God Files (>500 LOC)**: **78 files** total in `scp/` (75 within subsystem directories, 3 in package root).
- **Dead Code Footprint**: **64 orphaned modules** (63 completely untested and unreferenced, accounting for >13,000 LOC).
- **Coupling Complexity**: **30 circular dependency cycles** linking critical subsystems.

---

### 1.2 Complete Catalog of All 43 Subsystems Under `scp/`

The table below catalogs every active subsystem directory located directly within `scp/`, including exact file counts, approximate lines of code (LOC), core architectural responsibilities, God file counts, and inbound/outbound dependency counts across subsystems:

| # | Subsystem | Relative Path | Files | LOC | God Files (>500 LOC) | Core Architectural Responsibility | Outbound Deps | Inbound Deps |
|---|---|---|---|---|---|---|---|---|
| 1 | **api** | `scp/api` | 35 | 6,678 | 4 (`v105_routes.py` 727, `chat.py` 617, `v104_routes.py` 543, `dashboard_html.py` 540) | REST & WebSocket API routing layer exposing FastAPI endpoints, routers, and request validation for clients and dashboard. | 18 | 1 |
| 2 | **api_server_parts** | `scp/api_server_parts` | 6 | 1,891 | 1 (`_ask_impl.py` 869) | Unbundled request execution, fact-checking, and lifespan functions extracted from the monolithic `api_server.py`. | 24 | 2 |
| 3 | **audit_engine** | `scp/audit_engine` | 9 | 288 | 0 | Formal hermetic audit and verification pipeline engine; currently isolated as a deadzone subsystem. | 0 | 0 |
| 4 | **audit_r8** | `scp/audit_r8` | 0 | 0 | 0 | Historical Round 8 audit artifacts, self-audit notes, and findings data (non-code markdown/JSON repository). | 0 | 0 |
| 5 | **audit_r9** | `scp/audit_r9` | 0 | 0 | 0 | Historical Round 9 audit artifacts, self-audit notes, and findings data (non-code markdown/JSON repository). | 0 | 0 |
| 6 | **autofix** | `scp/autofix` | 99 | 32,648 | 18 (`autofix_mixin.py` 1631, `engine.py` 1045, `property_validator.py` 924, `policy_gate.py` 895, `speculative_prefixer.py` 847, `taint_flow_scanner.py` 830, etc.) | Autonomous error detection, AST transformation, vulnerability scanning, semantic code patching, and self-healing engine. | 7 | 2 |
| 7 | **benchmark** | `scp/benchmark` | 22 | 2,643 | 1 (`run_benchmark_enhanced.py` 526) | Performance benchmarking framework, baseline LLM comparisons, and anti-hallucination accuracy measurement. | 1 | 0 |
| 8 | **brain** | `scp/brain` | 8 | 2,122 | 2 (`error_store.py` 550, `error_store_index.py` 534) | System cognitive memory and error indexing; persists and indexes runtime execution failures and error traces. | 0 | 0 |
| 9 | **calibration** | `scp/calibration` | 4 | 374 | 0 | Model confidence calibration ensuring uncertainty estimates and probability thresholds align with empirical correctness. | 0 | 0 |
| 10 | **capabilities** | `scp/capabilities` | 4 | 231 | 0 | Fine-grained capability registry, token permission checks, and capability boundary definitions. | 1 | 1 |
| 11 | **consolidator** | `scp/consolidator` | 2 | 161 | 0 | Distributed state consolidation and reconciliation across asynchronous background worker loops. | 0 | 0 |
| 12 | **contracts** | `scp/contracts` | 8 | 263 | 0 | Formal interface schemas, protocol specifications, invariant declarations, and data structures. | 0 | 0 |
| 13 | **core** | `scp/core` | 94 | 21,791 | 8 (`request_run_ledger.py` 801, `fastlearningengine.py` 716, `phase0.py` 702, `multi_source_verifier.py` 701, `smart_cache.py` 612, etc.) | Core system orchestration, lifecycle management, ledger persistence, multi-source verification, and capability token validation. | 10 | 18 |
| 14 | **data_sources** | `scp/data_sources` | 71 | 12,382 | 2 (`live_knowledge.py` 705, `chemistry.py` 642) | External data connectors, live evidence crawlers, Wikipedia/Wikidata scrapers, and domain-specific knowledge fetchers. | 5 | 1 |
| 15 | **epistemic** | `scp/epistemic` | 5 | 884 | 0 | Epistemic evidence tracking, certainty boundary enforcement, and factual knowledge provenance verification. | 2 | 1 |
| 16 | **experience** | `scp/experience` | 3 | 846 | 1 (`experience.py` 822) | Historical experience accumulation, episodic case indexing, and historical query pattern matching. | 1 | 1 |
| 17 | **forecast** | `scp/forecast` | 3 | 405 | 0 | Predictive outcome scoring, trajectory forecasting, and failure risk estimation. | 0 | 0 |
| 18 | **foundation** | `scp/foundation` | 3 | 476 | 0 | Foundational system abstractions, abstract base classes, and low-level utility primitives. | 0 | 0 |
| 19 | **governance** | `scp/governance` | 4 | 515 | 0 | Ethical guardrails, privacy write gates, retention policies, and architectural compliance rules. | 1 | 1 |
| 20 | **hands** | `scp/hands` | 8 | 2,552 | 2 (`planner.py` 977, `task_kernel_bridge.py` 656) | Physical execution apparatus: task decomposition, goal planning, OS execution, and TaskKernel interop. | 3 | 2 |
| 21 | **history** | `scp/history` | 5 | 660 | 0 | Long-term session logs, historical interaction chronicles, and query timeline storage. | 1 | 1 |
| 22 | **interfaces** | `scp/interfaces` | 2 | 83 | 0 | Public abstract interface contracts and protocol specifications for external caller integration. | 0 | 0 |
| 23 | **knowledge** | `scp/knowledge` | 28 | 6,807 | 4 (`mixins.py` 1190, `source_reputation.py` 695, `antibody_system.py` 676, `domain_knowledge.py` 533) | Knowledge base management, antibody defect registry, domain vector stores, and source reputation scoring. | 7 | 1 |
| 24 | **learning** | `scp/learning` | 2 | 37 | 0 | Continual learning loop and reinforcement learning pipeline for model parameter and prompt adjustments. | 0 | 0 |
| 25 | **llm_gateway** | `scp/llm_gateway` | 5 | 1,317 | 1 (`client.py` 1024) | Unified LLM provider routing (OpenAI, Anthropic, OpenRouter), egress enforcement, token pricing, and model failover. | 2 | 5 |
| 26 | **mcp_server** | `scp/mcp_server` | 3 | 437 | 0 | Model Context Protocol (MCP) server implementation enabling standardized external tool interoperability. | 0 | 0 |
| 27 | **meta** | `scp/meta` | 55 | 14,110 | 5 (`falsification_engine.py` 987, `meta.py` 960, `why_gate.py` 650, `calibration_engine.py` 607, `adversary_verifier.py` 549) | Metacognitive reflection, falsification engines, WHY gate rationale evaluation, and multi-LLM consensus validation. | 10 | 4 |
| 28 | **observability** | `scp/observability` | 4 | 190 | 0 | Observability infrastructure, OpenTelemetry distributed tracing hooks, and Prometheus metrics definitions. | 0 | 2 |
| 29 | **pc_control** | `scp/pc_control` | 2 | 470 | 0 | Local PC and OS automation controller (desktop automation, command execution, window manipulation). | 1 | 1 |
| 30 | **persistence** | `scp/persistence` | 2 | 118 | 0 | Database persistence abstractions, connection pool configurations, and SQLite/PostgreSQL utilities. | 0 | 0 |
| 31 | **policy** | `scp/policy` | 2 | 113 | 0 | Access control policies, authorization rules, and policy decision evaluation. | 0 | 0 |
| 32 | **prediction** | `scp/prediction` | 2 | 1,011 | 1 (`predictive.py` 1006) | Predictive analytics engine modeling temporal state transitions and anomaly expectations. | 1 | 1 |
| 33 | **rag** | `scp/rag` | 2 | 77 | 0 | Retrieval-Augmented Generation pipeline coordinating document chunking, embeddings, and context synthesis. | 0 | 0 |
| 34 | **release** | `scp/release` | 2 | 210 | 0 | Release identity verification, build reproducibility gates, and commit SHA verification. | 0 | 0 |
| 35 | **risk_intelligence** | `scp/risk_intelligence` | 6 | 360 | 0 | Dynamic threat risk intelligence, anomaly detection, and vulnerability posture assessment. | 1 | 1 |
| 36 | **runtime** | `scp/runtime` | 61 | 10,932 | 7 (`question_router.py` 977, `humanities.py` 821, `chem_reality_astro.py` 817, `lifestyle.py` 692, `misc.py` 674, `scpv14_process_mixin.py` 650, `storage_manager.py` 529) | Execution runtime orchestrating the RealityJudge, domain SLM experts, ask pipeline execution, and worker processes. | 15 | 2 |
| 37 | **sandbox_evaluator** | `scp/sandbox_evaluator` | 4 | 753 | 0 | Isolated execution sandbox evaluating untrusted code snippets, patches, and commands safely. | 0 | 0 |
| 38 | **security** | `scp/security` | 44 | 11,623 | 6 (`counter_response.py` 708, `threat_detector.py` 625, `predictor.py` 575, `escalation.py` 570, `threat_simulator.py` 519, `attack_memory.py` 510) | Fail-Closed Security engine: JWT authorization, SSRF/egress filtering, attack classification, and canary tripwires. | 6 | 7 |
| 39 | **self_model** | `scp/self_model` | 2 | 280 | 0 | Introspective self-model tracking agent internal operational state, health status, and capability boundaries. | 0 | 0 |
| 40 | **task_kernel_parts** | `scp/task_kernel_parts` | 2 | 1,966 | 1 (`taskkernel.py` 1966) | Low-level TaskKernel state machine implementation, lease acquisition, transaction fencing, and event journal logs. | 0 | 1 |
| 41 | **tests** | `scp/tests` | 9 | 792 | 0 | Embedded internal test suites, chaos recovery tests, property-based tests, and external audit security regressions. | 2 | 0 |
| 42 | **web_control** | `scp/web_control` | 7 | 1,007 | 0 | Headless browser management (Playwright), search scraping, DOM traversal, and web navigation. | 2 | 2 |
| 43 | **world_state** | `scp/world_state` | 4 | 316 | 0 | External world state representation, temporal state delta tracking, and entity grounding. | 0 | 0 |

---

### 1.3 Standalone Root Modules Under `scp/`

In addition to the 43 subdirectories, 12 modules reside in the root `scp/` namespace:
- `scp/ask_kernel_adapter.py` (1,017 LOC - **God File**): Adapter bridging user queries between `/ask` pipeline and `TaskKernel`.
- `scp/api_server.py` (729 LOC - **God File**): FastAPI composition root, app lifespan orchestration, and rate limiting.
- `scp/kernel_storage_pg.py` (526 LOC - **God File**): PostgreSQL backend implementation of durable kernel storage.
- `scp/event_bus_pg.py` (495 LOC): PostgreSQL-backed distributed event bus.
- `scp/ai_patterns.py` (454 LOC): Generic prompting patterns, majority voting, and retry loops.
- `scp/task_kernel.py` (423 LOC): TaskKernel public contract, state enum definitions, and monkeypatched methods.
- `scp/kernel_storage.py` (238 LOC): SQLite and abstract backend definitions for KernelStorage.
- `scp/__main__.py` (128 LOC): CLI launcher entry point.
- `scp/verifier.py` (74 LOC): Base verifier protocol for worker task validation.
- `scp/trace_ledger.py` (58 LOC): Legacy JSONL file-based trace ledger reader/writer.
- `scp/hello_bug.py` (7 LOC): Intentional canary bug fixture for static analysis verification.
- `scp/__init__.py` (6 LOC): Package root identity and version declarations.

---

### 1.4 God Files (>500 LOC) Maintainability Profile

A total of **78 God Files** were identified across `scp/`. Below are the top 12 highest cognitive load files:

| File Path | LOC | Subsystem | Maintenance Risk Rationale |
|---|---|---|---|
| `scp/task_kernel_parts/taskkernel.py` | 1,966 | `task_kernel_parts` | Massive state machine handling transitions, leases, OCC locks, rollback, and event journaling in a single class. |
| `scp/autofix/engine_parts/autofix_mixin.py` | 1,631 | `autofix` | Giant mixin containing disparate patch generation, verification, and regression rollback logic. |
| `scp/knowledge/antibody_parts/mixins.py` | 1,190 | `knowledge` | Monolithic mixin managing antibody state, mutation, matching, and severity computation. |
| `scp/autofix/engine.py` | 1,045 | `autofix` | Autorepair engine core coordinating scanning, patch generation, testing, and feedback loops. |
| `scp/llm_gateway/client.py` | 1,024 | `llm_gateway` | Monolithic LLM client implementing retry logic, SSE stream parsing, cost calculation, and failover. |
| `scp/ask_kernel_adapter.py` | 1,017 | `root` | Complex glue module adapting `/ask` request flows, question routing, and async task execution. |
| `scp/prediction/predictive.py` | 1,006 | `prediction` | Monolithic predictive analytics class with mixed mathematical routines and database queries. |
| `scp/meta/falsification_engine.py` | 987 | `meta` | Multi-pass adversarial proposition falsifier with nested AST and regex rules. |
| `scp/hands/planner.py` | 977 | `hands` | Complex procedural task planning engine combining heuristic rules with LLM instructions. |
| `scp/runtime/question_router.py` | 977 | `runtime` | 44-domain routing decision tree, heuristic keyword matching, and SLM dispatch logic. |
| `scp/autofix/property_validator.py` | 924 | `autofix` | Deep property assertion validator analyzing AST invariants. |
| `scp/api_server_parts/_ask_impl.py` | 869 | `api_server_parts` | Monolithic request pipeline handling `/ask` execution, OCR/voice dispatch, and judge invocation. |

---

### 1.5 Domain R3 Findings with Concrete Evidence

#### Finding R3-01: Untracked & Unplugged Backward Traceability Stack with Test Suite Bypass
- **Severity**: **CRITICAL**
- **Affected Files**:
  - `scp/core/trace_store.py` (183 LOC, untracked)
  - `scp/api_server_parts/_trace_impl.py` (66 LOC, untracked)
  - `scp/core/trace_contract.py` (lines 25-29, 42-65, uncommitted modification)
  - `scp/api_server.py` (missing router inclusion)
  - `tests/T12_unified_chatbot/conftest.py` (lines 189-235, copy-paste test bypass)
  - `tests/T12_unified_chatbot/test_tier4_real_world_scenarios.py` (lines 261-320, 340-395)
- **Description**:
  Milestone 3 backward traceability functionality exists in a fragmented, uncommitted state. `scp/core/trace_store.py` implements the production `TraceStore` (SQLite WAL mode, indexing, causal DAG generation), and `scp/api_server_parts/_trace_impl.py` defines the REST router (`GET /api/scp/v3/trace/{trace_id}`). However, both files remain untracked in git. Crucially, `scp/api_server.py` **never mounts `_trace_impl.router`**, meaning the trace lookup API does not actually exist on the live running server.
  To compensate, the test suite (`tests/T12_unified_chatbot/conftest.py`) defined a duplicate copy of `class SqliteTraceStore`, and test cases (`test_scenario_04_decision_trace_audit_via_api`, `test_scenario_05_full_dashboard_ask_and_trace_flow`, `test_comb09_end_to_end_ask_trace_store_api_lookup`) claim in their docstrings to query `GET /api/scp/v3/trace/{trace_id}`, but actually bypass the HTTP layer entirely by calling `trace_store.get_trace(trace_id)` on the Python test fixture.
- **Evidence**:
  1. `git status` output confirms untracked and uncommitted files:
     ```
     Changes not staged for commit:
             modified:   scp/core/trace_contract.py
     Untracked files:
             scp/api_server_parts/_trace_impl.py
             scp/core/trace_store.py
     ```
  2. `scp/api_server_parts/_trace_impl.py` (lines 22-29):
     ```python
     @router.get("/api/scp/v3/trace/{trace_id}")
     @router.get("/api/v3/trace/{trace_id}")
     @router.get("/v3/trace/{trace_id}")
     async def get_trace_record(trace_id: str) -> dict[str, Any]:
         """Retrieve backward-traceable causal history for a specific trace_id."""
         store = get_trace_store()
         record = store.get_trace(trace_id)
     ```
  3. `scp/api_server.py` lines 680-724 include routers for `hands`, `batch_benchmark`, `agent`, and `call`, but **0 calls to `app.include_router(_trace_impl.router)`** exist.
  4. `tests/T12_unified_chatbot/test_tier4_real_world_scenarios.py` lines 261-266 vs 309-311:
     ```python
     def test_scenario_04_decision_trace_audit_via_api(self, trace_store):
         """Scenario 4: External auditor queries trace API and validates 5-stage causal DAG.
         Steps:
         1. Query executed and recorded with trace_id.
         2. Simulated auditor queries GET /api/scp/v3/trace/{trace_id}.
         """
         ...
         # Auditor lookup (Bypasses HTTP API completely!)
         audit = trace_store.get_trace(trace_id)
         assert audit is not None
     ```

---

#### Finding R3-02: Massive Dead Code Footprint — 63 Verified Orphaned Modules (>13,000 LOC)
- **Severity**: **HIGH**
- **Affected Files**: 63 Python modules under `scp/` with 0 inbound imports across the repository and 0 pytest coverage.
- **Description**:
  An AST-based import resolution across all 1,201 Python files in the repository proved that 63 Python modules under `scp/` are never imported by any other runtime file, entry point, or test. They represent >13,000 LOC of accumulated technical debt and abandoned refactoring artifacts.
- **Evidence Table (Selected High-Risk Orphaned Modules)**:

| Orphaned File Path | LOC | Subsystem | Description / Abandoned Functionality |
|---|---|---|---|
| `scp/runtime/experts/chem_reality_astro.py` | 817 | `runtime` | Legacy SLM domain expert abandoned during S26 unification; 0 callers in repo. |
| `scp/runtime/experts/misc.py` | 674 | `runtime` | Generic fallback SLM expert; completely unreferenced. |
| `scp/security/h8_redteam_bridge.py` | 660 | `security` | H8 Red Team evaluation harness; never imported by runtime or test suites. |
| `scp/runtime/engine_parts/scpv14_process_mixin.py` | 650 | `runtime` | Deprecated v14 process orchestration mixin; never imported by `runtime/engine.py`. |
| `scp/meta/calibration_engine.py` | 607 | `meta` | Standalone metacognitive calibration engine; 0 imports across codebase. |
| `scp/meta/adversary_verifier.py` | 549 | `meta` | Adversarial verification engine; replaced by `core/multi_source_verifier.py`. |
| `scp/brain/error_store_index.py` | 534 | `brain` | Secondary indexing structure for error store; unused by `brain/error_store.py`. |
| `scp/benchmark/run_benchmark_enhanced.py` | 526 | `benchmark` | Enhanced CLI runner with 8 metrics; never invoked in CI or imported by tests. |
| `scp/meta/question_tracker.py` | 460 | `meta` | Question evolution tracker; 0 callers in runtime. |
| `scp/ai_patterns.py` | 454 | `root` | Root helper containing `augment_prompt`, `verify_with_voting`; 0 callers. |
| `scp/runtime/experts/numeric_data.py` | 453 | `runtime` | Numerical data SLM expert; orphaned in S26 refactoring. |
| `scp/meta/verdict_predictor.py` | 396 | `meta` | Speculative verdict predictor; 0 callers. |
| `scp/meta/self_questioning.py` | 395 | `meta` | Self-questioning cognitive module; unused. |
| `scp/runtime/experts/math_biology.py` | 394 | `runtime` | Math & biology SLM expert; orphaned in S26 refactoring. |
| `scp/runtime/healing_v14.py` | 390 | `runtime` | Legacy v14 self-healing engine superseded by `autofix/` subsystems. |
| `scp/security/threat_intel.py` | 364 | `security` | Unused threat intelligence feed parser. |
| `scp/knowledge/scheduled_crawler.py` | 341 | `knowledge` | Background crawler thread; never instantiated by `api_server` lifespan. |
| `scp/core/real_question_fetcher.py` | 326 | `core` | Live question fetcher; 0 callers. |
| `scp/benchmark/run_baseline.py` | 296 | `benchmark` | Standalone benchmark script; unreferenced. |
| `scp/core/auto_backup.py` | 293 | `core` | Automatic local file backup utility; unreferenced. |
| `scp/security/auto_payload_generator.py` | 251 | `security` | Autonomous payload generation script; unreferenced. |
| `scp/security/memory_guard.py` | 229 | `security` | Security memory protection layer; unreferenced. |
| `scp/core/react_agent.py` | 214 | `core` | Standalone ReAct agent loop implementation; 0 callers. |
| `scp/core/github_backup.py` | 197 | `core` | GitHub remote backup synchronizer; unreferenced. |

---

#### Finding R3-03: 30 Circular Dependency Chains Across Core Subsystems
- **Severity**: **HIGH**
- **Affected Subsystems**: `core`, `autofix`, `hands`, `security`, `meta`, `knowledge`, `epistemic`, `governance`, `llm_gateway`, `api_server_parts`, `runtime`, `data_sources`
- **Description**:
  DFS cycle detection on the AST subsystem import graph identified **30 circular dependency chains**. The codebase suffers from direct bidirectional coupling between foundational and high-level subsystems, leading to fragile import order dependencies, runtime `ImportError` hazards during lazy initialization, and impossible standalone subsystem packaging.
- **Evidence of Direct Subsystem Cycles**:
  1. **`core` <-> `autofix`**:
     - `scp/core/bounded_evolution.py:54`: `from scp.autofix.evolution import get_evolution_engine`
     - `scp/autofix/engine.py:408`: `from scp.core.code_evolution_agent import _relative_repo_path`
     - `scp/autofix/runner.py:631`: `from scp.core.bounded_evolution import run_bounded_evolution`
     - `scp/autofix/engine_parts/autofix_mixin.py:337`: `from scp.core.code_evolution_agent import CodeEvolutionAgent`
  2. **`core` <-> `hands`**:
     - `scp/core/agent_orchestrator.py:23-25`: `from scp.hands.planner import HandsPlanner`
     - `scp/hands/planner.py:3`: `from scp.core.capability_token import verify_token`
     - `scp/hands/task_kernel_bridge.py:492`: `from scp.core.verifier_receipt import VerifierReceipt, sign_verifier_receipt`
  3. **`epistemic` <-> `governance`**:
     - `scp/epistemic/evidence_writer.py:11`: `from scp.governance.privacy import PrivacyDecision, PrivacyWriteGate`
     - `scp/governance/retention.py:16`: `from scp.epistemic.evidence_store import EvidenceStore`
  4. **`security` <-> `api_server_parts`**:
     - `scp/security/threat_simulator.py:468`: `from scp.api_server_parts.helpers import get_judge`
     - `scp/api_server_parts/helpers.py:85`: `from scp.security.attack_crawler import AttackCrawler`
     - `scp/api_server_parts/helpers.py:262`: `from scp.security.auth import verify_admin`
  5. **`llm_gateway` <-> `security`**:
     - `scp/llm_gateway/client.py:178-179`: `from scp.security.url_safety import EgressDeniedError, enforce_egress_policy`
     - `scp/security/quorum_why.py:59`: `from scp.llm_gateway import get_gateway`
  6. **`meta` <-> `knowledge`**:
     - `scp/meta/epistemic_boundary.py:6-7`: `from scp.knowledge.learning_db import LearningDB`
     - `scp/knowledge/antibody_system.py:49`: `from scp.meta.severity import Severity`
     - `scp/knowledge/antibody_parts/mixins.py:6`: `from scp.meta.severity import Severity`
  7. **`meta` <-> `security`**:
     - `scp/meta/why_sources/crypto.py:18`: `from scp.security.url_safety import safe_urlopen`
     - `scp/security/predictor.py:437`: `from scp.meta.why_gate import get_why_gate`

---

#### Finding R3-04: "Split-and-Stitch" Architectural Anti-Pattern (Pseudo-Modularization via `*_parts` with Runtime Monkeypatching)
- **Severity**: **HIGH**
- **Affected Files**:
  - `scp/api_server.py` (lines 299-310) & `scp/api_server_parts/`
  - `scp/task_kernel.py` (lines 407-415) & `scp/task_kernel_parts/`
  - `scp/autofix/engine.py` & `scp/autofix/engine_parts/`
  - `scp/core/fast_learning_engine.py` & `scp/core/fast_learning_engine_parts/`
  - `scp/knowledge/antibody_system.py` & `scp/knowledge/antibody_parts/`
  - `scp/meta/why_engine.py` & `scp/meta/why_engine_parts/`
  - `scp/runtime/engine.py` & `scp/runtime/engine_parts/`
- **Description**:
  Seven major subsystems have undergone cosmetic file splitting where monolithic files were decomposed into `*_parts` directories, but without proper dependency injection or class composition. Instead, the extracted files duplicate process-global state imports and are stitched back together using bytecode function rebinding and class monkeypatching at runtime.
- **Evidence**:
  1. `scp/api_server.py` lines 299-310:
     ```python
     def _rebind_part_function(fn):
         """Bind extracted code to this module's authoritative globals."""
         rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
         rebound.__kwdefaults__ = fn.__kwdefaults__
         rebound.__annotations__ = dict(getattr(fn, "__annotations__", {}))
         rebound.__doc__ = fn.__doc__
         rebound.__module__ = __name__
         return rebound

     _async_fact_check = _rebind_part_function(_async_fact_check_part._async_fact_check)
     _ask_impl = _rebind_part_function(_ask_impl_part._ask_impl)
     ```
  2. `scp/task_kernel.py` lines 407-415:
     ```python
     TaskKernel.idempotency_claim = _idempotency_claim_fenced
     TaskKernel.idempotency_complete = _idempotency_complete_fenced
     TaskKernel.idempotency_status = _idempotency_status
     TaskKernel.reconcile_unknown = _reconcile_unknown_complete_outcomes

     TaskKernel.__module__ = __name__
     ```
  3. `scp/api_server_parts/_ask_impl.py`, `_async_fact_check.py`, and `lifespan.py` copy-paste identical 40-line blocks of unneeded imports (e.g. `Limiter`, `Counter`, `Histogram`, `FastAPI`, `Request`) simply to satisfy code copied verbatim out of `api_server.py`.

---

#### Finding R3-05: Specification Authority & Maintenance Tool Remnants of Deleted Modules
- **Severity**: **MEDIUM**
- **Affected Files**:
  - `spec/implementation_bindings.yaml` (lines 37-40)
  - `spec/llm_outbound_paths.yaml` (lines 9, 16)
  - `tools/fix_judgecore_domain_signature.py` (lines 5-6)
  - `scripts/maintenance/patch_universal_local_only.py` (lines 4-5)
- **Description**:
  Specification files and operational maintenance scripts still reference modules that were permanently removed during earlier refactorings (such as S26 Expert Unification and zero-cost deprecation).
- **Evidence**:
  1. `spec/implementation_bindings.yaml` lines 37-40:
     ```yaml
       intelligence.zero_cost:
         - scp.llm_gateway.zero_cost_guard
         - scp.llm_gateway.zero_cost_runtime
     ```
     `scp/llm_gateway/zero_cost_guard.py` and `zero_cost_runtime.py` were physically deleted from disk.
  2. `spec/llm_outbound_paths.yaml` line 16:
     ```yaml
         evidence: scp/llm_gateway/__init__.py imports zero_cost_runtime; tests/T05_gateway/test_zero_cost_guard.py
     ```
  3. `tools/fix_judgecore_domain_signature.py` lines 5-6:
     ```python
     root = Path(__file__).resolve().parents[1]
     p = root / "scp" / "runtime" / "judge_parts" / "judgecore_mixin.py"
     ```
     Running this maintenance script fails with `FileNotFoundError` because `judge_parts/` was deleted in S26.
  4. `scripts/maintenance/patch_universal_local_only.py` line 5:
     ```python
     path = Path(str(Path(__file__).resolve().parent.parent / "scp" / "runtime" / "slm_impls" / "misc_slm.py"))
     ```
     Fails with `FileNotFoundError` because `slm_impls/` was deleted in S26.

---

#### Finding R3-06: Deadzone Subsystems & Non-Code Artifact Directories Polluting Library Root
- **Severity**: **MEDIUM**
- **Affected Directories**:
  - `scp/audit_r8/` (0 Python files, 6 markdown/JSON files)
  - `scp/audit_r9/` (0 Python files, 6 markdown/JSON files)
  - `scp/audit_engine/` (9 Python files, 288 LOC)
- **Description**:
  Directories `scp/audit_r8` and `scp/audit_r9` sit directly inside the production Python package directory `scp/`, but contain 0 code files. They store historical round 8 and 9 audit notes (`r8_findings.jsonl`, `FIXES_APPLIED_R8.md`, `V4_WIRE_LOG.md`). Furthermore, `scp/audit_engine` is a dead subsystem isolated by `test_deadzone_audit_engine.py` whose sole test assertion is that no external module imports it.
- **Evidence**:
  1. Directory listing in `scp/audit_r8`:
     `['FIXES_APPLIED_R8.md', 'r8_findings.jsonl', 'r8_findings.md', 'round9_findings.json', 'round9_self_audit.md', 'SCP_DNA_AUDIT_ROUND8_CHANGES.md']`
  2. `tests/test_deadzone_audit_r8.py` lines 11-16:
     ```python
     def test_dead_audit_r8_no_external_imports():
         """
         Hệ thống chết 'audit_r8' phải bị cách ly hoàn toàn.
         Không có file nào bên ngoài thư mục 'audit_r8/' được phép import nó.
         Nếu fail → Zombie Leak: code chết đang ảnh hưởng đến code sống.
         """
     ```

---

#### Finding R3-07: Internal Test Co-mingling (`scp/tests/`) & Superficial Test Coverage
- **Severity**: **MEDIUM**
- **Affected Files**:
  - `scp/tests/` (9 files, 792 LOC)
  - `pytest.ini` (line 3)
  - `tests/test_subsystem_*.py` (23 files)
- **Description**:
  1. Internal test modules (`chaos_recovery.py`, `golden_task.py`, `external_audit/test_security.py`, `property/test_none_safety.py`) are placed inside `scp/tests/` within the library package tree. `pytest.ini` explicitly configures `testpaths = tests scp/tests`.
  2. 23 test suites under `tests/` named `test_subsystem_<name>.py` are 13-line files providing illusory coverage by only asserting `assert mod is not None`.
  3. 17 subsystems (`calibration`, `capabilities`, `consolidator`, `experience`, `forecast`, `history`, `interfaces`, `learning`, `mcp_server`, `policy`, `rag`, `release`, `risk_intelligence`, `sandbox_evaluator`, `world_state`, `api_server_parts`, `task_kernel_parts`) have no dedicated test suite file.
- **Evidence**:
  1. `tests/test_subsystem_core.py` lines 8-13:
     ```python
     def test_subsystem_core_importable():
         """Core business logic: module phải import được không lỗi."""
         import importlib
         mod = importlib.import_module("scp.core")
         assert mod is not None, f"FAIL: scp.core không import được!"
     ```
  2. `pytest.ini` lines 1-3:
     ```ini
     [pytest]
     pythonpath = .
     testpaths = tests scp/tests
     ```

---

#### Finding R3-08: Intentional Canary Fixture Bug Documented as Protected Artifact
- **Severity**: **INFO**
- **Affected File**: `scp/hello_bug.py` (lines 1-8)
- **Description**:
  Static analysis scanners flag an undefined variable in `scp/hello_bug.py`. Investigation confirmed this is an intentional, protected canary fixture pinned by M07 circuit closure for verifying AST scanners.
- **Evidence**:
  `scp/hello_bug.py` lines 1-8:
  ```python
  # INTENTIONAL CANARY FIXTURE — DO NOT FIX, DO NOT MOVE, DO NOT DELETE.
  # Used by the /v105 autofix observe probe (ast_scan undefined-name visitor) to
  # prove the scanner really runs at runtime. Path is pinned by the M07 circuit
  # closure (docs/evidence-summary/M07-closure.json, probe commit 1f00d00):
  # ast_scan must keep finding scp/hello_bug.py as a live finding.
  def hello():
      x = unknown_var  # noqa: F821 -- intentional canary bug, see header above
  ```

---

#### Finding R3-09: Inconsistent Naming Conventions Across Subsystems
- **Severity**: **LOW**
- **Affected Files**: Codebase-wide
- **Description**:
  1. File naming violates Python PEP 8 standards with concatenated names (`fastlearningengine.py`, `taskkernel.py`, `whyengine.py`, `reflectmixin.py`) rather than snake_case (`fast_learning_engine.py`, `task_kernel.py`).
  2. Ephemeral audit milestone versions are embedded into persistent module names (`scp/meta/governance_v97.py`, `scp/runtime/healing_v14.py`, `scp/runtime/engine_parts/scpv14_process_mixin.py`, `scp/api/routes/v102_v103_routes.py`, `scp/api/routes/v104_routes.py`, `scp/api/routes/v105_routes.py`).

---

## 2. Logic Chain

1. **Observation**: `git status` shows uncommitted changes to `trace_contract.py` and untracked files `_trace_impl.py` and `trace_store.py`.
   - **Reasoning**: Backward traceability (Milestone 3) was implemented in working files but never committed.
   - **Observation**: `api_server.py` does not import `_trace_impl.py` or call `app.include_router()`.
   - **Observation**: `tests/T12_unified_chatbot/conftest.py` duplicates `SqliteTraceStore` and scenario tests query the fixture directly instead of HTTP.
   - **Inference**: The test suite exhibits a "green test illusion" — tests pass because they test local mock/fixture objects rather than the real server route, masking the fact that the production API route is completely unplugged.
   - **Conclusion**: Finding R3-01 is **CRITICAL**; committing the files and mounting `_trace_impl.router` on `app` in `api_server.py` is required.

2. **Observation**: AST import resolution confirmed that 63 `.py` files in `scp/` have 0 importers across the repo and 0 tests in `tests/`.
   - **Reasoning**: Previous refactorings (such as S26 removing `slms.py` and `judge_parts`) left behind individual expert files (`chem_reality_astro.py`, `misc.py`, `numeric_data.py`), old engines (`healing_v14.py`, `calibration_engine.py`), and unintegrated tools.
   - **Inference**: Over 13,000 LOC of dead code increases repository bloat, inflates test collection overhead, and creates confusion about authoritative paths.
   - **Conclusion**: Finding R3-02 is **HIGH**; a planned deprecation and cleanup phase is needed.

3. **Observation**: 30 circular dependency cycles exist across 12 major subsystems, with direct bidirectional imports (e.g. `core` <-> `autofix`, `core` <-> `hands`, `meta` <-> `knowledge`).
   - **Reasoning**: Subsystem boundaries are porous; higher-level workflow components import lower-level utilities, but lower-level utilities also import higher-level components for specialized features.
   - **Inference**: Circular imports cause fragile import sequencing, race conditions on module initialization, and prevent modular architectural decomposition.
   - **Conclusion**: Finding R3-03 is **HIGH**; dependency inversion or protocol abstractions are required to break cycles.

4. **Observation**: 7 subsystems employ `*_parts/` directories where functions are rebound via `types.FunctionType` or monkeypatched onto classes.
   - **Reasoning**: Developers attempted to reduce file LOC to comply with linting/LOC limits without refactoring class structures.
   - **Inference**: Runtime monkeypatching obscures IDE navigation, breaks static typing, complicates debugging, and introduces hidden coupling to global variables.
   - **Conclusion**: Finding R3-04 is **HIGH**.

---

## 3. Caveats

1. **Scope Boundary**: This investigation focused strictly on architecture, subsystem inventory, and Requirement Domain R3 (Architectural Integrity & Dead Code). Runtime concurrency (R5), security vulnerabilities (R2), and test logic assertions (R4) were surveyed solely where they intersected with dead code or architectural integrity.
2. **Intentional Canaries**: Certain files appearing dead or buggy (notably `scp/hello_bug.py`) are intentional canaries required by circuit closures; they must NOT be deleted without verifying circuit closure agreements.
3. **No Implementation**: In strict compliance with explorer subagent constraints, no source code was modified during this survey.

---

## 4. Conclusion

The SCP system is an advanced agent architecture with extensive self-correction and security controls. However, rapid evolutionary refactoring has left significant architectural debt:
1. **Unplugged Feature & Test Illusion**: Backward traceability (`trace_store.py`, `_trace_impl.py`, `trace_contract.py`) is functionally uncommitted and disconnected from `api_server.py`, while tests pass by testing a duplicated fixture rather than the live route.
2. **Substantial Dead Code**: 63 orphaned modules (>13,000 LOC) linger in `scp/` without callers or tests.
3. **Porous Boundaries**: 30 circular subsystem dependency cycles and 7 instances of pseudo-modular monkeypatching undermine architectural isolation.
4. **Specification Divergence**: Specification files still declare bindings to deleted zero-cost modules.

### Recommended Remediation Roadmap
1. **Immediate (P0)**:
   - Commit `scp/core/trace_store.py`, `scp/api_server_parts/_trace_impl.py`, and `scp/core/trace_contract.py`.
   - Mount `_trace_impl.router` in `scp/api_server.py`.
   - Update `tests/T12_unified_chatbot/conftest.py` to use `from scp.core.trace_store import TraceStore` instead of duplicated class.
   - Update scenario tests to execute real HTTP client calls against `/api/scp/v3/trace/{trace_id}`.
2. **Short-Term (P1)**:
   - Update `spec/implementation_bindings.yaml` and `spec/llm_outbound_paths.yaml` to remove references to `zero_cost_guard` and `zero_cost_runtime`.
   - Delete obsolete maintenance scripts (`tools/fix_judgecore_domain_signature.py`, `scripts/maintenance/patch_universal_local_only.py`).
   - Move `scp/audit_r8` and `scp/audit_r9` out of the Python package root into `docs/audit_history/`.
   - Move `scp/tests/` into `tests/internal/`.
3. **Medium-Term (P2)**:
   - Break bidirectional cycles between `core` <-> `autofix` and `core` <-> `hands` using abstract protocol interfaces.
   - Safely prune or archive the 63 dead modules.

---

## 5. Verification Method

To independently verify all findings in this report:

1. **Verify Uncommitted Traceability Stack**:
   ```bash
   git status
   git diff scp/core/trace_contract.py
   pytest tests/T02_contract/ -q
   ```
2. **Verify Meta-Audit Integrity Gate**:
   ```bash
   python tools/t00_meta_audit.py
   ```
   *Expected result*: `[T00 Meta-Audit] All integrity checks passed (0 new regressions).`
3. **Verify Zero Import Collection Errors**:
   ```bash
   pytest tests/ --collect-only -q
   ```
   *Expected result*: `1937 tests collected in ~3.7s` with 0 collection errors.
4. **Verify Orphaned Files**:
   Inspect `D:\scp\.agents\explorer_survey_1\orphaned_classified.json` and grep for any module:
   ```bash
   python -c "import json; data=json.load(open('D:/scp/.agents/explorer_survey_1/orphaned_classified.json')); print('Truly dead:', len(data['truly_dead']))"
   ```
5. **Verify Subsystem Circular Dependencies**:
   Inspect `D:\scp\.agents\explorer_survey_1\subsystem_cycles.json` and run:
   ```bash
   python D:\scp\.agents\explorer_survey_1\inspect_cycles.py
   ```
