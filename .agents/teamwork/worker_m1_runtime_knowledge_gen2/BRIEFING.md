# BRIEFING — 2026-09-27T11:15:00Z

## Mission
Implement robust, production-grade, genuine fixes for SEC-R2-01, SEC-R2-02, R4-F01, R4-F03, R4-F04, and the 4 broken production imports in the assigned modules under D:\scp.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2
- Original parent: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Milestone: M1 (Runtime & Knowledge remediation)

## 🔒 Key Constraints
- Fail-Closed & Evidence-First principles strictly enforced (FA-01 through FA-13).
- DO NOT CHEAT: No hardcoded test results, no dummy/facade implementations, real state and logic only.
- Exclusively own and edit ONLY:
  1. scp/runtime/judge.py
  2. scp/api_server_parts/_ask_impl.py
  3. scp/api/chat.py
  4. scp/knowledge/domain_knowledge.py
  5. scp/core/top_systems_learning.py
  6. scp/rag/canonical_retriever.py
  7. scp/release/evidence_authority.py
  8. scp/core/exception_policy.py
  9. scp/runtime/engine.py
  10. scp/meta/reverify_scheduler.py
  11. tests/T05_gateway/test_judge_sync_crosscheck_alive.py
  12. Any new/updated unit tests for these modules in tests/

## Current Parent
- Conversation ID: 2aaeeadc-d673-43f3-8c6c-2096e8377dec
- Updated: 2026-09-27T11:15:00Z

## Task Summary
- **What to build**:
  - SEC-R2-01: judge.py (no silent single-vendor downgrade, mark DEGRADED/UNCERTAIN, fix test_judge_sync_crosscheck_alive.py:134).
  - SEC-R2-02: _ask_impl.py & chat.py (remove bypass_verdict_pass, fail-closed on missing governance).
  - R4-F01: domain_knowledge.py (FactSeparator rewrite with stopwords, min 3 content tokens, semantic entities, remove tautology).
  - R4-F03: top_systems_learning.py (homoglyphs normalization table + expanded invisible regex).
  - R4-F04: canonical_retriever.py (missing corpus warning + fallback + HybridRetriever class).
  - Fix 4 broken production imports: ReleaseEvidenceAuthority, HybridRetriever, observe_nonfatal, RealityJudge export/import.
- **Success criteria**:
  - `python tools/stale_code_tripwire.py` passes with 0 FAIL.
  - `pytest tests/T02_contract/test_knowledge_domain_rules.py tests/T05_gateway/test_judge_sync_crosscheck_alive.py tests/T07_learning/ -q` passes with 0 FAIL.
- **Interface contracts**: PROJECT.md / SCOPE.md / DISPATCH.md
- **Code layout**: scp/ and tests/

## Key Decisions Made
- In-tree homoglyph table (`_HOMOGLYPH_TABLE` using `str.maketrans`) used to eliminate uninstalled dependencies like `unidecode`.
- Fail-closed on missing/unknown governance in `_ask_impl.py` (raises 403) and `chat.py` (withholds answer and sets governance="KILL").
- Degraded state handling in `judge.py` clamps confidence < 0.50 (0.3950) and returns `verdict="DEGRADED"`, `governance_decision="DEGRADED"`, `cross_model_agreement=False`.
- `FactSeparator` eliminates the 2-token overlap tautology by filtering stopwords with `ALL_FACT_STOPWORDS`, enforcing >= 3 content tokens and >= 60% overlap ratio, and rejecting claims where capitalized entities are absent in the evidence snippet.

## Artifact Index
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\DISPATCH.md
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\BRIEFING.md
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\progress.md
- D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\handoff.md

## Change Tracker
- **Files modified**:
  - `scp/runtime/judge.py`: Degraded state handling and confidence clamping on multi-LLM crosscheck fallback.
  - `scp/api_server_parts/_ask_impl.py`: Removed bypass_verdict_pass check, enforced fail-closed 403 on missing/UNKNOWN governance.
  - `scp/api/chat.py`: Removed bypass_verdict_pass check, enforced fail-closed withhold on missing/UNKNOWN governance.
  - `scp/knowledge/domain_knowledge.py`: FactSeparator rewrite with ALL_FACT_STOPWORDS, min 3 content tokens, >= 60% overlap, semantic entity constraints.
  - `scp/core/top_systems_learning.py`: _HOMOGLYPH_TABLE and _INVISIBLE_RE in inspect_untrusted.
  - `scp/rag/canonical_retriever.py`: HybridRetriever class, missing corpus logging, DomainKnowledge fallback.
  - `scp/release/evidence_authority.py`: ReleaseEvidenceAuthority class.
  - `scp/core/exception_policy.py`: observe_nonfatal telemetry logging.
  - `scp/runtime/engine.py`: Re-exported RealityJudge.
  - `scp/meta/reverify_scheduler.py`: Imported RealityJudge directly from scp.runtime.judge.
  - `tests/T05_gateway/test_judge_sync_crosscheck_alive.py`: Asserted DEGRADED verdict and clamped confidence.
  - `tests/test_rag_canonical_retriever.py`: Added tests for missing corpus fallback and HybridRetriever.
  - `tests/T03_capability/test_internet_safety_firewall.py`: Added tests for Cyrillic/Greek homoglyphs and invisible characters.
  - `tests/T02_contract/test_knowledge_domain_rules.py`: Contract tests for FactSeparator rules and hallucination rejection.
  - `tests/T02_contract/test_sec_r2_02_governance_failclosed.py`: Contract tests for SEC-R2-02 fail-closed governance.
- **Build status**: PASS (stale_code_tripwire: 0 FAIL; pytest: 195/195 passed; test collection: 2489 collected, 0 errors).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: All passing (100%).
- **Lint status**: Clean.
- **Tests added/modified**: 2 new test modules, 3 updated test files.
