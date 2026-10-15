# DISPATCH: explorer_m1_1

## Objective
Investigate and produce comprehensive remediation specifications for Stream R1 (Security & Tools) and Stream R3 (TaskKernel & Concurrency) critical vulnerabilities:
1. `SEC-R1-01`: `scp/pc_control/pc_controller.py:246-250` — Eliminate caller self-attestation bypass `approved: True`; mandate verification against `HumanConfirmationStore`.
2. `SEC-R1-02`: `scp/capabilities/tools.py:382-425` — Add working directory bounds checking for `dir`/`ls`; tighten `SafeCommandRunnerTool` sandbox; block `python -c` dynamic execution.
3. `SEC-R3-01`: `scp/task_kernel_parts/taskkernel.py:860-863` — Check `cur.rowcount > 0` on `UPDATE leases` and `UPDATE queue_accounts`; raise `OptimisticLockError`; isolate transactions per expired lease to prevent single conflict from rolling back entire sweep.
4. `SEC-R3-02`: `scp/task_kernel_parts/taskkernel.py:820-850` — Enforce `task['active_lease_id'] == lease['lease_id']` before lease reclaim.

## Input References
- `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` (mandatory read)
- `D:\scp\DEEP_AUDIT_REPORT_20260927.md` (sections SEC-R1-01, SEC-R1-02, SEC-R3-01, SEC-R3-02)
- Target source files and corresponding test files in `tests/`

## Output Requirements
Write `D:\scp\.agents\teamwork\explorer_m1_1\handoff.md` with:
- Exact findings confirmed with file line numbers and AST/behavioral analysis
- Precise before/after implementation recommendations adhering to Fail-Closed & Evidence-First principles
- Regression prevention and test strategy (unit tests to verify fixes)
- Conclude with a clear verdict/summary for Worker.

## 2026-09-27T08:24:34Z
Investigate the following 4 critical vulnerabilities in D:\scp:
1. SEC-R1-01: scp/pc_control/pc_controller.py:246-250 (eliminate caller self-attestation bypass approved: True; mandate verification against HumanConfirmationStore).
2. SEC-R1-02: scp/capabilities/tools.py:382-425 (bounds check dir/ls, tighten SafeCommandRunnerTool sandbox, block python -c).
3. SEC-R3-01: scp/task_kernel_parts/taskkernel.py:860-863 (check cur.rowcount > 0, raise OptimisticLockError, isolate per-lease transactions).
4. SEC-R3-02: scp/task_kernel_parts/taskkernel.py:820-850 (check task['active_lease_id'] == lease['lease_id'] before reclaim).

You are READ-ONLY. DO NOT modify any code.
Inspect existing files, callers, tests, and produce D:\scp\.agents\teamwork\explorer_m1_1\handoff.md with:
- Concrete evidence and AST/code line analysis
- Exact before/after code replacement recommendation
- Regression prevention and verification test plan
Update progress.md in your working directory as you work. When done, call send_message to report completion.



## 2026-10-04T10:23:00Z

You are explorer_m1_1 (Pre-Boot Environment Explorer).
Your working directory is: D:\scp\.agents\teamwork\explorer_m1_1
You MUST read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md (specifically the section under ## 2026-10-04T10:18:44Z).

## Core Directives & Constraints:
1. PURE READ-ONLY MODE: Absolutely do NOT modify or delete any source code files (git status must remain 100% untouched).
2. Skip static unit tests (pytest tests/). Focus entirely on live cluster operational verification and runtime audit.
3. Target baseline commit: 1aef24a8 on branch main in D:\scp.

## Mission:
Investigate and verify the pre-boot environment in D:\scp:
1. Check git baseline: run `git rev-parse HEAD` (must be 1aef24a8), `git branch --show-current`, and `git status --short`. Document exact output.
2. Inspect ports 8000, 8081, 3000 using PowerShell: `Get-NetTCPConnection -LocalPort 8000, 8081, 3000 -ErrorAction SilentlyContinue`. Are any ports occupied? If so, identify the process IDs.
3. Inspect service boot architecture:
   - FastAPI API Server: entry point in `scp/` or root, virtual environment python path, uvicorn startup command, health endpoints (`/health`, `/ready`, `/status`, `/v3/status`), auth tokens (admin token in .env or settings).
   - Bun LLM Bridge: directory (e.g. `mini-services/llm-bridge/`), bun executable path, package.json scripts, startup command for port 8081, token authorization mechanism.
   - Next.js Dashboard: directory (`dashboard/`), node/npm executable path, package.json scripts, build status (.next exists?), startup command for port 3000.
   - Existing probe & ops scripts: inspect `tools/cluster_operational_prober.py`, `tools/adversarial_goal3_probe.py`, `scripts/ops/`, etc.
4. Synthesize concrete operational instructions for booting the 3 services in background, probing health endpoints, and performing clean teardown.

Write your report to `D:\scp\.agents\teamwork\explorer_m1_1\handoff.md` and send a message back with your findings.
