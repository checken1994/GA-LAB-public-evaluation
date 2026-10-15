# DISPATCH: worker_m1_core_gen2

## Mandatory Instructions
MANDATORY: Read `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Source of Truth
Read `D:\scp\.agents\teamwork\explorer_m1_1\handoff.md` which contains complete AST analysis, line numbers, and exact before/after code blocks.

## Assigned Scope & Exclusive File Ownership
You exclusively own and may edit ONLY the following files:
1. `scp/pc_control/pc_controller.py`
2. `scp/api/routes/pc_controller_routes.py`
3. `scp/capabilities/tools.py`
4. `scp/task_kernel_parts/taskkernel.py`
5. New or updated unit tests for these modules in `tests/` (e.g. `tests/unit/test_pc_controller_security.py`, `tests/T03_capability/test_tools.py`, `tests/T04_kernel/test_taskkernel.py`).

## Implementation Checklist
1. **SEC-R1-01** (`scp/pc_control/pc_controller.py`):
   - In `PCController.__init__`, inject `human_store: HumanConfirmationStore | None = None` (fallback to singleton `get_human_confirmation_store()`).
   - In `evaluate(command, capability_level, approved, confirmation_id=None)`:
     For `capability_level >= CapabilityLevel.WORKSPACE` (level 3):
     Validate `self.human_store.is_confirmed("pc.execute", command, confirmation_id)`.
     If not confirmed, return `PolicyDecision(False, "Explicit human confirmation required via HumanConfirmationStore", "critical", True, int(level))`.
     Self-attestation `approved=True` without valid store confirmation MUST return `PolicyDecision(False, ...)`.
   - Update `execute()`, `write_file()`, `rollback_action()` to require and verify `confirmation_id` with `HumanConfirmationStore`.
   - In `scp/api/routes/pc_controller_routes.py`, accept `confirmation_id: str | None = None` and remove any automatic trust of caller `approved: True`.

2. **SEC-R1-02** (`scp/capabilities/tools.py`):
   - In `SafeCommandRunnerTool._execute_command()`:
     Add `_validate_dir_ls_bounds(cmd, working_dir)`: canonicalize paths in `dir`/`ls` targets, ensure they reside strictly within `working_dir`, and explicitly block sensitive targets (`/etc`, `C:\Windows`, `.ssh`, `.env`, `credentials`, `..` escapes).
   - In `WORKSPACE_ALLOWLIST`:
     Completely remove `r"^python\s+-c\s+.*"` and strictly block `python -c` execution to prevent arbitrary code execution bypassing regex filters via reflection/importlib.

3. **SEC-R3-01** (`scp/task_kernel_parts/taskkernel.py`):
   - In `expire_leases()`:
     Verify `cur.rowcount > 0` after every `UPDATE leases` and `UPDATE queue_accounts`.
     Raise `OptimisticLockError` if `cur.rowcount == 0` on an expected row update.
     Isolate transaction per expired lease (or catch `OptimisticLockError` per lease) so a single concurrent collision does not roll back the entire sweep or starve the watchdog.

4. **SEC-R3-02** (`scp/task_kernel_parts/taskkernel.py`):
   - In `expire_leases()`:
     Before clearing `active_lease_id` or setting task status to `RECOVERING`, verify that `task["active_lease_id"] == lease["lease_id"]`.
     If the task has already been acquired by a new worker under a different lease, do NOT clear `active_lease_id` or revert task state.

## Verification
Run unit tests for PCController, tools, and taskkernel:
`pytest tests/T03_capability/test_tools.py tests/T04_kernel/ -v`
Write `D:\scp\.agents\teamwork\worker_m1_core_gen2\handoff.md` detailing changes, before/after diffs, and test results.
Send message to parent when completed.

## 2026-09-27T11:01:00Z
You are worker_m1_core_gen2. Your working directory is D:\scp\.agents\teamwork\worker_m1_core_gen2.
MANDATORY: Read D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md and D:\scp\.agents\teamwork\worker_m1_core_gen2\DISPATCH.md before starting work.
Read D:\scp\.agents\teamwork\explorer_m1_1\handoff.md for exact AST analysis and code replacement specifications.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You own and may edit ONLY:
1. scp/pc_control/pc_controller.py
2. scp/api/routes/pc_controller_routes.py
3. scp/capabilities/tools.py
4. scp/task_kernel_parts/taskkernel.py
5. Tests for these components in tests/

Implement the fixes for SEC-R1-01, SEC-R1-02, SEC-R3-01, SEC-R3-02 as specified.
Run unit tests to verify:
`pytest tests/T03_capability/test_tools.py tests/T04_kernel/ -v`
Write your completion report to D:\scp\.agents\teamwork\worker_m1_core_gen2\handoff.md with passing test results and layout compliance.
Update progress.md in your directory as you work. When done, call send_message to report completion.

