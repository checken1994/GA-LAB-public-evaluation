# BRIEFING — 2026-09-27T15:32:00Z

## Mission
Investigate 5 critical vulnerabilities across Stream R2 (RealityJudge & Governance: SEC-R2-01, SEC-R2-02) and Stream R4 (Knowledge, Fact Separation & RAG: R4-F01, R4-F03, R4-F04), producing concrete AST/code evidence, before/after replacement designs, and verification test plans.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: D:\scp\.agents\teamwork\explorer_m1_2
- Original parent: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Milestone: M1 — Exploration & Remediation Specification (Stream R2 & R4)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Fail-Closed & Evidence-First principles strictly enforced
- Concrete evidence and AST/code line analysis
- Exact before/after code replacement recommendation
- Regression prevention and verification test plan

## Current Parent
- Conversation ID: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Updated: 2026-09-27T15:32:00Z

## Investigation State
- **Explored paths**:
  - `scp/runtime/judge.py`: Lines 296–325, 408–435, 474–509 (SEC-R2-01)
  - `scp/api_server_parts/_ask_impl.py`: Lines 685–690 (SEC-R2-02)
  - `scp/api/chat.py`: Lines 479–545 (SEC-R2-02)
  - `scp/runtime/question_router.py`: Lines 151, 335, 454, 481, 492 (SEC-R2-02)
  - `scp/knowledge/domain_knowledge.py`: Lines 436–464, 508–531 (R4-F01)
  - `scp/core/top_systems_learning.py`: Lines 92–107 (R4-F03)
  - `scp/rag/canonical_retriever.py`: Lines 40–70 (R4-F04)
  - Unit and integration tests in `tests/`
- **Key findings**:
  1. SEC-R2-01: Multi-LLM crosscheck catch block falls back to single-provider `_llm_judge` and awards `verdict="PASS"`, `governance_decision="UPHOLD"`, `cross_model_agreement=True`, and 0.846 confidence (from `0.30*1.0 + 0.70*0.78`).
  2. SEC-R2-02: `RouteDecision` sets `bypass_verdict_pass=True` for `LANE_CHATBOT`. `_ask_impl.py:688` sets `if not _gov_decision: _gov_decision = 'ALLOW'`. `chat.py:532` manufactures `"governance": "UPHOLD"` when `_abstain` is False.
  3. R4-F01: `FactSeparator` and `_is_match` lack stopwords filtering. 2-token overlap (e.g. `thủ`, `đô`, `của`) satisfies `len >= 2` and assigns `FACT_VERIFIED` badge with 0.92 confidence to false claims ("Sydney là thủ đô của Úc").
  4. R4-F03: `inspect_untrusted` uses `NFKC` which does not map Cyrillic/Greek homoglyphs to ASCII. `unidecode` is missing from environment. In-tree homoglyph mapping table is needed.
  5. R4-F04: `data/rag_corpus` does not exist on disk. `CanonicalRetriever._load` silently skips missing paths without logging, sets `_loaded=True`, and returns empty list with no fallback.
- **Unexplored areas**: None. All 5 targets fully analyzed.

## Key Decisions Made
- Confirmed AST line numbers and exact conditions for all 5 vulnerabilities.
- Formulated concrete before/after code replacement blocks for Worker.
- Documented regression-proofing requirements (including updating tests that pinned obsolete behavior).

## Artifact Index
- `D:\scp\.agents\teamwork\explorer_m1_2\handoff.md` — 5-component handoff report
- `D:\scp\.agents\teamwork\explorer_m1_2\progress.md` — liveness heartbeat
- `D:\scp\.agents\teamwork\explorer_m1_2\BRIEFING.md` — persistent working memory
