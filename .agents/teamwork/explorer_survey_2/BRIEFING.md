# BRIEFING — 2026-10-08T05:47:00Z

## Mission
Comprehensive survey and architectural investigation for Track 2: Pipeline Pattern Refactor for _ask_impl.py into scp/api_server_parts/pipeline/ while ensuring 2,745+ tests remain green.

## 🔒 My Identity
- Archetype: explorer
- Roles: Codebase & Architecture Investigator
- Working directory: D:\scp\.agents\teamwork\explorer_survey_2
- Original parent: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff
- Milestone: Survey Track 2 — Pipeline Pattern Refactor for _ask_impl.py

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production code
- Strictly bound by Fail-Closed & Evidence-First principles (FA-01 through FA-13)
- Write only to working directory D:\scp\.agents\teamwork\explorer_survey_2
- Produce thorough handoff report with 5-component structure

## Current Parent
- Conversation ID: d48c23a1-aa94-4967-ac9a-ed40fa3f5fff
- Updated: not yet

## Investigation State
- **Explored paths**:
  * `scp/api_server_parts/_ask_impl.py` (1,381 LOC, complete AST & execution flow)
  * `scp/api_server.py` (composition root, `_rebind_part_function`, exports)
  * `scp/ask_kernel_adapter.py` (`run_rag` calling handler)
  * All 26 test files in `tests/` importing, mocking, or statically inspecting `_ask_impl.py`
  * Baseline execution: 305 tests passing cleanly across ask-related test files
- **Key findings**:
  * `_ask_impl.py` has 5 distinct stages: Security, Lookup, Generation, Verification, Ledger.
  * `api_server.py` rebinds `_ask_impl` to execute against `api_server` globals; tested by `test_api_server_rebind_globals.py` which inspects all `LOAD_GLOBAL` opcodes.
  * Static tests (`test_chat_multimodal_contract.py`, `test_ask_factcheck_await_contract.py`, `test_flow_14_reintegrated_systems_scp_standard.py`, `test_ask_trace_ledger_final_decision.py`) perform direct `.read_text()`, `inspect.getsource()`, and `ast.parse()` on `_ask_impl.py`.
  * Dynamic tests monkeypatch `get_judge`, `_async_fact_check`, `InternetSearch` on `scp.api_server_parts._ask_impl`.
  * The refactor must use a Hybrid Facade Pattern: modular pipeline classes in `scp/api_server_parts/pipeline/` with a backward-compatibility facade in `_ask_impl.py` that preserves static tokens and dynamic monkeypatch resolution.
- **Unexplored areas**: None, investigation is comprehensive.

## Key Decisions Made
- Deconstruct pipeline into 5 modular stages: `SecurityStage`, `LookupStage`, `GenerationStage`, `VerificationStage`, `LedgerStage` orchestrated by `AskPipelineRunner` with shared `AskPipelineContext`.
- Context object includes dynamic namespace resolution (`resolve()`) to seamlessly honor test monkeypatching.
- Facade in `_ask_impl.py` retains contract anchors to guarantee 100% compliance with static AST/source scanner tests.

## Artifact Index
- D:\scp\.agents\teamwork\explorer_survey_2\DISPATCH.md — Task dispatch
- D:\scp\.agents\teamwork\explorer_survey_2\BRIEFING.md — Situational awareness
- D:\scp\.agents\teamwork\explorer_survey_2\progress.md — Liveness heartbeat
- D:\scp\.agents\teamwork\explorer_survey_2\handoff.md — Final handoff report
