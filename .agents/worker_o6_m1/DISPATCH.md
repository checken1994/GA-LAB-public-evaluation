# Dispatch: worker_o6_m1

## Role
Implementation Worker for Milestone M1: Sever Critical Security Chain (R1: F01 - F06).

## Working Directory
`D:\scp\.agents\worker_o6_m1`

## Mandatory Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Authoritative Inputs
- `D:\scp\.agents\ORIGINAL_REQUEST.md` (specifically `## 2026-09-22T18:07:00Z` and Section 6)
- `D:\scp\.agents\orchestrator_6\PROJECT.md`
- `D:\scp\.agents\explorer_o6_survey_1\survey_report.md` (read Section 1 for exact line-by-line fix specifications and Section 1.6 for integration test specs)
- `D:\scp\.agents\spec_miner_o6_survey_3\spec_report.md` (read Section 4 for chain-break integration test specifications)

## Exclusive File Ownership
You exclusively own and may edit the following files:
1. `dashboard/src/middleware.ts`
2. `dashboard/src/app/api/scp/ask/route.ts`
3. `scp/api_server_parts/_ask_impl.py`
4. `scp/api/chat.py`
5. `scp/security/jwt_guard.py`
6. `scp/api/routes/evaluation_routes.py`
7. `tests/integration/test_critical_chain_severed.py` (new test file)

DO NOT modify any other files.

## Technical Specifications to Implement
1. **F01: Dashboard Middleware Fail-Open Fix (`dashboard/src/middleware.ts:6-7`)**:
   - Do NOT default `clientIp` to `"127.0.0.1"` when headers are missing.
   - If missing `x-forwarded-for` or `x-real-ip`, return 403 Forbidden.
   - Use strict IP matching rather than loose `.includes("127.0.0.1")`.

2. **F02: Dashboard Ask Route Auto-Minting Removal (`dashboard/src/app/api/scp/ask/route.ts:15-35, 60-70`)**:
   - Completely remove the automatic JWT admin minting `createJwt(secret, { sub: "admin" })` for unauthenticated callers.
   - Require authentication: inspect the incoming request for authorization (e.g. `Authorization` header with bearer token or session cookie). Forward the caller's token to the backend, or reject with 401 Unauthorized if unauthenticated.

3. **F03: Chatbot Lane KILL Override to ALLOW Removal (`scp/api_server_parts/_ask_impl.py:548-555, 645-648` & `scp/api/chat.py:497-503`)**:
   - In `_ask_impl.py:549`: Remove `and not _is_chatbot_lane`. A KILL decision from governance MUST trigger security rejection for ALL lanes without exception.
   - In `_ask_impl.py:645-648`: REMOVE the override that rewrites `_gov_decision = 'ALLOW'` and `v.verdict = 'PASS'` when `_is_chatbot_lane`. If `_gov_decision == 'KILL'`, raise `HTTPException(status_code=403, detail="Governance KILL enforced")` or appropriate security violation.
   - In `scp/api/chat.py:497-503`: REMOVE lines forcing `v.verdict = "PASS"` when `_is_chatbot_lane` if governance flagged a violation. Governance KILL must terminate execution.

4. **F04: JWT Guard Static Key Separation (`scp/security/jwt_guard.py:37-43`)**:
   - In `verify_jwt_token(token)`: Remove the loop checking `SCP_API_KEY`, `SCP_ADMIN_KEY`, and `SCP_AUTH_TOKEN_SECRET` as valid JWT tokens.
   - `verify_jwt_token` must ONLY accept cryptographically signed JWT strings (`header.payload.signature`) decoded and verified with the configured secret and algorithm.
   - If static API keys need verification, provide a dedicated separate function `verify_api_key(key: str) -> dict` and do NOT allow static keys to pass as JWTs.

5. **F05: Evaluation API Fail-Closed Defaults & Confidence Clamping (`scp/api/routes/evaluation_routes.py:86-88, 211-212, 226-233`)**:
   - In lines 211-212, on exception/timeout, default to `verdict = "UNCERTAIN"` (or `"FAIL"`) and `confidence = 0.0`. NEVER default to `PASS`.
   - In lines 226-233, validate that `verdict` is in `{"PASS", "FAIL", "UNCERTAIN"}`. If unrecognized, fail-closed to `"UNCERTAIN"`.
   - Strictly clamp `confidence` float to `[0.0, 1.0]`.
   - Prevent prompt delimiter escaping in prompt templates.

6. **F06: Chain-Break Integration Test Suite (`tests/integration/test_critical_chain_severed.py`)**:
   - Implement comprehensive tests covering each severed link:
     - `test_dashboard_middleware_rejects_missing_ip_headers()`: unauthenticated request without local IP header receives 403.
     - `test_dashboard_ask_route_rejects_unauthenticated_request()`: request without caller credentials returns 401, does not mint admin JWT.
     - `test_jwt_guard_rejects_static_admin_key_as_jwt()`: passing `SCP_ADMIN_KEY` to `verify_jwt_token` raises `HTTPException` / invalid token, does not grant admin.
     - `test_chatbot_lane_governance_kill_is_not_overridden()`: a prompt classified as chatbot lane that triggers governance KILL results in 403 / rejection, not ALLOW or PASS.
     - `test_evaluation_api_fails_closed_on_gateway_error()`: evaluation API returns UNCERTAIN / confidence 0.0 on error, never default PASS.
     - `test_critical_security_chain_end_to_end_severed()`: full chain test demonstrating an unauthenticated attacker cannot reach administrative / allowed execution.

## Verification Requirements
You must execute:
1. `pytest tests/integration/test_critical_chain_severed.py -v` (all tests pass)
2. `pytest tests/T02_contract/ tests/T05_gateway/ tests/T12_unified_chatbot/ -q` (regression check)
3. `pytest tests/ --collect-only -q` (0 collection errors)
Include all command lines and actual stdout/stderr in your handoff report.

## Deliverables
- `progress.md` with timestamps and task progress
- `handoff.md` with Observation, Logic Chain, Caveats, Conclusion, Verification Method
- Message to orchestrator_6 when finished.

## 2026-09-22T18:21:12Z
You are worker_o6_m1.
Your working directory is D:\scp\.agents\worker_o6_m1.
Your parent orchestrator is orchestrator_6 (conversation ID: d743754f-8fbb-42e5-ae1d-08ee4bb86635).
Project root is D:\scp.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Read your full task instructions at D:\scp\.agents\worker_o6_m1\DISPATCH.md.
Read the authoritative user request at D:\scp\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6).
Read the technical survey report at D:\scp\.agents\explorer_o6_survey_1\survey_report.md (Section 1 and 1.6).
Read the spec report at D:\scp\.agents\spec_miner_o6_survey_3\spec_report.md (Section 4).

Your exclusive file ownership:
1. dashboard/src/middleware.ts
2. dashboard/src/app/api/scp/ask/route.ts
3. scp/api_server_parts/_ask_impl.py
4. scp/api/chat.py
5. scp/security/jwt_guard.py
6. scp/api/routes/evaluation_routes.py
7. tests/integration/test_critical_chain_severed.py (create this new test file)

Your mission is to implement all 6 items of Milestone M1 (Sever Critical Security Chain):
- F01: Dashboard middleware fail-open IP fix (reject missing IP headers with 403, strict check).
- F02: Dashboard ask route JWT admin auto-minting removal (reject unauthenticated callers with 401, forward caller credentials).
- F03: Chatbot lane KILL override to ALLOW removal in _ask_impl.py and chat.py (governance KILL terminates with 403 / violation, no override to ALLOW/PASS).
- F04: JWT guard static key separation from JWT decoding in jwt_guard.py (verify_jwt_token rejects non-JWT static keys with 401/InvalidTokenError; separate verify_api_key helper).
- F05: Evaluation API fail-closed defaults (default to UNCERTAIN/0.0 on error/timeout, validate verdict against {"PASS", "FAIL", "UNCERTAIN"}, strictly clamp confidence to [0.0, 1.0]).
- F06: Create tests/integration/test_critical_chain_severed.py and implement comprehensive integration tests proving the critical chain is completely severed at every link.

Verification Requirements:
Run:
1. pytest tests/integration/test_critical_chain_severed.py -v
2. pytest tests/T02_contract/ tests/T05_gateway/ tests/T12_unified_chatbot/ -q
3. pytest tests/ --collect-only -q
Include exact commands and output in your handoff report.

Deliverables:
- Maintain progress.md in your working directory.
- Deliver handoff.md with Observation, Logic Chain, Caveats, Conclusion, Verification Method.
- Send message to parent orchestrator_6 with your completion summary.
