# Milestone M2 Independent Review & Adversarial Challenge Report

**Reviewer Agent**: `reviewer_m2_2`  
**Working Directory**: `D:\scp\.agents\reviewer_m2_2`  
**Parent Agent**: `orchestrator_7` (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Worker Reviewed**: `worker_m2_1`  
**Milestone**: M2 (Wire Security Modules into Production Runtime)  
**Timestamp**: 2026-09-22T20:26:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct observations from codebase inspection, empirical test runs, and adversarial exploit probing:

### 1.1 Test Suite Execution Results
- `pytest tests/T03_capability/ -q`: **FAILED** (exit code 1)
  - Result: `9 failed, 794 passed, 2 skipped, 2 warnings in 118.65s`
  - Direct regressions in `tests/T03_capability/test_playwright_backend.py`:
    1. `FAILED test_validate_url_allows_clean_url`
    2. `FAILED test_missing_playwright_package_fails_closed`
    3. `FAILED test_navigator_opt_in_with_missing_playwright_fails_closed_at_call_time`
  - Verbatim error:
    ```text
    scp\policy\egress.py:156: EgressDeniedError: egress denied for 'https://example.com/page?q=1': Host not present in egress allowlist: []
    ```
- `pytest tests/T04_kernel/ -q`: **PASSED** (266 passed, 23 skipped in 61.10s)
- `pytest tests/T05_gateway/ -q`: **PASSED** (70 passed in 8.13s)
- `pytest tests/ --collect-only -q`: **PASSED** (2,147 tests collected, 0 collection errors in 2.95s)
- `python tools/adversarial_goal3_probe.py`: **PASSED** (Total=203, Passed=203, Failed=0)

### 1.2 Signature Stripping / Cryptographic Downgrade in `AutonomousAuditLedger`
In `scp/core/autonomous_ledger.py:186-224`, `verify_provenance()` contains:
```python
recorded_hmac = fields.get("hmac_sha256")
if recorded_hmac and event == "AUTONOMOUS_TOOL_INTENT":
    ...
elif recorded_hmac and event == "AUTONOMOUS_TOOL_RESULT":
    ...
```
If an adversary strips the `hmac_sha256` field from an autonomous record, `recorded_hmac` is `None`. The block verification is skipped, and `verify_provenance()` returns `{"hash_chain_valid": True, "errors": []}`.

Empirical verification in Python:
```python
ledger = AutonomousAuditLedger(ledger_path=lp, hmac_key="secret")
intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
# Adversary strips hmac_sha256, alters tool_name to 'forged.malicious_action', recalculates outer sha256
v = ledger.verify_provenance()
# Observation: {'entries': 1, 'hash_chain_valid': True, 'errors': []}
```

### 1.3 Premature/Erroneous Wiring in `PlaywrightBackend.validate_url`
In `scp/web_control/playwright_backend.py:162-163`:
```python
enforce_egress_policy(clean_url)
validate_safe_url(clean_url, allow_internal=self.allow_internal)
return clean_url
```
`PlaywrightBackend.validate_url()` is called during URL sanitization. In default test configurations where `SCP_EGRESS_MODE` defaults to `allowlist` (with empty `SCP_EGRESS_ALLOWLIST`), `backend.validate_url("https://example.com/page?q=1")` raises `EgressDeniedError`. Furthermore, `test_missing_playwright_package_fails_closed` and `test_navigator_opt_in_with_missing_playwright_fails_closed_at_call_time` crash before testing missing playwright imports.

### 1.4 Production Wiring Verified
- `scp/hands/action_registry.py` registers `cmd.run`, `sys.inspect`, and `workspace.analyze`.
- `scp/hands/hands_executor.py` imports and invokes `SafeCommandRunnerTool`, `SystemInspectionTool`, `WorkspaceAnalysisTool`, and Two-Phase Commit via `AutonomousAuditLedger`.
- `scp/security/autonomous_governor.py` delegates command validation to `SafeCommandRunnerTool.evaluate_command()`.
- `scp/security/url_safety.py` pins socket TCP connections to `resolved_ip` via `_PinnedHTTPConnection` and `_PinnedHTTPSConnection`.

---

## 2. Logic Chain

1. **Test Failure Logic**:
   - `worker_m2_1` reported in `handoff.md` that targeted M2 test suites passed (87 passed).
   - However, dispatch required executing `pytest tests/T03_capability/ -q`.
   - Running `pytest tests/T03_capability/ -q` produced 9 failures.
   - Specifically, 3 tests in `tests/T03_capability/test_playwright_backend.py` are direct regressions caused by adding `enforce_egress_policy(clean_url)` inside `PlaywrightBackend.validate_url()`.
   - Audit requirement R2-03 specified adding egress enforcement in `BrowserSession.navigate_and_read` and `open_visible`, NOT `PlaywrightBackend.validate_url()`.
   - Therefore, the codebase currently suffers from a regression in `T03_capability`.

2. **Cryptographic Integrity Logic**:
   - Feature F09 required adding HMAC-SHA256 to `AutonomousAuditLedger` to prevent ledger tampering where an attacker recalculates bare SHA-256 hashes.
   - While `commit_intent()` and `commit_result()` generate HMAC-SHA256 signatures, `verify_provenance()` gates verification behind `if recorded_hmac:`.
   - If an attacker strips `hmac_sha256` from a tampered record, `recorded_hmac` evaluates to `None`, bypassing HMAC validation completely while the bare SHA-256 chain passes.
   - This represents an integrity vulnerability (signature stripping downgrade). When `self.hmac_key` is configured, missing HMAC signatures must fail verification.

---

## 3. Caveats

1. **Pre-existing T03 Failures**:
   - 5 of the 9 failures in `tests/T03_capability/` (`test_flow_14`, `test_flow_20`, `test_flow_21`) stem from earlier refactorings where `audit_r8` and `audit_r9` were moved to `docs/audit_history/`, which are scheduled for cleanup in Milestone M3 / M4 (`F15`, `F19`).
   - 1 failure in `test_flow_34_swe_bench_scp_standard.py` is caused by rate-limiting crosstalk when the full suite triggers multiple 401s prior to that test; running `test_flow_34` in isolation passes cleanly.
   - The remaining 3 failures (`test_playwright_backend.py`) are new regressions introduced in M2.
2. **HTTP 302 Redirect Re-pinning**:
   - `safe_urlopen` pins the initial socket connection to `resolved_ip`. If a remote host issues an HTTP 301/302 redirect, `urllib.request.HTTPRedirectHandler` follows the redirect without invoking `validate_url` on the redirect target. This is noted as a future hardening opportunity.

---

## 4. Conclusion & Required Changes

**Verdict**: **REQUEST_CHANGES**

Before Milestone M2 can be approved, `worker_m2_1` (or the remediating worker) must address:

### Required Changes:
1. **Fix Signature Stripping Vulnerability in `AutonomousAuditLedger.verify_provenance()`**:
   - Location: `scp/core/autonomous_ledger.py:186-224`
   - In `verify_provenance()`, when `self.hmac_key` is set, any entry with `event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT")` that lacks `hmac_sha256` or has an invalid signature MUST append an error (e.g. `errors.append(f"missing_hmac:{i}")`).
2. **Resolve Regression in `PlaywrightBackend` / Egress Gate**:
   - Location: `scp/web_control/playwright_backend.py:162`
   - Remove `enforce_egress_policy(clean_url)` from `PlaywrightBackend.validate_url()`, or ensure `validate_url()` allows clean URLs while egress enforcement is properly scoped to actual navigation boundaries (such as `BrowserSession.navigate_and_read` and `open_visible` as per R2-03).
   - Verify that `pytest tests/T03_capability/test_playwright_backend.py` passes 31/31 tests cleanly.
3. **Verify Full Capability Test Suite**:
   - Run `pytest tests/T03_capability/test_playwright_backend.py -v` (must show 0 failures).
   - Ensure no regressions were introduced to previously passing tests.

---

## 5. Verification Method

1. **Verify Playwright Backend Tests**:
   ```powershell
   pytest tests/T03_capability/test_playwright_backend.py -v
   ```
   *Expected post-fix*: 31 passed, 0 failed.

2. **Verify HMAC Stripping Tamper Detection**:
   ```powershell
   python -c "
   import json, hashlib, tempfile
   from pathlib import Path
   from scp.core.autonomous_ledger import AutonomousAuditLedger

   with tempfile.TemporaryDirectory() as td:
       lp = Path(td) / 'test.jsonl'
       ledger = AutonomousAuditLedger(ledger_path=lp, hmac_key='secret-key')
       intent = ledger.commit_intent('t1', 's1', 'pc.status', {}, {'token_id': 'tok', 'signature': 'sig'})
       
       # Attacker strips HMAC and recalculates bare SHA-256
       lines = lp.read_text().splitlines()
       data = json.loads(lines[0])
       data['fields'].pop('hmac_sha256', None)
       data['fields']['tool_name'] = 'forged.malicious_action'
       body = {k: v for k, v in data.items() if k != 'hash'}
       data['hash'] = 'sha256:' + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
       lp.write_text(json.dumps(data) + '\n')
       
       res = ledger.verify_provenance()
       assert res['hash_chain_valid'] is False, 'HMAC stripping must be detected!'
       assert any('missing_hmac' in err or 'hmac' in err for err in res['errors'])
       print('PASS: HMAC stripping correctly caught')
   "
   ```

3. **Verify All Milestone M2 Suites**:
   ```powershell
   pytest tests/T04_kernel/ -q
   pytest tests/T05_gateway/ -q
   pytest tests/ --collect-only -q
   python tools/adversarial_goal3_probe.py
   ```
