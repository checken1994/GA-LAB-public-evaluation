# Dispatch for Reviewers (M2)

**Milestone**: M2 (Wire Security Modules into Production Runtime)
**Scope**: F07, F08 & F14, F09 implemented by `worker_m2_1`.

## Review Instructions
1. Review code modifications in:
   - `scp/capabilities/tools.py`
   - `scp/hands/action_registry.py`
   - `scp/security/autonomous_governor.py`
   - `scp/hands/hands_executor.py`
   - `scp/policy/egress.py`
   - `scp/security/url_safety.py`
   - `scp/llm_gateway/egress_policy.py`
   - `scp/web_control/playwright_backend.py`
   - `scp/security/egress_static_scan.py`
   - `scp/core/autonomous_ledger.py`
2. Verify production callers:
   - `grep -rn "from scp.capabilities.tools import" scp/`
   - `grep -rn "from scp.policy.egress import" scp/`
   - `grep -rn "from scp.core.autonomous_ledger import" scp/`
3. Run tests:
   - `pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v`
   - `pytest tests/ --collect-only -q`
4. Deliver verdict: APPROVE or REQUEST_CHANGES in `handoff.md`.

## 2026-09-22T20:15:29Z
You are reviewer_m2_1.
Your working directory is D:\scp\.agents\reviewer_m2_1.
You MUST read D:\scp\.agents\ORIGINAL_REQUEST.md before starting work.
Also read D:\scp\.agents\reviewer_m2_1\DISPATCH.md, D:\scp\.agents\orchestrator_7\PROJECT.md, and D:\scp\.agents\worker_m2_1\handoff.md.

Your mission:
Review Milestone M2 implementation (F07, F08 & F14, F09) by worker_m2_1.
Check code correctness, robustness, and verify tests pass.
Deliver verdict: APPROVE or REQUEST_CHANGES in D:\scp\.agents\reviewer_m2_1\handoff.md.
When complete, notify parent orchestrator via send_message.

