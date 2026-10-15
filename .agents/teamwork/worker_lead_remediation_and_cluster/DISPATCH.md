# DISPATCH: worker_lead_remediation_and_cluster

## Working Directory
`D:\scp\.agents\teamwork\worker_lead_remediation_and_cluster`

## Mandatory Instructions
MANDATORY: Read `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Inputs
1. `D:\scp\DEEP_AUDIT_REPORT_20260927.md`
2. `D:\scp\.agents\teamwork\explorer_m1_1\handoff.md`
3. `D:\scp\.agents\teamwork\explorer_m1_2\handoff.md`
4. `D:\scp\.agents\teamwork\explorer_m1_3\handoff.md`
5. `D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\handoff.md` (100% completed)
6. `D:\scp\.agents\teamwork\worker_m2_p1_boundary_gen2\handoff.md` (100% completed)

## Objectives & Step-by-Step Execution Plan

### Step 1: Complete Empty Pass Test Replacements & Write Core Handoff
1. Write `D:\scp\.agents\teamwork\worker_m1_core_gen2\handoff.md` documenting the already implemented and verified fixes for SEC-R1-01 (`pc_controller.py`), SEC-R1-02 (`tools.py`), and SEC-R3-01 / SEC-R3-02 (`taskkernel.py`) along with passing tests in `tests/T03_capability/test_sec_r1_remediation.py` and `tests/T04_kernel/test_sec_r3_remediation.py`.
2. Inspect the remaining empty `pass` tests across `tests/T02_contract/`, `tests/T03_capability/`, `tests/T11_release/` (specifically:
   - `tests/T11_release/test_rc_workflow_runtime_contract.py`
   - `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py`
   - `tests/T03_capability/test_flow_11_admin_import_scp_standard.py`
   - `tests/T03_capability/test_flow_14_reintegrated_systems_scp_standard.py`
   - `tests/T03_capability/test_flow_13_free_api_learning_scp_standard.py`
   - `tests/T03_capability/test_flow_08_audit_benchmark_scp_standard.py`
   - `tests/T03_capability/test_flow_09_threat_analysis_scp_standard.py`
   - `tests/T03_capability/test_flow_05_agent_call_scp_standard.py`
   - `tests/T03_capability/test_flow_07_autofix_scp_standard.py`
   - `tests/T03_capability/test_flow_04_control_hands_scp_standard.py`
   and any remaining placebo tests `test_flow_27` through `test_flow_33`).
   Replace all empty `pass` statements with genuine behavioral assertions (per `explorer_m1_3/handoff.md § 2.2`).
3. Verify that an AST scan confirms 0 empty `pass` tests and 0 placebo tests (`assert _AVAILABLE`) remain.

### Step 2: Milestone 3 — Independent Re-Audit Gate
Run the following verification commands and record exact stdout/stderr:
1. `pytest tests/ --collect-only -q` -> must have 0 collection errors.
2. `python tools/stale_code_tripwire.py` -> must return 0 drift / 0 broken imports.
3. `python tools/t00_meta_audit.py` -> must return 0 regressions vs baseline.
4. `pytest tests/integration/ -v` -> must pass contract & integration tests.

### Step 3: Milestone 4 — Live Cluster Launch & Full Operational Probing
1. Launch all 3 cluster services:
   - API Server on port 8000: `python -m uvicorn scp.api_server:app --port 8000` (or appropriate launch command)
   - Bun LLM Bridge on port 8081: `bun run mini-services/llm-bridge/index.ts` (or command in package.json/start script)
   - Dashboard Next.js on port 3000: `npm run dev` or `bun run dev` in `dashboard/`
2. Poll health endpoints to confirm HTTP 200 on ports 8000, 8081, 3000.
3. Execute automated operational probes:
   - Chat probe: send natural conversational query ("bạn là ai", "hôm nay thế nào") via API/chat -> verify intelligent response, verdict PASS, not withheld.
   - Retrieval probe: send factual query triggering retrieval & FactSeparator -> verify valid `trace_id`.
   - Trace probe: query `/v3/trace/{trace_id}` with admin token -> verify decision tree and HMAC audit ledger records.
   - Autonomous task probe: safe tool invocation, TaskKernel queue and lease heartbeat.
4. If any runtime exception, port collision, or error occurs, fix it immediately in the code and re-probe.
5. Clean Teardown:
   - Terminate all spawned server processes and child processes.
   - Verify with `Get-NetTCPConnection` or `netstat` that ports 8000, 8081, 3000 are completely released and no zombie processes remain.

### Step 4: Deliver Completion Report
Write `D:\scp\.agents\teamwork\worker_lead_remediation_and_cluster\handoff.md` with:
- Summary of all fixed findings (12 Critical + High P1)
- Re-audit gate test logs and outputs
- Live cluster probing logs (chat response, trace_id, /v3/trace payload)
- Port release verification output
- Notify parent orchestrator via `send_message`.
