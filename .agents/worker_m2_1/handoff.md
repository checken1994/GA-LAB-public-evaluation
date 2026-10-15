# Milestone M2 Implementation Handoff Report

**Agent**: worker_m2_1  
**Working Directory**: `D:\scp\.agents\worker_m2_1`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-22T20:15:00Z  
**Type**: Hard Handoff (Milestone M2 Completed)  

---

## 1. Observation

Direct observations from codebase inspection, tool executions, and empirical test harnesses:

1. **Unwired Capabilities in ActionRegistry and HandsExecutor (Feature F07)**:
   - `scp/capabilities/tools.py` provided `SafeCommandRunnerTool`, `SystemInspectionTool`, and `WorkspaceAnalysisTool`, but none were registered in `scp/hands/action_registry.py`.
   - `scp/hands/hands_executor.py` lacked branches for `cmd.run`, `sys.inspect`, and `workspace.analyze`, meaning invocations raised `KeyError` or returned `"Action implementation missing"`.
   - `scp/security/autonomous_governor.py` contained redundant and incomplete blocked regex patterns (`rm -rf`, `mkfs`, `dd`, `nc`, `bash -i`, etc.) rather than delegating command safety to `SafeCommandRunnerTool.evaluate_command()`.
   - `SafeCommandRunnerTool.evaluate_command()` checked generic piping and redirection before testing `BLOCKED_PATTERNS`, which caused blocked commands to return `Command contains disallowed redirection` instead of `Command matches blocked pattern: ...`. Furthermore, `echo` was missing from `READ_ONLY_ALLOWLIST`.

2. **Divergent Egress Policies, Dev-Default OPEN, and TOCTOU DNS Window (Features F08 & F14)**:
   - `scp/policy/egress.py` defined `EgressPolicy`, but `scp/security/url_safety.py` implemented a separate `enforce_egress_policy()` routine with dev-default OPEN behavior when `SCP_EGRESS_MODE` was unset.
   - `scp/llm_gateway/egress_policy.py` maintained a separate allowlist mechanism instead of delegating to `EgressPolicy`.
   - `scp/security/url_safety.py:safe_urlopen()` performed DNS resolution during URL validation (`validate_url()`), but opened the connection using standard `urllib.request.urlopen()`, introducing a Time-Of-Check to Time-Of-Use (TOCTOU) DNS rebinding window.
   - `scp/web_control/playwright_backend.py:validate_url()` did not invoke `enforce_egress_policy()`.
   - Static scan `scp/security/egress_static_scan.py` lacked `ast.Await` support in `_is_client_expr()`, failing to catch `await self._get_client()` in `client.py:423`.

3. **Autonomous Audit Ledger Missing HMAC-SHA256 & 2PC in Hands (Feature F09)**:
   - `scp/core/autonomous_ledger.py` only computed bare `sha256:` hashes without HMAC authentication, allowing an attacker to recalculate the hash chain if a record was modified.
   - `HandsExecutor.execute()` emitted events to `audit.jsonl` but did not execute Two-Phase Commit (2PC) into `AutonomousAuditLedger` (Intent commit before action dispatch, Outcome commit after execution).
   - `from scp.core.autonomous_ledger import AutonomousAuditLedger` had zero callers across `scp/`.

4. **Empirical Verification Baseline**:
   - Baseline adversarial probe `tools/adversarial_goal3_probe.py` showed 203/203 passed.
   - Existing unit tests across `tests/T03_capability/` and `tests/T04_kernel/` verified capability epoch enforcement, but highlighted gaps in unified policy enforcement.

---

## 2. Logic Chain

From the observations above, the implementation followed a structured, fail-closed derivation:

1. **Wiring Feature F07 (SafeCommandRunnerTool & Autonomous Tools)**:
   - Added `chmod -R 777`, `chown -R`, `nc -e`, `bash -i`, `/dev/tcp/`, and `> /dev/sda` to `SafeCommandRunnerTool.BLOCKED_PATTERNS`.
   - Added `echo` to `SafeCommandRunnerTool.READ_ONLY_ALLOWLIST` to permit safe status verification commands.
   - Reordered `SafeCommandRunnerTool.evaluate_command()` to check `BLOCKED_PATTERNS` (both raw command and quote/backslash-normalized command) *before* checking generic redirection and piping.
   - Registered `cmd.run` (level 1), `sys.inspect` (level 0), and `workspace.analyze` (level 0) in `scp/hands/action_registry.py`.
   - Delegated command validation in `AutonomousCapabilityGovernor.evaluate_and_grant_step()` directly to `SafeCommandRunnerTool(working_dir=working_dir).evaluate_command()`.
   - Added dispatch branches in `HandsExecutor.execute()` for `cmd.run`, `sys.inspect`, and `workspace.analyze`.

2. **Wiring Features F08 & F14 (EgressPolicy & TOCTOU Elimination)**:
   - Updated `EgressDeniedError` in `scp/policy/egress.py` to support `(target, reason, url=None)` retaining attributes `self.url` and `self.target`.
   - Modified `EgressDestination.from_url()` to extract destination metadata from `url.full_url` if present.
   - Updated default `SCP_EGRESS_MODE` when unset or empty from `"open"` to `"allowlist"` (fail-closed, loopback only).
   - Delegated `scp/security/url_safety.py:enforce_egress_policy()` directly to `EgressPolicy().enforce(...)`.
   - Implemented `_PinnedHTTPConnection`, `_PinnedHTTPSConnection`, `_PinnedHTTPHandler`, and `_PinnedHTTPSHandler` in `scp/security/url_safety.py`. In `safe_urlopen()`, resolved the IP address once, validated it against private/reserved/cloud-metadata ranges, and injected a custom opener that establishes the TCP connection directly to the verified IP while passing the original Host header and TLS SNI hostname. This closes the TOCTOU DNS rebinding window.
   - Replaced custom allowlist logic in `scp/llm_gateway/egress_policy.py` with `EgressPolicy(allowlist=...)`, enforcing fail-closed behavior for external LLMs.
   - Delegated `scp/llm_gateway/client.py:_llm_egress_allowed()` to `llm_egress_allowed()`.
   - Added `enforce_egress_policy(clean_url)` inside `scp/web_control/playwright_backend.py:validate_url()`.
   - Enhanced `scp/security/egress_static_scan.py` to unwrap `ast.Await` expressions.
   - Updated assertions in `tests/T03_capability/test_egress_enforcement.py` to match the fail-closed default.

3. **Wiring Feature F09 (HMAC-SHA256 & 2PC in HandsExecutor)**:
   - Added `compute_hmac(key)` and `compute_hash(key=None)` methods to `ProvenanceBlock` in `scp/core/autonomous_ledger.py`.
   - Added `hmac_key` initialization to `AutonomousAuditLedger` (reading optional constructor parameter or `os.environ.get("SCP_LEDGER_HMAC_KEY")`).
   - Updated `commit_intent` and `commit_result` to generate HMAC-SHA256 signatures prefixed with `hmac-sha256:`.
   - Updated `verify_provenance()` to verify HMAC signatures using constant-time `hmac.compare_digest()`.
   - Wired `AutonomousAuditLedger` into `HandsExecutor.__init__()`, obtaining `hmac_key` from `SCP_LEDGER_HMAC_KEY` or `self.capability_authority.secret`.
   - Integrated Two-Phase Commit in `HandsExecutor.execute()`:
     - Phase 1: `self.audit_ledger.commit_intent(...)` before action dispatch.
     - Phase 2: `self.audit_ledger.commit_result(...)` after execution.
     - Enriched execution result with `intentHash`, `outcomeHash`, and `ledgerSeq`.

---

## 3. Caveats

1. **Docker Container Tests Skipped**:
   `tests/T03_capability/test_egress_enforcement.py::test_h_container_deny_blocks_example_com_m13_reversal` and `test_h_container_deny_loopback_health_and_endpoint_fail_closed` were skipped because Docker is not available in the local execution environment. All non-containerized network, loopback, and static scan tests executed and passed.
2. **Backward Compatibility**:
   `AutonomousAuditLedger` maintains full backward compatibility for unkeyed instances; when `hmac_key` is `None` or empty, standard SHA-256 digests (`sha256:...`) are generated and verified.

---

## 4. Conclusion

Milestone M2 is fully implemented, verified, and integrated into the production runtime:
- `SafeCommandRunnerTool` is active in `ActionRegistry`, `AutonomousCapabilityGovernor`, and `HandsExecutor`.
- `EgressPolicy` is unified across all network callers (`url_safety.py`, `egress_policy.py`, `client.py`, `playwright_backend.py`), dev-default OPEN is removed (defaulting to fail-closed allowlist), and TOCTOU DNS rebinding in `safe_urlopen()` is prevented via socket-pinned HTTP/HTTPS connections.
- `AutonomousAuditLedger` enforces tamper-proof cryptographic provenance with HMAC-SHA256 and constant-time digest comparison, and `HandsExecutor` implements Two-Phase Commit across all executed actions.

Grep search confirms active, genuine production callers across `scp/`:
- `scp/hands/action_registry.py`, `scp/hands/hands_executor.py`, `scp/security/autonomous_governor.py` import `SafeCommandRunnerTool` from `scp.capabilities.tools`.
- `scp/capabilities/tools.py`, `scp/llm_gateway/egress_policy.py`, `scp/security/url_safety.py` import `EgressPolicy` from `scp.policy.egress`.
- `scp/hands/hands_executor.py` imports `AutonomousAuditLedger` from `scp.core.autonomous_ledger`.

---

## 5. Verification Method

To independently verify this implementation:

1. **Verify Production Grep Callers**:
   ```powershell
   python -c "
   import glob, re
   for pat, d in [(r'from scp\.capabilities\.tools import', 'scp'), (r'from scp\.policy\.egress import', 'scp'), (r'from scp\.core\.autonomous_ledger import', 'scp')]:
       for p in glob.glob(f'{d}/**/*.py', recursive=True):
           for l in open(p, encoding='utf-8', errors='ignore'):
               if re.search(pat, l): print(f'{p}: {l.strip()}')
   "
   ```
   **Expected**: 3 matches for `tools`, 3 matches for `egress`, 1 match for `autonomous_ledger`.

2. **Execute Targeted M2 Pytest Suites**:
   ```powershell
   pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v
   ```
   **Expected**: 87 passed, 2 skipped in ~8s.

3. **Execute Adversarial Goal 3 Probe (Egress & Tamper Probes)**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   **Expected**: Total=203, Passed=203, Failed=0.

4. **Verify Full Test Collection**:
   ```powershell
   pytest --collect-only -q
   ```
   **Expected**: 2,137 tests collected without syntax or import errors.

### Invalidation Conditions
This handoff is invalidated if:
- `SafeCommandRunnerTool.evaluate_command` permits chained or disallowed redirection commands.
- `safe_urlopen` connects to an IP different from the pre-validated IP address (TOCTOU re-emergence).
- Modifying a field in `autonomous_ledger.jsonl` passes `verify_provenance()` when HMAC is enabled.
- Unauthenticated requests bypass 2PC checks or generate orphaned intent records.
