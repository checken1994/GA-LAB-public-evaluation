# Dispatch: explorer_o6_survey_1

## Objective
Survey and map the exact technical state, file paths, line numbers, and dependencies for:
- **R1: Critical Security Chain**
  - Dashboard middleware fail-open & JWT auto-minting (`dashboard/src/middleware.ts`, `dashboard/src/app/ask/route.ts`)
  - Chatbot lane classification overriding governance KILL -> ALLOW (`scp/api/_ask_impl.py:646-648`, `scp/api/chat.py:501-502`)
  - JWT guard accepting static admin key as JWT (`scp/security/jwt_guard.py:37-42`)
  - Evaluation API default PASS & confidence (`scp/api/routes/evaluation_routes.py`)
  - Requirements for chain-break integration test.
- **R2: Runtime Wiring of Unwired Security Modules**
  - `scp/capabilities/tools.py` (bounded tool runner) vs `scp/runtime/engine_parts/hands_planner.py:486-495`
  - `scp/policy/egress.py` (fail-closed egress engine) vs `scp/llm_gateway/egress_policy.py` & `scp/security/url_safety.py`
  - `scp/core/autonomous_ledger.py` (cryptographic provenance with HMAC) vs executor execution paths (`hands_executor.py`, runtime, etc.)

## Scope Boundaries
- Read-only exploration. DO NOT modify any production or test files.
- Deliver verified evidence (file paths, exact lines, existing callers vs intended callers).

## Input Files
- `D:\scp\.agents\ORIGINAL_REQUEST.md` (read `## 2026-09-22T18:07:00Z` and Section 6)
- Target files in `dashboard/` and `scp/` cited above.

## Output
- Write your findings to `D:\scp\.agents\explorer_o6_survey_1\survey_report.md`
- Write `handoff.md` and send message to orchestrator_6 with summary.

## 2026-09-22T18:09:33Z

<USER_REQUEST>
You are explorer_o6_survey_1.
Your working directory is D:\scp\.agents\explorer_o6_survey_1.
Your parent orchestrator is orchestrator_6 (ID: d743754f-8fbb-42e5-ae1d-08ee4bb86635).
Project root is D:\scp.

Read your task assignment at D:\scp\.agents\explorer_o6_survey_1\DISPATCH.md.
Read the authoritative user request at D:\scp\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6).

Your mission is technical survey and mapping for:
1. R1: Critical Security Chain
   - dashboard/src/middleware.ts: lines 6-7 (fail-open)
   - dashboard/src/app/ask/route.ts: lines 15-34 (JWT auto-minting admin)
   - scp/api/_ask_impl.py:646-648 + scp/api/chat.py:501-502 (chatbot lane KILL override to ALLOW)
   - scp/security/jwt_guard.py:37-42 (static admin key accepted as JWT role admin)
   - scp/api/routes/evaluation_routes.py:211-212,226-233,86-88 (evaluation API default PASS and unvalidated confidence)
   - Requirements and approach for a chain-break integration test.
2. R2: Runtime Wiring of Unwired Security Modules
   - scp/capabilities/tools.py (bounded tool runner) vs current usage in scp/runtime/engine_parts/hands_planner.py:486-495 and execution path.
   - scp/policy/egress.py (fail-closed egress engine) vs scp/llm_gateway/egress_policy.py and scp/security/url_safety.py.
   - scp/core/autonomous_ledger.py (cryptographic provenance with HMAC) vs runtime executor callers (e.g. hands_executor or task kernel).

Deliverables:
- Maintain progress.md in your working directory.
- Write detailed survey report to D:\scp\.agents\explorer_o6_survey_1\survey_report.md.
- Write handoff.md in your working directory.
- Send message to parent orchestrator_6 with your executive summary when complete.
Do NOT modify production or test files. You are read-only explorer.
</USER_REQUEST>
