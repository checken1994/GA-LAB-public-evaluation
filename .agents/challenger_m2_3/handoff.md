# Adversarial Verification & Handoff Report — Milestone M2 (Iteration 2)

**Agent**: challenger_m2_3  
**Working Directory**: `D:\scp\.agents\challenger_m2_3`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-22T21:58:30Z  
**Verdict**: **APPROVE**  

---

## Challenge Summary

**Overall risk assessment**: **LOW** (All 4 adversarial attack vectors successfully repelled and verified fail-closed)

| # | Attack Surface Vector | Target Component | Observed Status | Result |
|---|---|---|---|---|
| 1 | HMAC Stripping Downgrade | `AutonomousAuditLedger` (`scp/core/autonomous_ledger.py`) | Stripped `hmac_sha256` with recalculated bare SHA-256 chain fails closed with `hash_chain_valid=False` | **PASSED** |
| 2 | PowerShell Subexpression Injection | `SafeCommandRunnerTool` (`scp/capabilities/tools.py`) | Unquoted parentheses (e.g. `echo (whoami)`) rejected across all capability levels | **PASSED** |
| 3 | SSRF & Metadata Redirects | `_SafeHTTPRedirectHandler` (`scp/security/url_safety.py`) | 301/302/303/307/308 redirects to metadata / RFC 1918 IPs blocked fail-closed | **PASSED** |
| 4 | Goal 3 Adversarial Probe Suite | `tools/adversarial_goal3_probe.py` | 203/203 adversarial probes passed cleanly | **PASSED** |

---

## 1. Observation

Direct observations and evidence from code inspections, empirical attack testbeds, and test executions:

### 1.1 HMAC Stripping on AutonomousAuditLedger
- **Target File**: `scp/core/autonomous_ledger.py:194-234`
- **Empirical Attack Testbed**:
  1. Initialized an `AutonomousAuditLedger` with a secret HMAC key (`adversarial-secret-test-key`).
  2. Committed Phase 1 intent and Phase 2 result. Pristine verification confirmed:
     `{'entries': 2, 'hash_chain_valid': True, 'errors': []}`.
  3. **Attack Scenario 1 (Strip Intent HMAC)**: Deleted `hmac_sha256` from the intent record and recalculated the bare SHA-256 chain (`hash` and `prev_hash`).
     - Bare `TraceLedger.verify()` evaluated the recomputed chain as valid:
       `{'entries': 2, 'hash_chain_valid': True, 'errors': []}`.
     - `AutonomousAuditLedger.verify_provenance()` rejected the stripped entry:
       `{'entries': 2, 'hash_chain_valid': False, 'errors': ['missing_hmac_intent:1']}`.
  4. **Attack Scenario 2 (Strip Result HMAC)**: Deleted `hmac_sha256` from the result record and recalculated the bare SHA-256 chain.
     - `AutonomousAuditLedger.verify_provenance()` rejected the stripped entry:
       `{'entries': 2, 'hash_chain_valid': False, 'errors': ['missing_hmac_result:2']}`.
  5. **Attack Scenario 3 (Strip Both HMACs)**: Deleted `hmac_sha256` from both records and recalculated the bare SHA-256 chain.
     - `AutonomousAuditLedger.verify_provenance()` rejected with:
       `{'entries': 2, 'hash_chain_valid': False, 'errors': ['missing_hmac_intent:1', 'missing_hmac_result:2']}`.
  6. **Attack Scenario 4 (Bogus/Forged HMAC)**: Injected `0123456789abcdef` * 4 into intent record.
     - `AutonomousAuditLedger.verify_provenance()` rejected with:
       `{'entries': 2, 'hash_chain_valid': False, 'errors': ['hmac_intent:1']}`.
  7. **Attack Scenario 5 (Timestamp Forgery)**: Altered timestamp by +1000s with recomputed bare SHA-256 chain.
     - `AutonomousAuditLedger.verify_provenance()` rejected with:
       `{'entries': 2, 'hash_chain_valid': False, 'errors': ['hmac_intent:1']}`.

### 1.2 PowerShell Subexpression Execution in SafeCommandRunnerTool
- **Target File**: `scp/capabilities/tools.py:283-322`
- **Empirical Attack Testbed**: Tested 13 adversarial payloads across Capability Levels 0, 1, 3 and `approved` in `{False, True}`:
  1. `echo (whoami)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  2. `dir (Get-Process)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  3. `ls (Get-ChildItem)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  4. `echo (dir)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  5. `git status (whoami)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  6. `pytest --collect-only (Get-Date)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  7. `python --version (whoami)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  8. `echo ((whoami))` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  9. `echo ( whoami )` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  10. `echo (Get-Content C:\Windows\System32\drivers\etc\hosts)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  11. `dir (ls)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  12. `python -c (whoami)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
  13. `bun run test (whoami)` -> Rejected: `(False, 'Subexpression execution and unquoted parentheses are prohibited', 0)`
- **Legitimate Command Preservation**:
  - `git status` (Cap 1, unapproved) -> Allowed: `(True, 'Read-only allowlist match', 1)`
  - `python --version` (Cap 1, unapproved) -> Allowed: `(True, 'Read-only allowlist match', 1)`
  - `echo hello_world` (Cap 1, unapproved) -> Allowed: `(True, 'Read-only allowlist match', 1)`
  - `python -c "print(123)"` (Cap 3, approved=True) -> Allowed: `(True, 'Workspace allowlist match with approval', 3)`
  - `python -c "print(123)"` (Cap 3, approved=False) -> Rejected: `(False, 'Command requires capability level >= 3 and explicit approval', 3)`

### 1.3 301/302 Redirect Interception in safe_urlopen
- **Target File**: `scp/security/url_safety.py:211-272`
- **Empirical Attack Testbed**: Local mock HTTP redirect server running on `127.0.0.1` testing 5 HTTP status codes (`301`, `302`, `303`, `307`, `308`) across 9 target destinations:
  - AWS IPv4 IMDS `http://169.254.169.254/latest/meta-data`: All 5 codes blocked with `EgressDeniedError`
  - AWS ECS IMDS `http://169.254.170.2/v2/credentials`: All 5 codes blocked with `EgressDeniedError`
  - GCP metadata `http://metadata.google.internal/computeMetadata/v1/`: All 5 codes blocked with `EgressDeniedError`
  - AWS metadata `http://metadata.aws/latest`: All 5 codes blocked with `EgressDeniedError`
  - AWS IPv6 IMDS `http://[fd00:ec2::254]/latest/meta-data`: All 5 codes blocked with `EgressDeniedError`
  - Scheme-relative `//169.254.169.254/latest/meta-data`: All 5 codes blocked with `EgressDeniedError`
  - RFC 1918 Private IP `http://10.0.0.1/admin`: All 5 codes blocked with `EgressDeniedError`
  - RFC 1918 Private IP `http://192.168.1.1/router`: All 5 codes blocked with `EgressDeniedError`
  - RFC 1918 Private IP `http://172.16.0.1/corp`: All 5 codes blocked with `EgressDeniedError`
  - Multi-hop redirect chain (`Hop 1 [302] -> Hop 2 [302] -> http://169.254.169.254/...`): Blocked fail-closed with `EgressDeniedError: egress denied for 'http://169.254.169.254/latest/meta-data': Access to cloud metadata endpoints is unconditionally prohibited`.

### 1.4 Goal 3 Adversarial Probe Suite Execution
- **Command**: `python tools/adversarial_goal3_probe.py`
- **Output**:
  ```
  ================================================================================
  PROBE SUMMARY: Total=203, Passed=203, Failed=0
  ================================================================================
  Detailed probe results written to D:\scp\data\adversarial_probe_goal3_report.json
  ```
- **Exit Code**: 0.

### 1.5 Supporting Regression Test Suites
- `pytest tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -v`: 8 passed in 0.66s.
- `pytest tests/T03_capability/test_autonomous_tool_contracts.py -v`: 17 passed in 2.64s.
- `pytest tests/T03_capability/test_playwright_backend.py -v`: 31 passed in 8.12s.
- `pytest tests/T03_capability/test_egress_policy_unified.py -v`: 11 passed in 0.97s.
- `pytest tests/T03_capability/test_egress_enforcement.py -k "test_g2_scp_tree_has_no_unpinned_client_method_calls" -v`: 1 passed in 2.14s.
- `pytest tests/T03_capability/test_hands_authority_pep.py -v`: 9 passed in 0.79s.
- `pytest tests/test_m2_adversarial_challenger2.py -v`: 10 passed in 0.68s.
- `pytest tests/T04_kernel/ -q`: 267 passed, 23 skipped in 59.41s.
- `pytest tests/T05_gateway/ -q`: 70 passed in 7.90s.
- `pytest tests/ --collect-only -q`: 2,150 tests collected with 0 errors.

---

## 2. Logic Chain

1. From **Observation 1.1**, an attacker without the secret HMAC key can forge a mathematically valid bare SHA-256 chain by recalculating entry hashes after stripping `hmac_sha256`. However, `AutonomousAuditLedger.verify_provenance()` enforces that whenever `self.hmac_key` is set, any autonomous entry lacking `recorded_hmac` causes `hash_chain_valid` to evaluate to `False` and appends `missing_hmac_intent:<line>` or `missing_hmac_result:<line>`. Furthermore, binding `timestamp` into canonical HMAC payloads ensures that metadata manipulation or replay without the key is also detected with `hmac_intent:<line>`. The attack vector is completely closed.
2. From **Observation 1.2**, PowerShell treats unquoted parentheses `(...)` as subexpressions and executes them inline before passing output as arguments. By prohibiting parentheses in `READ_ONLY_ALLOWLIST` regexes and explicitly detecting unquoted parentheses in `evaluate_command()`, commands such as `echo (whoami)` or `dir (Get-Process)` are fail-closed rejected. Quoted strings with parentheses (such as `python -c "print(123)"`) are cleanly preserved for workspace execution under Capability Level 3 with approval.
3. From **Observation 1.3**, `_SafeHTTPRedirectHandler` subclasses `urllib.request.HTTPRedirectHandler` and hooks `redirect_request()`, `http_error_301`, `http_error_302`, `http_error_303`, `http_error_307`, and `http_error_308`. For every redirect hop, the resolved URL is passed through `enforce_egress_policy()` and `validate_url()`, and subsequently delegated to `safe_urlopen()` for IP socket pinning. All redirect attempts to cloud metadata (IPv4, IPv6, ECS, GCP) and private networks are fail-closed intercepted with `EgressDeniedError`.
4. From **Observation 1.4**, running `tools/adversarial_goal3_probe.py` exercises the complete 203-case adversarial test harness across workspace traversal, command injection, egress policy, and ledger tampering, achieving 203/203 passes.
5. From **Observation 1.5**, all regression suites across capability contracts, playwright backends, kernel provenance, gateway, and test collection pass cleanly with 0 unexpected regressions.
6. Therefore, all requirements for Milestone M2 Iteration 2 are empirically verified and resilient against adversarial subversion.

---

## 3. Caveats

- **Docker Environment**: Tests requiring a local Docker daemon (`tests/T03_capability/test_egress_enforcement.py::test_h_container_deny_*`) were skipped due to Docker daemon unavailability on this Windows host.
- **Pre-existing Tripwire Drift in T00 Meta-Audit**: Running `tools/t00_meta_audit.py` flagged `tests/internal/external_audit/test_security.py` (which was not modified in M1 or M2) and `silent_except_pass` baseline drift. Per `PROJECT.md`, `t00_meta_audit.py` fixes and baseline reconciliations are explicitly assigned to Milestone M4 (Feature F21) and Milestone M5.

---

## 4. Conclusion

**Verdict**: **APPROVE**

Milestone M2 Iteration 2 fixes (HMAC stripping prevention, PowerShell subexpression rejection, 301/302 redirect egress enforcement, and Goal 3 adversarial probe 203/203) have been empirically verified and tested against active attack payloads. The codebase behaves strictly fail-closed.

---

## 5. Verification Method

To independently reproduce the empirical findings of this report:

1. **Verify Goal 3 Adversarial Probe**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   *Expected*: Total=203, Passed=203, Failed=0.

2. **Verify HMAC Stripping Rejection**:
   ```powershell
   pytest tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -k "test_autonomous_ledger_hmac_stripping_rejected" -v
   ```
   *Expected*: 1 passed with `hash_chain_valid=False` and `missing_hmac_intent:1`.

3. **Verify PowerShell Subexpression Prevention**:
   ```powershell
   pytest tests/T03_capability/test_autonomous_tool_contracts.py -k "test_safe_command_runner_redirection_and_ampersand_blocked" -v
   ```
   *Expected*: 1 passed.

4. **Verify Redirect SSRF / Egress Enforcement**:
   ```powershell
   pytest tests/T03_capability/test_egress_policy_unified.py -k "test_safe_urlopen_redirect_enforces_egress_and_url_safety" -v
   ```
   *Expected*: 1 passed with `EgressDeniedError`.

5. **Verify Full M2 Regression Suite**:
   ```powershell
   pytest tests/T03_capability/test_playwright_backend.py tests/T03_capability/test_autonomous_tool_contracts.py tests/T03_capability/test_egress_policy_unified.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/test_m2_adversarial_challenger2.py -q
   ```
   *Expected*: 77 passed.
