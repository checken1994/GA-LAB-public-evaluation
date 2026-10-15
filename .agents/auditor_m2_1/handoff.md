# Milestone M2 Forensic Integrity Audit Report

**Auditor Agent**: auditor_m2_1  
**Working Directory**: `D:\scp\.agents\auditor_m2_1`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Audit Scope**: Milestone M2 (Wiring Security Modules into Production Runtime: F07, F08 & F14, F09)  
**Profile**: General Project (Integrity Mode: Development)  
**Verdict**: **CLEAN**  

---

## 1. Observation

Direct empirical observations from source code audits, git diff analysis, file inspections, and execution runs:

### A. Phase 1: Source Code & Integrity Inspection
1. **SafeCommandRunnerTool & Capability Tools (`scp/capabilities/tools.py`)**:
   - `SafeCommandRunnerTool.evaluate_command()` strictly enforces security boundaries before allowlist checks. Lines 308-316 normalize quotes/backslashes (`re.sub(r'[\'\"\\]', '', cmd)`) and evaluate `BLOCKED_PATTERNS` (`rm -rf`, `chmod -R 777`, `chown -R`, `nc -e`, `bash -i`, `/dev/tcp/`, `> /dev/sda`, etc.) before evaluating redirection (`[><]`) or command chaining (`(?:;|&|\||`|\$\(|\$\{)`).
   - `SafeCommandRunnerTool.run()` (lines 330-405) creates genuine subprocesses using `asyncio.create_subprocess_exec` (`powershell.exe` on Windows, `/bin/sh` on Unix) with process group management, enforces timeouts via `taskkill /F /T /PID` or `process.kill()`, reads actual stdout/stderr streams, computes SHA-256 hashes of outputs, and performs bounded dual-head/tail truncation (first 2,000 + last 4,000 bytes) when output exceeds 6,000 characters. No mock outputs, facades, or dummy constants exist.
   - `SystemInspectionTool.run()` (lines 85-155) gathers authentic OS metrics using `shutil.disk_usage()`, `os.cpu_count()`, `platform.system()`, `psutil.virtual_memory()`, and `os.getpid()`.
   - `WorkspaceAnalysisTool.run()` (lines 190-265) performs real directory iteration (`iterdir()`, `rglob()`), strictly verifies workspace containment via `relative_to(self.working_dir)`, and blocks access to sensitive paths (`.env`, `secrets`, `.pem`, `.key`, `.git/config`, etc.).

2. **Egress Policy & TOCTOU Elimination (`scp/policy/egress.py`, `scp/security/url_safety.py`, `scp/llm_gateway/egress_policy.py`)**:
   - `EgressPolicy.__init__()` (lines 64-72) defaults `SCP_EGRESS_MODE` when unset or empty to `"allowlist"` (fail-closed, loopback only), eliminating the historical dev-default open behavior.
   - `EgressPolicy.enforce()` (lines 118-162) unconditionally blocks cloud metadata hosts (`169.254.169.254`, `metadata.google.internal`, `metadata.aws`, IPv6-mapped IPv4 metadata), permits loopback (`127.0.0.1`, `localhost`, `::1`), strictly validates allowlist members including wildcard matching (`*.example.com`), and enforces fail-closed behavior in production mode.
   - `scp/security/url_safety.py:enforce_egress_policy()` delegates directly to `EgressPolicy().enforce(url_str, token_allowed_hosts=extra_allowed_hosts)`.
   - `scp/security/url_safety.py:safe_urlopen()` resolves the destination hostname via `socket.getaddrinfo`, verifies that the resolved candidate IP is not private/reserved, and injects `_PinnedHTTPHandler(resolved_ip)` / `_PinnedHTTPSHandler(resolved_ip)`. `_PinnedHTTPConnection.connect()` and `_PinnedHTTPSConnection.connect()` open the TCP socket directly to `(self._resolved_ip, self.port)` while passing the original hostname for HTTP `Host` headers and TLS SNI. This definitively eliminates DNS rebinding TOCTOU vulnerabilities.
   - `scp/llm_gateway/egress_policy.py:llm_egress_allowed()` delegates directly to `EgressPolicy(allowlist=llm_egress_allowlist_hosts()).enforce(base_url)`.
   - `scp/web_control/playwright_backend.py:validate_url()` enforces `enforce_egress_policy(clean_url)` before browser navigation.

3. **Autonomous Audit Ledger & Two-Phase Commit (`scp/core/autonomous_ledger.py`, `scp/hands/hands_executor.py`)**:
   - `AutonomousAuditLedger` (lines 52-225) computes canonical SHA-256 and HMAC-SHA256 digests. When `hmac_key` is provided (via constructor parameter or `SCP_LEDGER_HMAC_KEY`), `commit_intent()` and `commit_result()` sign the canonical JSON representation of events using `hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()`.
   - `AutonomousAuditLedger.verify_provenance()` re-verifies the hash chain and verifies HMAC signatures using constant-time `hmac.compare_digest()`. If a record is tampered with or recalculated with bare SHA-256, it reports `hash_chain_valid: False` with error identifiers (`hmac_intent:<line>` or `hmac_result:<line>`).
   - `ActionRegistry` (lines 38-68) registers `cmd.run` (medium risk, capability level 1), `sys.inspect` (low risk, capability level 0), and `workspace.analyze` (low risk, capability level 0).
   - `HandsExecutor.__init__()` (lines 75-83) initializes `SafeCommandRunnerTool`, `SystemInspectionTool`, `WorkspaceAnalysisTool`, and `AutonomousAuditLedger(hmac_key=...)`.
   - `HandsExecutor.execute()` (lines 190-471) strictly verifies capability tokens via `self.capability_authority.validate(capability_token)`. Before tool dispatch, it executes **Phase 1: Intent Commit** to `self.audit_ledger.commit_intent(...)`. It then dispatches `cmd.run`, `sys.inspect`, and `workspace.analyze` to their respective tools. After execution, it executes **Phase 2: Outcome Commit** to `self.audit_ledger.commit_result(...)`, returning a result enriched with `intentHash`, `outcomeHash`, and `ledgerSeq`.

### B. Production Caller Grep Verification
Grep search across all production code in `scp/` confirmed active callers:
1. `from scp.capabilities.tools import`:
   - `scp/hands/hands_executor.py:22` (SafeCommandRunnerTool, SystemInspectionTool, WorkspaceAnalysisTool)
   - `scp/hands/action_registry.py:12` (SafeCommandRunnerTool, SystemInspectionTool, WorkspaceAnalysisTool)
   - `scp/security/autonomous_governor.py:5` (SafeCommandRunnerTool)
2. `from scp.policy.egress import`:
   - `scp/capabilities/tools.py:18` (EgressPolicy)
   - `scp/llm_gateway/egress_policy.py:50` (EgressPolicy, EgressDeniedError)
   - `scp/security/url_safety.py:48` (EgressPolicy, EgressDeniedError, EgressDestination)
3. `from scp.core.autonomous_ledger import`:
   - `scp/hands/hands_executor.py:27` (AutonomousAuditLedger)

All 7 production import sites are active in the runtime execution pipeline.

### C. Behavioral Verification
1. **Targeted Pytest Suite**:
   Command: `pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v`
   Result: **87 passed, 2 skipped** (Docker container tests skipped due to no Docker in test environment).
2. **Adversarial Goal 3 Probe**:
   Command: `python tools/adversarial_goal3_probe.py`
   Result: **Total=203, Passed=203, Failed=0**.
3. **Pytest Collection**:
   Command: `pytest --collect-only -q`
   Result: **2,137 tests collected with 0 errors**.
4. **Independent Auditor Stress-Test**:
   Command: `python D:\scp\.agents\auditor_m2_1\adversarial_m2_stress_test.py`
   Result: **Total=8, Passed=8, Failed=0**.

---

## 2. Logic Chain

1. **Authenticity of Tools & Execution**:
   - *Observation A.1* demonstrates that `SafeCommandRunnerTool`, `SystemInspectionTool`, and `WorkspaceAnalysisTool` contain zero hardcoded returns or simulated passes. `run()` directly invokes `asyncio.create_subprocess_exec` and captures actual OS command execution outputs.
   - *Independent stress test Check 1.3* confirmed execution of `echo forensic_token_...` returning actual stdout containing the token and exit code 0.
   - Therefore, the tool implementations are authentic and non-facade.

2. **Integrity of Egress Enforcement & Socket Pinning**:
   - *Observation A.2* demonstrates that `SCP_EGRESS_MODE` defaults to `allowlist` (loopback only), removing dev-default open behavior.
   - *Observation A.2* and *Adversarial Probe 3* confirm that cloud metadata is unconditionally blocked, loopback is permitted, and external egress is denied unless specifically allowlisted.
   - *Observation A.2* confirms that `safe_urlopen` resolves the IP address once and connects directly to the resolved IP via custom handlers `_PinnedHTTPHandler` and `_PinnedHTTPSHandler`, eliminating TOCTOU DNS rebinding.
   - Therefore, egress enforcement is fail-closed, unified, and free of TOCTOU vulnerabilities.

3. **Authenticity of Cryptographic Ledger Provenance & 2PC**:
   - *Observation A.3* demonstrates that `AutonomousAuditLedger` generates authentic HMAC-SHA256 signatures over canonical event payloads.
   - *Independent stress test Check 3.2* proved that an attacker modifying a payload and recalculating the bare SHA-256 hash is caught by `verify_provenance()`, which fails with `hmac_intent:1`.
   - *Observation A.3* and *Independent stress test Check 4.2* confirm that `HandsExecutor.execute()` commits Phase 1 intent before tool execution and Phase 2 outcome after tool execution, embedding immutable hashes and sequence numbers.
   - Therefore, cryptographic provenance is genuine, verifiable, and tamper-resistant.

4. **Production Wiring Verification**:
   - *Observation B* confirms that `from scp.capabilities.tools import`, `from scp.policy.egress import`, and `from scp.core.autonomous_ledger import` are present in production code (`scp/`) across 7 distinct caller locations.
   - Calls occur during actual capability registration (`action_registry.py`), plan evaluation (`autonomous_governor.py`), runtime action execution (`hands_executor.py`), network request resolution (`url_safety.py`), and LLM gateway routing (`llm_gateway/egress_policy.py`).
   - Therefore, the security modules are genuinely wired into production runtime and are not decorative.

---

## 3. Caveats

1. **Pre-Existing T00 Meta-Audit Debt**:
   Running `python tools/t00_meta_audit.py` revealed failures stemming from:
   - Path normalization at line 356 (`tests/internal/external_audit/test_security.py`), which is already tracked and scheduled for remediation under Milestone M4 (Feature F21).
   - Silent except drift (`silent_except_pass: 8 > baseline 6`), caused by M1 `evaluation_routes.py` (lines 45, 51), not by M2 code.
   These issues are out of scope for M2 and are tracked for M4/M5.
2. **Environment Variable Prerequisite**:
   `HandsExecutor` and `PCController` require `SCP_CAPABILITY_SECRET` to be set in the execution environment to issue and validate capability tokens; this is expected behavior adhering to fail-closed security.

---

## 4. Conclusion

**Verdict: CLEAN**

Milestone M2 strictly complies with all integrity and architecture requirements:
- **No Cheating**: No hardcoded outputs, dummy implementations, or simulated PASS outputs exist in any M2 work product.
- **Authentic Implementations**: `SafeCommandRunnerTool` genuinely executes subprocess commands, `EgressPolicy` and `safe_urlopen` enforce fail-closed socket pinning, and `AutonomousAuditLedger` enforces authentic HMAC-SHA256 provenance.
- **Genuine Two-Phase Commit**: `HandsExecutor` enforces capability token checks, commits Phase 1 intent before dispatch, and commits Phase 2 outcome after execution.
- **Active Production Wiring**: All required imports and call sites are present in production runtime code across `scp/`.

---

## 5. Verification Method

To independently reproduce the forensic verification:

1. **Verify Production Callers**:
   ```powershell
   python -c "
   import glob, re
   for pat, d in [(r'from scp\.capabilities\.tools import', 'scp'), (r'from scp\.policy\.egress import', 'scp'), (r'from scp\.core\.autonomous_ledger import', 'scp')]:
       for p in glob.glob(f'{d}/**/*.py', recursive=True):
           for l in open(p, encoding='utf-8', errors='ignore'):
               if re.search(pat, l): print(f'{p}: {l.strip()}')
   "
   ```
   *Expected Output*: 3 matches for `tools`, 3 matches for `egress`, 1 match for `autonomous_ledger`.

2. **Execute Targeted Pytest Suite**:
   ```powershell
   pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T04_kernel/test_autonomous_governor.py tests/T03_capability/test_egress_enforcement.py tests/T03_capability/test_egress_policy_unified.py tests/T05_gateway/test_llm_egress_policy.py tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v
   ```
   *Expected Output*: 87 passed, 2 skipped in ~8s.

3. **Execute Adversarial Goal 3 Probe**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   *Expected Output*: Total=203, Passed=203, Failed=0.

4. **Execute Independent Auditor Stress-Test**:
   ```powershell
   python D:\scp\.agents\auditor_m2_1\adversarial_m2_stress_test.py
   ```
   *Expected Output*: Total Checks: 8, All Passed: True.

5. **Verify Full Pytest Collection**:
   ```powershell
   pytest --collect-only -q
   ```
   *Expected Output*: 2,137 tests collected with 0 errors.

### Invalidation Conditions
This verdict is invalidated if:
- `SafeCommandRunnerTool.evaluate_command()` allows command chaining, redirection, or un-allowlisted execution.
- `safe_urlopen` connects to any IP other than the pre-validated destination IP.
- Modifying an intent or outcome record in `autonomous_ledger.jsonl` passes `verify_provenance()` when HMAC is enabled.
- Any production call to `HandsExecutor.execute()` bypasses Two-Phase Commit logging.
