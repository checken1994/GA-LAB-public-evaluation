# Dispatch for worker_m2_2

**Milestone**: M2 Remediation (Iteration 2)
**Working Directory**: `D:\scp\.agents\worker_m2_2`

## Context & Gate Feedback from Iteration 1
Reviewers and Challengers reported REQUEST_CHANGES on 5 specific items:
1. **Critical Security Fix in `scp/core/autonomous_ledger.py`**:
   - In `verify_provenance()`: Whenever `self.hmac_key` is configured on the ledger, every entry with `event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT")` MUST have `recorded_hmac`. If `recorded_hmac` is missing or empty, fail closed:
     ```python
     if self.hmac_key and event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT"):
         if not recorded_hmac:
             errors.append(f"missing_hmac_{'intent' if event == 'AUTONOMOUS_TOOL_INTENT' else 'result'}:{i}")
             continue
     ```
   - Bind `timestamp` (`str(fields.get("timestamp", ""))`) into the canonical dictionary for both Intent and Result blocks so timing cannot be forged.
   - Add an adversarial test to `tests/T04_kernel/test_autonomous_audit_ledger_provenance.py` verifying that stripping `hmac_sha256` from a record causes `verify_provenance()` to fail with `missing_hmac_*`.
2. **Restore Test Invariant in `tests/T03_capability/test_egress_enforcement.py`**:
   - Restore line 492 to `assert gated >= 12` (the AST scanner already detects 12 gated sites with `ast.Await` support).
3. **Fix `PlaywrightBackend.validate_url()` in `scp/web_control/playwright_backend.py`**:
   - `test_playwright_backend.py` tests `http://example.com`.
   - In `validate_url()`: Only enforce egress if not `self.allow_internal`, or permit `example.com` when running in test mode/allowlist, or pass `extra_allowed_hosts={"example.com"}` if `self.allow_internal`. Ensure all tests in `tests/T03_capability/test_playwright_backend.py` pass.
4. **Harden PowerShell Subexpression Execution in `scp/capabilities/tools.py`**:
   - In `SafeCommandRunnerTool.evaluate_command()`: check for unquoted parentheses or subexpressions (e.g. `r"\([^\)]*\)"` or `r"(?<![a-zA-Z0-9_-])\("`) in `BLOCKED_PATTERNS` or chaining checks to block `echo (whoami)` and `dir (...)`.
5. **Harden 301/302 Redirects in `scp/security/url_safety.py:safe_urlopen`**:
   - Subclass `urllib.request.HTTPRedirectHandler` to intercept redirects and re-validate the target URL through `validate_url(redirect_url)` and `enforce_egress_policy(redirect_url)` before following, preventing redirect SSRF.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run tests:
1. `pytest tests/T03_capability/ -q`
2. `pytest tests/T04_kernel/ -q`
3. `pytest tests/T05_gateway/ -q`
4. `python tools/adversarial_goal3_probe.py`
5. `pytest tests/ --collect-only -q`

Write handoff report to `D:\scp\.agents\worker_m2_2\handoff.md` and notify parent orchestrator via `send_message`.

## 2026-09-23T03:37:01Z
You are worker_m2_2.
Your working directory is D:\scp\.agents\worker_m2_2.
You MUST read D:\scp\.agents\ORIGINAL_REQUEST.md before starting work.
Also read D:\scp\.agents\worker_m2_2\DISPATCH.md, D:\scp\.agents\orchestrator_7\PROJECT.md, and the gate feedback in:
- D:\scp\.agents\reviewer_m2_1\handoff.md
- D:\scp\.agents\reviewer_m2_2\handoff.md
- D:\scp\.agents\challenger_m2_1\handoff.md
- D:\scp\.agents\challenger_m2_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your mission:
Remediate the 5 specific issues identified during Milestone M2 gate review:
1. Critical HMAC stripping downgrade in scp/core/autonomous_ledger.py: fail closed if recorded_hmac is missing when hmac_key is configured. Bind timestamp into canonical HMAC dictionary. Add test to tests/T04_kernel/test_autonomous_audit_ledger_provenance.py.
2. Restore line 492 of tests/T03_capability/test_egress_enforcement.py to assert gated >= 12.
3. Fix PlaywrightBackend.validate_url() so test_playwright_backend.py tests pass.
4. Block PowerShell subexpression execution `(...)` in SafeCommandRunnerTool.evaluate_command().
5. Validate 301/302 redirect URLs in safe_urlopen against validate_url and enforce_egress_policy.

Verify all fixes with pytest and tools/adversarial_goal3_probe.py.
Write your complete handoff report to D:\scp\.agents\worker_m2_2\handoff.md.
When complete, notify parent orchestrator via send_message.

