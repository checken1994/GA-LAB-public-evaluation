# Master Execution Plan: SCP Remediation, Re-Audit & Live Operational Probing

## Scope: Autonomous Remediation of DEEP_AUDIT_REPORT_20260927.md

### Milestone 1: P0 Critical Vulnerabilities Remediation (12 Findings)
- [ ] M1.1: `SEC-R1-01` (`scp/pc_control/pc_controller.py:246-250`) — Remove self-attestation bypass `approved: True`, enforce HumanConfirmationStore verification.
- [ ] M1.2: `SEC-R1-02` (`scp/capabilities/tools.py:382-425`) — Add working directory bounds checking for `dir`/`ls`, tighten `SafeCommandRunnerTool` sandbox, block `python -c` dynamic execution.
- [ ] M1.3: `SEC-R2-01` (`scp/runtime/judge.py:305-325`) — Remove silent single-vendor fallback, mark `DEGRADED`/`UNCERTAIN`, eliminate fake 0.846 confidence.
- [ ] M1.4: `SEC-R2-02` (`scp/api_server_parts/_ask_impl.py:688-689` & `scp/api/chat.py`) — Remove `bypass_verdict_pass=True`, fail-closed on missing governance.
- [ ] M1.5: `SEC-R3-01` (`scp/task_kernel_parts/taskkernel.py:860-863`) — Check `cur.rowcount > 0` on `UPDATE leases` and `UPDATE queue_accounts`, raise `OptimisticLockError`, isolate transactions per expired lease.
- [ ] M1.6: `SEC-R3-02` (`scp/task_kernel_parts/taskkernel.py:820-850`) — Enforce `task['active_lease_id'] == lease['lease_id']` before lease reclaim.
- [ ] M1.7: `R4-F01` (`scp/knowledge/domain_knowledge.py:436-464`) — Rewrite `FactSeparator`: stopwords, min 3 content tokens, semantic entity constraints, eliminate 2-token tautology.
- [ ] M1.8: `R4-F03` (`scp/core/top_systems_learning.py:95-107`) — Normalize Cyrillic/Greek homoglyphs to Latin in Semantic Firewall before pattern matching.
- [ ] M1.9: `R4-F04` (`scp/rag/canonical_retriever.py:41-54`) — Fix missing corpus handling for `corpus_all_fetched.jsonl`, avoid silent empty success, provide transparent fallback.
- [ ] M1.10: `SEC-R6-01` & `SEC-R6-02` — Fix 4 broken imports in production code:
  - `scp/api_server_parts/admin_v100.py`
  - `scp/api_server_parts/v105_routes.py`
  - `scp/runtime/reverify_scheduler.py`
  - `scp/runtime/ask_kernel_adapter.py`
- [ ] M1.11: `SEC-R6-01` & `SEC-R6-02` — Replace 131 empty `pass` tests and 13 placebo tests (`assert _AVAILABLE`) with real behavior assertions.

### Milestone 2: P1 High Reliability & Boundary Vulnerabilities
- [ ] M2.1: `extractCallerAuth` in Dashboard Next.js — remove pseudo-auth, enforce real token check.
- [ ] M2.2: IP spoofing prevention in `dashboard/src/middleware.ts` — validate headers, prevent spoofed `X-Forwarded-For`/`X-Real-IP`, tighten private IP allowlist.
- [ ] M2.3: Bun microservice token protection (`mini-services/llm-bridge`) — enforce auth token on all bridge endpoints.
- [ ] M2.4: Egress Policy enforcement — verify `enforce_egress_policy()` on outbound network calls and browser sessions.

### Milestone 3: Re-Audit & Independent Verification Gate
- [ ] M3.1: Run `pytest tests/ --collect-only -q` -> 0 collection errors.
- [ ] M3.2: Run `python tools/t00_meta_audit.py` -> 0 new regressions.
- [ ] M3.3: Run `python tools/stale_code_tripwire.py` -> 0 broken imports or code drift.
- [ ] M3.4: Run `pytest tests/integration/ -v` -> 100% pass on contract and integration tests.

### Milestone 4: Live Cluster Launch & Full Operational Probing
- [ ] M4.1: Launch services: API Server (8000), Bun LLM Bridge (8081), Dashboard Next.js (3000).
- [ ] M4.2: Health checks on all three ports.
- [ ] M4.3: Automated live probing:
  - Conversational chat ("bạn là ai", "hôm nay thế nào") -> PASS verdict, not withheld.
  - Factual retrieval query -> triggers retriever & FactSeparator -> valid trace_id.
  - Admin trace inspection (`/v3/trace/{trace_id}`) -> inspect decision tree & audit ledger.
  - Autonomous task execution -> safe tool invocation, TaskKernel queue & lease heartbeat.
- [ ] M4.4: Fix any runtime exceptions or errors encountered during probing.
- [ ] M4.5: Clean Teardown: terminate all server processes, verify ports 8000, 8081, 3000 are completely released.
- [ ] M4.6: Synthesize final report and send victory message to Sentinel.
