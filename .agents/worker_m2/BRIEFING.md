# BRIEFING — 2026-09-21T11:44:20Z

## Mission
Triển khai Milestone 2 (Autonomous Evidence Retrieval & Fact Separation - R2): Tự động truy xuất bằng chứng (KB -> Web Search với Data Quarantine) và bóc tách fact vs suy đoán kèm Confidence Badge Payload.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: D:\scp\.agents\worker_m2
- Original parent: 07f69cac-cae8-4515-b416-b4b3082c4bc7
- Milestone: Milestone 2 - Autonomous Evidence Retrieval & Fact Separation (R2)

## 🔒 Key Constraints
- File ownership: You exclusively own and may modify:
  * scp/knowledge/ (claim_extractor.py, domain_knowledge.py, autonomous retrieval modules)
  * scp/api_server_parts/_ask_impl.py
  * scp/api/chat.py
  * tests/ (accompanying tests for M2)
- Fail-Closed & Evidence-First principles strictly enforced.
- DO NOT CHEAT. All implementations must be genuine.
- Preserve backward compatibility with AskResponse (ensure final_answer remains a valid string so existing clients and tests continue to work).
- Data Quarantine: All retrieved web snippets must pass inspect_untrusted from scp.core.top_systems_learning before entering the prompt context (preventing web prompt injection).

## Current Parent
- Conversation ID: 07f69cac-cae8-4515-b416-b4b3082c4bc7
- Updated: 2026-09-21T11:44:20Z

## Task Summary
- **What to build**:
  1. Autonomous Evidence Retrieval: When answers contain factual claims lacking sufficient evidence or confidence < 0.7:
     (a) Automatically query internal knowledge base (knowledge.sqlite3 / DomainKnowledgeStore).
     (b) If KB does not have sufficient evidence, automatically trigger safe public web search (InternetSearch).
     (c) Data Quarantine: All retrieved web snippets pass inspect_untrusted from scp.core.top_systems_learning.
  2. Fact Separation & Confidence Badge Payload in /ask and WebSocket /chat:
     * verified_facts: list of dicts (claim, source, url, confidence, evidence_snippet).
     * llm_reasoning: str.
     * confidence_badge: dict (badge, score, sources_consulted, transparency_notes).
     * Backward compatibility with AskResponse (final_answer valid string).
- **Success criteria**:
  - Tests pass: pytest tests/T07_learning tests/T02_contract -q, pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q, python tools/t00_meta_audit.py.
  - 0 new regressions.
- **Interface contracts**: PROJECT.md § Autonomous Retrieval ↔ Synthesis Payload
- **Code layout**: scp/knowledge/, scp/api_server_parts/_ask_impl.py, scp/api/chat.py

## Key Decisions Made
- [Autonomous Retriever Chain]: `AutonomousEvidenceRetriever` queries `DomainKnowledge` (SQLite + JSONL backing) first. If evidence is empty/insufficient, falls back to `InternetSearch` with `inspect_untrusted` data quarantine.
- [Fact Separation]: `FactSeparator` extracts verified facts against retrieved context, isolates pure LLM reasoning / conversational commentary, and assigns dynamic `confidence_badge` (`FACT_VERIFIED`, `CONVERSATIONAL`, or `UNVERIFIED_CONJECTURE`).
- [Effective Confidence Calculation]: When grounded factual claims are verified by authoritative facts, effective confidence incorporates the verified fact score (>=0.90) ensuring `FACT_VERIFIED` badge with transparency notes.
- [Backward Compatibility]: `AskResponse` preserves `final_answer` string contract while extending with `verified_facts`, `llm_reasoning`, and `confidence_badge`.

## Change Tracker
- **Files modified**:
  * `scp/knowledge/domain_knowledge.py` — Added `DomainKnowledge`, `AutonomousEvidenceRetriever`, `FactSeparator`, `VerifiedFact`, `ConfidenceBadge`.
  * `scp/knowledge/__init__.py` — Exported new retrieval and fact separation classes.
  * `scp/knowledge/claim_extractor.py` — Added bidirectional capital patterns and entity relations.
  * `scp/api_server_parts/_ask_impl.py` — Integrated retriever, fact separation, payload extension, module-level singletons.
  * `scp/api/chat.py` — Integrated retriever, fact separation, WebSocket payload extension.
  * `tests/T07_learning/test_m2_autonomous_retrieval.py` — Added 10 comprehensive M2 tests.
- **Build status**: PASS (All test suites pass cleanly)
- **Pending issues**: None

## Quality Status
- **Build/test result**:
  * `pytest tests/T07_learning/test_m2_autonomous_retrieval.py`: 10 passed in 16.11s.
  * `pytest tests/T07_learning -q`: 131 passed in 51.55s.
  * `pytest tests/T02_contract -q`: 163 passed in 92.26s.
  * `pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q`: 105 passed in 24.34s.
  * `python tools/t00_meta_audit.py`: Exited 0, all integrity checks passed (0 new regressions).
- **Lint status**: 0 violations
- **Tests added/modified**: 10 new tests in `tests/T07_learning/test_m2_autonomous_retrieval.py`

## Loaded Skills
- None specified by prompt

## Artifact Index
- D:\scp\.agents\worker_m2\DISPATCH.md — Dispatch instructions
- D:\scp\.agents\worker_m2\BRIEFING.md — Situational awareness
- D:\scp\.agents\worker_m2\progress.md — Progress log & heartbeat
- D:\scp\.agents\worker_m2\handoff.md — Final handoff report

