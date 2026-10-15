# Dispatch for worker_m2_3

**Milestone**: M2 Remediation (Iteration 2)
**Working Directory**: `D:\scp\.agents\worker_m2_3`

## Context & Gate Feedback from Iteration 1
Remediate the 5 specific issues identified during Milestone M2 gate review:
1. **Critical HMAC stripping downgrade in `scp/core/autonomous_ledger.py`**:
   - In `verify_provenance()`: Whenever `self.hmac_key` is configured on the ledger, every entry with `event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT")` MUST have `recorded_hmac`. If `recorded_hmac` is missing or empty, fail closed:
     ```python
     if self.hmac_key and event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT"):
         if not recorded_hmac:
             errors.append(f"missing_hmac_{'intent' if event == 'AUTONOMOUS_TOOL_INTENT' else 'result'}:{i}")
             continue
     ```
   - Bind `timestamp` (`str(fields.get("timestamp", ""))`) into the canonical dictionary for both Intent and Result blocks so timing cannot be forged.
   - Add test `test_autonomous_ledger_hmac_stripping_rejected` to `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py` verifying that deleting `hmac_sha256` from a record causes `verify_provenance()` to return `hash_chain_valid=False` and `missing_hmac_*` in errors.
2. **Restore Test Invariant in `tests/T03_capability/test_egress_enforcement.py`**:
   - Restore line 492 to `assert gated >= 12`.
3. **Fix `PlaywrightBackend.validate_url()` in `scp/web_control/playwright_backend.py`**:
   - Ensure tests in `tests/T03_capability/test_playwright_backend.py` pass (e.g. allow `example.com` or check `self.allow_internal`).
4. **Harden PowerShell Subexpression Execution in `scp/capabilities/tools.py`**:
   - In `SafeCommandRunnerTool.evaluate_command()`: check for unquoted parentheses or subexpressions (e.g. `r"\([^\)]*\)"`) to block `echo (whoami)` and `dir (...)`.
5. **Harden 301/302 Redirects in `scp/security/url_safety.py:safe_urlopen`**:
   - Subclass `urllib.request.HTTPRedirectHandler` to intercept redirects and re-validate destination URLs with `validate_url` and `enforce_egress_policy`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run tests:
1. `pytest tests/T03_capability/ -q`
2. `pytest tests/T04_kernel/ -q`
3. `pytest tests/T05_gateway/ -q`
4. `python tools/adversarial_goal3_probe.py`
5. `pytest tests/ --collect-only -q`

Write handoff report to `D:\scp\.agents\worker_m2_3\handoff.md` and notify parent orchestrator via `send_message`.
