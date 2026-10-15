# Dispatch for explorer_m4_1

**Milestone**: M4 — Evidence Restoration, Zero Dangling References & Hygiene (F17-F25)
**Working Directory**: `D:\scp\.agents\explorer_m4_1`

## Investigation Scope
1. **F17 & F18 (Evidence Restoration & Relocation Manifest)**:
   - Investigate commit `87d78da~1` for deleted closure records (`docs/evidence-summary/` or `circuit-closures/`).
   - Identify the 16 essential evidence files needed by tests and tools (e.g. `WITNESS-REPORT-W2-2026-09-11.md`, closure records referenced by tests or docs).
   - Design the restoration to `docs/evidence-summary/`.
   - Design `RELOCATION_MANIFEST.md` documenting git provenance, hashes, and original vs relocated paths for all deleted files.
2. **F19 (Dangling References)**:
   - Search for all references to `docs/evidence-summary/` or deleted evidence across the repo (`grep -rn "circuit-closures"`).
   - Detail how to update these references to point to `docs/evidence-summary/` or `RELOCATION_MANIFEST.md` so that `grep -rn "reports/circuit-closures"` returns 0 dangling hits.
3. **F20 & F21 (Doc Links & Tool Paths)**:
   - Inspect `README.md` claims that cite specific numbers and verify they link to `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md`.
   - Inspect `tools/t00_meta_audit.py` (around line 356) and `tools/create_snapshot_manifest.py` for path checks expecting old files, and formulate the exact fixes.
4. **F22 (Debris Cleanup)**:
   - Locate `prev_ask_impl.py` and `sleeps.txt` in git status/repo and confirm safe deletion without breaking imports.
5. **F23 (Hardcoded Token in Verifier)**:
   - Inspect `tools/e2e_live_cluster_verifier.py:100` for fallback admin token and formulate secure fix.
6. **F24 (FactSeparator Tautology)**:
   - Inspect `scp/knowledge/domain_knowledge.py:526-532` for FactSeparator "verified" = 2-token overlap tautology and formulate genuine semantic/factual verification logic.
7. **F25 (Observability Passwords & Compose Port Binding)**:
   - Inspect `docker-compose.observability.yml` and `docker-compose.test.yml` for passwords in plaintext and `0.0.0.0` port bindings; formulate secure `127.0.0.1` binding and env var configuration.

## Required Output
Write your comprehensive findings to `D:\scp\.agents\explorer_m4_1\handoff.md`.
Follow the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
When complete, notify parent orchestrator via `send_message`.

## 2026-09-22T20:00:19Z
You are explorer_m4_1.
Your working directory is D:\scp\.agents\explorer_m4_1.
You MUST read D:\scp\.agents\ORIGINAL_REQUEST.md before starting work.
Also read D:\scp\.agents\explorer_m4_1\DISPATCH.md and D:\scp\.agents\orchestrator_7\PROJECT.md.

Your mission:
Investigate Milestone M4 (Features F17-F25):
- F17 & F18: Evidence restoration from commit 87d78da~1 to docs/evidence-summary/ and creation of RELOCATION_MANIFEST.md.
- F19: Batch fixing all dangling references to docs/evidence-summary/ across documentation and code.
- F20 & F21: README.md verifiable evidence links, tools/t00_meta_audit.py:356, and tools/create_snapshot_manifest.py paths.
- F22: Removal of dead files prev_ask_impl.py and sleeps.txt.
- F23: Removal of hardcoded admin token in tools/e2e_live_cluster_verifier.py:100.
- F24: Fixing FactSeparator 2-token overlap tautology in scp/knowledge/domain_knowledge.py:526-532.
- F25: docker-compose observability passwords and compose.test port binding to 127.0.0.1.

Write your findings to D:\scp\.agents\explorer_m4_1\handoff.md following the Handoff Protocol.
When complete, notify parent orchestrator via send_message.
