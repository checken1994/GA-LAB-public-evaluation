# Milestone M4 Investigation & Technical Specification Handoff Report

**Agent**: `explorer_m4_1`  
**Working Directory**: `D:\scp\.agents\explorer_m4_1`  
**Target Milestone**: M4 — Evidence Restoration, Zero Dangling References & Repository Hygiene (Features F17–F25)  
**Date**: 2026-09-22T20:10:00Z  
**Type**: Hard Handoff (Investigation & Specification Complete)  
**Parent Orchestrator**: `orchestrator_7` (ID: `81004ee7-0162-4442-9168-937ecae6dd34`)  

---

## 1. Observation

### 1.1 F17 & F18: Commit `87d78da` Forensics & Evidence Files
- **Git Commit Command**: `git show -s --format=fuller 87d78da`
  - Commit SHA: `87d78dae8178b3b0cb6c655b20c32dca943977ee`
  - Parent SHA: `3d08b466144e5485458ee30623253b27b165bf29` (`87d78da~1`)
  - Author/Date: `zcode-agent`, Mon Sep 21 10:29:08 2026 +07:00
  - Commit Subject: `"chore: Relocate non-source artifacts, reports, archives, and agent directives out of repository"`
  - Diff Stat: `500 files changed, 152699 deletions(-)`
- **Pruned File Breakdown**:
  - `reports/`: 442 files (including `docs/evidence-summary/`: 214 files, `reports/expert-panel/`: 77 files, `reports/runtime_8002_...`: 28 files, `reports/system_audit_strict/`: 15 files).
  - `archive/`: 28 files.
  - `research/`: 1 file (`research/continual_learning.ipynb`).
  - `.agents/`: 27 files (subsequently restored in commit `ed71733`).
  - `AGENTS.md` and `GA.md`: 2 files (subsequently restored in commit `ed71733`).
  - **Net Absent Files**: Exactly **471 files** absent from working tree (442 in `reports/`, 28 in `archive/`, 1 in `research/`).
- **Essential Evidence Files at `87d78da~1`**:
  - Execution of `git cat-file -e 87d78da~1:<path>` confirmed the existence of all 16 essential evidence and contract files:
    1. `docs/evidence-summary/M01-closure.json` (35.9 KB, blob `22d6e653055408f92d50eff24a74643df0d83653`)
    2. `docs/evidence-summary/M02-closure.json` (20.1 KB, blob `29749eb72c676dd3f88f01b333cfc85775f0a719`)
    3. `docs/evidence-summary/M03-closure.json` (21.5 KB, blob `2d93e110cb1577771746f334a1b02008779b76eb`)
    4. `docs/evidence-summary/M04-closure.json` (24.2 KB, blob `e26a457493a7c64c12563345d3fa961ef05eb093`)
    5. `docs/evidence-summary/M05-closure.json` (11.9 KB, blob `b2488e36fa7885b59bb93fe6f7a7990c885bb4a0`)
    6. `docs/evidence-summary/M06-closure.json` (18.4 KB, blob `ecfcbb6a4f91ef52cb8b62562ccf7d7aa7e8d64d`)
    7. `docs/evidence-summary/M07-closure.json` (10.5 KB, blob `cfa99d14697bfd237190ca6440db42c4483ae594`)
    8. `docs/evidence-summary/M08-closure.json` (8.2 KB, blob `e8964d4229bb1f057c7d425cff2f0b9f0e13bc8c`)
    9. `docs/evidence-summary/M09-closure.json` (10.3 KB, blob `364e032549a04a600cb8490a07159c3cf2be84a7`)
    10. `docs/evidence-summary/M10-closure.json` (20.5 KB, blob `0b200b3e7bf97f804fc903d3bc95ba6f49e41980`)
    11. `docs/evidence-summary/M11-closure.json` (11.1 KB, blob `c683b544b82d431f087d8a6e4313f89063858066`)
    12. `docs/evidence-summary/M12-closure.json` (22.9 KB, blob `654a9386d49495444ca93945cf45a165b4c10a11`)
    13. `docs/evidence-summary/M13-closure.json` (15.9 KB, blob `9f9c73562624cfca7fa35bfbc7811efaa756e18f`)
    14. `docs/evidence-summary/M14-closure.json` (11.3 KB, blob `f750b3e551e70e94e50882e30f146a48d88e6a2b`)
    15. `docs/evidence-summary/STATUS-LEDGER.md` (55.3 KB, blob `ff3e6beee6302251ee2bc3d6797cb3984ca5cf91`)
    16. `reports/witness/WITNESS-REPORT-W2-2026-09-11.md` (7.1 KB, blob `c4062f6b8665da98eec8e7b9be9b60da42323e44`)
  - Total combined footprint: ~316 KB (100% structured JSON and Markdown, zero binary databases or ephemeral test logs).

### 1.2 F19: Census of Dangling References Across Repository
- `git grep -n "circuit-closures"` yielded **82 exact hits** across the tracked tree:
  - **72 Python files** in `scp/`: each contains line 1 or 2 with comment:  
    `# SCP CIRCUIT: Mxx ... (closure: docs/evidence-summary/Mxx-closure.json)`  
    (e.g., `scp/api_server.py:1`, `scp/api/chat.py:1`, `scp/ask_kernel_adapter.py:1`, `scp/consolidator/consolidator.py:1`, `scp/core/agent_orchestrator.py:1`, `scp/hands/hands_executor.py:1`, etc.).
  - **4 test files**:
    - `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py:14`: `docs/evidence-summary/M03-closure.json`
    - `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py:23,470`: `docs/evidence-summary/M03-evidence/_probe_failure_triggers.py`
    - `tests/T03_capability/test_flow_04_control_hands_scp_standard.py:34`: `docs/evidence-summary/INVENTORY/M4.txt`
    - `tests/T03_capability/test_mcp_server.py:1`: `docs/evidence-summary/M04-closure.json`
    - `tests/T03_capability/test_playwright_backend.py:1`: `docs/evidence-summary/M04-closure.json`
  - **1 README.md**:
    - `README.md:26`: `Closure records: [docs/evidence-summary/](docs/evidence-summary/) · Witness: [reports/witness/](reports/witness/)`
    - `README.md:29`: `([STATUS-LEDGER](docs/evidence-summary/STATUS-LEDGER.md))`
  - **1 hello_bug.py**:
    - `scp/hello_bug.py:4`: `# closure (docs/evidence-summary/M07-closure.json, probe commit 1f00d00):`
  - **1 dead debris file**:
    - `prev_ask_impl.py:1`: `# SCP CIRCUIT: M02 ... (closure: docs/evidence-summary/M02-closure.json)`
- Additional references to pruned `reports/` files:
  - `README.md:34` & `GA.md:179`: `reports/witness/WITNESS-REPORT-W2-2026-09-11.md`
  - `tests/T04_kernel/test_ask_kernel_lifecycle_and_identity.py:7`: `reports/witness/WITNESS-REPORT-W2-2026-09-11.md`
  - `tests/T04_kernel/test_ask_kernel_lifecycle_and_identity.py:19`: `reports/expert-panel/S19-ask-kernel-fixes.md`
  - `scp/ask_kernel_adapter.py:977` & `scp/runtime/question_router.py:5`: `reports/benchmark-2026-09-12/bench_combined_seed2026.json`
  - `tests/T07_learning/test_judge_knowledge_wire.py:3`: `reports/expert-panel/ARCH-AUDIT-B-knowledge.md`
  - `tests/T03_capability/test_egress_enforcement.py:491`: `reports/expert-panel/EE-G1-client-method-census.json`
  - `tools/create_snapshot_manifest.py:22-26`: references 5 deleted `reports/` files in `REQUIRED_PATHS`.

### 1.3 F20 & F21: README Evidence Claims, Meta-Audit & Snapshot Manifest
- **README.md Claims Verification**:
  - `README.md:41`: `| Soak 5.5 phút | **184,276 requests, zero error**, RSS +14MB (no leak) |`
  - `git show 87d78da~1:reports/witness/WITNESS-REPORT-W2-2026-09-11.md` Section 5 states:
    `Phase 1 (150s, C=16 direct): 138,094 requests`  
    `Phase 2 (120s, C=8 through SCP provider code): 46,159 requests`  
    `Total real requests served by the witness API in 5.5 min: 184,276. HTTP errors: 0.`  
    Memory: `RSS +14.2 MB across 5.5 min`.
- **`tools/t00_meta_audit.py:356` Root Cause**:
  - Code at lines 354–362:
    ```python
    for norm_path in normalized_paths:
        if norm_path.startswith("tests/internal/"):
            base_path = norm_path.replace("tests/internal/", "scp/tests/", 1)
        else:
            base_path = norm_path
        c_code = get_local_content(norm_path)
        b_code = get_git_content(trusted_base, base_path)
        new_v, debts = audit_content(c_code, b_code or "", norm_path)
    ```
  - In `origin/main`, `scp/tests/` was already moved to `tests/internal/` (commit `6d6256f`).
  - Therefore, `git cat-file -e origin/main:scp/tests/external_audit/test_security.py` fails with:
    `fatal: path 'scp/tests/external_audit/test_security.py' does not exist in 'origin/main'`
  - Because `b_code` returns `None` (`""`), historical skips in `test_security.py` are misclassified:
    `new violations = 2 debts = 0` (causing T00 Meta-Audit failure).
  - Tested with corrected fallback:
    `b_code = get_git_content(trusted_base, norm_path) or get_git_content(trusted_base, base_path)`  
    Result: `new violations = 0 debts = 2` (PASS).
- **`tools/create_snapshot_manifest.py` Crash**:
  - Running `python tools/create_snapshot_manifest.py --commit HEAD --output test.json` crashed with:
    `FileNotFoundError: required tracked path missing at 7344c1e...: reports/SCP_KERNEL_ASK_INTEGRATION_REPORT_20260825.md`
  - Caused by hardcoded `REQUIRED_PATHS` containing 5 pruned files from `reports/`.

### 1.4 F22: Dead Files `prev_ask_impl.py` and `sleeps.txt`
- `prev_ask_impl.py`: 876-line dead copy of old `_ask_impl.py`.
- `sleeps.txt`: 47-line text file containing raw grep results of sleep calls.
- `git grep "prev_ask_impl"` and `git grep "sleeps.txt"` return 0 references across the entire codebase.

### 1.5 F23: Hardcoded Token in `tools/e2e_live_cluster_verifier.py:100`
- `tools/e2e_live_cluster_verifier.py:96-101`:
  ```python
  return (
      os.environ.get("SCP_AUTH_TOKEN_SECRET")
      or os.environ.get("SCP_ADMIN_KEY")
      or os.environ.get("SCP_AUTH_PASSWORD")
      or "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
  )
  ```
- Hardcoded string `"scp-v3-68fcc2ae7dac74cc436decf214cae8cc"` at line 100 violates fail-closed secret handling.

### 1.6 F24: FactSeparator 2-Token Overlap Tautology
- `scp/knowledge/domain_knowledge.py:526-532`:
  ```python
  # Token overlap check
  c_tokens = {w.lower() for w in claim.text.split() if len(w) > 2}
  t_tokens = {w.lower() for w in text.split() if len(w) > 2}
  if c_tokens and t_tokens:
      overlap = c_tokens & t_tokens
      if len(overlap) >= 2 or (len(overlap) / len(c_tokens)) >= 0.5:
          return True
  ```
- Also lines 444-446:
  ```python
  s_tokens = {w.lower() for w in sentence.split() if len(w) > 2}
  snip_tokens = {w.lower() for w in snippet.split() if len(w) > 2}
  if s_tokens and snip_tokens and (len(s_tokens & snip_tokens) >= 2 or len(s_tokens & snip_tokens) / len(s_tokens) >= 0.4):
  ```
- Any two words of length > 2 (e.g. "the", "and", "was", "for", "cho", "các", "của") that appear in both the claim and evidence triggers `len(overlap) >= 2 -> return True`, declaring an ungrounded claim "verified".
- Furthermore, `claim.value is not None` (lines 519-525) checks `str(claim.value) in text_lower`: matching isolated digits (like `"1"` or `"0"`) anywhere in evidence falsely verifies the claim.

### 1.7 F25: Observability Passwords and Docker Compose Port Bindings
- `docker-compose.observability.yml`:
  - Line 24: Plaintext admin password: `GF_SECURITY_ADMIN_PASSWORD=scp_admin`.
  - Lines 9, 10, 18, 31, 38: Ports bound to all interfaces (`0.0.0.0`): `"4317:4317"`, `"4318:4318"`, `"9090:9090"`, `"3000:3000"`, `"3100:3100"`.
- `compose.test.yml`:
  - Line 11: Backend exposed on all interfaces: `"8080:8000"`.

---

## 2. Logic Chain

1. **Evidence Restoration (F17 & F18)**:
   - *From Obs 1.1*: Commit `87d78da` deleted 152,699 lines to remove ephemeral test logs and raw terminal outputs. However, it also swept away the 14 closure JSONs, the master STATUS-LEDGER.md, and the independent witness report.
   - *Inference*: Restoring all 500 files would re-introduce massive bloat (18k-line JSONs, sqlite WAL binaries). Restoring only the 16 core structured files (~316 KB) to `docs/evidence-summary/` restores verification grounding with minimal repo footprint.
   - *Inference*: Creating `RELOCATION_MANIFEST.md` in repository root documents the provenance of all 471 pruned files at git commit `87d78da~1` (`3d08b46`), providing exact `git show` commands for retrieving any raw log.
2. **Dangling References Elimination (F19)**:
   - *From Obs 1.2*: 82 references in live code/tests point to `docs/evidence-summary/`.
   - *Inference*: Updating the 72 Python header comments to point to `docs/evidence-summary/Mxx-closure.json` and updating test docstrings/comments to cite `docs/evidence-summary/` or `RELOCATION_MANIFEST.md` ensures `git grep -rn "reports/circuit-closures"` returns exactly 0 hits.
3. **README Claims and Verification Tooling (F20 & F21)**:
   - *From Obs 1.3*: The README soak test claim (184,276 requests) is verified word-for-word in Section 5 of `WITNESS-REPORT-W2-2026-09-11.md`. Updating README links to `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md` makes this claim verifiable on disk.
   - *From Obs 1.3*: `tools/t00_meta_audit.py` fails because `origin/main` has tests at `tests/internal/`, while the audit script was hardcoded to look only at `scp/tests/` in the baseline. Checking `norm_path` first resolves the regression false positive and makes `t00_meta_audit.py` pass cleanly.
   - *From Obs 1.3*: `tools/create_snapshot_manifest.py` crashes on 5 missing paths in `REQUIRED_PATHS`. Replacing them with `docs/evidence-summary/STATUS-LEDGER.md`, `WITNESS-REPORT-W2-2026-09-11.md`, and `RELOCATION_MANIFEST.md` restores snapshot creation.
4. **Debris Cleanup (F22)**:
   - *From Obs 1.4*: `prev_ask_impl.py` and `sleeps.txt` have zero importers and zero callers. Their deletion eliminates dead code without side effects.
5. **Verifier Credential Hardening (F23)**:
   - *From Obs 1.5*: Static fallback token `"scp-v3-68fcc2ae7dac74cc436decf214cae8cc"` in `tools/e2e_live_cluster_verifier.py:100` creates a hardcoded secret vulnerability.
   - *Inference*: Replacing it with an ephemeral secure token `secrets.token_hex(32)` when environment variables are absent maintains functionality while preventing hardcoded secret leakage.
6. **FactSeparator Semantic Grounding (F24)**:
   - *From Obs 1.6*: `len(overlap) >= 2` allows false positives on common stopwords.
   - *Inference*: Factual verification must enforce entity grounding (entity present in evidence text), stopword filtering (English & Vietnamese), and a high fraction of content-token overlap (>= 60% of significant words with a minimum of 3 content words), preventing tautological verification.
7. **Compose Hardening (F25)**:
   - *From Obs 1.7*: Binding services to `0.0.0.0` and using static passwords exposes observability services.
   - *Inference*: Explicitly binding to `127.0.0.1` and using `${GRAFANA_ADMIN_PASSWORD:-}` restricts access to localhost and allows deployment-specific secrets.

---

## 3. Caveats

1. **Historical Terminal Logs Remain in Git History**: Raw execution traces (`docs/evidence-summary/M*-evidence/*.txt`, ~150K lines) are intentionally NOT restored to disk to preserve repository hygiene. They remain fully recoverable via `git show 87d78da~1:<path>`.
2. **Reality Test `reality_4-c-007.py`**:
   - `tests/reality-tests/reality_4-c-007.py` line 74 asserts: `assert "reports/" in src and "scp/" in src` on `dashboard/src/components/dashboard/closing-section.tsx`.
   - *Caution*: When modifying `closing-section.tsx` or documentation, ensure the note referencing canonical repository paths preserves the `reports/` and `scp/` tokens, or update `reality_4-c-007.py` simultaneously so the reality test does not break.
3. **Execution Responsibility**: This subagent performed read-only exploration and technical specification. Actual file edits, file restorations, and git commits belong to the implementer role.

---

## 4. Conclusion & Concrete Implementation Specifications

### F17: Restore 16 Essential Files to `docs/evidence-summary/`
Create directory `docs/evidence-summary/` and restore via git:
```bash
mkdir -p docs/evidence-summary
git show 87d78da~1:docs/evidence-summary/M01-closure.json > docs/evidence-summary/M01-closure.json
git show 87d78da~1:docs/evidence-summary/M02-closure.json > docs/evidence-summary/M02-closure.json
git show 87d78da~1:docs/evidence-summary/M03-closure.json > docs/evidence-summary/M03-closure.json
git show 87d78da~1:docs/evidence-summary/M04-closure.json > docs/evidence-summary/M04-closure.json
git show 87d78da~1:docs/evidence-summary/M05-closure.json > docs/evidence-summary/M05-closure.json
git show 87d78da~1:docs/evidence-summary/M06-closure.json > docs/evidence-summary/M06-closure.json
git show 87d78da~1:docs/evidence-summary/M07-closure.json > docs/evidence-summary/M07-closure.json
git show 87d78da~1:docs/evidence-summary/M08-closure.json > docs/evidence-summary/M08-closure.json
git show 87d78da~1:docs/evidence-summary/M09-closure.json > docs/evidence-summary/M09-closure.json
git show 87d78da~1:docs/evidence-summary/M10-closure.json > docs/evidence-summary/M10-closure.json
git show 87d78da~1:docs/evidence-summary/M11-closure.json > docs/evidence-summary/M11-closure.json
git show 87d78da~1:docs/evidence-summary/M12-closure.json > docs/evidence-summary/M12-closure.json
git show 87d78da~1:docs/evidence-summary/M13-closure.json > docs/evidence-summary/M13-closure.json
git show 87d78da~1:docs/evidence-summary/M14-closure.json > docs/evidence-summary/M14-closure.json
git show 87d78da~1:docs/evidence-summary/STATUS-LEDGER.md > docs/evidence-summary/STATUS-LEDGER.md
git show 87d78da~1:reports/witness/WITNESS-REPORT-W2-2026-09-11.md > docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md
```

### F18: Create `RELOCATION_MANIFEST.md`
Place `RELOCATION_MANIFEST.md` at repo root with sections:
- Git baseline snapshot: Commit `3d08b466144e5485458ee30623253b27b165bf29` (`87d78da~1`).
- Relocation explanation: Ephemeral execution traces pruned; structured contracts relocated.
- Retrieval instructions: `git show 87d78da~1:<path>`.
- Categorized table mapping all 471 pruned files.

### F19: Batch Update Dangling References
1. In all 72 `scp/` files, replace:
   `docs/evidence-summary/M([0-9]{2})-closure.json` with `docs/evidence-summary/M$1-closure.json`
2. In `scp/hello_bug.py:4`, replace `docs/evidence-summary/` with `docs/evidence-summary/`.
3. In `tests/T02_contract/test_flow_03_openai_compat_scp_standard.py`:
   - Line 14: `docs/evidence-summary/M03-closure.json` → `docs/evidence-summary/M03-closure.json`
   - Lines 23, 470: cite `RELOCATION_MANIFEST.md` (`87d78da~1:docs/evidence-summary/M03-evidence/_probe_failure_triggers.py`).
4. In `tests/T03_capability/test_flow_04_control_hands_scp_standard.py:34`:
   - Cite `RELOCATION_MANIFEST.md` (`87d78da~1:docs/evidence-summary/INVENTORY/M4.txt`).
5. In `tests/T03_capability/test_mcp_server.py:1` & `test_playwright_backend.py:1`:
   - `docs/evidence-summary/M04-closure.json` → `docs/evidence-summary/M04-closure.json`.
6. In `tests/T04_kernel/test_ask_kernel_lifecycle_and_identity.py:7`:
   - `reports/witness/WITNESS-REPORT-W2-2026-09-11.md` → `docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md`.

### F20 & F21: README.md & Tooling Fixes
1. In `README.md`:
   - Line 26: `[docs/evidence-summary/](docs/evidence-summary/) · Witness: [reports/witness/](reports/witness/)` → `[docs/evidence-summary/](docs/evidence-summary/)`
   - Line 29: `([STATUS-LEDGER](docs/evidence-summary/STATUS-LEDGER.md))` → `([STATUS-LEDGER](docs/evidence-summary/STATUS-LEDGER.md))`
   - Line 34: `[báo cáo đầy đủ](reports/witness/WITNESS-REPORT-W2-2026-09-11.md)` → `[báo cáo đầy đủ](docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md)`
2. In `tools/t00_meta_audit.py`:
   Line 361:
   ```python
   b_code = get_git_content(trusted_base, norm_path) or get_git_content(trusted_base, base_path)
   ```
3. In `tools/create_snapshot_manifest.py`:
   Update lines 22-26:
   ```python
   REQUIRED_PATHS = (
       ".github/workflows/scp-release-gate.yml",
       "scp/api_server.py",
       "scp/task_kernel.py",
       "scp/ask_kernel_adapter.py",
       "scp/autofix/restricted_exec.py",
       "scp/runtime/safe_math.py",
       "scp/history/migration.py",
       "scp/core/knowledge_io.py",
       "docs/evidence-summary/STATUS-LEDGER.md",
       "docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md",
       "docs/evidence-summary/M01-closure.json",
       "docs/evidence-summary/M02-closure.json",
       "RELOCATION_MANIFEST.md",
       "tools/summarize_bandit_report.py",
   )
   ```

### F22: Dead Files Removal
Execute:
```bash
git rm prev_ask_impl.py sleeps.txt
```

### F23: Verifier Hardcoded Token Removal
In `tools/e2e_live_cluster_verifier.py:96-101`:
```python
    token = (
        os.environ.get("SCP_AUTH_TOKEN_SECRET")
        or os.environ.get("SCP_ADMIN_KEY")
        or os.environ.get("SCP_AUTH_PASSWORD")
    )
    if token:
        return token
    import secrets
    return f"scp-ephemeral-{secrets.token_hex(16)}"
```

### F24: FactSeparator Tautology Fix
In `scp/knowledge/domain_knowledge.py`:
1. Define stop words set (`STOPWORDS = {"the", "and", "is", "of", "to", "in", "for", "with", "that", "this", "là", "của", "và", "ở", "có", "cho", "với", "được", "các", "một", "trong", "những", "này", "đó"}`).
2. In `_is_match(claim: Claim, text: str) -> bool`:
   - Exact substring match (`claim.text.lower() in text_lower`) → `return True`.
   - Entity-target co-occurrence (`claim.entity and claim.target`): if entity and target both present → `return True`.
   - Numeric check: require entity present AND `str(claim.value)` in `text_lower`.
   - Content token overlap:
     ```python
     c_tokens = {w.lower() for w in claim.text.split() if len(w) > 2 and w.lower() not in STOPWORDS}
     t_tokens = {w.lower() for w in text.split() if len(w) > 2 and w.lower() not in STOPWORDS}
     if c_tokens and t_tokens:
         overlap = c_tokens & t_tokens
         if len(overlap) >= 3 and (len(overlap) / len(c_tokens)) >= 0.6:
             return True
     ```
3. Update fallback loop (lines 444–446) with identical stopword and ratio threshold logic.

### F25: Observability Passwords & Compose Port Binding
1. In `docker-compose.observability.yml`:
   - Change `GF_SECURITY_ADMIN_PASSWORD=scp_admin` to `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-}`.
   - Bind all ports to `127.0.0.1`:
     - `"127.0.0.1:4317:4317"`
     - `"127.0.0.1:4318:4318"`
     - `"127.0.0.1:9090:9090"`
     - `"127.0.0.1:3000:3000"`
     - `"127.0.0.1:3100:3100"`
2. In `compose.test.yml`:
   - Line 11: change `"8080:8000"` to `"127.0.0.1:8080:8000"`.

---

## 5. Verification Method

1. **Verify Evidence Restoration (F17 & F18)**:
   ```bash
   python -c "
   import os
   for i in range(1, 15):
       assert os.path.exists(f'docs/evidence-summary/M{i:02d}-closure.json')
   assert os.path.exists('docs/evidence-summary/STATUS-LEDGER.md')
   assert os.path.exists('docs/evidence-summary/WITNESS-REPORT-W2-2026-09-11.md')
   assert os.path.exists('RELOCATION_MANIFEST.md')
   print('F17/F18 files verified.')
   "
   ```
2. **Verify Zero Dangling References (F19)**:
   ```bash
   git grep -rn "reports/circuit-closures"
   ```
   *Expected*: Exactly 0 results returned.
3. **Verify Meta-Audit (F20 & F21)**:
   ```bash
   python tools/t00_meta_audit.py
   ```
   *Expected*: Passes with `0 new regressions`.
4. **Verify Snapshot Manifest Tool (F21)**:
   ```bash
   python tools/create_snapshot_manifest.py --commit HEAD --output test_manifest.json
   ```
   *Expected*: Exits with code 0 and valid JSON output.
5. **Verify Debris Deletion (F22)**:
   ```bash
   python -c "import os; assert not os.path.exists('prev_ask_impl.py'); assert not os.path.exists('sleeps.txt'); print('Debris verified absent.')"
   ```
6. **Verify Verifier Token Absence (F23)**:
   ```bash
   git grep "scp-v3-68fcc2ae7dac74cc436decf214cae8cc"
   ```
   *Expected*: 0 matches.
7. **Verify FactSeparator Reality Test (F24)**:
   ```bash
   pytest tests/T07_learning/test_m2_autonomous_retrieval.py -q
   ```
   *Expected*: All tests pass.
8. **Verify Compose Configuration (F25)**:
   ```bash
   grep -n "0.0.0.0" docker-compose.observability.yml compose.test.yml
   grep -n "scp_admin" docker-compose.observability.yml
   ```
   *Expected*: 0 matches.
9. **Verify Overall Test Suite Integrity**:
   ```bash
   pytest tests/ --collect-only -q
   python tests/reality-tests/reality_4-c-007.py
   ```
   *Expected*: 2,127+ tests collected with 0 errors, reality test passes.
