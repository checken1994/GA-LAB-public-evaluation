## 2026-09-21T10:17:56Z

You are Worker M1 (teamwork_preview_worker) for the SCP project.
Your working directory is: D:\scp\.agents\worker_m1
Workspace root: D:\scp

MANDATORY: Read D:\scp\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-21T10:17:56Z) before starting.
Read project architecture: D:\scp\.agents\orchestrator_1\PROJECT.md
Read survey findings:
- D:\scp\.agents\explorer_survey_1\analysis.md
- D:\scp\.agents\explorer_survey_1\handoff.md
- D:\scp\.agents\explorer_survey_3\handoff.md

FILE OWNERSHIP:
You exclusively own and may modify:
- scp/runtime/question_router.py
- scp/ask_kernel_adapter.py
- scp/api_server_parts/_ask_impl.py
- scp/api/chat.py
- scp/core/chat_memory.py
- tests/ (accompanying unit tests for M1)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Milestone 1: Unified Chatbot Interaction Core (R1)
1. Question Routing: Categorize queries into LANE_CHATBOT, LANE_FACTUAL, LANE_SECURITY with dynamic language detection (vi, en, other) and routing metadata (bypass_verdict_pass).
2. Gate Unblocking & Double-Judge Elimination: For LANE_CHATBOT, unblock responses without requiring verdict == 'PASS' or RAG grounding; eliminate redundant second call to RealityJudge().judge_async; eliminate web_fallback_not_used penalty; maintain strict fail-closed for true security threats (LANE_SECURITY, Governance KILL, prompt injections).
3. Response Boundary & Bilingual Prompts: Ensure neither /ask nor WebSocket /chat withholds conversational/identity/reasoning queries; deploy dynamic Vietnamese/English system prompts based on query language.
4. Multi-Turn Memory Unification: Unify session persistence across /ask and /chat via ChatMemoryStore and ConversationManager.
5. Verification & Audit: Pass affected test suites (pytest tests/T02_contract tests/T03_capability tests/T07_learning -q), verify 0 regressions via python tools/t00_meta_audit.py, create dedicated unit tests, write handoff.md, and notify parent.
