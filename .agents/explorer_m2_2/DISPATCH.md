# Dispatch for explorer_m2_2

**Milestone**: M2 (Wire Security Modules into Production Runtime)
**Focus**: Feature F08 (and interaction with F14) — Wiring `EgressPolicy` (`scp/policy/egress.py`) into production runtime via `url_safety.py` and network callers.

## Investigation Scope
1. Inspect `scp/policy/egress.py` to understand `EgressPolicy` API, rules, and dev-default open behavior.
2. Inspect `scp/security/url_safety.py` and see how it currently validates URLs and where `EgressPolicy` should be delegated to.
3. Inspect `scp/llm_gateway/egress_policy.py` and identify all callers across runtime (BrowserSession, API server, LLM clients, external data sources).
4. Identify how to ensure `from scp.policy.egress import EgressPolicy` (or relevant functions) has active production callers in `scp/` without breaking existing valid network requests.
5. Check F14 requirements: removing dev-default OPEN in `egress.py` & `url_safety.py` and eliminating TOCTOU DNS window.
6. Identify affected test suites and recommend a concrete implementation strategy and test verification commands.

## Required Output
Write your findings to `D:\scp\.agents\explorer_m2_2\handoff.md`.
Follow the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).

## 2026-09-22T19:48:14Z
Task received:
Investigate Feature F08 (and F14 interaction) of Milestone M2:
- Wiring EgressPolicy (scp/policy/egress.py) into production runtime: delegate url_safety.py calls to EgressPolicy.enforce across all runtime network callers.
- Investigate scp/llm_gateway/egress_policy.py vs scp/policy/egress.py, BrowserSession callers, API server callers, etc.
- Investigate F14 requirements: eliminating dev-default OPEN in egress.py & url_safety.py, and eliminating TOCTOU DNS window.
- Ensure grep -rn "from scp.policy.egress import" will find genuine production callers (not in tests/).
- Determine impact on existing test suites, edge cases, and define the exact fix strategy and verification commands.
Write findings to D:\scp\.agents\explorer_m2_2\handoff.md following Handoff Protocol. Notify parent orchestrator via send_message.
