# Worker M2 Dispatch
Scope: Milestone 2 - Autonomous Evidence Retrieval & Fact Separation (R2)

## 2026-09-21T11:44:20Z
You are Worker M2 (teamwork_preview_worker) for the SCP project.
Your working directory is: D:\scp\.agents\worker_m2
Workspace root: D:\scp

MANDATORY: Read D:\scp\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-21T10:17:56Z) before starting.
Read project architecture: D:\scp\.agents\orchestrator_1\PROJECT.md
Read M1 handoff: D:\scp\.agents\worker_m1\handoff.md
Read Survey report: D:\scp\.agents\explorer_survey_1\analysis.md

FILE OWNERSHIP:
You exclusively own and may modify:
- scp/knowledge/ (claim_extractor.py, domain_knowledge.py, autonomous retrieval modules)
- scp/api_server_parts/_ask_impl.py
- scp/api/chat.py
- tests/ (accompanying tests for M2)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & TASK - MILESTONE 2 (Autonomous Evidence Retrieval & Fact Separation - R2):
1. Autonomous Evidence Retrieval:
   - When answers contain factual claims lacking sufficient evidence or confidence < 0.7:
     (a) Automatically query internal knowledge base (knowledge.sqlite3 / DomainKnowledgeStore).
     (b) If KB does not have sufficient evidence, automatically trigger safe public web search (scp/web_control/internet_search.py via InternetSearch).
   - Data Quarantine: All retrieved web snippets must pass inspect_untrusted from scp.core.top_systems_learning before entering the prompt context (preventing web prompt injection).

2. Fact Separation & Confidence Badge Payload:
   - Clearly separate verified facts from model reasoning in the response payload for both /ask and WebSocket /chat:
     * verified_facts: list of dictionaries, each containing:
       - claim: str
       - source: str ("knowledge_base" or "web_search")
       - url: Optional[str]
       - confidence: float
       - evidence_snippet: str
     * llm_reasoning: str (reasoning, commentary, or conversational synthesis)
     * confidence_badge: dictionary containing:
       - badge: "FACT_VERIFIED" | "CONVERSATIONAL" | "UNVERIFIED_CONJECTURE"
       - score: float [0.0 - 1.0]
       - sources_consulted: list[str]
       - transparency_notes: str
   - Preserve backward compatibility with AskResponse (ensure final_answer remains a valid string so existing clients and tests continue to work).

3. Verification:
   - Run tests:
     pytest tests/T07_learning tests/T02_contract -q
     pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q
     python tools/t00_meta_audit.py
   - Ensure 0 new regressions.

OUTPUT:
Write detailed implementation notes and verification results to D:\scp\.agents\worker_m2\handoff.md.
When complete, send a concise message to your parent.

## 2026-09-21T12:01:03Z
From parent (07f69cac-cae8-4515-b416-b4b3082c4bc7):
Status check: Please report your current progress on implementing the autonomous retriever, fact separator, and integration into _ask_impl.py and chat.py.

