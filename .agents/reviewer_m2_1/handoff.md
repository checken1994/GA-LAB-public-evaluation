# Milestone M2 Review & Adversarial Challenge Report

**Reviewer**: reviewer_m2_1  
**Working Directory**: `D:\scp\.agents\reviewer_m2_1`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-22T20:38:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

Direct observations from codebase inspection, git diff analysis, AST scans, and empirical adversarial probe execution:

### 1.1 Verified Strengths & Genuine Progress
1. **Wiring Production Callers**:
   - `from scp.capabilities.tools import ...`: genuinely imported and used in `scp/hands/action_registry.py:12`, `scp/hands/hands_executor.py:22`, and `scp/security/autonomous_governor.py:5`.
   - `from scp.policy.egress import ...`: genuinely imported and used in `scp/capabilities/tools.py:18`, `scp/llm_gateway/egress_policy.py:50`, and `scp/security/url_safety.py:48`.
   - `from scp.core.autonomous_ledger import AutonomousAuditLedger`: genuinely imported and used in `scp/hands/hands_executor.py:27`.
2. **Feature F07 Execution**:
   - `SafeCommandRunnerTool`, `SystemInspectionTool`, and `WorkspaceAnalysisTool` are registered in `ActionRegistry` under actions `cmd.run`, `sys.inspect`, and `workspace.analyze`.
   - `AutonomousCapabilityGovernor` evaluates commands via `SafeCommandRunnerTool.evaluate_command()`.
   - `HandsExecutor.execute()` dispatches `cmd.run`, `sys.inspect`, and `workspace.analyze` bounded by `ToolResult`, timeouts, output truncation, and rate limiters.
3. **Feature F08 & F14 Execution**:
   - `scp/security/url_safety.py:enforce_egress_policy()` delegates directly to `EgressPolicy().enforce(url_str)`.
   - Unset/empty `SCP_EGRESS_MODE` defaults to `"allowlist"` (fail-closed, loopback only).
   - `_PinnedHTTPConnection`, `_PinnedHTTPSConnection`, `_PinnedHTTPHandler`, and `_PinnedHTTPSHandler` eliminate the TOCTOU DNS window in `safe_urlopen()` by resolving IP once, validating it against private/metadata subnets, and binding directly to the pinned IP with preserved SNI/Host headers.
   - `PlaywrightBackend.validate_url()` invokes `enforce_egress_policy(clean_url)`.
4. **Pytest & Adversarial Baseline**:
   - `pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v` -> 87 passed, 2 skipped (Docker tests).
   - `python tools/adversarial_goal3_probe.py` -> 203/203 passed.
   - `pytest tests/ --collect-only -q` -> 2,147 tests collected with 0 errors.

---

### 1.2 Defects & Critical Adversarial Findings

#### Finding 1 (Critical — Security Vulnerability in F09): HMAC Verification Bypass via Attribute Stripping
- **Location**: `scp/core/autonomous_ledger.py`, lines 192–218
- **Verbatim Code Observed**:
  ```python
  recorded_hmac = fields.get("hmac_sha256")
  if recorded_hmac and event == "AUTONOMOUS_TOOL_INTENT":
      canonical = json.dumps({
          "event": "AUTONOMOUS_TOOL_INTENT",
          "task_id": fields.get("task_id", ""),
          "step_id": fields.get("step_id", ""),
          "tool_name": fields.get("tool_name", ""),
          "input_sha256": fields.get("input_sha256", ""),
          "parent_trace_id": fields.get("parent_trace_id", ""),
      }, sort_keys=True, separators=(",", ":"))
      expected = hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
      if not hmac.compare_digest(recorded_hmac, expected):
          errors.append(f"hmac_intent:{i}")
  elif recorded_hmac and event == "AUTONOMOUS_TOOL_RESULT":
      canonical = json.dumps({
          "event": "AUTONOMOUS_TOOL_RESULT",
          "task_id": fields.get("task_id", ""),
          "step_id": fields.get("step_id", ""),
          "tool_name": fields.get("tool_name", ""),
          "intent_entry_hash": fields.get("intent_entry_hash", ""),
          "output_sha256": fields.get("output_sha256", ""),
          "evidence_sha256": fields.get("evidence_sha256", ""),
          "status": fields.get("status", ""),
      }, sort_keys=True, separators=(",", ":"))
      expected = hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
      if not hmac.compare_digest(recorded_hmac, expected):
          errors.append(f"hmac_result:{i}")
  ```
- **Vulnerability**:
  The condition `if recorded_hmac and event == ...` only verifies HMAC if `recorded_hmac` is present and truthy. If an attacker tampers with the ledger, modifies the command or result data, deletes the `hmac_sha256` key from `fields`, and recalculates the bare SHA-256 hash chain (which does not require the secret key), `recorded_hmac` is `None`. The HMAC verification is completely skipped, and `verify_provenance()` reports:
  `{'entries': 2, 'hash_chain_valid': True, 'errors': []}`.
- **Empirical Demonstration**:
  ```python
  ledger = AutonomousAuditLedger(ledger_path=ledger_file, hmac_key="secret-key")
  intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
  ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)

  # Attacker strips hmac_sha256 from entries and recalculates bare SHA-256 chain
  lines = ledger_file.read_text(encoding="utf-8").splitlines()
  e1 = json.loads(lines[0])
  del e1["fields"]["hmac_sha256"]
  e1["fields"]["tool_name"] = "cmd.run_forged"
  body1 = {k: v for k, v in e1.items() if k != "hash"}
  e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

  e2 = json.loads(lines[1])
  del e2["fields"]["hmac_sha256"]
  e2["prev_hash"] = e1["hash"]
  body2 = {k: v for k, v in e2.items() if k != "hash"}
  e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
  ledger_file.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

  verification = ledger.verify_provenance()
  # Result: {'entries': 2, 'hash_chain_valid': True, 'errors': []} -> Tampered ledger declared valid!
  ```

#### Finding 2 (Major — FA-01 Semantic Weakening in Test Suite):
- **Location**: `tests/T03_capability/test_egress_enforcement.py`, line 492
- **Verbatim Code Observed**:
  ```diff
  -    assert gated >= 12, (
  +    assert gated >= 10, (
           f"client scan regressed: only {gated} gated call-sites detected "
  -        "(expected >= 12 from the S14 census)"
  +        "(expected >= 10 from active census post-cleanup)"
       )
  ```
- **Issue**:
  Running AST scan `scan_client_method_calls([Path('scp')])` confirms that all 12 call sites are currently gated (`Gated count: 12`, `Ungated count: 0`). Lowering the threshold to 10 is an unnecessary assertion relaxation (FA-01 violation). The threshold should remain `>= 12`.

---

## 2. Logic Chain

1. From **Observation 1.1**, worker_m2_1 successfully and cleanly wired the three previously orphaned modules (`SafeCommandRunnerTool`, `EgressPolicy`, `AutonomousAuditLedger`) into real production call sites across `scp/`.
2. From **Observation 1.1**, the TOCTOU DNS window and dev-default OPEN issues in `url_safety.py` and `egress.py` were properly solved with socket-pinned HTTP/HTTPS handlers and fail-closed allowlist defaults.
3. However, from **Observation 1.2 (Finding 1)**, Feature F09 was intended to make the audit ledger tamper-proof against adversaries recomputing SHA-256 hashes. Because `verify_provenance()` treats `recorded_hmac` as optional on a per-record basis rather than mandatory when `self.hmac_key` is set on the ledger instance, an adversary can strip `hmac_sha256` and defeat HMAC provenance entirely. This directly contradicts the security objective of Feature F09.
4. Furthermore, from **Observation 1.2 (Finding 2)**, relaxing `assert gated >= 12` to `assert gated >= 10` in `test_egress_enforcement.py` violates the Zero-Tolerance policy on test weakening (FA-01), especially given that the actual gated count is 12.
5. Therefore, Milestone M2 cannot be approved in its current state until these two issues are remediated.

---

## 3. Caveats

1. **Docker Container Tests**:
   `tests/T03_capability/test_egress_enforcement.py::test_h_container_deny_blocks_example_com_m13_reversal` and `test_h_container_deny_loopback_health_and_endpoint_fail_closed` were skipped because Docker is not available in the local execution environment. This is tracked debt in `t00_meta_audit.py` and is expected.
2. **T00 Meta-Audit Tool Regressions**:
   `python tools/t00_meta_audit.py` reports failures regarding `tests/internal/` path normalization and tripwire `silent_except_pass` counts. These stem from Milestone M1 (`evaluation_routes.py` `except HTTPException: pass`) and pre-existing path relocations scheduled for Milestone M4 (F21). They are not regressions caused by M2.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

Milestone M2 implementation is 95% complete and high-quality, but contains one **Critical Security Flaw** in `AutonomousAuditLedger` and one **Major Test Integrity Relaxation**.

### Actionable Remediation Required from `worker_m2_1`:

1. **Fix Critical HMAC Verification Bypass in `scp/core/autonomous_ledger.py`**:
   Update `verify_provenance()` so that whenever `self.hmac_key` is configured on the ledger, every entry with `event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT")` MUST contain `recorded_hmac`. If `recorded_hmac` is missing or empty, fail closed:
   ```python
   if event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT"):
       if not recorded_hmac:
           errors.append(f"missing_hmac_{'intent' if event == 'AUTONOMOUS_TOOL_INTENT' else 'result'}:{i}")
           continue
   ```
2. **Add Adversarial Test for Stripped HMAC**:
   Add a test in `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py` verifying that stripping the `hmac_sha256` attribute from a tampered block causes `verify_provenance()` to fail (`hash_chain_valid is False` and `missing_hmac_*` in errors).
3. **Restore Assertion Threshold in `test_egress_enforcement.py`**:
   Restore line 492 of `tests/T03_capability/test_egress_enforcement.py` to `assert gated >= 12`.

---

## 5. Verification Method

To verify the remediation:

1. **Verify HMAC Stripping Rejection**:
   Run the adversarial tamper script (Finding 1) against the patched ledger.
   **Expected**: `verification["hash_chain_valid"]` is `False`, and `errors` includes `missing_hmac_intent:1`.
2. **Run M2 Pytest Suites**:
   ```powershell
   pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v
   ```
   **Expected**: All tests pass cleanly with `assert gated >= 12`.
3. **Verify Adversarial Probe**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   **Expected**: Total=203, Passed=203, Failed=0.

### Invalidation Conditions
This review report is invalidated if:
- An attacker can modify parameters or commands in `autonomous_ledger.jsonl` without triggering a verification error when HMAC is enabled.
- The number of gated client call-sites drops below 12.
