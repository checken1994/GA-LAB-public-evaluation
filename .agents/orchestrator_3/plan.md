# Execution Plan — Orchestrator 3

## Topology & Orchestration Strategy
- **Pattern**: Project Orchestration with iterative Explorer -> Worker -> Reviewer -> Challenger -> Auditor gate loops.
- **Strict Role Boundaries**:
  - Orchestrator (me): Dispatch-only. Manages state files, evaluates reports, coordinates lifecycle.
  - Explorer (`teamwork_preview_explorer`): Reads files, investigates context, plans precise patches.
  - Worker (`teamwork_preview_worker`): Applies changes, runs tests, executes build commands.
  - Reviewer (`teamwork_preview_reviewer`): Evaluates diffs, ensures correctness and contracts.
  - Challenger (`teamwork_preview_challenger`): Adversarial stress testing, security boundary probes.
  - Auditor (`teamwork_preview_auditor`): Forensic integrity verification. Hard veto if cheating or fake pass detected.

## Milestones & Phased Execution

### Milestone 1: P0 Critical Security & Data Integrity (11 Findings)
- Scope: R2-01, R2-02, R3-01, R1-01, R5-01, R5-02, R5-03, R1-02, R4-01, R4-02, R6-01
- Target:
  1. Secure `/v3/trace/{trace_id}` in `api_server.py` with admin auth.
  2. Complete `redact_attributes()` tuple/string/key redaction in `trace_contract.py`.
  3. Commit and mount `_trace_impl.py` and `trace_store.py`.
  4. Restore 6 lazy properties on `Judge` in `runtime/judge.py`.
  5. Thread & file locks in `ChatMemoryStore`.
  6. Exclusive lock & tail read in `TraceLedger.append()`.
  7. Full query & fetch lock in `db_manager.py`.
  8. Real verification in `EvidenceReplay.verify()`.
  9. Replace 23+ `test_subsystem_*.py` import-only tests with real functional tests.
  10. Replace `assert True` in `chaos_recovery.py` with real TaskKernel crash/recovery.
  11. Document all 165 missing env vars in `.env.example`.
- Gate Criteria:
  - Worker passes all targeted tests + collection check.
  - Reviewer approves all diffs.
  - Challenger verifies concurrency and auth protection.
  - Auditor confirms zero integrity violations.

### Milestone 2: P1 High-Severity Reliability & Deployment (18 Findings)
- Scope: R6-02, R6-03, R6-04, R2-03, R2-04, R2-05, R2-06, R1-03, R1-04, R5-04, R5-05, R5-06, R5-07, R4-03, R4-04, R3-02, R3-03, R3-04
- Gate Criteria:
  - All 18 fixes implemented and verified.
  - No broken imports or regressions.

### Milestone 3: P2 Medium/Low Architectural Cleanup (17 Findings)
- Scope: R1-05 to R1-07, R2-07 to R2-08, R3-05 to R3-08, R4-05 to R4-06, R5-08 to R5-09, R6-05 to R6-06, remaining orphans & cycles
- Gate Criteria:
  - Cleanup completed, dependencies updated, test sleep refactored.

### Milestone 4: Final System Verification & Clean Commit
- Run full `pytest tests/ -q` (>1,937 tests pass, 0 failures).
- Run `python tools/t00_meta_audit.py` (0 regressions).
- Run `pytest tests/ --collect-only -q` (0 collection errors).
- Clean working tree, git commit and push.
