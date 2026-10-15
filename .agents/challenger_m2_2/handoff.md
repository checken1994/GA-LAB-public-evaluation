# Milestone M2 Adversarial Challenge Report

**Agent**: challenger_m2_2  
**Working Directory**: `D:\scp\.agents\challenger_m2_2`  
**Parent Agent**: orchestrator_7 (`81004ee7-0162-4442-9168-937ecae6dd34`)  
**Timestamp**: 2026-09-22T20:22:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

Direct observations from source code inspection and empirical adversarial execution:

1. **HMAC Stripping / Downgrade Vulnerability (`scp/core/autonomous_ledger.py:191-218`)**:
   In `AutonomousAuditLedger.verify_provenance()`:
   ```python
   recorded_hmac = fields.get("hmac_sha256")
   if recorded_hmac and event == "AUTONOMOUS_TOOL_INTENT":
       ...
   elif recorded_hmac and event == "AUTONOMOUS_TOOL_RESULT":
       ...
   ```
   When `AutonomousAuditLedger` is configured with `hmac_key`, `verify_provenance()` conditionally checks HMAC signatures *only if* `recorded_hmac` is truthy. If an attacker tampers with record bodies (e.g. changing `tool_name` from `"pc.status"` to `"cmd.run"`), deletes `"hmac_sha256"`, and recalculates the bare SHA-256 hash chain (`entry["hash"] = "sha256:" + hashlib.sha256(...)`), the HMAC checks are completely bypassed.
   Direct tool execution output from empirical reproducer (`tests/test_m2_adversarial_challenger2.py::test_adversarial_hmac_stripping_downgrade_vulnerability`):
   ```
   Initial valid: True []
   After attack, verify_provenance says: True []
   ```
   Verification returns `{"hash_chain_valid": True, "errors": []}` despite tampered records and missing cryptographic signatures.

2. **Unauthenticated Timestamp & Duration in HMAC Canonical Dictionary (`scp/core/autonomous_ledger.py:118-126, 159-170, 193-217`)**:
   `commit_intent` constructs the canonical intent payload for HMAC without `timestamp`:
   ```python
   canonical_intent = json.dumps({
       "event": "AUTONOMOUS_TOOL_INTENT",
       "task_id": task_id,
       "step_id": step_id,
       "tool_name": tool_name,
       "input_sha256": input_hash,
       "parent_trace_id": parent_trace_id or "",
   }, sort_keys=True, separators=(",", ":"))
   ```
   `commit_result` constructs the canonical result payload for HMAC without `duration_ms` and `timestamp`:
   ```python
   canonical_result = json.dumps({
       "event": "AUTONOMOUS_TOOL_RESULT",
       "task_id": task_id,
       "step_id": step_id,
       "tool_name": tool_name,
       "intent_entry_hash": intent_entry_hash,
       "output_sha256": output_hash,
       "evidence_sha256": evidence_hash,
       "status": status,
   }, sort_keys=True, separators=(",", ":"))
   ```
   An attacker can backdate or forward-date timestamps or alter tool execution durations arbitrarily, recompute the bare SHA-256 chain, and retain the original `hmac_sha256`. `verify_provenance()` passes `{"hash_chain_valid": True, "errors": []}` (`tests/test_m2_adversarial_challenger2.py::test_adversarial_timestamp_tampering_unauthenticated`).

3. **Event Type Spoofing Bypasses HMAC (`scp/core/autonomous_ledger.py:190-218`)**:
   If `fields["event"]` is renamed to any non-autonomous string (e.g. `"STANDARD_STEP_RECORD"`), `verify_provenance()` skips HMAC verification entirely, allowing forged records to persist in the ledger (`tests/test_m2_adversarial_challenger2.py::test_adversarial_event_type_spoofing_bypasses_hmac_check`).

4. **Lack of 2PC Atomicity and Linkage Verification in `AutonomousAuditLedger` (`scp/core/autonomous_ledger.py:174-225`)**:
   `AutonomousAuditLedger.verify_provenance()` verifies records purely on a per-line basis. It does not verify:
   - Whether each `AUTONOMOUS_TOOL_INTENT` has a corresponding `AUTONOMOUS_TOOL_RESULT`.
   - Whether an `AUTONOMOUS_TOOL_RESULT` references a real, existing `intent_entry_hash`.
   3 orphaned intents and 1 orphaned result pointing to `sha256:0000...` pass `verify_provenance()` without error (`tests/test_m2_adversarial_challenger2.py::test_adversarial_unverified_2pc_linkage_permits_orphaned_intents`).

5. **Two-Phase Commit in `HandsExecutor.execute()` (`scp/hands/hands_executor.py:155-217, 447-471`)**:
   - **Orphan Intent Prevention**: Pre-execution validation (missing token, scope mismatch, unapproved action, insufficient level, revoked authority, forged signature, kill switch engaged, dry run) all reject BEFORE line 207 (`self.audit_ledger.commit_intent(...)`). Zero entries are written to `autonomous_ledger.jsonl`.
   - **Failure Recovery**: Physical action dispatch is wrapped in `try ... except Exception as exc:`. When an action fails (e.g. non-zero returncode, file missing, or unhandled Python exception such as `RuntimeError`), Phase 2 Result block is committed with `status="FAILED"`, linking `intent_entry_hash` to `intent_hash`.
   - **Concurrency Safety**: 20 concurrent actions executed under `asyncio.gather` produced 40 strictly ordered sequential records (1..40) with valid cryptographic hash chains and no race conditions.

---

## 2. Logic Chain

1. **Premise 1**: The dispatch directive and Milestone M2 requirements mandate:
   *"Stress test AutonomousAuditLedger against tampering, recalculating hash chains without HMAC key. Verify verify_provenance() fails with hash_chain_valid=False and catches HMAC mismatch."*
2. **Premise 2**: An adversarial threat actor who has access to modify `autonomous_ledger.jsonl` does not possess `SCP_LEDGER_HMAC_KEY`.
3. **Observation 1 & Test**: The attacker modifies payload fields (e.g. `tool_name = "cmd.run"`) and strips `hmac_sha256`. The attacker then recalculates the bare SHA-256 hash chain for all blocks.
4. **Deduction 1**: Because `verify_provenance()` gates HMAC verification behind `if recorded_hmac:`, stripping `recorded_hmac` causes the HMAC verification branch to be skipped entirely.
5. **Deduction 2**: `TraceLedger.verify()` only validates that `entry["hash"] == sha256(canonical_body)`. Because the attacker recomputed bare SHA-256 digests, `TraceLedger.verify()` passes.
6. **Inference**: An attacker without the HMAC key CAN successfully tamper with records and recalculate hash chains without being caught by `verify_provenance()`. This is a classic signature stripping / algorithm downgrade vulnerability.
7. **Deduction 3**: `HandsExecutor.execute()` correctly implements Two-Phase Commit at the runtime execution boundary (no orphan intent on token failure, FAILED outcome committed on execution exception). However, `AutonomousAuditLedger`'s verification engine fails to provide the cryptographic tamper-proofing promised in M2.
8. **Conclusion**: Milestone M2 cannot be approved in its current state. A targeted remediation is required to close the HMAC stripping and unauthenticated timestamp vulnerabilities.

---

## 3. Caveats

1. **HandsExecutor Runtime PEP is Robust**:
   The runtime boundary in `HandsExecutor` is well-implemented: token checks occur strictly prior to Phase 1 intent commit, ensuring no orphan intent records are generated by blocked calls. Action failures (both handled errors and unhandled exceptions) cleanly commit Phase 2 result records with `status="FAILED"`.
2. **Keyed HMAC Check Works When Signature is Present**:
   When an attacker modifies authenticated fields (`task_id`, `step_id`, `tool_name`, `input_sha256`, `status`, etc.) while retaining the `hmac_sha256` field, `verify_provenance()` correctly detects the mismatch and flags `hmac_intent:1` or `hmac_result:2`. The flaw is strictly the omission of mandatory signature presence enforcement when `self.hmac_key` is configured.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M2 is **blocked** pending remediation of the following findings:

### Required Remediations:
1. **Fix HMAC Stripping in `AutonomousAuditLedger.verify_provenance()` (`scp/core/autonomous_ledger.py:188-220`)**:
   When `self.hmac_key` is not None, require that `hmac_sha256` MUST be present on every autonomous entry (`AUTONOMOUS_TOOL_INTENT` and `AUTONOMOUS_TOOL_RESULT`). If `recorded_hmac` is missing or falsy, append an error (e.g. `missing_hmac:{i}`) and invalidate provenance.
2. **Authenticate Timestamps in HMAC Canonical Payloads (`scp/core/autonomous_ledger.py:118-126, 159-170, 193-217`)**:
   Include `"timestamp"` in canonical intent and result dictionaries, and include `"duration_ms"` in canonical result dictionaries so timing metadata cannot be falsified without the secret key.
3. **Verify 2PC Linkage in `verify_provenance()`**:
   Track active intent hashes and verify that every `AUTONOMOUS_TOOL_RESULT` references a prior matching `AUTONOMOUS_TOOL_INTENT`, and flag any orphaned intent that lacks a corresponding outcome commit.

---

## 5. Verification Method

To independently reproduce the vulnerabilities and verify the findings:

1. **Run Full Adversarial Stress Suite**:
   ```powershell
   pytest tests/test_m2_adversarial_challenger2.py -v
   ```
   **Expected**: 10 passed in ~1s.
   Tests `test_adversarial_hmac_stripping_downgrade_vulnerability`, `test_adversarial_timestamp_tampering_unauthenticated`, `test_adversarial_event_type_spoofing_bypasses_hmac_check`, and `test_adversarial_unverified_2pc_linkage_permits_orphaned_intents` provide standalone, empirical proof of each identified flaw.

2. **Run Baseline Tests**:
   ```powershell
   pytest tests/T04_kernel/test_autonomous_audit_ledger_provenance.py tests/T03_capability/test_hands_authority_pep.py -v
   ```
   **Expected**: 16 passed.

3. **Run Goal 3 Adversarial Probe**:
   ```powershell
   python tools/adversarial_goal3_probe.py
   ```
   **Expected**: Total=203, Passed=203, Failed=0.

### Invalidation Conditions
This challenge report is invalidated if:
- `AutonomousAuditLedger.verify_provenance()` already rejects entries where `hmac_sha256` has been stripped by an attacker.
- An attacker modifying timestamps in an HMAC-authenticated ledger causes `verify_provenance()` to fail.
- `HandsExecutor.execute()` commits intent records to `autonomous_ledger.jsonl` when an invalid capability token is supplied.
