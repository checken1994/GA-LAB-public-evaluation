# DISPATCH: explorer_m1_2

## Objective
Investigate and produce comprehensive remediation specifications for Stream R2 (RealityJudge & Governance) and Stream R4 (Knowledge, Fact Separation & RAG) critical vulnerabilities:
1. `SEC-R2-01`: `scp/runtime/judge.py:305-325` — Remove silent single-vendor downgrade when multi-LLM crosscheck crashes or times out; do not forge PASS/UPHOLD with 0.846 confidence; explicitly mark `DEGRADED`/`UNCERTAIN`.
2. `SEC-R2-02`: `scp/api_server_parts/_ask_impl.py:688-689` & `scp/api/chat.py` — Remove `bypass_verdict_pass=True` flag in `LANE_CHATBOT`; when governance decision is missing or UNKNOWN, enforce fail-closed rejection instead of defaulting to `ALLOW`.
3. `R4-F01`: `scp/knowledge/domain_knowledge.py:436-464` — Rewrite `FactSeparator`: include stopwords list, require minimum 3 content tokens, enforce semantic entity constraints; eliminate the 2-token overlap tautology.
4. `R4-F03`: `scp/core/top_systems_learning.py:95-107` — Add Unidecode / Cyrillic/Greek homoglyphs normalization to Latin in Semantic Firewall before regex inspection.
5. `R4-F04`: `scp/rag/canonical_retriever.py:41-54` — Fix handling of missing `corpus_all_fetched.jsonl` corpus file; do not silently swallow error and set `_loaded=True`; emit warnings and provide transparent fallback.

## Input References
- `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` (mandatory read)
- `D:\scp\DEEP_AUDIT_REPORT_20260927.md` (sections SEC-R2-01, SEC-R2-02, R4-F01, R4-F03, R4-F04)
- Target source files and corresponding test files in `tests/`

## Output Requirements
Write `D:\scp\.agents\teamwork\explorer_m1_2\handoff.md` with:
- Exact findings confirmed with file line numbers and logic analysis
- Precise before/after implementation recommendations adhering to Fail-Closed & Evidence-First principles
- Regression prevention and test strategy (unit tests to verify fixes)
- Conclude with a clear verdict/summary for Worker.
