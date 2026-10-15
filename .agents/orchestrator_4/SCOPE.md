# SCOPE: Next-Stage Development & Verification Cycle (2026-09-22T12:50:00Z)

## Architecture & Integration Boundaries
- **Cluster E2E Boot & Shutdown (Goal 1)**:
  - Port 8000: SCP FastAPI / Uvicorn Server (`scp/api_server.py`, `scp/__main__.py`)
  - Port 8081: LLM Bridge Microservice (`mini-services/llm-bridge/`)
  - Port 3000: Web Dashboard Next.js (`dashboard/`)
  - Launcher & Stop scripts: `scripts/ops/start_scp_silent.ps1`, `stop-scp.bat`, `stop-scp.sh`
  - Automated Verifier: `tools/e2e_live_cluster_verifier.py`, `tests/T01_boot/test_live_cluster_e2e.py`
  - Unit contract: `tests/T01_boot/test_startup_launcher_contract.py`

- **Subsystem Functional & Concurrency Stress (Goal 2)**:
  - Epistemic Engine: `tests/test_epistemic_functional.py` (14 tests)
  - TaskKernel: `tests/test_task_kernel_stress.py` (10 tests)
  - Self-Model: `tests/test_self_model_behavioral.py` (8 tests)
  - Observability: `tests/test_observability_functional.py` (8 tests)
  - Concurrency Stress: `tests/test_concurrency_stress_v2.py` (8 tests)
  - Baseline: 2,049 tests -> Expected: 2,097+ tests, 0 collection errors, 0 meta-audit regressions

- **Agent OS Autonomous Tooling & Cryptographic Provenance (Goal 3)**:
  - Egress Policy PEP: `scp/policy/egress.py`
  - Bounded Tools: `scp/capabilities/tools.py` (`SystemInspectionTool`, `WorkspaceAnalysisTool`, `SafeCommandRunnerTool`)
  - Provenance Ledger: `scp/core/autonomous_ledger.py` (`AutonomousAuditLedger` with two-phase commit into `TraceLedger`)
  - Tests: `tests/T03_capability/test_autonomous_tool_contracts.py`, `tests/T03_capability/test_egress_policy_unified.py`, `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py`

## Work Allocation & Exclusive File Ownership

### Worker 1 (`worker_o4_1`): Agent OS Autonomous Tooling & Cryptographic Provenance
- **Exclusive Files Owned**:
  - `scp/policy/egress.py`
  - `scp/capabilities/tools.py`
  - `scp/core/autonomous_ledger.py`
  - `tests/T03_capability/test_autonomous_tool_contracts.py`
  - `tests/T03_capability/test_egress_policy_unified.py`
  - `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py`

### Worker 2 (`worker_o4_2`): Subsystem Functional & Concurrency Stress Test Suites
- **Exclusive Files Owned**:
  - `tests/test_epistemic_functional.py`
  - `tests/test_task_kernel_stress.py`
  - `tests/test_self_model_behavioral.py`
  - `tests/test_observability_functional.py`
  - `tests/test_concurrency_stress_v2.py`

### Worker 3 (`worker_o4_3`): Live Cluster Boot, Verification & Clean Process Shutdown
- **Exclusive Files Owned**:
  - `scripts/ops/start_scp_silent.ps1`
  - `stop-scp.bat`
  - `stop-scp.sh`
  - `mini-services/llm-bridge/core.ts`
  - `dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts`
  - `tests/T01_boot/test_startup_launcher_contract.py`
  - `tools/e2e_live_cluster_verifier.py`
  - `tests/T01_boot/test_live_cluster_e2e.py`
