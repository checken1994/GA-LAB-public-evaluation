# Dispatch for worker_m4_1

## 2026-09-22T21:59:17Z

**Milestone**: M4 — Evidence Restoration, Zero Dangling References & Hygiene (F17-F25)
**Working Directory**: `D:\scp\.agents\worker_m4_1`

## Implementation Tasks
Read `D:\scp\.agents\explorer_m4_1\handoff.md` for exact blueprints, git commands, and code diffs:

1. **F17: Restore 16 Essential Files to `docs/evidence-summary/`**:
   - Create directory `docs/evidence-summary/`
   - Restore all 16 files from git commit `87d78da~1`:
     - `docs/evidence-summary/M01-closure.json` through `M14-closure.json` -> `docs/evidence-summary/Mxx-closure.json`
     - `docs/evidence-summary/STATUS-LEDGER.md` -> `docs/evidence-summary/STATUS-LEDGER.md`
     - `reports/witness/WITNESS-REPORT-W2-2026-09-11.md` -> `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md`
2. **F18: Create `RELOCATION_MANIFEST.md`**:
   - Create `RELOCATION_MANIFEST.md` at repository root documenting the git provenance, commit SHA `87d78da~1` (`3d08b466144e5485458ee30623253b27b165bf29`), retrieval instructions, and categorized manifest for all 471 pruned files.
3. **F19: Fix Dangling References to `docs/evidence-summary/`**:
   - Batch update references in tracked files pointing to `docs/evidence-summary/` so they point to `docs/evidence-summary/` or cite `RELOCATION_MANIFEST.md`.
   - NOTE ON CONCURRENT WRITES: Do NOT modify `scp/runtime/judge.py`, `scp/task_kernel_parts/taskkernel.py`, `scp/core/top_systems_learning.py`, or `scp/core/chat_memory_store.py` (which are currently being modified by worker_m3_1). You can update all other files in `scp/`, `tests/`, and docs.
   - Verify `git grep -rn "reports/circuit-closures"` returns 0 (excluding files currently locked by M3).
4. **F20 & F21: README.md, Meta-Audit & Snapshot Manifest**:
   - In `README.md`: link claims to `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md` and `docs/evidence-summary/STATUS-LEDGER.md`.
   - In `tools/t00_meta_audit.py:361`: update `b_code = get_git_content(trusted_base, norm_path) or get_git_content(trusted_base, base_path)` so that tests relocated to `tests/internal/` pass cleanly without false regression counts.
   - In `tools/create_snapshot_manifest.py:22-26`: update `REQUIRED_PATHS` with active paths.
5. **F22: Remove Debris Files**:
   - Delete dead files `prev_ask_impl.py` and `sleeps.txt`.
6. **F23: Remove Hardcoded Token in `tools/e2e_live_cluster_verifier.py:100`**:
   - Replace static string with ephemeral `secrets.token_hex(16)` when env vars are absent.
7. **F24: Fix FactSeparator Tautology in `scp/knowledge/domain_knowledge.py:526-532`**:
   - Implement entity-grounded, stopword-filtered semantic matching (require entity present, minimum 3 content words, >= 60% overlap) to eliminate the 2-token overlap tautology.
8. **F25: Observability Compose Passwords & Test Port Binding**:
   - In `docker-compose.observability.yml`: replace `GF_SECURITY_ADMIN_PASSWORD=scp_admin` with `${GRAFANA_ADMIN_PASSWORD:-}` and bind all ports to `127.0.0.1`.
   - In `compose.test.yml`: bind port 8080 to `127.0.0.1:8080:8000`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run tests:
1. `python tools/t00_meta_audit.py`
2. `python tools/create_snapshot_manifest.py --commit HEAD --output test_manifest.json`
3. `pytest tests/T07_learning/test_m2_autonomous_retrieval.py -q`
4. `python tests/reality-tests/reality_4-c-007.py`
5. `pytest tests/ --collect-only -q`

Write handoff report to `D:\scp\.agents\worker_m4_1\handoff.md` and notify parent orchestrator via `send_message`.
