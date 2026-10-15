# Progress: spec_miner_o6_survey_3

Last visited: 2026-09-22T18:20:00Z
Status: Completed

## Tasks
- [x] Initialize BRIEFING.md and progress.md
- [x] Read ORIGINAL_REQUEST.md (specifically ## 2026-09-22T18:07:00Z and Section 6)
- [x] Investigate Git Commit 87d78da (what was deleted, commit details, trees, blobs)
  - Discovered 500 files deleted (152,699 lines): 442 in reports/, 28 in archive/, 27 in .agents/, 1 AGENTS.md, 1 GA.md, 1 research/.
  - ed71733 restored .agents/, AGENTS.md, GA.md; 471 files remain deleted.
- [x] Scan and enumerate all dangling references across the repo
  - Found 115 occurrences across 79 unique tracked files.
  - Exactly 34 distinct deleted file paths have exact git grep hits.
  - 82 references specifically to `docs/evidence-summary/` across 79 files.
- [x] Analyze approach for R4: restore to docs/evidence-summary/ vs RELOCATION_MANIFEST.md
  - Determined recommended Hybrid strategy: restore 16 essential evidence files (M01-M14, STATUS-LEDGER, WITNESS-REPORT, ~316 KB total) to `docs/evidence-summary/` and create `RELOCATION_MANIFEST.md` for historical test runs/artifacts.
- [x] Audit README.md claims (e.g., "184,276 requests") against evidence
  - Traced exact source to `WITNESS-REPORT-W2-2026-09-11.md` Section 5.
- [x] Test Verification Gates:
  - pytest tests/ --collect-only -q (2,127 tests collected, 0 errors, PASS)
  - python tools/t00_meta_audit.py (FAILED due to base path mapping in tests/internal/, root-caused and fix specified)
  - python tools/adversarial_goal3_probe.py (203/203 probes passed, PASS)
  - tools/create_snapshot_manifest.py (FileNotFoundError on deleted reports, fix specified)
- [x] Define integration test specs for proving the CRITICAL chain is severed
- [x] Compile comprehensive spec_report.md
- [x] Compile handoff.md and send message to orchestrator_6
