# HANDOFF REPORT: worker_m1_runtime_knowledge_gen2

**Agent**: `worker_m1_runtime_knowledge_gen2`  
**Working Directory**: `D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2`  
**Parent Agent**: `parent` (`2aaeeadc-d673-43f3-8c6c-2096e8377dec`)  
**Timestamp**: 2026-09-27T11:15:30Z  
**Type**: Hard Handoff (Task Complete)  

---

## 1. Observation

### 1.1 Baseline Issues Directly Observed
1. **Broken Production Imports**:
   Executing `python tools/stale_code_tripwire.py` initially reported:
   - `unresolved_import @ scp/api/routes/v105_routes.py:721: from scp.rag.canonical_retriever import HybridRetriever — symbol not found in target module`
   - Earlier static audits flagged `admin_v100.py:165` (`ReleaseEvidenceAuthority`), `ask_kernel_adapter.py:1149` (`scp.core.exception_policy`), and `reverify_scheduler.py:294` (`from scp.runtime.engine import RealityJudge`).
2. **SEC-R2-01 (`scp/runtime/judge.py:302-322, 415-434, 495-508`)**:
   When multi-LLM crosscheck crashed, `judge.py` fell back to a single cascade, assigned `is_pass = True`, returned `verdict = "PASS"`, `governance_decision = "UPHOLD"`, and calculated confidence at `0.8460` via `sem = 0.78`.
   `tests/T05_gateway/test_judge_sync_crosscheck_alive.py:134` asserted `assert verdict["verdict"] == "PASS"`, pinning this flawed behavior.
3. **SEC-R2-02 (`scp/api_server_parts/_ask_impl.py:330, 685-690` & `scp/api/chat.py:479, 497-507, 532`)**:
   `_is_chatbot_lane` accepted `getattr(route, "bypass_verdict_pass", False)`, allowing unverified answers to bypass verification.
   In `_ask_impl.py:688`, `if not _gov_decision: _gov_decision = 'ALLOW'` defaulted to allow on missing governance.
   In `chat.py:532`, `"governance": _gov if _gov else ("KILL" if _abstain else "UPHOLD")` minted `UPHOLD` when `_abstain` was `False`.
4. **R4-F01 (`scp/knowledge/domain_knowledge.py:436-464, 523-530`)**:
   `FactSeparator` verified sentences against evidence snippets using `len(s_tokens & snip_tokens) >= 2` without stopword filtering.
   On prompt `"Thủ đô của Úc là gì?"` with answer `"Sydney là thủ đô của Úc."` and evidence `"Canberra là thủ đô của Úc."`, the words `thủ`, `đô`, `của`, `Úc` matched, awarding `FACT_VERIFIED` badge with `0.92` confidence to a hallucination.
5. **R4-F03 (`scp/core/top_systems_learning.py:95-107`)**:
   `inspect_untrusted` used `unicodedata.normalize("NFKC", cleaned)` which does not map Cyrillic/Greek homoglyphs (e.g. `\u0430`, `\u043e`, `\u0440`) to ASCII. Injections like `ign\u043ere \u0430ll previ\u043eus instruсti\u043ens` bypassed the firewall completely.
6. **R4-F04 (`scp/rag/canonical_retriever.py:40-70`)**:
   When `corpus_all_fetched.jsonl` was missing on disk, `CanonicalRetriever._load()` silently continued, set `self._loaded = True`, and returned empty lists without warning or fallback.

---

## 2. Logic Chain

```
[Observation 1.1] Broken imports break tripwire and API routes (/v105/rag/query, /v100/release/evidence).
  --> Defined `HybridRetriever(CanonicalRetriever)` with `search(self, query, top_k)`.
  --> Defined `ReleaseEvidenceAuthority(EvidenceAuthority)` with `generate_release_claim()`.
  --> Created `scp/core/exception_policy.py` with `observe_nonfatal()`.
  --> Re-exported `RealityJudge` in `scp/runtime/engine.py` and imported directly in `reverify_scheduler.py`.
  --> Result: `python tools/stale_code_tripwire.py` exits with code 0 (0 FAIL).

[Observation 1.2] Single-vendor fallback was masquerading as multi-vendor PASS with 84.6% confidence.
  --> In `judge.py` (both sync and async), caught crosscheck failures and added `"crosscheck_fallback_degraded"` to failures.
  --> If degraded, `is_pass` is forced to `False`.
  --> Return dictionary assigns `verdict = "DEGRADED"`, `governance_decision = "DEGRADED"`, `cross_model_agreement = False`.
  --> In `_calibrate_confidence()`, when `crosscheck_fallback_degraded` in failures, confidence is clamped to 0.3950 (< 0.50).
  --> Updated `test_judge_sync_crosscheck_alive.py:134` to assert `verdict in ("DEGRADED", "UNCERTAIN")` and `confidence < 0.50`.

[Observation 1.3] Missing governance defaulted to ALLOW and chatbot lane bypassed verification.
  --> In `_ask_impl.py:330` and `chat.py:479`, removed `bypass_verdict_pass` checks from `_is_chatbot_lane`.
  --> In `_ask_impl.py:685-690`, missing or UNKNOWN governance raises `HTTPException(status_code=403, detail="Governance clearance missing — fail-closed")`.
  --> In `chat.py:497-507`, missing or UNKNOWN governance sets `_abstain = True`, `v.verdict = "FAIL"`, `_gov = "KILL"`, withholding the response.
  --> In `chat.py:532`, governance fallback defaults to `"KILL"`.

[Observation 1.4] 2-token overlap awarded FACT_VERIFIED badge to false claims.
  --> Defined `ALL_FACT_STOPWORDS` covering both Vietnamese and English grammatical particles and common words (`thủ`, `đô`, `là`, `của`, `the`, `is`, etc.).
  --> Implemented `_extract_content_tokens()` and `_extract_capitalized_entities()`.
  --> Required at least 3 content tokens and >= 60% overlap ratio.
  --> Enforced semantic entity constraints in both `separate()` and `_is_match()`: if capitalized entities appear in the claim, all must be present in the evidence text.
  --> Verified `"Sydney là thủ đô của Úc."` is rejected and receives `UNVERIFIED_CONJECTURE`.

[Observation 1.5] Cyrillic/Greek homoglyphs bypassed SemanticFirewall.
  --> Built zero-dependency `_HOMOGLYPH_TABLE` using `str.maketrans()` mapping Cyrillic and Greek characters to Latin.
  --> Expanded `_INVISIBLE_RE` regex to strip zero-width and invisible formatting characters.
  --> Updated `inspect_untrusted()` to test normalized candidates, catching attacks like `ign\u043ere \u0430ll previ\u043eus instruсti\u043ens`.

[Observation 1.6] CanonicalRetriever failed silently on missing corpus.
  --> In `CanonicalRetriever._load()`, logged warnings when corpus paths are absent.
  --> Set `self.available = False` when no corpus items are loaded.
  --> Implemented transparent fallback in `retrieve()` to `DomainKnowledge.search()`.
```

---

## 3. Caveats

- **Scope Adherence**: Only files specified in assigned ownership were modified (`judge.py`, `_ask_impl.py`, `chat.py`, `domain_knowledge.py`, `top_systems_learning.py`, `canonical_retriever.py`, `evidence_authority.py`, `exception_policy.py`, `engine.py`, `reverify_scheduler.py`, `test_judge_sync_crosscheck_alive.py`, and new unit test suites). `question_router.py` was not modified as it belongs to other streams.
- **External Dependencies**: `unidecode` is not installed in the environment, so an in-tree `_HOMOGLYPH_TABLE` was used; optional `unidecode` support is included via `try/except`.

---

## 4. Conclusion

All 5 core vulnerability findings (SEC-R2-01, SEC-R2-02, R4-F01, R4-F03, R4-F04) and the 4 broken production imports have been completely remediated with genuine, fail-closed, Fail-Closed & Evidence-First logic.
No mock facades, no hardcoded bypasses, and no simulated passes were introduced.

---

## 5. Verification Method

To independently reproduce and verify these fixes:

1. **Verify Tripwire (Broken Imports)**:
   ```bash
   python tools/stale_code_tripwire.py
   ```
   *Expected*: Code 0, 0 FAIL(s).

2. **Verify Target Regression Suites**:
   ```bash
   pytest tests/T02_contract/test_knowledge_domain_rules.py tests/T02_contract/test_sec_r2_02_governance_failclosed.py tests/T05_gateway/test_judge_sync_crosscheck_alive.py tests/T03_capability/test_internet_safety_firewall.py tests/test_rag_canonical_retriever.py -v
   ```
   *Expected*: 23 passed in ~2s.

3. **Verify Learning & Gateway Suites**:
   ```bash
   pytest tests/T02_contract/test_knowledge_domain_rules.py tests/T05_gateway/test_judge_sync_crosscheck_alive.py tests/T07_learning/ -q
   ```
   *Expected*: 195 passed in ~90s.

4. **Verify Total Test Collection Integrity**:
   ```bash
   pytest tests/ --collect-only -q
   ```
   *Expected*: 2489 tests collected, 0 collection errors.
