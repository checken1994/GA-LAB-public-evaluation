# Dispatch: challenger_o6_m1_2

## Role
Adversarial Challenger for Governance KILL & Evaluation API Fail-Closed (Milestone M1).

## Working Directory
`D:\scp\.agents\challenger_o6_m1_2`

## Inputs
- `D:\scp\.agents\ORIGINAL_REQUEST.md` (specifically `## 2026-09-22T18:07:00Z` and Section 6)
- `D:\scp\.agents\orchestrator_6\PROJECT.md`
- `D:\scp\.agents\worker_o6_m1\handoff.md`

## Mission
Adversarially challenge governance KILL enforcement and Evaluation API fail-closed behavior:
1. Verify that NO prompt, lane classification (`LANE_CHATBOT`, `LANE_SYSTEM`, etc.), or parameter combination can override governance KILL to ALLOW or force PASS in `scp/api_server_parts/_ask_impl.py` and `scp/api/chat.py`.
2. Test `/v1/eval` and `/v1/systemone` in `scp/api/routes/evaluation_routes.py` with malformed inputs, prompt injection attempts (e.g. attempting to escape `<state_to_evaluate>`), simulated gateway crashes, and extreme confidence values (NaN, negative, > 1.0). Verify fail-closed defaults and strict [0.0, 1.0] clamping.
3. Run tests:
   - `pytest tests/integration/test_critical_chain_severed.py -v`
4. Report verdict: **APPROVE** (if invariants hold) or **REQUEST_CHANGES** (with reproducible attack evidence).

## 2026-09-22T19:00:51Z
You are challenger_o6_m1_2.
Your working directory is D:\scp\.agents\challenger_o6_m1_2.
Your parent orchestrator is orchestrator_6 (conversation ID: d743754f-8fbb-42e5-ae1d-08ee4bb86635).
Project root is D:\scp.

Read your task instructions at D:\scp\.agents\challenger_o6_m1_2\DISPATCH.md.
Read the authoritative user request at D:\scp\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6).
Read worker_o6_m1 handoff report at D:\scp\.agents\worker_o6_m1\handoff.md.

Adversarially challenge governance KILL enforcement and Evaluation API fail-closed behavior:
1. Stress test scp/api_server_parts/_ask_impl.py and scp/api/chat.py to verify that NO lane or prompt permutation can ever override a KILL decision to ALLOW or force PASS.
2. Stress test scp/api/routes/evaluation_routes.py with extreme confidence values, malformed inputs, prompt escaping, and verify strict [0.0, 1.0] clamping and fail-closed verdict UNKNOWN.
3. Run pytest tests/integration/test_critical_chain_severed.py -v.

Deliver your report in handoff.md with a clear verdict: APPROVE or REQUEST_CHANGES.
Send message to orchestrator_6 with your verdict.
