# Project: Deep Comprehensive Audit of SCP (Secure Control Plane)

## Architecture Overview
- **Repository Python Scale**: 1,201 `.py` files (~221,000 Python LOC)
- **Core Library Scale (`scp/`)**: 655 `.py` files (162,118 LOC)
- **Subsystem Count**: 43 active directories directly under `scp/` + 12 root modules
- **God Files (>500 LOC)**: 78 files identified (top: `task_kernel_parts/taskkernel.py` 1,966 LOC, `autofix_mixin.py` 1,631 LOC)
- **Test Infrastructure**: T00-T12 test suites (1,937 tests currently collected and passing)

---

## Subsystem Inventory (All 43 Subsystems + Root Modules)

| # | Subsystem | Relative Path | Files | LOC | God Files | Core Responsibility |
|---|---|---|---|---|---|---|
| 1 | **api** | `scp/api` | 35 | 6,678 | 4 | REST & WebSocket API routing layer, routers, and request validation |
| 2 | **api_server_parts** | `scp/api_server_parts` | 6 | 1,891 | 1 | Unbundled request execution, fact-checking, and lifespan functions |
| 3 | **audit_engine** | `scp/audit_engine` | 9 | 288 | 0 | Formal hermetic audit and verification pipeline engine |
| 4 | **audit_r8** | `scp/audit_r8` | 0 | 0 | 0 | Historical Round 8 audit artifacts and findings data (non-code) |
| 5 | **audit_r9** | `scp/audit_r9` | 0 | 0 | 0 | Historical Round 9 audit artifacts and findings data (non-code) |
| 6 | **autofix** | `scp/autofix` | 99 | 32,648 | 18 | Autonomous error detection, AST transformation, semantic patching |
| 7 | **benchmark** | `scp/benchmark` | 22 | 2,643 | 1 | Performance benchmarking and anti-hallucination evaluation |
| 8 | **brain** | `scp/brain` | 8 | 2,122 | 2 | System cognitive memory and runtime error indexing |
| 9 | **calibration** | `scp/calibration` | 4 | 374 | 0 | Model confidence calibration and uncertainty estimation |
| 10 | **capabilities** | `scp/capabilities` | 4 | 231 | 0 | Fine-grained capability registry and token permission checks |
| 11 | **consolidator** | `scp/consolidator` | 2 | 161 | 0 | Distributed state consolidation across asynchronous loops |
| 12 | **contracts** | `scp/contracts` | 8 | 263 | 0 | Formal interface schemas and protocol invariant specifications |
| 13 | **core** | `scp/core` | 94 | 21,791 | 8 | Core orchestration, lifecycle management, ledger persistence |
| 14 | **data_sources** | `scp/data_sources` | 71 | 12,382 | 2 | External data connectors, live evidence crawlers, scrapers |
| 15 | **epistemic** | `scp/epistemic` | 5 | 884 | 0 | Epistemic evidence tracking and provenance verification |
| 16 | **experience** | `scp/experience` | 3 | 846 | 1 | Historical experience accumulation and case indexing |
| 17 | **forecast** | `scp/forecast` | 3 | 405 | 0 | Predictive outcome scoring and failure risk estimation |
| 18 | **foundation** | `scp/foundation` | 3 | 476 | 0 | Foundational system abstractions and low-level primitives |
| 19 | **governance** | `scp/governance` | 4 | 515 | 0 | Ethical guardrails, privacy write gates, retention policies |
| 20 | **hands** | `scp/hands` | 8 | 2,552 | 2 | Task decomposition, goal planning, and TaskKernel interop |
| 21 | **history** | `scp/history` | 5 | 660 | 0 | Long-term session logs and interaction chronicles |
| 22 | **interfaces** | `scp/interfaces` | 2 | 83 | 0 | Public abstract interface contracts and protocol specifications |
| 23 | **knowledge** | `scp/knowledge` | 28 | 6,807 | 4 | Knowledge base management, antibody defect registry, domain stores |
| 24 | **learning** | `scp/learning` | 2 | 37 | 0 | Continual learning loop and reinforcement learning pipeline |
| 25 | **llm_gateway** | `scp/llm_gateway` | 5 | 1,317 | 1 | Unified LLM provider routing, egress enforcement, failover |
| 26 | **mcp_server** | `scp/mcp_server` | 3 | 437 | 0 | Model Context Protocol server for standardized external tools |
| 27 | **meta** | `scp/meta` | 55 | 14,110 | 5 | Metacognitive reflection, falsification engines, WHY gate |
| 28 | **observability** | `scp/observability` | 4 | 190 | 0 | OpenTelemetry tracing hooks and Prometheus metrics |
| 29 | **pc_control** | `scp/pc_control` | 2 | 470 | 0 | Local PC and OS automation controller |
| 30 | **persistence** | `scp/persistence` | 2 | 118 | 0 | Database persistence abstractions and connection pools |
| 31 | **policy** | `scp/policy` | 2 | 113 | 0 | Access control policies and authorization rules |
| 32 | **prediction** | `scp/prediction` | 2 | 1,011 | 1 | Predictive analytics engine modeling temporal state transitions |
| 33 | **rag** | `scp/rag` | 2 | 77 | 0 | Retrieval-Augmented Generation pipeline |
| 34 | **release** | `scp/release` | 2 | 210 | 0 | Release identity verification and commit SHA gates |
| 35 | **risk_intelligence** | `scp/risk_intelligence` | 6 | 360 | 0 | Dynamic threat risk intelligence and anomaly detection |
| 36 | **runtime** | `scp/runtime` | 61 | 10,932 | 7 | Execution runtime, RealityJudge, domain SLMs, worker processes |
| 37 | **sandbox_evaluator** | `scp/sandbox_evaluator` | 4 | 753 | 0 | Isolated execution sandbox evaluating untrusted code |
| 38 | **security** | `scp/security` | 44 | 11,623 | 6 | Fail-Closed Security engine, JWT auth, SSRF filtering, canaries |
| 39 | **self_model** | `scp/self_model` | 2 | 280 | 0 | Introspective self-model tracking internal agent health |
| 40 | **task_kernel_parts** | `scp/task_kernel_parts` | 2 | 1,966 | 1 | TaskKernel state machine implementation, OCC locks, leases |
| 41 | **tests** | `scp/tests` | 9 | 792 | 0 | Embedded internal test suites, chaos recovery tests |
| 42 | **web_control** | `scp/web_control` | 7 | 1,007 | 0 | Headless browser management (Playwright), DOM traversal |
| 43 | **world_state** | `scp/world_state` | 4 | 316 | 0 | External world state representation and entity grounding |
| - | **root files** | `scp/*.py` | 12 | 5,142 | 3 | Key entrypoints: `api_server.py`, `ask_kernel_adapter.py`, `task_kernel.py`, `kernel_storage_pg.py` |

---

## Requirements Domain Matrix (R1-R6)

| Domain | Scope | Findings Count | Critical Items |
|---|---|:---:|---|
| **R1: Silent Bugs & Logic Errors** | Swallowed exceptions, dead branches, type coercion, off-by-one, async/await misuse | 7 (2 CRIT, 2 HIGH, 2 MED, 1 LOW) | Stubbed Judge properties breaking 4 public APIs; Fake evidence replay |
| **R2: Security & Secret Handling** | Hardcoded secrets, leakage, auth bypass, egress gaps, SQL injection, path traversal, trace redaction | 8 (2 CRIT, 4 HIGH, 2 MED) | Public unredacted trace API; Redaction blind spots in `redact_attributes` |
| **R3: Architectural Integrity & Dead Code** | Orphaned files, unused functions, circular imports, god files, uncommitted trace files | 9 (1 CRIT, 3 HIGH, 4 MED, 1 INFO) | Untracked & unplugged trace stack with test bypass; 63 dead modules (>13k LOC) |
| **R4: Test Coverage & Test Quality** | Under-covered subsystems, trivial assertions, heavy mocking, external state, flaky tests | 7 (2 CRIT, 2 HIGH, 2 MED, 1 INFO) | 38 import-only test files; Fake chaos recovery test (`assert True`) |
| **R5: Runtime Correctness & Concurrency** | Race conditions, SQLite thread-safety, resource leaks, graceful shutdown, memory growth | 9 (3 CRIT, 4 HIGH, 2 MED) | `ChatMemoryStore` un-locked rewrite race; `TraceLedger` hash chain corruption; DB lock dropped before execution |
| **R6: Configuration & Deployment Consistency** | Env var drift, port conflicts, docker/compose, startup scripts, missing dependencies | 6 (1 CRIT, 3 HIGH, 1 MED, 1 LOW) | 84% env var drift (165 missing); Windows `start-scp.bat` omits LLM Bridge |

---

## Audit Workflow Milestones

| # | Milestone | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | **Survey & Inventory** | Map all 43 subsystems, files, LOC, and initial findings across R1-R6 | none | DONE |
| M2 | **Programmatic Verification** | Worker runs test collection, `t00_meta_audit.py`, and grep verifications | M1 | DONE |
| M3 | **Synthesis & Report Compilation** | Compile comprehensive audit report markdown with executive summary & Top 10 | M2 | DONE |
| M4 | **Review & Adversarial Challenge** | 2 Reviewers (APPROVE), 2 Challengers (CONFIRM), 1 Forensic Auditor (CLEAN) | M3 | DONE |
| M5 | **Final Delivery & Handoff** | Victory claim and final handoff submission to caller | M4 | IN_PROGRESS |
