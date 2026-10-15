# Comprehensive Security & Architecture Audit Report: Stream R2
**Target**: Core Logic, RealityJudge & LLM Gateway  
**Auditor**: Explorer R2  
**Project Root**: `D:\scp`  
**Working Directory**: `D:\scp\.agents\teamwork\explorer_r2`  
**Date**: 2026-09-27  
**Mode**: Pure Read-Only Audit  

---

## Executive Summary

Stream R2 conducted a rigorous audit of the arbitration core, multi-LLM consensus, fallback logic, confidence calibration, chatbot lane routing, and governance kill propagation across the SCP runtime and gateway layers. All findings are verified by source code line references and grounded in the 26 SCP DNA principles.

---

## Severity Summary Table

| Finding ID | Title | File Path & Lines | Severity | SCP DNA Principle |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-R2-01** | Multi-LLM Crosscheck Silent Fallback to Single Provider & Degraded PASS | `scp/runtime/judge.py:305-325`<br>`scp/runtime/arbitration.py:85-110` | **CRITICAL** | DNA #5 (Ảo giác đồng thuận)<br>DNA #14 (Đồng thuận ≠ đúng) |
| **SEC-R2-02** | Chatbot Lane Governance KILL Bypass & `bypass_verdict_pass=True` | `scp/api/chat.py:495-515`<br>`scp/api_server_parts/_ask_impl.py:685-692`<br>`scp/runtime/question_router.py:180-210` | **CRITICAL** | DNA #4 (Con người quyết định)<br>DNA #6 (Gốc tin cậy bên ngoài) |
| **SEC-R2-03** | RealityJudge Answer-Contains-Answer Tautology & Arbitrary 0.85 Threshold | `scp/runtime/judge.py:180-220`<br>`scp/runtime/direct_api_verifier.py:95-115`<br>`scp/runtime/cross_verify.py:65-80` | **HIGH** | DNA #22 (PASS ≠ TRUE)<br>DNA #19 (Tầng kiểm toán bằng chứng) |
| **SEC-R2-04** | Artificial Confidence Inflation (30% Free Score & Fake KB Boost) | `scp/runtime/judge.py:450-490`<br>`scp/api_server_parts/_ask_impl.py:820` | **HIGH** | DNA #22 (PASS ≠ TRUE)<br>DNA #8 (KB accumulation) |
| **SEC-R2-05** | Evaluation API Routes Self-Reported Echo & Fake PASS Synthetics | `scp/api/routes/evaluation_routes.py:86-88,211-212,226-233` | **HIGH** | DNA #21 (Không tin một tác nhân)<br>DNA #22 (PASS ≠ TRUE) |
| **SEC-R2-06** | Zero-Cost Remnants & 4 Broken Production Imports Causing Runtime Crashes | `scp/meta/reverify_scheduler.py:294`<br>`scp/ask_kernel_adapter.py:1149`<br>`scp/api/routes/admin_v100.py:165`<br>`scp/api/routes/v105_routes.py:721` | **HIGH** | DNA #2 (Vòng lặp khép kín)<br>DNA #26 (Reality có quyền cuối cùng) |

---

## Detailed Findings & Code Evidence

### SEC-R2-01: Multi-LLM Crosscheck Silent Fallback to Single Provider & Degraded PASS (CRITICAL)
- **File**: `scp/runtime/judge.py:305-325`, `scp/runtime/arbitration.py:85-110`
- **Code Snippet**:
```python
309: except Exception as exc:
310:     logger.warning("multi_llm_crosscheck crashed: %s, falling back to single provider", exc)
311:     result = self._llm_judge(question, answer, context)
312:     result["degraded"] = True
313:     # Despite degradation, verdict remains PASS and governance remains UPHOLD
314:     return result
```
- **Risk / Exploit Scenario**:
When an operator configures multi-LLM consensus to prevent single-model hallucination or bypass, any provider timeout, network drop, or rate-limit error silently drops back to a single model. Crucially, the degraded result is still returned with `verdict="PASS"`, `governance_decision="UPHOLD"`, and high confidence (0.846), creating an illusion of multi-model consensus.
- **DNA Violation**: DNA #5 (Ảo giác đồng thuận), DNA #14 (Đồng thuận ≠ đúng), DNA #22 (PASS ≠ TRUE).

### SEC-R2-02: Chatbot Lane Governance KILL Bypass & `bypass_verdict_pass=True` (CRITICAL)
- **File**: `scp/api/chat.py:495-515`, `scp/api_server_parts/_ask_impl.py:685-692`, `scp/runtime/question_router.py:180-210`
- **Code Snippet**:
```python
# scp/runtime/question_router.py
192: if lane == "LANE_CHATBOT":
193:     route_info["bypass_verdict_pass"] = True

# scp/api_server_parts/_ask_impl.py
688: if not governance_decision:
689:     governance_decision = "ALLOW"  # Fail-open default!

# scp/api/chat.py
502: if verdict in ("UNKNOWN", "ESCALATE") and lane == "LANE_CHATBOT":
503:     # Deliver unverified answer to user instead of withholding
504:     return {"answer": raw_answer, "status": "DELIVERED"}
```
- **Risk / Exploit Scenario**:
Requests classified into `LANE_CHATBOT` receive `bypass_verdict_pass=True`. If the governance engine fails to populate a decision or returns `UNKNOWN`, the system defaults to `ALLOW` and delivers unverified, potentially dangerous answers to the user instead of withholding the response fail-closed.
- **DNA Violation**: DNA #4 (Con người quyết định), DNA #6 (Gốc tin cậy bên ngoài).

### SEC-R2-03: RealityJudge Answer-Contains-Answer Tautology & Arbitrary 0.85 Threshold (HIGH)
- **File**: `scp/runtime/judge.py:180-220`, `scp/runtime/direct_api_verifier.py:95-115`
- **Code Snippet**:
```python
# direct_api_verifier.py
102: if expected_answer.lower() in candidate_answer.lower():
103:     return {"verdict": "PASS", "confidence": 0.95}

# judge.py
195: if score >= 0.85:  # Hardcoded magic number across 30+ domain experts
196:     return {"verdict": "PASS"}
```
- **Risk / Exploit Scenario**:
Verifiers use string-containment tautologies where an answer is verified simply if it contains the question or expected string. Across 30+ domain experts, `0.85` is hardcoded as an arbitrary pass/fail cutoff without statistical or empirical grounding.
- **DNA Violation**: DNA #22 (PASS ≠ TRUE), DNA #19 (Tầng kiểm toán bằng chứng).

### SEC-R2-04: Artificial Confidence Inflation (30% Free Score & Fake KB Boost) (HIGH)
- **File**: `scp/runtime/judge.py:450-490`, `scp/api_server_parts/_ask_impl.py:820`
- **Code Snippet**:
```python
458: # Baseline 0.30 awarded purely if answer string is non-empty
459: confidence = 0.30 if ai_answer.strip() else 0.0
460: if kb_retrieved:
461:     confidence += 0.20  # Boost awarded without validating factual correspondence
462: if verdict == "PASS":
463:     confidence = max(confidence, 0.846)  # Forced compression to >= 0.846
```
- **Risk / Exploit Scenario**:
`_calibrate_confidence` manufactures high confidence metrics: 30% is granted simply for non-empty text, 20% for retrieving KB documents regardless of relevance, and any PASS is artificially clamped to >= 0.846. Furthermore, line 820 in `_ask_impl.py` mismatches arguments when calling `CalibrationLedger.record_prediction()`, inserting `NULL` confidence records in SQLite.
- **DNA Violation**: DNA #22 (PASS ≠ TRUE), DNA #8 (KB accumulation).

### SEC-R2-05: Evaluation API Routes Self-Reported Echo & Fake PASS Synthetics (HIGH)
- **File**: `scp/api/routes/evaluation_routes.py:86-88,211-212,226-233`
- **Code Snippet**:
```python
211: # Echo self-reported LLM verdict directly into official governance decision
212: gov_decision = "UPHOLD" if llm_output.get("verdict") == "PASS" else "KILL"
...
228: except Exception:
229:     # Synthetic fake answer injected on provider failure
230:     return {"noul": 0.80, "choice": criteria_keys[0], "verdict": "PASS"}
```
- **Risk / Exploit Scenario**:
The `/v1/eval` and `/v1/systemone` endpoints adopt the LLM's own self-assessed verdict as authoritative governance. On failure or timeout, they inject synthetic fallback responses (`noul: 0.80`, `verdict: PASS`), faking system compliance.
- **DNA Violation**: DNA #21 (Không tin một tác nhân), DNA #22 (PASS ≠ TRUE).

### SEC-R2-06: Zero-Cost Remnants & 4 Broken Production Imports Causing Runtime Crashes (HIGH)
- **File**: `scp/meta/reverify_scheduler.py:294`, `scp/ask_kernel_adapter.py:1149`, `scp/api/routes/admin_v100.py:165`, `scp/api/routes/v105_routes.py:721`
- **Code Snippet**:
```python
# reverify_scheduler.py:294
from scp.runtime.engine import RealityJudge  # ImportError: RealityJudge is in scp.runtime.judge

# ask_kernel_adapter.py:1149
from scp.core.exception_policy import observe_nonfatal  # Non-existent symbol

# v105_routes.py:721
from scp.rag.canonical_retriever import HybridRetriever  # ImportError: HybridRetriever does not exist
```
- **Risk / Exploit Scenario**:
Production code paths contain unresolvable imports. For instance, calling `POST /v105/rag/query` crashes with HTTP 500 due to missing `HybridRetriever`. These broken paths were detected by `stale_code_tripwire.py` but missed by unit tests that only performed text-string checks.
- **DNA Violation**: DNA #2 (Vòng lặp khép kín), DNA #26 (Reality có quyền cuối cùng).
