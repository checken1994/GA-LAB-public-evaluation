# BRIEFING — 2026-09-22T20:01:00Z

## Mission
Investigate Milestone M4 (Features F17-F25): Evidence Restoration, Relocation Manifest, Dangling References, Doc/Tool Links, Debris Cleanup, Hardcoded Token, FactSeparator Tautology, and Docker/Compose Configs.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: D:\scp\.agents\explorer_m4_1
- Original parent: 81004ee7-0162-4442-9168-937ecae6dd34
- Milestone: M4

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Adhere to Fail-Closed & Evidence-First principles
- Write reports and analysis only to D:\scp\.agents\explorer_m4_1
- Output handoff report handoff.md following 5-Component Handoff Protocol
- Notify parent orchestrator via send_message when complete

## Current Parent
- Conversation ID: 81004ee7-0162-4442-9168-937ecae6dd34
- Updated: 2026-09-22T20:01:00Z

## Investigation State
- **Explored paths**:
  - D:\scp\.agents\ORIGINAL_REQUEST.md
  - D:\scp\.agents\orchestrator_7\PROJECT.md
  - D:\scp\.agents\explorer_m4_1\DISPATCH.md
  - Git history `87d78da` and `87d78da~1`
  - D:\scp\.agents\spec_miner_o6_survey_3\spec_report.md & handoff.md
  - D:\scp\README.md (lines 20-60)
  - D:\scp\tools\t00_meta_audit.py (lines 340-370)
  - D:\scp\tools\create_snapshot_manifest.py (lines 1-70)
  - D:\scp\tools\e2e_live_cluster_verifier.py (lines 80-125)
  - D:\scp\scp\knowledge\domain_knowledge.py (lines 340-534)
  - D:\scp\docker-compose.observability.yml (full file)
  - D:\scp\compose.test.yml (full file)
  - D:\scp\prev_ask_impl.py, sleeps.txt
  - D:\scp\tests\reality-tests\reality_4-c-007.py
  - D:\scp\tests\T02_contract\test_flow_03_openai_compat_scp_standard.py
- **Key findings**:
  - F17/F18: Exactly 16 core structured evidence files (~316 KB) need restoration to `docs/evidence-summary/`. The remaining 455 pruned files in `87d78da` are ephemeral test logs, sqlite WAL dumps, and JSON dumps preserved at commit `87d78da~1` and documented in `RELOCATION_MANIFEST.md`.
  - F19: 82 occurrences explicitly reference `docs/evidence-summary/` across 79 files (72 in scp/ line 1, 4 tests, README.md, scp/hello_bug.py, prev_ask_impl.py). Batch renaming to `docs/evidence-summary/` achieves 0 dangling hits.
  - F20/F21: README claim "184,276 requests" is backed by Section 5 of `WITNESS-REPORT-W2-2026-09-11.md`. `tools/t00_meta_audit.py:356` falsely flags 2 historical skips as new regressions due to `scp/tests/` lookup on `main`; fixing path lookup to check `tests/internal/` first yields 0 new violations. `create_snapshot_manifest.py` crashes on 5 missing historical paths in `REQUIRED_PATHS`; updating to active `docs/evidence-summary/` files resolves it.
  - F22: `prev_ask_impl.py` and `sleeps.txt` have 0 code references and can be deleted safely.
  - F23: `tools/e2e_live_cluster_verifier.py:100` hardcoded static token can be replaced by ephemeral `secrets.token_hex(32)` fallback.
  - F24: `domain_knowledge.py:526-532` `len(overlap) >= 2` token overlap without stopword filtering verified any claim sharing 2 generic words; replaced by entity-grounded, stopword-filtered semantic matching.
  - F25: `docker-compose.observability.yml` exposes 5 ports on `0.0.0.0` and has hardcoded `GF_SECURITY_ADMIN_PASSWORD=scp_admin`; `compose.test.yml` exposes 8080 on `0.0.0.0`. Both must be hardened with `127.0.0.1` bindings and env-based credentials.
- **Unexplored areas**: None for M4. All 9 features fully mapped and verified.

## Key Decisions Made
- Recommended Hybrid Restoration: restore 16 structured evidence files to `docs/evidence-summary/` and document historical logs in `RELOCATION_MANIFEST.md`.
- Confirmed reality test `reality_4-c-007.py` caveat: checks `"reports/" in src` in `closing-section.tsx`.
- Formulated exact code changes and verification commands for all features F17 through F25.

## Artifact Index
- D:\scp\.agents\explorer_m4_1\DISPATCH.md — Dispatch instructions
- D:\scp\.agents\explorer_m4_1\BRIEFING.md — Persistent working memory
- D:\scp\.agents\explorer_m4_1\progress.md — Liveness heartbeat
- D:\scp\.agents\explorer_m4_1\handoff.md — Final handoff report
