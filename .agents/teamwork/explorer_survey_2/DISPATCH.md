# DISPATCH — explorer_survey_2

## Identity
- Role: Explorer (Codebase & Architecture Investigator)
- Type: teamwork_preview_explorer
- Working Directory: D:\scp\.agents\teamwork\explorer_survey_2
- Parent: orchestrator_4 (conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff)

## Mandatory Constraints & Bindings
MANDATORY BINDING: You are strictly bound by Fail-Closed & Evidence-First principles. You MUST adhere to FA-01 through FA-13 (defined in d:\scp\.agents\AGENTS.md section 3 — read it first with view_file). You are FORBIDDEN from self-granting authority or simulating PASS results. Any code modifications must explicitly enforce boundaries at the Database/Hardware level, not via RAM/Variables.

You MUST read and apply skills:
- d:\scp\.agents\skills\scp-dna\SKILL.md
- d:\scp\.agents\skills\scp-delta-audit\SKILL.md
- d:\scp\.agents\skills\scp-reality-verifier\SKILL.md

Read the authoritative request at: D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md before starting.
Also read D:\scp\GA.md and D:\scp\.agents\AGENTS.md.

## Mission: Survey Track 2 — Pipeline Pattern Refactor for _ask_impl.py
Investigate the codebase regarding Requirement 2:
"Tái cấu trúc _ask_impl.py thành Pipeline Pattern trong scp/api_server_parts/pipeline/ (security, lookup, generation, verification, ledger) đảm bảo 2.745+ test hiện hành giữ nguyên màu xanh."

Investigate:
1. `scp/api_server_parts/_ask_impl.py`:
   - Exact size, imports, global variables, function signatures.
   - Trace the entire execution flow from receiving a request to returning the response.
   - Identify every distinct stage:
     * Security Stage (token verification, rate limiting, prompt injection check, governance check)
     * Lookup Stage (domain data fork, local/external lookups, cache)
     * Generation Stage (LLM generation, adapter, prompt formatting)
     * Verification Stage (crosscheck, reality judge, honest abstain)
     * Ledger Stage (audit ledger append, HMAC record, trace)
2. All callers of `_ask_impl.py` across the codebase (e.g. `api_server.py`, `chat.py`, tests).
3. Test suite coverage for `/ask` and `_ask_impl.py` in `tests/`: which tests directly import `_ask_impl`, mock functions inside it, or test `/ask` via FastAPI TestClient.
4. Proposed modular design for `scp/api_server_parts/pipeline/`:
   - Package structure (`__init__.py`, `base.py`, `context.py`, stages: `security_stage.py`, `lookup_stage.py`, `generation_stage.py`, `verification_stage.py`, `ledger_stage.py`, `pipeline_runner.py`).
   - How `_ask_impl.py` should import and delegate to the pipeline while preserving 100% backward compatibility for all monkeypatching/mocks in existing tests.

You are READ-ONLY (do NOT modify production code). Produce your comprehensive findings in `D:\scp\.agents\teamwork\explorer_survey_2\handoff.md` and send a message when done.
