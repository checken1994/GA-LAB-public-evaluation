# Stream R2 Dispatch — Core Logic, RealityJudge & LLM Gateway

## Target Working Directory
`D:\scp\.agents\teamwork\explorer_r2`

## Project Root & Request Reference
- Project Root: `D:\scp`
- Authoritative Request: `D:\scp\.agents\teamwork\ORIGINAL_REQUEST.md`

## Mission
Conduct a meticulous, line-by-line, read-only audit of Stream R2 in the SCP codebase.
Ground every finding in the 26 SCP DNA principles, Fail-Closed & Evidence-First, and Fail-Closed requirements.

## Specific Areas of Investigation
1. **RealityJudge Arbitration & Logic**:
   - Inspect `scp/runtime/judge.py`, `scp/runtime/arbitration.py`, and related modules under `scp/runtime/`.
   - Check if RealityJudge employs tautological comparisons (e.g. answer-contains-answer) or arbitrary hardcoded thresholds (e.g. 0.85).
2. **Multi-LLM Crosscheck & Crash Fallback**:
   - Inspect crosscheck execution when multi-provider consensus is requested.
   - Investigate how timeouts, network errors, or provider crashes are handled. Does it silently fall back to a single provider or fake consensus?
3. **Confidence Calibration (`_calibrate_confidence()`)**:
   - Review mathematical logic and calibration curves in `_calibrate_confidence()`.
   - Check if outputs are strictly clamped to [0, 1] and if confidence can be inflated artificially.
4. **Chatbot Lane & Question Router**:
   - Inspect `scp/api/_ask_impl.py`, `scp/api/chat.py`, and `question_router.py` (or router modules).
   - Check if Governance `KILL` verdicts are ever overridden to `ALLOW` or defaulted to `PASS`.
   - Inspect `/v1/eval` and `/v1/systemone` routes (`scp/api/routes/evaluation_routes.py`) for fake PASS or bypassed evaluations.
5. **LLM Gateway Routing & Dead Code Excision**:
   - Inspect `scp/llm_gateway/` and routes.
   - Confirm whether all deprecated zero-cost code remnants (`zero_cost_guard`, `zero_cost_runtime`, etc.) have been excised or if dead branches/broken imports remain.

## Output Requirements
Write `D:\scp\.agents\teamwork\explorer_r2\handoff.md` containing:
- Complete list of findings with:
  * `file_path` (exact path relative to D:\scp)
  * `line_number(s)` (exact lines)
  * `code snippet` (verbatim from codebase)
  * `severity` (CRITICAL, HIGH, MEDIUM, LOW, INFO)
  * `concrete risk / exploit scenario`
  * `SCP DNA principle citation`
- Summary table of findings by severity.
- Clear conclusion on logic correctness and governance propagation for R2.

## Invariant
PURE READ-ONLY. DO NOT modify or create any source code or test files.
