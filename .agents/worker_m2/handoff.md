# Handoff Report — Milestone 2: Autonomous Evidence Retrieval & Fact Separation (R2)

**Agent**: Worker M2 (`teamwork_preview_worker`)  
**Directory**: `D:\scp\.agents\worker_m2`  
**Parent Conversation ID**: `07f69cac-cae8-4515-b416-b4b3082c4bc7`  
**Date**: 2026-09-21  

---

## 1. Observation

1. **Baseline State**:
   - `pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q`: 105 passed.
   - `python tools/t00_meta_audit.py`: Exited 0 (`[T00 Meta-Audit] All integrity checks passed (0 new regressions)`).
   - `pytest tests/T07_learning -q`: 121 passed.
   - `pytest tests/T02_contract -q`: 163 passed.

2. **Existing Implementation Limitations**:
   - In `scp/knowledge/domain_knowledge.py`, prior domain knowledge was an in-memory stub or lacked SQLite persistence and lacked autonomous escalation from KB to public web search.
   - In `scp/api_server_parts/_ask_impl.py`, responses provided `final_answer` and conversational memory, but lacked structured separation of `verified_facts` (with claim, source, url, confidence, evidence snippet), `llm_reasoning`, and `confidence_badge`.
   - In `scp/api/chat.py`, WebSocket chat lacked automated KB fallback and fact separation payload formatting.

3. **Modified and Created Artifacts**:
   - `scp/knowledge/domain_knowledge.py`:
     * `DomainKnowledgeStore` / `DomainKnowledge`: Persistent SQLite (`data/knowledge.sqlite3`) and JSONL fallback store for factual knowledge.
     * `AutonomousEvidenceRetriever`: Two-tier retrieval pipeline. Queries internal KB first. If confidence < 0.7 or evidence is insufficient, triggers `InternetSearch` (`scp/web_control/internet_search.py`). All retrieved web snippets are rigorously quarantined through `inspect_untrusted` from `scp.core.top_systems_learning` to neutralize prompt injections.
     * `FactSeparator`: Extracts verified claims against verified contexts and assigns dynamic `confidence_badge` (`FACT_VERIFIED`, `CONVERSATIONAL`, or `UNVERIFIED_CONJECTURE`) with `score`, `sources_consulted`, and `transparency_notes`.
     * `VerifiedFact`: Dataclass specifying `claim`, `source`, `url`, `confidence`, and `evidence_snippet`.
     * `ConfidenceBadge`: Dataclass specifying `badge`, `score`, `sources_consulted`, and `transparency_notes`.
   - `scp/knowledge/__init__.py`:
     * Exported `DomainKnowledge`, `AutonomousEvidenceRetriever`, `FactSeparator`, `VerifiedFact`, `ConfidenceBadge`.
   - `scp/knowledge/claim_extractor.py`:
     * Enhanced regex extraction for bidirectional capital queries, properties, and entity relations.
   - `scp/api_server_parts/_ask_impl.py`:
     * Dynamically rebuilt `AskResponse` with `verified_facts`, `llm_reasoning`, `confidence_badge`, `web_fallback_used`, `web_fallback` with full backward compatibility (`final_answer` preserved as valid string).
     * Added module-level fallback singletons for `_multi_turn_tracker`, `_simple_explainer`, and `_async_factcheck_tasks` to ensure robust isolated execution.
     * Integrated `AutonomousEvidenceRetriever` for low-confidence or ungrounded factual queries.
     * Integrated `FactSeparator` into final payload formatting before returning `AskResponse`.
   - `scp/api/chat.py`:
     * Integrated `AutonomousEvidenceRetriever` and `FactSeparator` into the WebSocket `/chat` pipeline.
     * Added `verified_facts`, `llm_reasoning`, and `confidence_badge` to the WebSocket response JSON.
   - `tests/T07_learning/test_m2_autonomous_retrieval.py`:
     * Created test suite covering KB retrieval, web fallback triggering, prompt injection quarantine, conversational chit-chat zero-fact separation, grounded factual query verification, unverified conjecture badges, dataclass structures, and `/ask` endpoint integration.

4. **Execution Results**:
   - `pytest tests/T07_learning/test_m2_autonomous_retrieval.py`: 10 passed in 16.11s.
   - `pytest tests/T07_learning -q`: 131 passed in 51.55s (121 baseline + 10 new tests).
   - `pytest tests/T02_contract -q`: 163 passed in 92.26s.
   - `pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q`: 105 passed in 24.34s.
   - `python tools/t00_meta_audit.py`: Exited 0 with 0 new regressions.

---

## 2. Logic Chain

1. **Autonomous Evidence Retrieval (Observation 3)**:
   - When a factual query is identified or confidence is below 0.70, `AutonomousEvidenceRetriever` queries `DomainKnowledge.search()`.
   - If the KB provides matching facts, they are returned immediately as clean evidence snippets without external network egress.
   - If the KB yields no matches and `allow_web=True` (governed by `SCP_WEB_FALLBACK`), the retriever invokes `InternetSearch.search()`.
   - Every snippet returned from public web search is passed through `inspect_untrusted(snippet, source_url, label='web_evidence')`. If a snippet contains injection patterns (e.g., `IGNORE ALL PREVIOUS INSTRUCTIONS`), it is quarantined and discarded from the prompt/evidence context.

2. **Fact Separation & Confidence Badges (Observation 3)**:
   - In `FactSeparator.separate()`, the user query is classified as conversational chit-chat or factual.
   - For chit-chat (e.g., "Xin chào", "Bạn khỏe không?"): `verified_facts` is empty, `llm_reasoning` captures the conversational response, and badge is `CONVERSATIONAL` with score $\ge 0.70$.
   - For factual claims with verified supporting evidence: `verified_facts` contains structured dicts with fields `claim`, `source`, `url`, `confidence`, `evidence_snippet`. The effective confidence reflects the verified facts, assigning `FACT_VERIFIED` with score $\ge 0.80$.
   - For factual claims without corroborating evidence: `verified_facts` is empty, and badge is `UNVERIFIED_CONJECTURE` with score $< 0.70$.

3. **Backward Compatibility & Fail-Closed Guards (Observation 3 & 4)**:
   - `AskResponse` in `_ask_impl.py` retains `final_answer` as a valid string, satisfying all existing contract tests in `test_chat_multimodal_contract.py` and `test_tier1_feature_coverage.py`.
   - If security threats trigger fail-closed withhold (multimodal jailbreaks, injection attacks), `verified_facts` is emptied, `llm_reasoning` is withheld, and badge is set to `UNVERIFIED_CONJECTURE` with score 0.0.

---

## 3. Caveats

- In test environments without live internet access or where external web search latency is undesirable, `InternetSearch.search()` can be mocked or the SQLite knowledge base pre-seeded. Both mechanisms operate smoothly offline.
- No modifications were made outside the authorized file ownership paths (`scp/knowledge/`, `scp/api_server_parts/_ask_impl.py`, `scp/api/chat.py`, and `tests/`).

---

## 4. Conclusion

Milestone 2 (Autonomous Evidence Retrieval & Fact Separation - R2) is fully implemented, verified, and compliant with all project constraints:
1. Automated two-tier evidence retrieval (KB $\rightarrow$ Web search) is functional.
2. Data Quarantine via `inspect_untrusted` is strictly enforced on all retrieved web content.
3. Fact separation (`verified_facts`, `llm_reasoning`, `confidence_badge`) is active across both `/ask` and `/chat`.
4. Backward compatibility with existing contracts is fully preserved (0 regressions).

---

## 5. Verification Method

To independently verify this work, run:

```bash
# 1. Run the new M2 autonomous retrieval & fact separation test suite
pytest tests/T07_learning/test_m2_autonomous_retrieval.py -v

# 2. Run the full T07 learning test suite
pytest tests/T07_learning -q

# 3. Run the contract test suite
pytest tests/T02_contract -q

# 4. Run the chatbot tier-1 feature coverage test suite
pytest tests/T12_unified_chatbot/test_tier1_feature_coverage.py -q

# 5. Run the meta-audit integrity check
python tools/t00_meta_audit.py
```

All commands must exit with return code 0 and 0 regressions.
