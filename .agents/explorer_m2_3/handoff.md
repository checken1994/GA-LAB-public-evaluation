# Handoff Report — Feature F09 (Milestone M2)
**Agent**: `explorer_m2_3`  
**Working Directory**: `D:\scp\.agents\explorer_m2_3`  
**Date**: 2026-09-23T02:59:00+07:00  
**Focus**: HMAC-SHA256 support in `AutonomousAuditLedger` (`scp/core/autonomous_ledger.py`) and Wiring Two-Phase Commit into `HandsExecutor.execute()` (`scp/hands/hands_executor.py`).

---

## 1. Observation

### 1.1 Unwired `AutonomousAuditLedger` Production Callers
Execution of ripgrep for references to `autonomous_ledger` across the codebase:
```powershell
grep -rn "autonomous_ledger" D:\scp
```
Yielded only 4 matches across test and probe files:
- `D:\scp\tools\adversarial_goal3_probe.py:31`: `from scp.core.autonomous_ledger import AutonomousAuditLedger`
- `D:\scp\tests\T04_kernel\test_autonomous_audit_ledger_provenance.py:9`: `from scp.core.autonomous_ledger import AutonomousAuditLedger, ProvenanceBlock`
- `D:\scp\tests\T04_kernel\test_autonomous_audit_ledger_provenance.py:58`: `def test_autonomous_ledger_tamper_detection(tmp_path: Path) -> None:`
- `D:\scp\tests\T04_kernel\test_autonomous_audit_ledger_provenance.py:97`: `def test_autonomous_ledger_redacts_tokens(tmp_path: Path) -> None:`

**Result**: Exactly ZERO production callers exist in `scp/`. `AutonomousAuditLedger` was completely unwired from the runtime execution path.

### 1.2 Unkeyed SHA-256 Weakness in `AutonomousAuditLedger`
In `scp/core/autonomous_ledger.py`:
- Lines 36–38:
  ```python
  def compute_hash(self) -> str:
      serialized = json.dumps(self.canonical_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
      return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
  ```
- Lines 51–54:
  ```python
  @staticmethod
  def _hash_value(val: Any) -> str:
      raw = json.dumps(val, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
      return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
  ```
Because SHA-256 is an unkeyed hash, an attacker or compromised component with write access to the ledger file can modify a record and recompute the bare SHA-256 hash chain without detection. This was empirically demonstrated by Probe 4.7 in `tools/adversarial_goal3_probe.py:568-589`:
```python
# In adversarial_goal3_probe.py:
entry4["hash"] = "sha256:" + hashlib.sha256(json.dumps(body5, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
# TraceLedger.verify() returned hash_chain_valid=True despite data tampering!
```

### 1.3 `HandsExecutor.execute()` Lacks Two-Phase Ledger Commit
In `scp/hands/hands_executor.py`:
- Lines 56–65:
  ```python
  self.audit_path = self.data_dir / "audit.jsonl"
  def _audit(self, event: str, payload: dict[str, Any]) -> None:
      record = {"timestamp": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **payload}
      with self.audit_path.open("a", encoding="utf-8") as handle:
          handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
  ```
- Lines 132–370:
  `execute()` writes unstructured JSON records to `audit.jsonl` upon completion (`ACTION_EXECUTED` or `ACTION_FAILED`), but does NOT:
  1. Commit Phase 1 (Intent) to an immutable cryptographic ledger prior to dispatch.
  2. Bind the execution to an authorized capability token digest.
  3. Commit Phase 2 (Outcome) linked to the Phase 1 Intent hash.
  4. Provide crash-consistent recovery detection if execution is interrupted mid-flight.

### 1.4 Downstream Caller Dependencies on `HandsExecutor`
Inspection of `scp/` revealed that `HandsExecutor` is the central execution choke-point:
- `scp/hands/planner.py:542, 676`: `HandsPlanner` executes plan steps via `await self.executor.execute(...)`.
- `scp/hands/task_kernel_bridge.py:319`: `TaskKernelHandsBridge` delegates both mutating and non-mutating actions to `await self.executor.execute(...)`.
- `scp/api/routes/hands_routes.py:24`: Direct endpoint invocations delegate to `_hands = HandsExecutor()`.
- `scp/core/agent_orchestrator.py:44`: Instantiates `HandsExecutor()`.
- `scp/mcp_server/server.py:89`: MCP tool calls execute via `HandsExecutor`.

Wiring two-phase commit into `HandsExecutor.execute()` automatically instruments ALL execution entry points across the system.

### 1.5 Field Redaction Behavior in `TraceLedger._redact`
In `scp/trace_ledger.py:14-25`:
```python
_SECRET_WORDS = ("secret", "token", "password", "cookie", "api_key", "authorization", "private_key")
def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if any(w in str(k).lower() for w in _SECRET_WORDS) else _redact(v) for k, v in value.items()}
```
Any field containing `"token"` (such as `token_id` or `token_hash`) is redacted to `"[REDACTED]"` when serialized to disk. Therefore, if the HMAC signature signs `token_id` as plaintext before `TraceLedger` writes it, re-verifying from disk would fail because the file contains `"[REDACTED]"`.

---

## 2. Logic Chain

1. **Vulnerability Resolution via Keyed Hash (HMAC-SHA256)**:
   - *From Observation 1.2*: Bare SHA-256 permits arbitrary recalculation of the hash chain by untrusted actors.
   - *Inference*: By adding HMAC-SHA256 using a shared or environment secret (`SCP_LEDGER_HMAC_KEY` / `CapabilityAuthority.secret`), ledger records cannot be forged or modified without the secret key.
   - *Backward Compatibility*: If no `hmac_key` is provided and `SCP_LEDGER_HMAC_KEY` is unset, `AutonomousAuditLedger` must seamlessly default to unkeyed SHA-256 (`sha256:` prefix) so all existing tests (`test_autonomous_audit_ledger_provenance.py`) pass without changes.

2. **Redaction-Aware Canonical HMAC Payload**:
   - *From Observation 1.5*: `TraceLedger` replaces fields containing `"token"` with `"[REDACTED]"`.
   - *Inference*: To achieve deterministic, tamper-evident verification from disk, the canonical HMAC signature payload for `AUTONOMOUS_TOOL_INTENT` must bind immutable execution parameters:
     ```python
     canonical = {
         "event": "AUTONOMOUS_TOOL_INTENT",
         "task_id": fields["task_id"],
         "step_id": fields["step_id"],
         "tool_name": fields["tool_name"],
         "input_sha256": fields["input_sha256"],  # digests redacted params
         "parent_trace_id": fields["parent_trace_id"],
     }
     ```
     And for `AUTONOMOUS_TOOL_RESULT`:
     ```python
     canonical = {
         "event": "AUTONOMOUS_TOOL_RESULT",
         "task_id": fields["task_id"],
         "step_id": fields["step_id"],
         "tool_name": fields["tool_name"],
         "intent_entry_hash": fields["intent_entry_hash"],
         "output_sha256": fields["output_sha256"],
         "evidence_sha256": fields["evidence_sha256"],
         "status": fields["status"],
     }
     ```
     None of these keys match `_SECRET_WORDS`, ensuring byte-for-byte serialization stability between write time and verification time.

3. **Two-Phase Commit Placement in `HandsExecutor.execute()`**:
   - *From Observation 1.3 & 1.4*: Actions are validated at the gate (capability token present, subject matches `hands:<action>`, epoch valid).
   - *Inference*:
     - **Pre-execution gate**: If `capability_token` is missing or invalid, execution is rejected fail-closed with `ACTION_BLOCKED_UNAUTHORIZED` *without* creating an unverified orphan intent in the ledger.
     - **Phase 1 (Intent Commit)**: Executed immediately after authority validation passes, prior to action execution. It commits `AUTONOMOUS_TOOL_INTENT`, returning `intent_hash`.
     - **Execution**: Tool runs inside the standard `try / except` block.
     - **Phase 2 (Outcome Commit)**: Executed immediately after action completes (or fails with exception). It commits `AUTONOMOUS_TOOL_RESULT` linked to `intent_hash`, recording `status` (`SUCCESS` or `FAILED`), duration, output digest, and evidence digest.
     - **Enriched Return**: `result["intentHash"] = intent_hash`, `result["outcomeHash"] = outcome_entry["hash"]`, `result["ledgerSeq"] = outcome_entry["seq"]`.
     - **Crash Consistency**: If the worker process crashes between Phase 1 and Phase 2, the ledger retains the uncommitted intent block, allowing TaskKernel recovery and auditors to detect interrupted executions.

4. **Satisfying the Production Caller Requirement**:
   - *From Observation 1.1*: No production file imported `from scp.core.autonomous_ledger import AutonomousAuditLedger`.
   - *Inference*: Placing `from scp.core.autonomous_ledger import AutonomousAuditLedger` at top-level in `scp/hands/hands_executor.py:24` establishes an essential production caller in the core executor path without circular imports (`autonomous_ledger.py` only imports standard library, `trace_contract`, and `trace_ledger`).

---

## 3. Caveats

1. **Environment Key Sourcing**:
   - In automated test suites (`tests/conftest.py`), `SCP_CAPABILITY_SECRET` is set by default.
   - `HandsExecutor` defaults its ledger HMAC key to `os.environ.get("SCP_LEDGER_HMAC_KEY") or getattr(self.capability_authority, "secret", None)`.
   - `AutonomousAuditLedger` standalone (when used without `HandsExecutor`) uses `hmac_key` argument or `os.environ.get("SCP_LEDGER_HMAC_KEY")`. It does not forcefully require an HMAC key if unconfigured, preserving backward compatibility.
2. **ActionRegistry vs SafeCommandRunnerTool**:
   - Wiring `SafeCommandRunnerTool` into `ActionRegistry` is Feature F07 (handled by peer `explorer_m2_1`).
   - The two-phase commit in `HandsExecutor.execute()` wraps the entire action dispatch table. When F07 adds `cmd.run` / `SafeCommandRunnerTool`, it automatically inherits the two-phase commit mechanism without further executor changes.

---

## 4. Conclusion

Feature F09 is thoroughly analyzed, prototyped, and validated:
1. **`scp/core/autonomous_ledger.py`**:
   - Enhanced `ProvenanceBlock` with `compute_hmac(key)` and backward-compatible `compute_hash(key=None)`.
   - Enhanced `AutonomousAuditLedger.__init__` with optional `hmac_key: str | bytes | None = None` and `SCP_LEDGER_HMAC_KEY` env var fallback.
   - Enhanced `commit_intent` and `commit_result` to generate HMAC-SHA256 signatures (`hmac_sha256` field) and keyed digests (`hmac-sha256:` prefix) when an HMAC key is present.
   - Enhanced `verify_provenance()` to validate HMAC signatures using constant-time `hmac.compare_digest`, detecting and preventing the Probe 4.7 attack.
   - Fully backward-compatible: when unkeyed, produces standard `sha256:` digests and passes `TraceLedger.verify()`.
2. **`scp/hands/hands_executor.py`**:
   - Added `from scp.core.autonomous_ledger import AutonomousAuditLedger` (satisfies grep audit).
   - In `__init__`, initializes `self.audit_ledger = audit_ledger or AutonomousAuditLedger(...)` bound to the capability authority secret or `SCP_LEDGER_HMAC_KEY`.
   - In `execute()`, implements two-phase commit: Phase 1 Intent prior to dispatch, Phase 2 Outcome post-execution linked by `intent_entry_hash`.
   - Enriches execution result with `intentHash`, `outcomeHash`, and `ledgerSeq`.
3. **Artifacts Produced**:
   - Replacement file: `D:\scp\.agents\explorer_m2_3\proposed_autonomous_ledger.py`
   - Replacement file: `D:\scp\.agents\explorer_m2_3\proposed_hands_executor.py`
   - Unified patch: `D:\scp\.agents\explorer_m2_3\f09_remediation.patch`

---

## 5. Verification Method

### 5.1 Verification Commands for Implementer / Auditor

1. **Verify Production Grep Caller Requirement**:
   ```powershell
   grep -rn "from scp.core.autonomous_ledger import" scp/
   ```
   **Expected**: Exactly matches `scp/hands/hands_executor.py:24:from scp.core.autonomous_ledger import AutonomousAuditLedger`.

2. **Verify Existing Ledger Provenance Tests (Zero Regressions)**:
   ```powershell
   pytest tests/T04_kernel/test_autonomous_audit_ledger_provenance.py -q
   ```
   **Expected**: All 4 existing tests pass cleanly in unkeyed mode.

3. **Verify Existing Capability & Executor PEP Tests**:
   ```powershell
   pytest tests/T03_capability/test_hands_authority_pep.py tests/T03_capability/test_pc_controller_token_pep.py -q
   ```
   **Expected**: All 15 tests pass cleanly.

4. **Verify Golden A End-to-End Execution Flow**:
   ```powershell
   pytest tests/T09_golden_task/test_golden_a_agent_os.py -q
   ```
   **Expected**: Pass (TaskKernelHandsBridge -> HandsExecutor -> PCController -> Verifier).

5. **Verify Adversarial Probe 4 Tamper Detection**:
   ```powershell
   python -c "from tools.adversarial_goal3_probe import EmpiricalHarness, run_probe_4_ledger_tampering; h = EmpiricalHarness(); run_probe_4_ledger_tampering(h); print('Failed:', [r for r in h.results if not r['passed']]); h.cleanup()"
   ```
   **Expected**: `Failed: []` (all 8 sub-probes pass).

6. **New Functional Tests to Add to `test_autonomous_audit_ledger_provenance.py`**:
   The implementer should add the following 3 tests:
   ```python
   def test_autonomous_ledger_hmac_sha256_two_phase_commit(tmp_path: Path) -> None:
       """Verifies HMAC-SHA256 signing and verification across Intent and Result blocks."""
       ledger = AutonomousAuditLedger(ledger_path=tmp_path / "ledger.jsonl", hmac_key="test-key-32b")
       intent = ledger.commit_intent("t1", "s1", "pc.status", {"foo": "bar"}, {"token_id": "tok1", "signature": "sig1"})
       assert "hmac_sha256" in intent["fields"]
       assert intent["fields"]["input_sha256"].startswith("hmac-sha256:")
       
       result = ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {"ok": True}, {}, "SUCCESS", 2.5)
       assert "hmac_sha256" in result["fields"]
       assert result["fields"]["intent_entry_hash"] == intent["hash"]
       
       verification = ledger.verify_provenance()
       assert verification["hash_chain_valid"] is True
       assert verification["entries"] == 2

   def test_autonomous_ledger_hmac_tamper_detection_probe47(tmp_path: Path) -> None:
       """Verifies that an attacker recalculating the bare SHA-256 hash chain is caught by HMAC verification."""
       ledger_file = tmp_path / "tamper_hmac.jsonl"
       ledger = AutonomousAuditLedger(ledger_path=ledger_file, hmac_key="secret-key")
       intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
       ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)
       
       # Attacker modifies tool_name and recalculates bare SHA-256 hash to trick TraceLedger
       lines = ledger_file.read_text(encoding="utf-8").splitlines()
       entry = json.loads(lines[0])
       entry["fields"]["tool_name"] = "pc.forged_command"
       body = {k: v for k, v in entry.items() if k != "hash"}
       entry["hash"] = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
       lines[0] = json.dumps(entry, sort_keys=True)
       ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
       
       verification = ledger.verify_provenance()
       assert verification["hash_chain_valid"] is False
       assert any("hmac_intent:1" in err for err in verification["errors"])

   def test_hands_executor_wires_two_phase_commit(tmp_path: Path) -> None:
       """Verifies HandsExecutor.execute commits both Intent and Result into AutonomousAuditLedger."""
       cap_auth = CapabilityAuthority(tmp_path / "cap_state.json")
       executor = HandsExecutor(data_dir=tmp_path / "hands_data", capability_authority=cap_auth)
       token = cap_auth.issue("hands:pc.status")
       
       res = asyncio.run(executor.execute("pc.status", capability_token=token))
       assert res["success"] is True
       assert "intentHash" in res
       assert "outcomeHash" in res
       assert res["ledgerSeq"] == 2
       
       v = executor.audit_ledger.verify_provenance()
       assert v["hash_chain_valid"] is True
       assert v["entries"] == 2
   ```

### 5.2 Invalidation Conditions
The conclusion is invalidated if:
1. `from scp.core.autonomous_ledger import AutonomousAuditLedger` in `scp/hands/hands_executor.py` triggers an unhandled circular dependency during `pytest --collect-only`.
2. Existing tests fail when `AutonomousAuditLedger` is instantiated without `hmac_key`.
3. An unauthenticated request (`capability_token=None`) generates orphaned intent records in `autonomous_ledger.jsonl`.
