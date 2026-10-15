# Dispatch for worker_m2_1

**Milestone**: M2 — Wire Unwired Security Modules into Production Runtime (F07, F08, F09) & F14 Interaction
**Working Directory**: `D:\scp\.agents\worker_m2_1`

## Implementation Tasks

### 1. Feature F07: Wire `SafeCommandRunnerTool` into Production Runtime
Read `D:\scp\.agents\explorer_m2_1\handoff.md` for full blueprints and logic.
- `scp/capabilities/tools.py`:
  - Incorporate blocked patterns from autonomous governor (`chmod -R 777`, `chown -R`, `nc -e`, `bash -i`, `/dev/tcp/`, `> /dev/sda`).
  - In `evaluate_command()`, scan both raw command and normalized command (`re.sub(r'[\'\"\\]', '', cmd)`).
  - Add safe `echo` (`r"^\s*echo(?:\s+[^\s;&|><`$]+)*\s*$"`) to `READ_ONLY_ALLOWLIST`.
- `scp/hands/action_registry.py`:
  - Import `from scp.capabilities.tools import SafeCommandRunnerTool, SystemInspectionTool, WorkspaceAnalysisTool`.
  - Register `cmd.run`, `sys.inspect`, and `workspace.analyze` actions. (Note: do NOT add `pc.execute` as it is intentionally excluded from ActionRegistry).
- `scp/security/autonomous_governor.py`:
  - Import `from scp.capabilities.tools import SafeCommandRunnerTool`.
  - In `evaluate_and_grant_step()`, delegate command safety checking for `("pc.execute", "cmd.run")` to `SafeCommandRunnerTool.evaluate_command()`.
- `scp/hands/hands_executor.py`:
  - Import `from scp.capabilities.tools import SafeCommandRunnerTool, SystemInspectionTool, WorkspaceAnalysisTool`.
  - Instantiate tools in `__init__`.
  - In `execute()`, add dispatch branches for `cmd.run`, `sys.inspect`, and `workspace.analyze`.

### 2. Feature F08 & F14: Wire `EgressPolicy` into `url_safety.py` and Close DNS Rebinding / Dev-Default OPEN
Read `D:\scp\.agents\explorer_m2_2\handoff.md` for full blueprints and logic.
- `scp/policy/egress.py`:
  - Update `EgressDeniedError` to accept `url` and set `self.url = url or target` and `self.target = target`.
  - Update `EgressDestination.from_url` to inspect `url.full_url` if present (`hasattr(url, "full_url")`).
- `scp/security/url_safety.py`:
  - Import `from scp.policy.egress import EgressPolicy, EgressDeniedError, EgressDestination, EgressMode`.
  - In `enforce_egress_policy()`, delegate directly to `EgressPolicy().enforce(...)`.
  - Remove dev-default OPEN (lines 121-122). When `SCP_EGRESS_MODE` is unset, default to `allowlist` (fail-closed, loopback only).
  - Eliminate TOCTOU DNS window in `safe_urlopen()` by porting socket-level pinned connection handler (`_PinnedHTTPHandler` / `_PinnedHTTPSHandler`) from `scp/core/url_fetcher.py`.
- `scp/llm_gateway/egress_policy.py`:
  - Import `from scp.policy.egress import EgressPolicy, EgressDeniedError`.
  - Delegate `llm_egress_allowed()` through `EgressPolicy(allowlist=...)`.
  - Remove dev-default OPEN on line 70.
- `scp/web_control/playwright_backend.py`:
  - In `validate_url()`, call `enforce_egress_policy(clean_url)`.
- `scp/security/egress_static_scan.py`:
  - Add `ast.Await` support in `_is_client_expr` so `await self._get_client()` in `client.py:423` is recognized.
- `tests/T03_capability/test_egress_enforcement.py`:
  - Adjust latch count check in `test_g2_scp_tree_has_no_unpinned_client_method_calls` to `assert gated >= 10` (accounting for the 2 historical deleted files).
  - Update any tests expecting dev-default OPEN to assert fail-closed.

### 3. Feature F09: `AutonomousAuditLedger` HMAC-SHA256 & Two-Phase Commit in `HandsExecutor`
Read `D:\scp\.agents\explorer_m2_3\handoff.md` for full blueprints and logic.
- `scp/core/autonomous_ledger.py`:
  - Add HMAC-SHA256 support to `ProvenanceBlock` and `AutonomousAuditLedger` (`hmac_key` param and `SCP_LEDGER_HMAC_KEY` env var).
  - Embed `hmac_sha256` signatures and `hmac-sha256:` keyed digests.
  - In `verify_provenance()`, verify HMAC signatures with `hmac.compare_digest`.
  - Preserve backward compatibility when unkeyed (`sha256:` prefix).
- `scp/hands/hands_executor.py`:
  - Import `from scp.core.autonomous_ledger import AutonomousAuditLedger`.
  - In `__init__`, initialize `self.audit_ledger`.
  - In `execute()`, implement Two-Phase Commit: Phase 1 (Intent) before action execution; Phase 2 (Outcome) post-execution linked by `intent_entry_hash`.
  - Enrich return result with `intentHash`, `outcomeHash`, and `ledgerSeq`.
  - Ensure unauthenticated requests fail-closed without orphan ledger records.
- Add tests to `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py` covering HMAC signing, Probe 4.7 tamper detection, and two-phase commit verification.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run builds, lint, and tests:
1. `pytest tests/T03_capability/ -q`
2. `pytest tests/T04_kernel/ -q`
3. `pytest tests/T05_gateway/ -q`
4. `python tools/adversarial_goal3_probe.py`
5. `pytest tests/ --collect-only -q`
6. Verify production callers via:
   - `grep -rn "from scp.capabilities.tools import" scp/`
   - `grep -rn "from scp.policy.egress import" scp/`
   - `grep -rn "from scp.core.autonomous_ledger import" scp/`

Write handoff report to `D:\scp\.agents\worker_m2_1\handoff.md` and notify parent orchestrator via `send_message`.

## 2026-09-22T19:59:36Z
Invoked as worker_m2_1 with mission:
Implement Milestone M2:
1. Feature F07: Wire SafeCommandRunnerTool (scp/capabilities/tools.py) into ActionRegistry, AutonomousCapabilityGovernor, and HandsExecutor.
2. Feature F08 & F14: Wire EgressPolicy (scp/policy/egress.py) into url_safety.py delegation across all runtime network callers, remove dev-default OPEN, and close TOCTOU DNS rebinding window in safe_urlopen via pinned socket connection.
3. Feature F09: Add HMAC-SHA256 to AutonomousAuditLedger (scp/core/autonomous_ledger.py) and wire two-phase commit into HandsExecutor.execute().

Verify all changes by running pytest test suites and tools/adversarial_goal3_probe.py.
Confirm that grep -rn for all 3 modules under scp/ shows genuine production callers.
Write complete handoff report to D:\scp\.agents\worker_m2_1\handoff.md following the Handoff Protocol.
When complete, notify parent orchestrator via send_message.
