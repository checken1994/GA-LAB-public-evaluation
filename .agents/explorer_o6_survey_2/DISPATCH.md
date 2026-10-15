# Dispatch: explorer_o6_survey_2

## Objective
Survey and map the exact technical state, file paths, line numbers, and dependencies for:
- **R3: Remaining Unfixed Findings from Previous Audit**
  - Judge crash fallback & tautology (`scp/runtime/judge.py:309-314`, `answer-contains-answer`, threshold 0.85)
  - `expire_leases` OCC rowcount checks on 4 branches (`scp/task_kernel/taskkernel.py:805-855`)
  - Semantic firewall gaps (github-desc/wiki bypass in `scp/knowledge/top_systems_learning.py:263,318`)
  - Dashboard SSRF on remaining raw-fetch routes (status, scanners, loop, loop/trigger in dashboard API routes)
  - Egress DNS-rebinding & dev defaults
  - Memory multi-turn redaction gaps (JWT/ghp_/AKIA patterns not in regex set)
- **R5: Cleanup Debris and Hygiene**
  - Delete `prev_ask_impl.py` and `sleeps.txt` (check references and repo location)
  - Fix `e2e_live_cluster_verifier.py:100` hardcoded fallback admin token
  - Fix `SCP_ARCHITECTURE.md` claims about quorum (feature was deleted)
  - Fix `domain_knowledge.py` FactSeparator "verified" = 2-token overlap tautology
  - Observability compose password and compose.test 0.0.0.0 binding

## Scope Boundaries
- Read-only exploration. DO NOT modify any production or test files.
- Deliver verified evidence (file paths, exact lines, potential side effects).

## Input Files
- `D:\scp\.agents\ORIGINAL_REQUEST.md` (read `## 2026-09-22T18:07:00Z` and Section 6)
- Relevant files under `scp/`, `dashboard/`, `docs/`, `docker-compose*.yml`.

## Output
- Write your findings to `D:\scp\.agents\explorer_o6_survey_2\survey_report.md`
- Write `handoff.md` and send message to orchestrator_6 with summary.
## 2026-09-22T18:09:33Z
You are explorer_o6_survey_2.
Your working directory is D:\scp\.agents\explorer_o6_survey_2.
Your parent orchestrator is orchestrator_6 (ID: d743754f-8fbb-42e5-ae1d-08ee4bb86635).
Project root is D:\scp.

Read your task assignment at D:\scp\.agents\explorer_o6_survey_2\DISPATCH.md.
Read the authoritative user request at D:\scp\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6).

Your mission is technical survey and mapping for:
1. R3: Remaining Unfixed Findings from Previous Audit
   - Judge crash fallback & tautology (scp/runtime/judge.py:309-314, answer-contains-answer, threshold 0.85)
   - expire_leases OCC rowcount checks on 4 branches (scp/task_kernel/taskkernel.py:805-855)
   - Semantic firewall gaps (github-desc/wiki bypass in scp/knowledge/top_systems_learning.py:263,318)
   - Dashboard SSRF on remaining raw-fetch routes (status, scanners, loop, loop/trigger in dashboard API routes)
   - Egress DNS-rebinding & dev defaults
   - Quorum claims in documentation (SCP_ARCHITECTURE.md) vs removed feature
   - Memory multi-turn redaction gaps (JWT/ghp_/AKIA patterns not in regex set in memory store / redaction)
2. R5: Cleanup Debris and Hygiene
   - Identify location and any references to prev_ask_impl.py and sleeps.txt to safely remove them
   - Fix e2e_live_cluster_verifier.py:100 hardcoded fallback admin token
   - Fix FactSeparator "verified" = 2-token overlap tautology in scp/knowledge/domain_knowledge.py:526-532
   - Observability compose password and compose.test 0.0.0.0 binding

Deliverables:
- Maintain progress.md in your working directory.
- Write detailed survey report to D:\scp\.agents\explorer_o6_survey_2\survey_report.md.
- Write handoff.md in your working directory.
- Send message to parent orchestrator_6 with your executive summary when complete.
Do NOT modify production or test files. You are read-only explorer.
