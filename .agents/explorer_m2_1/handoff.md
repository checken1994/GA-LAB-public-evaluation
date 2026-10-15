# Feature F07 Investigation Report: Wiring SafeCommandRunnerTool into Production Runtime Paths

**Target**: Feature F07 (Milestone M2)  
**Investigator**: `explorer_m2_1`  
**Date**: 2026-09-22T19:54:00Z  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Zero Production Callers of `scp.capabilities.tools`
Executing pattern search across the codebase:
```powershell
grep -rn "from scp.capabilities.tools import" D:\scp
```
Returned exactly two occurrences:
1. `D:\scp\tools\adversarial_goal3_probe.py:26`:
   ```python
   from scp.capabilities.tools import (
       SafeCommandRunnerTool,
       SystemInspectionTool,
       WorkspaceAnalysisTool,
   )
   ```
2. `D:\scp\tests\T03_capability\test_autonomous_tool_contracts.py:10`:
   ```python
   from scp.capabilities.tools import (
       BaseAutonomousTool,
       SafeCommandRunnerTool,
       SystemInspectionTool,
       TokenBucketRateLimiter,
       ToolResult,
       WorkspaceAnalysisTool,
   )
   ```
**Direct Observation**: There are ZERO callers of `scp.capabilities.tools` under production paths in `scp/`. The entire module exists solely as an unwired library exercised only by test suites and diagnostic probes.

---

### 1.2 `SafeCommandRunnerTool` Implementation Details
Located at `scp/capabilities/tools.py:257-414`:
- Inherits from `BaseAutonomousTool` (`name = "cmd.run"`, `capability_level = 1`, `requires_approval = False`, `mutates_state = False`).
- Enforces rate limiting via `TokenBucketRateLimiter(refill_rate_per_sec=2.0, capacity=3.0)`.
- Defines security policies:
  ```python
  BLOCKED_PATTERNS = (
      r"\bformat\s+[a-z]:",
      r"\bshutdown\b",
      r"\breg\s+delete\b",
      r"\bnet\s+user\b",
      r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(/|[a-zA-Z]:\\)",
      r"\b(remove|del|erase)\b.*\s(-recurse|-force|/s|/q)\b",
      r"\b(curl|wget)\s+.*\|.*(bash|sh|iex)",
      r"\b(iex|invoke-expression)\b",
      r"\b(su|sudo)\b",
      r"\bmkfs\b",
      r"\bdd\s+if=",
  )
  READ_ONLY_ALLOWLIST = (
      r"^\s*git\s+(status|diff|log|branch|rev-parse)(?:\s+[^\s;&|><`$]+)*\s*$",
      r"^\s*pytest\s+.*--collect-only.*$",
      r"^\s*(python|python3|bun|node)\s+--version\s*$",
      r"^\s*(dir|ls)(?:\s+[^\s;&|><`$]+)*\s*$",
  )
  WORKSPACE_ALLOWLIST = (
      r"^\s*pytest\b",
      r"^\s*(python|python3)\s+(-m\s+(pytest|compileall)|-c\s+.*)\b",
      r"^\s*(bun|npm)\s+run\s+(test|build|lint)\b",
      r"^\s*git\s+diff\s+--check\b",
  )
  ```
- Method `evaluate_command(command, capability_level, approved) -> tuple[bool, str, int]`:
  - Blocks empty commands, multiline commands (`\n`, `\r`), redirection operators (`>`, `<`), and command chaining/subshells (`;`, `&`, `|`, `` ` ``, `$(`, `${`).
  - Scans `BLOCKED_PATTERNS`.
  - Matches `READ_ONLY_ALLOWLIST` (allows `capability_level >= 1`).
  - Matches `WORKSPACE_ALLOWLIST` (requires `capability_level >= 3` AND `approved=True`).
- Method `run(params) -> ToolResult`:
  - Clamps timeout to `[1, 120]` seconds.
  - Spawns process via `asyncio.create_subprocess_exec` (`powershell.exe` on Windows; `/bin/sh` on POSIX).
  - Handles timeout with process tree termination (`taskkill /F /T /PID` on Windows; `process.kill()` on POSIX).
  - Performs bounded dual-head/tail truncation (first 2,000 + last 4,000 chars if stdout > 6,000 chars).
  - Returns structured `ToolResult` containing `success`, `data`, `evidence` (with `stdout_sha256` and `duration_ms`), `error`, `truncated`, `rate_limited`.

---

### 1.3 Old Governor Regexes in `AutonomousCapabilityGovernor`
Located at `scp/security/autonomous_governor.py:1-73`:
- Lines 10-15 define a legacy, ad-hoc blocklist:
  ```python
  BLOCKED_PATTERNS = [
      r"(?i)\b(rm\s+(?:-[a-zA-Z]*[rf][a-zA-Z]*\s+)+\s*/|mkfs|dd\s+if=|chmod\s+-R\s+777|chown\s+-R|> /dev/sda)(?:\s|$)",
      r"(?i)\b(nc\s+-e|bash\s+-i|/dev/tcp/)(?:\s|$)",
      r"(?i)\b(curl|wget)\s+.*\|.*(?:bash|sh)(?:\s|$)",
      r"(?i)\b(su|sudo)\b"
  ]
  ```
- Lines 47-53 check commands via crude regex search:
  ```python
  # 2. Command safety (Regex allowlists / blocklists)
  if action == "pc.execute":
      command = params.get("command", "")
      normalized_command = re.sub(r'[\'\"\\]', '', command)
      for pattern in self._compiled_patterns:
          if pattern.search(command) or pattern.search(normalized_command):
              return False, None, f"Command matches blocked pattern: {pattern.pattern}"
  ```
- **Vulnerabilities Observed**:
  1. Blocklist-only check: Any command NOT in the 4 blocklist patterns is granted a token (e.g. `whoami ; Start-Process ...`, or arbitrary unrecognized executables).
  2. Missing allowlists: It does not enforce read-only vs workspace tiers.
  3. Redirection and subshells (`>`, `$(...)`, `` `...` ``) are NOT blocked.
  4. Only checks `action == "pc.execute"`, completely blind to `cmd.run`.

---

### 1.4 `ActionRegistry` Catalog Gaps
Located at `scp/hands/action_registry.py:29-85`:
- Defines 25 actions (16 under domain `pc`, 9 under domain `web`).
- `cmd.run`, `sys.inspect`, and `workspace.analyze` are completely missing.
- Note on `pc.execute`: `tests/T03_capability/test_flow_04_control_hands_scp_standard.py:709-712` explicitly documents:
  > `(1) the test called bridge.execute("pc.execute", ...) but "pc.execute" is deliberately NOT in the Hands ActionRegistry allowlist — the Hands lane never exposes raw command execution, so registry.require raised KeyError before any dispatch`
  Therefore, raw `pc.execute` must NOT be in `ActionRegistry`. Instead, `cmd.run` is the bounded command execution tool for Hands.

---

### 1.5 `HandsExecutor` Execution Paths
Located at `scp/hands/hands_executor.py`:
- Line 54 initializes `self.registry = ActionRegistry()`.
- Lines 126-130 implement `_pc_command(command, definition, capability_token)` delegating to `self.controller.execute(...)` (which runs raw PowerShell).
- Lines 179-365 dispatch registered actions. There is NO branch handling `cmd.run` (or `sys.inspect`, `workspace.analyze`).
- Calling `HandsExecutor.execute("cmd.run", ...)` currently raises `KeyError: 'Unknown Hands action: cmd.run'`.

---

### 1.6 `HandsPlanner` Autonomous Step Execution
Located at `scp/hands/planner.py`:
- Lines 484-496:
  ```python
  import os
  autonomous_mode = str(os.environ.get("SCP_AUTONOMOUS_MODE", "")).lower() in ("1", "true", "yes")
  if autonomous_mode and getattr(self, "autonomous_governor", None):
      granted, auth_token, reason = self.autonomous_governor.evaluate_and_grant_step(
          step, plan, str(self.executor.data_dir.resolve())
      )
      if granted and auth_token:
          step["capabilityToken"] = auth_token.to_dict()
          step["approved"] = True
          self._save(plan, "PLAN_STEP_AUTONOMOUS_GRANT", {"stepId": step["stepId"], "reason": reason})
      else:
          self._save(plan, "PLAN_STEP_AUTONOMOUS_DENY", {"stepId": step["stepId"], "reason": reason})
  ```
- Lines 812-824 in `run_dag` check `autonomous_mode` and capability levels, but currently lack the `evaluate_and_grant_step` delegation before capability checks.

---

## 2. Logic Chain

### Step 1: Diagnosing the "Hardening Trang Trí" (Decorative Hardening) Flaw
The codebase contains a full, well-tested capability module in `scp/capabilities/tools.py` with 100% test coverage in `test_autonomous_tool_contracts.py`. However, because no file in `scp/` imports it, the production runtime paths (`planner.py` -> `autonomous_governor.py` -> `hands_executor.py`) bypass `SafeCommandRunnerTool` entirely, executing commands through legacy regexes and raw `PCController` calls.

### Step 2: Role of `ActionRegistry` as the Bounded Catalog
In SCP Agent OS architecture, the Hands subsystem only permits execution of actions defined in `ActionRegistry`. Adding `cmd.run` (with domain `pc`, risk `medium`, capability level 1, verifier `command_success`, rollback `none`) enables `HandsExecutor` to accept `cmd.run` as a first-class action while preserving the invariant that raw `pc.execute` remains excluded. Bounded siblings `sys.inspect` and `workspace.analyze` should also be registered.

### Step 3: Unifying Command Safety in `SafeCommandRunnerTool`
`AutonomousCapabilityGovernor` previously checked for `chmod -R 777`, `chown -R`, `nc -e`, `bash -i`, `/dev/tcp/`, `> /dev/sda`.
Meanwhile, `SafeCommandRunnerTool` checked for format, shutdown, reg delete, net user, recursive rm, curl|bash, iex, sudo, mkfs, dd.
To eliminate split-brain security:
1. `SafeCommandRunnerTool.BLOCKED_PATTERNS` must incorporate `chmod -R 777`, `chown -R`, `nc -e`, `bash -i`, `/dev/tcp/`, `> /dev/sda`.
2. `SafeCommandRunnerTool.evaluate_command()` must test both raw command and normalized command (`re.sub(r'[\'\"\\]', '', cmd)`) against `BLOCKED_PATTERNS` to catch quote/backslash evasion (e.g. `rm -r"f" /`, `rm -r\f /`).
3. `SafeCommandRunnerTool.READ_ONLY_ALLOWLIST` must include safe `echo` (`r"^\s*echo(?:\s+[^\s;&|><`$]+)*\s*$"`) so that benign commands like `echo Hello` in `test_governor_grants_safe_command` pass, while dangerous constructs like `echo $(whoami)` or `echo x > file` are stopped by subshell and redirection checks.

### Step 4: Delegating `AutonomousCapabilityGovernor` to `SafeCommandRunnerTool`
In `AutonomousCapabilityGovernor.evaluate_and_grant_step()`:
When `action in ("pc.execute", "cmd.run")`:
- Call `runner = SafeCommandRunnerTool(working_dir=working_dir)`
- Call `allowed, reason, req_cap = runner.evaluate_command(command, capability_level, approved)`
- If `not allowed`: return `False, None, reason`.
Because `reason` is formatted as `f"Command matches blocked pattern: {pattern}"` when a blocked pattern triggers, existing test assertions in `test_autonomous_governor.py` (`assert "matches blocked pattern" in reason`) will continue to pass.
When allowed, the governor issues a signed `CapabilityToken` with subject `f"hands:{action}"`.

### Step 5: Wiring `HandsExecutor.execute()` to `SafeCommandRunnerTool`
In `HandsExecutor.execute()`:
When `action == "cmd.run"`:
- The token PEP checks subject `hands:cmd.run`.
- Execute via `await self.command_runner.run(params)`.
- Capture `ToolResult` attributes (`success`, `data`, `evidence`, `error`, `duration_ms`, `truncated`, `rate_limited`).
- Produce verification record `{"passed": tool_res.success, "rule": definition.verifier}`.
- Record structured audit event `ACTION_EXECUTED` / `ACTION_FAILED`.

### Step 6: Grep Verification Invariant
With imports added to:
1. `scp/hands/action_registry.py`
2. `scp/security/autonomous_governor.py`
3. `scp/hands/hands_executor.py`
Running `grep -rn "from scp.capabilities.tools import"` will yield at least 3 genuine production callers in `scp/`.

---

## 3. Caveats

1. **`PCController` Internal Execution Boundary**:
   `PCController.execute()` handles direct hardware/OS calls for specific tests (e.g. `test_pc_controller_token_pep.py`). `PCController` has its own PowerShell subprocess caller and token validator. Replacing `PCController`'s internal `subprocess.run` with `SafeCommandRunnerTool` could disrupt tests specifically asserting `PCController`'s raw output format. The correct architectural boundary is:
   - `PCController` = low-level OS adapter.
   - `SafeCommandRunnerTool` = high-level bounded tool capability.
   - `HandsExecutor` & `AutonomousCapabilityGovernor` = runtime orchestration layer enforcing `SafeCommandRunnerTool` boundaries.
2. **Coordination with Feature F09 (HMAC-SHA256 Ledger Two-Phase Commit)**:
   Feature F09 modifies `HandsExecutor.execute()` to commit intent to `AutonomousAuditLedger` before execution and commit result after execution. The wiring of `SafeCommandRunnerTool` in F07 directly provides the execution payload that F09 wraps in two-phase audit logging.
3. **Windows vs POSIX Execution**:
   `SafeCommandRunnerTool` uses `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command <cmd>` on Windows and `/bin/sh -c <cmd>` on POSIX. On Windows, process termination uses `taskkill /F /T /PID`. These platform-specific branches are already implemented and tested in `SafeCommandRunnerTool`.

---

## 4. Conclusion & Concrete Fix Strategy

### 4.1 Changes to `scp/capabilities/tools.py`
1. Expand `BLOCKED_PATTERNS`:
   ```python
   BLOCKED_PATTERNS = (
       r"\bformat\s+[a-z]:",
       r"\bshutdown\b",
       r"\breg\s+delete\b",
       r"\bnet\s+user\b",
       r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(/|[a-zA-Z]:\\)",
       r"\b(remove|del|erase)\b.*\s(-recurse|-force|/s|/q)\b",
       r"\b(curl|wget)\s+.*\|.*(bash|sh|iex)",
       r"\b(iex|invoke-expression)\b",
       r"\b(su|sudo)\b",
       r"\bmkfs\b",
       r"\bdd\s+if=",
       r"\bchmod\s+(-[a-zA-Z]*[R][a-zA-Z]*\s+)*777\b",
       r"\bchown\s+-[a-zA-Z]*[R]\b",
       r"\b(nc\s+-e|bash\s+-i|/dev/tcp/)\b",
       r">\s*/dev/sda\b",
   )
   ```
2. Add `echo` to `READ_ONLY_ALLOWLIST`:
   ```python
   READ_ONLY_ALLOWLIST = (
       r"^\s*git\s+(status|diff|log|branch|rev-parse)(?:\s+[^\s;&|><`$]+)*\s*$",
       r"^\s*pytest\s+.*--collect-only.*$",
       r"^\s*(python|python3|bun|node)\s+--version\s*$",
       r"^\s*(dir|ls)(?:\s+[^\s;&|><`$]+)*\s*$",
       r"^\s*echo(?:\s+[^\s;&|><`$]+)*\s*$",
   )
   ```
3. In `evaluate_command`:
   ```python
   normalized_cmd = re.sub(r'[\'\"\\]', '', cmd)
   for pattern in self.BLOCKED_PATTERNS:
       if re.search(pattern, cmd, re.IGNORECASE) or re.search(pattern, normalized_cmd, re.IGNORECASE):
           return False, f"Command matches blocked pattern: {pattern}", 0
   ```

### 4.2 Changes to `scp/hands/action_registry.py`
1. Import tools:
   ```python
   from scp.capabilities.tools import (
       SafeCommandRunnerTool,
       SystemInspectionTool,
       WorkspaceAnalysisTool,
   )
   ```
2. Add definitions to `ActionRegistry.__init__`:
   ```python
   ActionDefinition("cmd.run", SafeCommandRunnerTool.description, "pc", "medium", 1, False, False, "command_success", "none"),
   ActionDefinition("sys.inspect", SystemInspectionTool.description, "pc", "low", 0, False, False, "metrics_collected", "none"),
   ActionDefinition("workspace.analyze", WorkspaceAnalysisTool.description, "pc", "low", 0, False, False, "entries_bounded", "none"),
   ```

### 4.3 Changes to `scp/security/autonomous_governor.py`
1. Import tool:
   ```python
   from scp.capabilities.tools import SafeCommandRunnerTool
   ```
2. In `AutonomousCapabilityGovernor`:
   Reference `SafeCommandRunnerTool.BLOCKED_PATTERNS`:
   ```python
   BLOCKED_PATTERNS = list(SafeCommandRunnerTool.BLOCKED_PATTERNS)
   ```
3. In `evaluate_and_grant_step`:
   ```python
   # 2. Command safety (SafeCommandRunnerTool boundary execution)
   if action in ("pc.execute", "cmd.run"):
       command = params.get("command", "")
       cap_level = max(1, int(step.get("capabilityLevel", 0)))
       approved = bool(step.get("approved", False))
       runner = SafeCommandRunnerTool(working_dir=working_dir)
       allowed, reason, required_cap = runner.evaluate_command(command, cap_level, approved)
       if not allowed:
           return False, None, reason
   ```

### 4.4 Changes to `scp/hands/hands_executor.py`
1. Import tools:
   ```python
   from scp.capabilities.tools import (
       SafeCommandRunnerTool,
       SystemInspectionTool,
       WorkspaceAnalysisTool,
   )
   ```
2. In `__init__`:
   ```python
   self.command_runner = SafeCommandRunnerTool(working_dir=self.controller.working_dir)
   self.inspection_tool = SystemInspectionTool(working_dir=self.controller.working_dir)
   self.analysis_tool = WorkspaceAnalysisTool(working_dir=self.controller.working_dir)
   ```
3. In `execute()`:
   ```python
   elif action == "cmd.run":
       cmd_text = str(params.get("command", "")).strip()
       timeout = max(1, min(int(params.get("timeout", 30)), 120))
       tool_res = await self.command_runner.run({
           "command": cmd_text,
           "capability_level": capability_level,
           "approved": approved,
           "timeout": timeout,
       })
       result = {
           "success": tool_res.success,
           "command": cmd_text,
           "data": tool_res.data,
           "evidence": {
               **tool_res.evidence,
               "truncated": tool_res.truncated,
               "rateLimited": tool_res.rate_limited,
           },
           "error": tool_res.error,
           "durationMs": tool_res.duration_ms,
           "verification": {"passed": tool_res.success, "rule": definition.verifier},
       }
   elif action == "sys.inspect":
       tool_res = await self.inspection_tool.run(params)
       result = {
           "success": tool_res.success,
           "data": tool_res.data,
           "evidence": tool_res.evidence,
           "error": tool_res.error,
           "durationMs": tool_res.duration_ms,
           "verification": {"passed": tool_res.success, "rule": definition.verifier},
       }
   elif action == "workspace.analyze":
       tool_res = await self.analysis_tool.run(params)
       result = {
           "success": tool_res.success,
           "data": tool_res.data,
           "evidence": tool_res.evidence,
           "error": tool_res.error,
           "durationMs": tool_res.duration_ms,
           "verification": {"passed": tool_res.success, "rule": definition.verifier},
       }
   ```

### 4.5 Enhancement in `scp/hands/planner.py`
In `run_dag()`, add autonomous evaluation parity so that DAG steps also benefit from `self.autonomous_governor.evaluate_and_grant_step()` when `autonomous_mode` is enabled.

---

## 5. Verification Method

### 5.1 Programmatic Commands for Verification
1. **Verify Production Callers via Grep**:
   ```powershell
   grep -rn "from scp.capabilities.tools import" D:\scp\scp
   ```
   *Expected Output*: Must return at least 3 distinct production callers:
   - `scp/hands/action_registry.py`
   - `scp/security/autonomous_governor.py`
   - `scp/hands/hands_executor.py`

2. **Run Kernel & Governor Test Suites**:
   ```powershell
   pytest tests/T04_kernel/test_autonomous_governor.py tests/T04_kernel/test_autonomous_e2e_reality.py -v
   ```
   *Expected Output*: 100% PASS (confirms safe command grant, blocked pattern rejection, obfuscated command rejection, path isolation).

3. **Run Capability & Tool Contract Suites**:
   ```powershell
   pytest tests/T03_capability/test_autonomous_tool_contracts.py tests/T03_capability/test_pc_controller_token_pep.py tests/T03_capability/test_hands_authority_pep.py tests/T03_capability/test_flow_04_control_hands_scp_standard.py -v
   ```
   *Expected Output*: 100% PASS (confirms ActionRegistry invariants, PCController PEP tokens, rate limiter, output bounds, command chaining blocks).

4. **Run Adversarial Goal 3 Security Probe**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   *Expected Output*: Total=203, Passed=203, Failed=0.

5. **Pytest Collection Check**:
   ```powershell
   pytest tests/ --collect-only -q
   ```
   *Expected Output*: 0 collection errors.

### 5.2 Integration Test Proposal
Add integration test `tests/integration/test_safe_command_runner_wiring.py` asserting:
1. `ActionRegistry` exposes `cmd.run` with capability level 1.
2. `AutonomousCapabilityGovernor` evaluates a `cmd.run` step via `SafeCommandRunnerTool` and issues a `hands:cmd.run` token for safe commands while blocking injection attempts (`rm -rf /`, `curl | bash`, `; whoami`).
3. `HandsExecutor.execute("cmd.run", params={"command": "python --version"}, capability_token=token)` successfully executes through `SafeCommandRunnerTool`, produces truncated bounded evidence, and records verified audit status.
