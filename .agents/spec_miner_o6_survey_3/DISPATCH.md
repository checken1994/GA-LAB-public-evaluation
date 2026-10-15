# Dispatch: spec_miner_o6_survey_3

## Objective
Survey and extract the precise specifications, requirements, and reference inventory for:
- **R4: Restore Deleted Evidence and Fix Dangling References**
  - Commit `87d78da` deleted 152,699 lines of audit evidence (closure records M01–M14, STATUS-LEDGER, witness reports) without creating a relocation manifest.
  - Find all dangling references across the repo pointing to non-existent evidence/closure JSON files.
  - Determine optimal approach: restore evidence to `docs/evidence-summary/` or create `RELOCATION_MANIFEST.md` and clean up dangling references.
  - Review `README.md` claims (e.g., "184,276 requests") linking to verifiable evidence.
- **Verification Gates Specification**:
  - `pytest tests/ --collect-only -q` (0 collection errors)
  - `python tools/t00_meta_audit.py` (0 regressions)
  - `python tools/adversarial_goal3_probe.py`
  - Integration test requirements for proving chain is severed.

## Scope Boundaries
- Read-only specification miner. DO NOT modify any production or test files.
- Deliver verified evidence (list of dangling references, git history of deleted files, exact line numbers).

## Input Files
- `D:\scp\.agents\ORIGINAL_REQUEST.md` (read `## 2026-09-22T18:07:00Z` and Section 6)
- Git log / status / references in repo.

## Output
- Write your findings to `D:\scp\.agents\spec_miner_o6_survey_3\spec_report.md`
- Write `handoff.md` and send message to orchestrator_6 with summary.

## 2026-09-22T18:09:33Z
You are spec_miner_o6_survey_3.
Your working directory is D:\scp\.agents\spec_miner_o6_survey_3.
Your parent orchestrator is orchestrator_6 (ID: d743754f-8fbb-42e5-ae1d-08ee4bb86635).
Project root is D:\scp.

Read your task assignment at D:\scp\.agents\spec_miner_o6_survey_3\DISPATCH.md.
Read the authoritative user request at D:\scp\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6).

Your mission is technical survey and specification mining for:
1. R4: Restore Deleted Evidence and Fix Dangling References
   - Commit 87d78da deleted 152,699 lines of audit evidence (closure records M01-M14, STATUS-LEDGER, witness reports).
   - Locate git commit 87d78da or find all dangling references across the repo pointing to non-existent evidence/closure JSON files.
   - Determine whether to restore evidence to docs/evidence-summary/ or generate RELOCATION_MANIFEST.md.
   - Enumerate all dangling file references that must be fixed to achieve ZERO dangling references.
   - Check README.md claims (e.g. "184,276 requests") that need verifiable backing or update.
2. Verification Gates & Test Specification:
   - pytest tests/ --collect-only -q (0 collection errors)
   - python tools/t00_meta_audit.py (0 regressions)
   - python tools/adversarial_goal3_probe.py
   - Integration test specs for proving the CRITICAL chain is severed.

Deliverables:
- Maintain progress.md in your working directory.
- Write detailed spec report to D:\scp\.agents\spec_miner_o6_survey_3\spec_report.md.
- Write handoff.md in your working directory.
- Send message to parent orchestrator_6 with your executive summary when complete.
Do NOT modify production or test files. You are read-only spec miner.

