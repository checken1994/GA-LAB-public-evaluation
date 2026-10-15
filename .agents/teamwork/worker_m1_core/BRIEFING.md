# BRIEFING — 2026-09-27T15:40:00Z

## Mission
Implement security fixes SEC-R1-01, SEC-R1-02, SEC-R3-01, SEC-R3-02 in PCController, SafeCommandRunnerTool, and TaskKernel.

## 🔒 My Identity
- Archetype: worker_m1_core
- Roles: implementer, qa, specialist
- Working directory: D:\scp\.agents\teamwork\worker_m1_core
- Original parent: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Milestone: M1 Core Security & Concurrency Fixes

## 🔒 Key Constraints
- Own and edit ONLY:
  1. scp/pc_control/pc_controller.py
  2. scp/api/routes/pc_controller_routes.py
  3. scp/capabilities/tools.py
  4. scp/task_kernel_parts/taskkernel.py
  5. Tests for these components in tests/
- Genuine implementations only (no hardcoding, no facades, real behavior).
- Pass all unit tests: `pytest tests/T03_capability/test_tools.py tests/T04_kernel/ -v`

## Current Parent
- Conversation ID: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Updated: 2026-09-27T15:40:00Z

## Task Summary
- **What to build**:
  - SEC-R1-01: PCController HumanConfirmationStore integration for WORKSPACE/RESTRICTED levels, confirmation_id validation, reject self-attestation without store confirmation, update routes.
  - SEC-R1-02: SafeCommandRunnerTool path traversal prevention for dir/ls bounds checking, remove python -c from WORKSPACE_ALLOWLIST.
  - SEC-R3-01: TaskKernel expire_leases optimistic locking with rowcount verification and isolated per-lease transactions.
  - SEC-R3-02: TaskKernel expire_leases check active_lease_id before clearing/reverting task state.
- **Success criteria**: All targeted unit tests pass, no regressions, strict security adherence.
- **Interface contracts**: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md & explorer_m1_1\handoff.md
- **Code layout**: D:\scp

## Change Tracker
- **Files modified**: [TBD]
- **Build status**: [TBD]
- **Pending issues**: None

## Quality Status
- **Build/test result**: [TBD]
- **Lint status**: clean
- **Tests added/modified**: [TBD]

## Key Decisions Made
- Follow explorer_m1_1/handoff.md AST analysis and specification.

## Artifact Index
- D:\scp\.agents\teamwork\worker_m1_core\BRIEFING.md
- D:\scp\.agents\teamwork\worker_m1_core\DISPATCH.md
- D:\scp\.agents\teamwork\worker_m1_core\progress.md
- D:\scp\.agents\teamwork\worker_m1_core\handoff.md
