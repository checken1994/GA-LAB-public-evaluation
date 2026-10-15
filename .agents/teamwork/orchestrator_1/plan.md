# SCP Deep Security & System Audit — Master Plan

## 1. Objective
Execute a comprehensive, strictly read-only, evidence-grounded security and system architecture audit of the entire SCP codebase (~221k Python LOC, 1,142 .py files, 43 subsystems, Next.js dashboard, Bun microservices).
Ground all findings in the 26 SCP DNA principles, Fail-Closed & Evidence-First, and Fail-Closed requirements.

## 2. Invariants & Rules
1. Pure Read-Only Audit: ZERO code changes, deletions, or test modifications.
2. Every finding MUST contain:
   - `file_path` (exact path)
   - `line_number(s)` (exact lines)
   - `code snippet` (verbatim from codebase)
   - `severity` (CRITICAL, HIGH, MEDIUM, LOW, INFO)
   - `concrete risk / exploit / failure scenario`
   - `SCP DNA violation / principle reference`
3. Zero tolerance for unverified assumptions, hallucinated line numbers, or speculative claims.

## 3. Scope Decomposition (R1 - R6)

### Stream R1: Security Boundaries, Auth & Secret Handling
- Auth headers & JWT token validation (`scp/security/jwt_guard.py`, etc.).
- Static API key role segregation (`admin` vs `user`).
- Next.js dashboard middleware IP verification & spoofing resistance (`X-Forwarded-For`, `X-Real-IP`).
- SSRF & Egress Policy enforcement across Python backend, BrowserSession, and Next.js API routes (`scp/policy/egress.py`, `scp/security/url_safety.py`).
- `SafeCommandRunnerTool` (`cmd.run`) & `HumanConfirmationStore` for risk level >= 3.
- Secret leakage in logging, exceptions, chat memory store, and trace payloads (`redact_attributes`, `trace_contract.py`).

### Stream R2: Core Logic, RealityJudge & LLM Gateway
- RealityJudge arbitration & consensus logic (`scp/runtime/judge.py`, etc.).
- Multi-LLM crosscheck, crash fallback, timeout handling.
- `_calibrate_confidence()` mathematical / calibration soundness.
- Chatbot lane (`scp/api/_ask_impl.py`, `chat.py`), question router (`question_router.py`).
- Governance `KILL` verdict propagation (ensuring no override to `ALLOW`).
- LLM Gateway routing and verification of clean dead-code removal (no remnant zero-cost code).

### Stream R3: TaskKernel Architecture, Concurrency & Data Integrity
- TaskKernel state machine transitions and invariants (`scp/task_kernel/taskkernel.py`).
- Lease management & `expire_leases` OCC rowcount validation (`rowcount > 0`, `OptimisticLockError`).
- SQLite file locking, WAL mode, transaction isolation, connection sharing & thread safety.
- Append-only ledger integrity (.jsonl files, concurrent append guards).
- HMAC audit ledger: hash chain immutability and domain-separated keys (`autonomous_ledger.py`, `trace_store.py`).

### Stream R4: Knowledge, Fact Separation & RAG
- `FactSeparator` algorithm logic and correctness (`domain_knowledge.py`).
- Semantic Firewall robustness against invisible characters, homoglyphs, zero-width spaces (`top_systems_learning.py`).
- Retrieval pipeline & canonical corpus validation of RAG.

### Stream R5: Dashboard Frontend & Microservices
- Next.js API routes (`dashboard/src/app/api/scp/**/*.ts`) — no unsolicited internal token injection when client lacks credentials.
- Bun microservices (`mini-services/llm-bridge`) — token endpoint security, authentication, and boundary controls.
- Loop scheduler and background microservices integration security.

### Stream R6: Test Suite Quality, Static Tools & Tripwire
- Execution and analysis of static tools: `python tools/t00_meta_audit.py` and `python tools/stale_code_tripwire.py`.
- Deep review of test suites T00 through T12 for placebo assertions (`assert True`, hollow mocks, pass!=true illusions).
- Assessment of test coverage gaps across all 43 subsystems.

### Synthesis & Reporting Stream
- Aggregate, cross-verify, and format findings into `D:\scp\DEEP_AUDIT_REPORT_20260927.md`.
- Generate executive summary, severity matrix, top 10 critical vulnerabilities, and remediation recommendations.
- Produce orchestrator handoff.

## 4. Execution Phases & Milestones
- Phase 1: Planning, State Tracking & Heartbeat Setup [Current]
- Phase 2: Parallel Explorers & Static Worker Dispatch (R1-R6)
- Phase 3: Result Collection, Cross-Review & Reality-Verification
- Phase 4: Final Report Compilation (`DEEP_AUDIT_REPORT_20260927.md`) & Handoff
