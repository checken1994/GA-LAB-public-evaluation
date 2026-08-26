# SCP Phase 3 RAG Gate Status v3

**Snapshot:** `fb629aead5c3332422980ab4facfc2b31900f466` before this evidence-only commit
**Date:** 2026-08-26
**Verdict:** `CANDIDATE_NOT_PROVEN`; the evidence lane is intentionally fail-closed.

## Executive conclusion

The four blocked gates were re-run rather than promoted by declaration. The 50-row candidate package was reviewed by an independent `gpt-5-mini` pass using only the supplied source text. All 50 rows completed without reviewer-call failures, but **zero original questions** and only **one static-core question** were accepted by the programmatic safety gate. This is negative evidence against the existing corpus: most rows have empty source text, unrelated legacy sources, or temporal/high-stakes claims that the current source cannot support.

The 1,000-row official Ragas admission audit saw 1,000 runtime rows but admitted zero: 725 were not HTTP 200, 225 had no matching 50-row Gold record, and all 50 matching Gold rows were still ineligible. A separate one-row pilot did reach the official Ragas engine after a real `/ask` HTTP run on isolated `127.0.0.1:8002`; the proxy embedding endpoint returned HTTP 404, so the pilot was rerun with a local multilingual sentence-transformer embedding. The official Ragas engine then executed, but produced a non-finite `answer_correctness` value. Therefore the pilot is evidence that the engine path can execute in this environment, **not a releasable score**.

## Gate results

| Gate | Observed result | Status | Why it is not promoted |
|---|---|---|---|
| Gold-50 review | 50/50 independent LLM reviews returned; 0 original promotions; 1 static-core promotion | `BLOCKED` | Independent LLM review is not human review; 38 rows were current/high-stakes and the corpus has source gaps/mismatches |
| Official Ragas on 1,000 | 0 admitted; `BLOCKED_NO_VERIFIED_ROWS` | `BLOCKED` | No Gold row had verified provenance plus `eligible_for_ragas=true` |
| Official Ragas pilot | 1 row admitted and engine executed; `faithfulness=1.0`, `context_precision≈1.0`, `context_recall=0.0`, `answer_relevancy≈0.5767`, `answer_correctness=null` | `PILOT_ONLY` | One independent-LLM row, zero human-reviewed rows, and a missing/non-finite metric; no score release |
| ARES | Preconditions remain false | `BLOCKED` | Missing at least 50 human-annotated rows, few-shot examples, unlabeled query-document-answer set, verified non-abstain Gold and importable package |
| Real RAG 1,000 | Historical lane remains 185 `COMPLETED`, 565 `NO_TEXT_ABSTAIN`, 250 `REQUEST_ERROR`; answers were empty in the Phase 3 artifact | `BLOCKED` | Completed requests are not answered-and-verified rows; no reviewed Gold or valid full runtime answer set |

## Evidence chain

| Step | Artifact | Observation |
|---|---|---|
| Candidate validation | `benchmark/gold_anchor_50_v2_validation.json` | 50 rows; 9 source-fetch candidates; 18 current/high-stakes; 22 source mismatch; 1 additional review-required; 0 Ragas-eligible |
| Independent review | `phase3_rag_evidence_20260826/independent_gold_review_50.jsonl` | 50 reviewer outputs, 0 call failures, 0 original promotions, 1 static-core promotion; explicit non-human provenance |
| 1,000 admission | `phase3_rag_evidence_20260826/ragas_1000_admission_audit.json` | 1,000 runtime rows; 0 admitted; official `evaluate()` not called |
| Runtime | `phase3_rag_evidence_20260826/ragas_independent_pilot_runtime.jsonl` | One real HTTP `/ask` row from isolated 8002; HTTP 200, `PASS`, `SUCCESS`, grounding ratio 1.0 |
| Official evaluator | `phase3_rag_evidence_20260826/ragas_independent_pilot_result.json` | Official Ragas 0.1.7 executed on one row with local multilingual embedding; one metric normalized from non-finite to null; release disabled |
| ARES precondition audit | `benchmark/ares_preconditions_v2.json` | 5 failed preconditions, `score=null`, `BLOCKED_PRECONDITIONS` |

## Why automation cannot honestly finish all four gates

A source fetch can prove that a quote is contained in a fetched page. It cannot prove that the quote answers the exact question, that a current claim is still valid, or that a medical/legal/financial answer is safe and complete. That is why the Gold builder retains `human_review_required=true` and `gold_promotion=BLOCKED_PENDING_HUMAN_REVIEW` rather than silently self-promoting its own output.

Ragas is an evaluation library, not an official universal Gold corpus. Its evaluator requires a dataset with an answer, contexts and ground truth; this repository's admission gate additionally requires verified review provenance. ARES is a judge/evaluation framework whose calibration and validation inputs must exist before a score is meaningful. Neither package can manufacture missing in-domain Vietnamese truth data. See [Ragas documentation](https://docs.ragas.io/en/stable/) and [ARES repository](https://github.com/stanford-futuredata/ARES).

## Final classification

The four gates are not all product defects. They consist of three different blockers:

1. **Data-quality blockers:** the legacy candidate corpus contains empty or unrelated source text and questions whose wording demands current facts not present in the source.
2. **Human/provenance blockers:** the 50-row Gold lane has no human-verified rows. Independent LLM review produced a useful triage artifact but cannot be labeled human review.
3. **Evaluation-environment blockers:** the proxy embedding endpoint returned 404; a local embedding fallback allowed a one-row official-Ragas pilot, but one metric was non-finite and the pilot is too small for release.

The correct next action is not to change `eligible_for_ragas=true` by hand. It is to rebuild each row from an authoritative canonical source, obtain independent human review for the answer and `gold_chunk_ids`, then rerun the same admission gate and ARES calibration with their required datasets. Until that happens, the honest status remains `BLOCKED`, not `PASS`.
