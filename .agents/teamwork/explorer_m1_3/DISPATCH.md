# DISPATCH: explorer_m1_3

## Objective
Investigate and produce comprehensive remediation specifications for Stream R6 (Test Suite Quality & Broken Production Imports) and boundary findings:
1. 4 broken imports in production code:
   - `scp/api_server_parts/admin_v100.py`
   - `scp/api_server_parts/v105_routes.py`
   - `scp/runtime/reverify_scheduler.py`
   - `scp/runtime/ask_kernel_adapter.py`
2. 131 empty `pass` tests and 13 placebo tests (`assert _AVAILABLE`) across `tests/T02_contract/`, `tests/T03_capability/`, `tests/T08_runtime/` (finding SEC-R6-01 & SEC-R6-02 in DEEP_AUDIT_REPORT_20260927.md).
3. P1 Boundary & Reliability items:
   - `extractCallerAuth` in Dashboard Next.js pseudo-auth
   - IP spoofing in `dashboard/src/middleware.ts` (`X-Forwarded-For`, `X-Real-IP`, private IP allowlist)
   - Bun LLM bridge token protection (`mini-services/llm-bridge`)
   - `enforce_egress_policy()` on network calls & browser sessions

## Input References
- `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` (mandatory read)
- `D:\scp\DEEP_AUDIT_REPORT_20260927.md` (sections SEC-R6-01, SEC-R6-02, and P1 findings)
- Target source files and corresponding test files in `tests/`

## Output Requirements
Write `D:\scp\.agents\teamwork\explorer_m1_3\handoff.md` with:
- Exact broken imports and why they fail
- List of the 131 empty `pass` test functions and 13 placebo tests with exact file paths and names
- Replacement strategy for each test to make it an active, rigorous behavioral test
- Recommendations for P1 boundary and middleware fixes
- Conclude with a clear verdict/summary for Worker.

## 2026-09-27T08:24:34Z
You are explorer_m1_3. Your working directory is D:\scp\.agents\teamwork\explorer_m1_3.
MANDATORY: Read D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md and D:\scp\.agents\teamwork\explorer_m1_3\DISPATCH.md before starting work.
Refer to D:\scp\DEEP_AUDIT_REPORT_20260927.md for findings SEC-R6-01, SEC-R6-02, and P1 findings.

Investigate the following items in D:\scp:
1. 4 broken imports in production code:
   - scp/api_server_parts/admin_v100.py
   - scp/api_server_parts/v105_routes.py
   - scp/runtime/reverify_scheduler.py
   - scp/runtime/ask_kernel_adapter.py
2. 131 empty `pass` tests and 13 placebo tests (`assert _AVAILABLE`) across tests/T02_contract/, tests/T03_capability/, tests/T08_runtime/. Locate all of them and specify how to replace them with real behavioral assertions.
3. P1 boundary items: extractCallerAuth in dashboard, IP spoofing in dashboard/src/middleware.ts, Bun LLM bridge token protection (mini-services/llm-bridge), and enforce_egress_policy() enforcement.

You are READ-ONLY. DO NOT modify any code.
Inspect existing files, callers, tests, and produce D:\scp\.agents\teamwork\explorer_m1_3\handoff.md with:
- Exact broken import analysis and fix instructions
- Exhaustive list of empty/placebo tests and concrete replacement implementations
- Concrete guidance for P1 fixes
Update progress.md in your working directory as you work. When done, call send_message to report completion.
