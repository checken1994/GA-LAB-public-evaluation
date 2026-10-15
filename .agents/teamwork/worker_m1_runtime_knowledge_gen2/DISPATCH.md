# DISPATCH: worker_m1_runtime_knowledge_gen2

## Mandatory Instructions
MANDATORY: Read `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Sources of Truth
Read `D:\scp\.agents\teamwork\explorer_m1_2\handoff.md` and `D:\scp\.agents\teamwork\explorer_m1_3\handoff.md` which contain exact line numbers, AST analyses, and drop-in code blocks.

## Assigned Scope & Exclusive File Ownership
You exclusively own and may edit ONLY the following files:
1. `scp/runtime/judge.py`
2. `scp/api_server_parts/_ask_impl.py`
3. `scp/api/chat.py`
4. `scp/knowledge/domain_knowledge.py`
5. `scp/core/top_systems_learning.py`
6. `scp/rag/canonical_retriever.py`
7. `scp/release/evidence_authority.py`
8. `scp/core/exception_policy.py`
9. `scp/runtime/engine.py`
10. `scp/meta/reverify_scheduler.py`
11. `tests/T05_gateway/test_judge_sync_crosscheck_alive.py`
12. Any new/updated unit tests for these modules in `tests/`

## Implementation Checklist
1. **SEC-R2-01** (`scp/runtime/judge.py`):
   - When `_run_crosscheck_sync` or async crosscheck crashes/fails, catch the exception, log clearly, and do NOT treat the single-vendor fallback as an authoritative PASS with 0.846 confidence.
   - Return `verdict="DEGRADED"`, `governance_decision="DEGRADED"`, `cross_model_agreement=False`.
   - In `_calibrate_confidence()`, when `crosscheck_fallback_degraded` occurs, clamp confidence < 0.50 (e.g. 0.40).
   - In `tests/T05_gateway/test_judge_sync_crosscheck_alive.py:134`, update the test assertion from expecting `PASS` on fallback to expecting `DEGRADED`.

2. **SEC-R2-02** (`scp/api_server_parts/_ask_impl.py` & `scp/api/chat.py`):
   - In `_ask_impl.py:688-689` and `chat.py`: remove `bypass_verdict_pass=True` from `LANE_CHATBOT`.
   - When governance evaluation is missing, `UNKNOWN`, or none, enforce fail-closed: do NOT default to `ALLOW`. Set `_gov_decision = "DENY"` / `"WITHHELD"` and do not release unverified output.

3. **R4-F01** (`scp/knowledge/domain_knowledge.py`):
   - In `FactSeparator`: rewrite matching logic to remove the 2-token overlap tautology.
   - Define a comprehensive stopwords list `ALL_FACT_STOPWORDS` (Vietnamese and English: `là`, `của`, `và`, `các`, `có`, `được`, `ở`, `tại`, `trong`, `thủ`, `đô`, `is`, `the`, `of`, `in`, `and`, etc.).
   - Require at least 3 content tokens (non-stopwords) and >= 60% content ratio.
   - Enforce semantic entity constraints: entities mentioned in the claim must align with entities in the evidence.

4. **R4-F03** (`scp/core/top_systems_learning.py`):
   - In `SemanticFirewall` / `inspect_untrusted()`:
     Normalize Cyrillic/Greek homoglyphs to Latin before pattern matching.
     Implement in-tree `_HOMOGLYPH_TABLE` translation table (`str.maketrans`) mapping Cyrillic (`а, с, е, о, р, х, у, і, ј, ѕ`, etc.) and Greek characters to their Latin counterparts.
     Also expand invisible character strip/regex.

5. **R4-F04** (`scp/rag/canonical_retriever.py`):
   - Fix handling of missing `corpus_all_fetched.jsonl`: if file is missing, log a warning, do not set `_loaded = True` blindly, set `self.available = False`, and provide transparent fallback to `DomainKnowledge`.

6. **Fix 4 Broken Production Imports**:
   - `scp/release/evidence_authority.py`: define class `ReleaseEvidenceAuthority(EvidenceAuthority)` with `__init__(self, db_path: Path | str | None = None)` and method `generate_release_claim() -> dict[str, Any]`.
   - `scp/rag/canonical_retriever.py`: define class `HybridRetriever(CanonicalRetriever)` with method `search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]`.
   - `scp/core/exception_policy.py`: create this new file containing:
     ```python
     import logging
     logger = logging.getLogger("scp.core.exception_policy")
     def observe_nonfatal(component: str, exception_type: str, details: str = "") -> None:
         logger.warning(f"[NONFATAL] {component}: {exception_type} - {details}")
     ```
   - `scp/runtime/engine.py` & `scp/meta/reverify_scheduler.py`:
     In `scp/runtime/engine.py`, re-export `RealityJudge` (`from scp.runtime.judge import RealityJudge; __all__ = ["RealityJudge", ...]`).
     In `scp/meta/reverify_scheduler.py`, import `from scp.runtime.judge import RealityJudge`.

## Verification
Run tests for judge, knowledge, canonical retriever, and stale_code_tripwire:
`python tools/stale_code_tripwire.py`
`pytest tests/T02_contract/test_knowledge_domain_rules.py tests/T05_gateway/test_judge_sync_crosscheck_alive.py tests/T07_learning/ -q`
Write `D:\scp\.agents\teamwork\worker_m1_runtime_knowledge_gen2\handoff.md` and notify parent when complete.
