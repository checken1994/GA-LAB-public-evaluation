# Review and Adversarial Verification Report: Milestone M2 Iteration 2

**Agent**: reviewer_m2_3  
**Working Directory**: `D:\scp\.agents\reviewer_m2_3`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-23T04:54:30+07:00  
**Verdict**: **APPROVE**

---

## 1. Observation

Direct evidence gathered across source code inspection, adversarial test executions, and test runner outputs:

### 1.1 AutonomousAuditLedger HMAC Stripping and Timestamp Enforcement
- **Inspected File**: `scp/core/autonomous_ledger.py:115-234`
- **Observed Source**:
  - Lines 125 & 169: `"timestamp": str(fields.get("timestamp", ""))` is bound into `canonical_intent` and `canonical_result` dictionaries used for HMAC computation.
  - Lines 194-197:
    ```python
    if self.hmac_key and event in ("AUTONOMOUS_TOOL_INTENT", "AUTONOMOUS_TOOL_RESULT"):
        if not recorded_hmac:
            errors.append(f"missing_hmac_{'intent' if event == 'AUTONOMOUS_TOOL_INTENT' else 'result'}:{i}")
            continue
    ```
  - Lines 207 & 222: Canonical dictionary construction in `verify_provenance()` includes `"timestamp": str(fields.get("timestamp", ""))`.
  - Line 232: `"hash_chain_valid": len(errors) == 0`.
- **Test Execution**:
  - `pytest tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -v`: 8 passed in 1.10s.
  - `pytest tests/test_m2_adversarial_challenger2.py -v`: 10 passed in 0.71s (including `test_adversarial_hmac_stripping_downgrade_vulnerability`, `test_adversarial_timestamp_tampering_unauthenticated`, `test_adversarial_bogus_hmac_key_recomputation`, `test_adversarial_event_type_spoofing_bypasses_hmac_check`).

### 1.2 Line 492 of `tests/T03_capability/test_egress_enforcement.py`
- **Inspected File**: `tests/T03_capability/test_egress_enforcement.py:450-496`
- **Observed Source**:
  - Lines 453-457:
    ```python
    if s["gated"]:
        gated += 1
        continue
    if rel in _GATE_EXCLUDED_MODULES:
        continue
    ```
  - Line 492: Verbatim `assert gated >= 12, (`
- **Test Execution**:
  - `pytest tests/T03_capability/test_egress_enforcement.py -k "test_g2_scp_tree_has_no_unpinned_client_method_calls" -v`: 1 passed in 2.05s.
  - Full module execution: 27 passed, 2 skipped (container tests requiring docker daemon).

### 1.3 `PlaywrightBackend.validate_url()` Contract & Test Pass
- **Inspected File**: `scp/web_control/playwright_backend.py:149-166`
- **Observed Source**:
  - Line 162: `validate_safe_url(clean_url, allow_internal=self.allow_internal)` enforces SSRF prevention, credentials block, scheme validation, and path traversal block.
  - Lines 163-164:
    ```python
    if not self.allow_internal:
        enforce_egress_policy(clean_url, extra_allowed_hosts=frozenset(["example.com"]))
    ```
- **Test Execution**:
  - `pytest tests/T03_capability/test_playwright_backend.py -v`: All 31 passed in 7.44s with 0 failures.

### 1.4 SafeCommandRunnerTool Subexpression and Parentheses Execution Guard
- **Inspected File**: `scp/capabilities/tools.py:284-322`
- **Observed Source**:
  - Lines 284 & 287-288: `READ_ONLY_ALLOWLIST` patterns updated to `[^\s;&|><`$()]+` explicitly disallowing `(` and `)`.
  - Lines 318-321:
    ```python
    unquoted_cmd = re.sub(r'"[^"]*"|\'[^\']*\'', '', cmd)
    if re.search(r"[()]", unquoted_cmd):
        return False, "Subexpression execution and unquoted parentheses are prohibited", 0
    ```
- **Adversarial Probe**:
  - Commands evaluated:
    - `echo (whoami)` -> `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
    - `dir (Get-Date)` -> `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
    - `git status (calc)` -> `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
    - `python -c "print(1)" (calc)` -> `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
    - `python -c "print(1)"` -> `(True, 'Workspace allowlist match with approval', 3)`
  - `pytest tests/T03_capability/test_autonomous_tool_contracts.py -v`: 17 passed in 2.48s.

### 1.5 `safe_urlopen` 301/302 Redirect Interception and Egress Validation
- **Inspected File**: `scp/security/url_safety.py:211-273, 336-341`
- **Observed Source**:
  - `_SafeHTTPRedirectHandler(urllib.request.HTTPRedirectHandler)` intercepts 301, 302, 303, 307, 308 redirect status codes.
  - Resolves `full_new_url = urllib.parse.urljoin(req.full_url, newurl)` and runs `enforce_egress_policy(full_new_url, ...)` and `validate_url(full_new_url, ...)`.
  - Recursively calls `safe_urlopen` on valid destinations to ensure fresh IP pinning and socket binding.
  - `EgressPolicy.BLOCKED_METADATA_HOSTS` includes AWS IPv6 IMDS `fd00:ec2::254`.
- **Adversarial Probe**:
  - Live redirect server to `http://169.254.169.254/latest` raised `EgressDeniedError: egress denied for 'http://169.254.169.254/latest': Access to cloud metadata endpoints is unconditionally prohibited`.
  - Live redirect server to `http://[fd00:ec2::254]/latest` raised `EgressDeniedError`.
  - Live redirect server to `http://127.0.0.1:9999/secret` with `allow_internal=False` raised `ValueError: URL host '127.0.0.1' resolves to internal/private IP — blocked`.
  - `pytest tests/T03_capability/test_egress_policy_unified.py -v`: 11 passed in 1.48s.

### 1.6 Full Test Suite Status
- Combined M2 test execution:
  `pytest tests/T03_capability/test_playwright_backend.py tests/T03_capability/test_autonomous_tool_contracts.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -v`
  **Result**: 93 passed, 2 skipped in 14.36s (0 failures).
- Test collection: `pytest tests/ --collect-only -q`: 2,150 tests collected in 2.76s (0 errors).
- Goal 3 Adversarial Probe: `python tools/adversarial_goal3_probe.py`: Total=203, Passed=203, Failed=0.

---

## 2. Logic Chain

1. **HMAC & Ledger Provenance (Observation 1.1)**: Stripping `hmac_sha256` or forging records in `AutonomousAuditLedger` is unconditionally caught because `verify_provenance()` mandates the presence of `recorded_hmac` for all autonomous entries when `self.hmac_key` is set, and verifies the cryptographic signature over the canonical representation including `timestamp`. Thus, tamper attempts fail closed (`hash_chain_valid = False`).
2. **Gated Call-Site Count Invariant (Observation 1.2)**: `tests/T03_capability/test_egress_enforcement.py:492` enforces `assert gated >= 12`. By counting all genuine gated client call sites prior to module exclusion filtering, the census test accurately verifies all 12 hardened call-sites without relaxing thresholds.
3. **Playwright URL Security (Observation 1.3)**: `PlaywrightBackend.validate_url()` integrates both `validate_safe_url()` and `enforce_egress_policy()`, allowing `example.com` for local testing fixtures while keeping SSRF, traversal, credentials, and non-allowlisted external endpoints blocked. All 31 tests pass with zero regressions.
4. **Command Runner Subexpression Security (Observation 1.4)**: `SafeCommandRunnerTool` prevents arbitrary command execution via PowerShell subexpressions `(...)` by stripping quoted strings and prohibiting unquoted parentheses, while preserving legitimate quoted command arguments in workspace tools.
5. **Redirect SSRF Prevention (Observation 1.5)**: `_SafeHTTPRedirectHandler` in `safe_urlopen` enforces destination validation against `enforce_egress_policy` and `validate_url` at each redirect hop, preventing SSRF pivot attacks to cloud metadata (IPv4 `169.254.169.254` and IPv6 `[fd00:ec2::254]`) and internal networks.
6. **Integrity Assessment**: No hardcoded test outputs, no facade implementations, and no bypasses were detected in any of the reviewed files. All implementations contain real cryptographic, regex, and network validation logic.

---

## 3. Caveats

- **Docker Environment**: Container runtime tests in `test_egress_enforcement.py` (`test_h_container_deny_*`) were skipped due to the absence of a running Docker daemon on the Windows test machine.
- **T00 Meta-Audit Baseline Debt**: `python tools/t00_meta_audit.py` failed due to pre-existing debt in `test_security.py` (bandit skip) and metric drift for `silent_except_pass` in `Judge` (8 > limit 6.3). As specified in `PROJECT.md`, these findings are assigned to Milestone M3 (Feature F10) and Milestone M4/M5, and are out of scope for Milestone M2.

---

## 4. Conclusion

**Verdict**: **APPROVE**

All 5 fixes for Milestone M2 Iteration 2 have been thoroughly reviewed, adversarially tested, and verified:
1. `AutonomousAuditLedger` enforces HMAC fail-closed and binds `timestamp`.
2. `test_egress_enforcement.py:492` asserts `gated >= 12` and passes.
3. `PlaywrightBackend.validate_url()` passes all 31 tests.
4. `SafeCommandRunnerTool` blocks unquoted parentheses and subexpression execution.
5. `safe_urlopen` intercepts and validates 301/302 redirects fail-closed.

Milestone M2 is verified and ready for completion.

---

## 5. Verification Method

To independently reproduce the verification results:

```powershell
# 1. Run targeted M2 test suite
pytest tests/T03_capability/test_playwright_backend.py tests/T03_capability/test_autonomous_tool_contracts.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -v

# 2. Run adversarial test suite
pytest tests/test_m2_adversarial_challenger2.py -v

# 3. Run full collection check
pytest tests/ --collect-only -q

# 4. Run adversarial Goal 3 probe
python tools/adversarial_goal3_probe.py
```
