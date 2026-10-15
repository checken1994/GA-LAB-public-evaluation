"""Adversarial stress testing suite for Milestone M2:
- AutonomousAuditLedger tamper resistance, hash chain recalculation without HMAC key, HMAC downgrade/stripping attacks.
- HandsExecutor Two-Phase Commit token boundary, failure recovery, and orphan intent prevention.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scp.core.autonomous_ledger import AutonomousAuditLedger
from scp.hands.hands_executor import HandsExecutor
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken


@pytest.fixture(autouse=True)
def setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCP_CAPABILITY_SECRET", "adversarial-test-secret-32bytes-long!")
    monkeypatch.setenv("SCP_LEDGER_HMAC_KEY", "ledger-hmac-key-for-challenger2-32b!")


# ==============================================================================
# 1. AUTONOMOUS AUDIT LEDGER ADVERSARIAL CHALLENGES
# ==============================================================================


def test_adversarial_hmac_tamper_detection_when_signature_retained(tmp_path: Path) -> None:
    """Verifies that tampering record fields while keeping the old HMAC signature fails verification."""
    ledger_path = tmp_path / "tamper_retained.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="secret-key")

    intent = ledger.commit_intent("t1", "s1", "pc.status", {"cmd": "ls"}, {"token_id": "tok1", "signature": "sig1"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {"ok": True}, {}, "SUCCESS", 1.0)

    # Attacker tampers with tool_name in intent, recalculates bare SHA-256 hash
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])

    e1["fields"]["tool_name"] = "pc.forged_command"
    body1 = {k: v for k, v in e1.items() if k != "hash"}
    e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    e2["prev_hash"] = e1["hash"]
    body2 = {k: v for k, v in e2.items() if k != "hash"}
    e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_path.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False
    assert any("hmac_intent:1" in err for err in verification["errors"])


def test_adversarial_hmac_stripping_downgrade_vulnerability(tmp_path: Path) -> None:
    """DEMONSTRATES VULNERABILITY VULN-M2-01:
    An attacker without HMAC key can modify record fields, delete 'hmac_sha256',
    recompute bare SHA-256 hash chains, and verify_provenance() silently passes!
    """
    ledger_path = tmp_path / "tamper_strip.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="super-secret-key")

    intent = ledger.commit_intent("task_root", "step_01", "pc.status", {"mode": "safe"}, {"token_id": "tok_1", "signature": "sig_1"})
    ledger.commit_result("task_root", "step_01", "pc.status", intent["hash"], {"ok": True}, {}, "SUCCESS", 1.0)

    # Initial provenance is valid
    assert ledger.verify_provenance()["hash_chain_valid"] is True

    # Attacker tampering: Change tool to forbidden cmd.run, delete hmac_sha256
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])

    e1["fields"]["tool_name"] = "cmd.run"
    del e1["fields"]["hmac_sha256"]
    body1 = {k: v for k, v in e1.items() if k != "hash"}
    e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    e2["prev_hash"] = e1["hash"]
    del e2["fields"]["hmac_sha256"]
    body2 = {k: v for k, v in e2.items() if k != "hash"}
    e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_path.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False, "verify_provenance must reject stripped HMACs"
    assert any("missing_hmac_intent:1" in err for err in verification["errors"])


def test_adversarial_timestamp_tampering_unauthenticated(tmp_path: Path) -> None:
    """DEMONSTRATES VULNERABILITY VULN-M2-02 REMEDIATION:
    The canonical HMAC payload includes timestamp,
    preventing an attacker from backdating or falsifying execution records without detection.
    """
    ledger_path = tmp_path / "tamper_time.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="super-secret-key")

    intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 10.0)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])

    # Tamper timestamps by backdating 10 years
    e1["fields"]["timestamp"] = 1400000000.0
    body1 = {k: v for k, v in e1.items() if k != "hash"}
    e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    e2["prev_hash"] = e1["hash"]
    e2["fields"]["timestamp"] = 1400000001.0
    e2["fields"]["duration_ms"] = 999999.0
    body2 = {k: v for k, v in e2.items() if k != "hash"}
    e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_path.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False, "verify_provenance must detect tampered timestamps"
    assert any("hmac_intent:1" in err for err in verification["errors"])


def test_adversarial_bogus_hmac_key_recomputation(tmp_path: Path) -> None:
    """Verifies that an attacker recalculating HMAC signatures with an incorrect key fails verification."""
    ledger_path = tmp_path / "bogus_key.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="correct-key-32bytes")

    intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])

    # Attacker recalculates HMAC using 'attacker-bogus-key'
    bogus_key = b"attacker-bogus-key"
    canonical1 = json.dumps({
        "event": "AUTONOMOUS_TOOL_INTENT",
        "task_id": "t1",
        "step_id": "s1",
        "tool_name": "pc.forged",
        "input_sha256": e1["fields"]["input_sha256"],
        "parent_trace_id": "",
    }, sort_keys=True, separators=(",", ":"))
    e1["fields"]["tool_name"] = "pc.forged"
    import hmac
    e1["fields"]["hmac_sha256"] = hmac.new(bogus_key, canonical1.encode("utf-8"), hashlib.sha256).hexdigest()

    body1 = {k: v for k, v in e1.items() if k != "hash"}
    e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    e2["prev_hash"] = e1["hash"]
    body2 = {k: v for k, v in e2.items() if k != "hash"}
    e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_path.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False
    assert any("hmac_intent:1" in err for err in verification["errors"])


def test_adversarial_event_type_spoofing_bypasses_hmac_check(tmp_path: Path) -> None:
    """REGRESSION PIN (A13b H-03 / VULN-M2-03 remediation, nodeid preserved):
    the adversarial technique under test is renaming the event type of an
    autonomous record (plus stripping its HMAC and re-anchoring the bare hash
    chain) to dodge keyed HMAC verification. Post-remediation this must FAIL
    closed: the record is still recognized as autonomous via its structural
    markers and rejected with a ``spoofed_event_type`` error.
    """
    ledger_path = tmp_path / "tamper_event.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="super-secret-key")

    intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])

    # Spoof event name and modify tool_name
    e1["fields"]["event"] = "STANDARD_STEP_RECORD"
    e1["fields"]["tool_name"] = "pc.forged_command"
    del e1["fields"]["hmac_sha256"]
    body1 = {k: v for k, v in e1.items() if k != "hash"}
    e1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    e2["prev_hash"] = e1["hash"]
    del e2["fields"]["hmac_sha256"]
    e2["fields"]["event"] = "STANDARD_STEP_RESULT"
    body2 = {k: v for k, v in e2.items() if k != "hash"}
    e2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_path.write_text(json.dumps(e1, sort_keys=True) + "\n" + json.dumps(e2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False, "spoofed event type must fail verification closed"
    assert any("spoofed_event_type:1" in err for err in verification["errors"])
    assert any("spoofed_event_type:2" in err for err in verification["errors"])


def test_adversarial_unverified_2pc_linkage_permits_orphaned_intents(tmp_path: Path) -> None:
    """REGRESSION PIN (A13b H-03 / FINDING-M2-04 remediation, nodeid preserved):
    the adversarial technique under test is committing orphaned intents and a
    result pointing to a non-existent intent. Post-remediation 2PC linkage is
    enforced and such records must FAIL verification (``orphan_intent`` /
    ``orphan_result``), never pass silently.
    """
    ledger_path = tmp_path / "orphan_chain.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="super-secret-key")

    # Record 3 intents without ever recording results (orphaned intents)
    ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok1", "signature": "sig1"})
    ledger.commit_intent("t2", "s2", "pc.status", {}, {"token_id": "tok2", "signature": "sig2"})
    ledger.commit_intent("t3", "s3", "pc.status", {}, {"token_id": "tok3", "signature": "sig3"})

    # Record an orphan result pointing to a completely non-existent intent hash
    ledger.commit_result("t4", "s4", "pc.status", "sha256:0000000000000000000000000000000000000000000000000000000000000000", {"ok": True}, {}, "SUCCESS", 1.0)

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False, "orphan 2PC records must fail verification closed"
    assert any("orphan_intent:1" in err for err in verification["errors"])
    assert any("orphan_intent:2" in err for err in verification["errors"])
    assert any("orphan_intent:3" in err for err in verification["errors"])
    assert any("orphan_result:4" in err for err in verification["errors"])


def test_adversarial_corrupt_line_fails_closed_as_parse_error(tmp_path: Path) -> None:
    """A ledger line corrupted beyond JSON parsing must fail verification
    closed (``parse_error``), never be silently skipped by the verifier."""
    ledger_path = tmp_path / "corrupt_line.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_path, hmac_key="super-secret-key")

    intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    lines[0] = "{corrupted-json-not-an-object"
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False, "corrupt ledger lines must fail closed"
    assert any("parse_error:1" in err for err in verification["errors"])


# ==============================================================================
# 2. HANDSEXECUTOR TWO-PHASE COMMIT BOUNDARY & ORPHAN PREVENTION
# ==============================================================================


@pytest.mark.asyncio
async def test_hands_2pc_orphan_prevention_on_unauthorized_token_rejections(tmp_path: Path) -> None:
    """Stress test ensuring that ANY policy/token rejection blocks execution and commits ZERO intent records."""
    cap_auth = CapabilityAuthority(tmp_path / "cap_state.json")
    executor = HandsExecutor(
        data_dir=tmp_path / "hands_data",
        capability_authority=cap_auth,
    )
    tok_status = cap_auth.issue("hands:pc.status")
    tok_write = cap_auth.issue("hands:pc.write_file")

    # 1. Missing token
    r1 = await executor.execute("pc.status", capability_token=None)
    assert r1["success"] is False
    assert "CapabilityRequiredError" in r1["error"]

    # 2. Scope mismatch
    r2 = await executor.execute("pc.write_file", {"path": "test.txt", "content": "x"}, capability_token=tok_status)
    assert r2["success"] is False
    assert "CapabilityScopeMismatchError" in r2["error"]

    # 3. Unregistered action
    tok_unreg = cap_auth.issue("hands:unregistered.action")
    r3 = await executor.execute("unregistered.action", capability_token=tok_unreg)
    assert r3["success"] is False

    # 4. Insufficient capability level
    r4 = await executor.execute("pc.write_file", {"path": "test.txt", "content": "x"}, capability_level=0, approved=True, capability_token=tok_write)
    assert r4["success"] is False
    assert "requires capability" in r4["error"]

    # 5. Missing approval
    r5 = await executor.execute("pc.write_file", {"path": "test.txt", "content": "x"}, capability_level=3, approved=False, capability_token=tok_write)
    assert r5["success"] is False
    assert "Explicit approval required" in r5["error"]

    # 6. Dry run mode
    r6 = await executor.execute("pc.status", capability_token=tok_status, dry_run=True)
    assert r6["success"] is True
    assert r6.get("dryRun") is True

    # 7. Revoked authority
    cap_auth.revoke()
    r7 = await executor.execute("pc.status", capability_token=tok_status)
    assert r7["success"] is False
    assert "revoked" in r7["error"].lower()

    # 8. Malformed token signature: raises InvalidTokenSignatureError fail-closed
    from scp.core.capability_token import InvalidTokenSignatureError
    tok_forged = CapabilityToken(
        subject="hands:pc.status",
        epoch=cap_auth.status()["epoch"],
        token_id="forged_tok",
        issued_at=100.0,
        signature="invalid_signature_xyz",
    )
    with pytest.raises(InvalidTokenSignatureError):
        await executor.execute("pc.status", capability_token=tok_forged)

    # VERIFY ORPHAN PREVENTION: Ledger must contain ZERO entries across all 8 blocked/dry-run calls!
    ledger_path = tmp_path / "hands_data" / "autonomous_ledger.jsonl"
    lines = ledger_path.read_text(encoding="utf-8").splitlines() if ledger_path.exists() else []
    assert len(lines) == 0, f"Orphan intent records detected: {lines}"


@pytest.mark.asyncio
async def test_hands_2pc_failure_recovery_commits_failed_outcome(tmp_path: Path) -> None:
    """Verifies that when tool execution fails (e.g., file not found or internal error),
    Phase 2 outcome block is properly committed with status='FAILED' and linked to Phase 1 intent.
    """
    cap_auth = CapabilityAuthority(tmp_path / "cap_state.json")
    executor = HandsExecutor(
        data_dir=tmp_path / "hands_data",
        capability_authority=cap_auth,
    )
    tok_read = cap_auth.issue("hands:pc.read_file")

    # Execute read_file on non-existent file
    res = await executor.execute("pc.read_file", {"path": str(tmp_path / "missing_file.txt")}, capability_token=tok_read)
    assert res["success"] is False
    assert "intentHash" in res
    assert "outcomeHash" in res
    assert res["ledgerSeq"] == 2

    # Check ledger records
    ledger_path = tmp_path / "hands_data" / "autonomous_ledger.jsonl"
    lines = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[0]["fields"]["event"] == "AUTONOMOUS_TOOL_INTENT"
    assert lines[1]["fields"]["event"] == "AUTONOMOUS_TOOL_RESULT"
    assert lines[1]["fields"]["status"] == "FAILED"
    assert lines[1]["fields"]["intent_entry_hash"] == res["intentHash"]

    v = executor.audit_ledger.verify_provenance()
    assert v["hash_chain_valid"] is True
    assert v["entries"] == 2


@pytest.mark.asyncio
async def test_hands_2pc_simulated_exception_commits_failed_outcome(tmp_path: Path) -> None:
    """Verifies that an unexpected Python exception inside action dispatch is caught
    and commits a Phase 2 outcome block with status='FAILED', avoiding orphan intents.
    """
    cap_auth = CapabilityAuthority(tmp_path / "cap_state.json")
    executor = HandsExecutor(
        data_dir=tmp_path / "hands_data",
        capability_authority=cap_auth,
    )
    tok = cap_auth.issue("hands:pc.status")

    with patch.object(executor.controller, "status", side_effect=RuntimeError("Simulated controller crash")):
        res = await executor.execute("pc.status", capability_token=tok)

    assert res["success"] is False
    assert "Simulated controller crash" in res["error"]
    assert "intentHash" in res
    assert "outcomeHash" in res

    ledger_path = tmp_path / "hands_data" / "autonomous_ledger.jsonl"
    lines = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[1]["fields"]["status"] == "FAILED"
    assert lines[1]["fields"]["intent_entry_hash"] == res["intentHash"]


@pytest.mark.asyncio
async def test_hands_2pc_high_concurrency_stress(tmp_path: Path) -> None:
    """Stress test executing 20 concurrent actions to verify lock integrity,
    continuous sequential sequence numbers, and strict 2PC Intent-Result interleaving.
    """
    cap_auth = CapabilityAuthority(tmp_path / "cap_state.json")
    executor = HandsExecutor(
        data_dir=tmp_path / "hands_data",
        capability_authority=cap_auth,
    )
    tokens = [cap_auth.issue("hands:pc.status") for _ in range(20)]

    async def execute_task(i: int) -> dict:
        return await executor.execute("pc.status", params={"task_id": f"conc_task_{i}", "step_id": f"step_{i}"}, capability_token=tokens[i])

    results = await asyncio.gather(*[execute_task(i) for i in range(20)])
    assert len(results) == 20
    assert all(r["success"] for r in results)

    ledger_path = tmp_path / "hands_data" / "autonomous_ledger.jsonl"
    lines = [json.loads(l) for l in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 40

    # Verify sequence numbers are strictly 1..40
    for idx, entry in enumerate(lines, 1):
        assert entry["seq"] == idx

    # Verify provenance across all 40 blocks
    v = executor.audit_ledger.verify_provenance()
    assert v["hash_chain_valid"] is True
    assert v["entries"] == 40
