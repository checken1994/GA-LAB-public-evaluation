# DISPATCH: worker_m1_tests_gen2

## Mandatory Instructions
MANDATORY: Read `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Source of Truth
Read `D:\scp\.agents\teamwork\explorer_m1_3\handoff.md` Section 1.2 and Section 2.2, which maps out every single one of the 131 empty `pass` tests and 13 placebo tests (`assert _AVAILABLE`) and provides concrete behavioral replacement specifications.

## Assigned Scope & Exclusive File Ownership
You exclusively own and may edit ONLY the specified test files:
1. The 10 files containing the 131 empty `pass` tests:
   - `tests/T02_contract/test_forecast_scoring.py`
   - `tests/T02_contract/test_governance_rejection.py`
   - `tests/T02_contract/test_knowledge_domain_rules.py`
   - `tests/T02_contract/test_model_selection_engine.py`
   - `tests/T02_contract/test_recovery_circuit_breaker.py`
   - `tests/T02_contract/test_release_evidence_contract.py`
   - `tests/T02_contract/test_retrieval_fusion_engine.py`
   - `tests/T02_contract/test_semantic_firewall_contract.py`
   - `tests/T02_contract/test_task_kernel_concurrency.py`
   - `tests/T11_release/test_release_evidence_gate.py` (specifically line 131 `test_release_gate_placebo`)
2. The 13 files containing the 13 placebo tests (`assert _AVAILABLE`):
   - `tests/T03_capability/test_flow_01_*.py` through `tests/T03_capability/test_flow_13_*.py`

## Implementation Checklist
1. Replace all 131 empty `pass` test functions with genuine behavioral assertions:
   - Each test must instantiate the real subsystem class, execute real inputs, and assert realistic outputs or error states (e.g. valid threshold calculations in `forecast_scoring`, strict rejection states in `governance_rejection`, rule matches in `knowledge_domain_rules`, circuit breaker transitions in `recovery_circuit_breaker`, etc.).
   - Follow the detailed implementation specifications in `explorer_m1_3/handoff.md § 2.2`.
2. Replace all 13 placebo tests (`assert _AVAILABLE`) with real behavior tests:
   - Instead of checking `assert _AVAILABLE` or inspecting docstrings, execute the underlying module/engine methods and assert meaningful postconditions and return types.
3. Verify that NO empty `pass` tests or placebo assertions remain:
   - Run AST / grep checks to confirm 0 empty `pass` tests in T02, T03, T11.
   - Run `pytest tests/T02_contract/ tests/T03_capability/ tests/T11_release/ -v` to ensure 100% PASS with genuine execution.

Write `D:\scp\.agents\teamwork\worker_m1_tests_gen2\handoff.md` and report back to parent.
