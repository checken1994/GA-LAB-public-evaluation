import asyncio
import hashlib
import json
import os
from pathlib import Path

from scp.core.autonomous_ledger import AutonomousAuditLedger, ProvenanceBlock
from scp.hands.hands_executor import HandsExecutor
from scp.security.capability_epoch import CapabilityAuthority


def test_autonomous_tool_two_phase_commit(tmp_path: Path) -> None:
    """Verifies Phase 1 Intent and Phase 2 Result form a continuous cryptographic SHA-256 hash chain."""
    ledger_file = tmp_path / "trace_ledger.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_file)

    # Phase 1: Tool invocation intent
    intent = ledger.commit_intent(
        task_id="task_auton_01",
        step_id="step_01",
        tool_name="sys.inspect",
        params={"category": "hardware"},
        capability_token={"token_id": "tok_alpha", "signature": "sig_hmac_123"},
        parent_trace_id="trace_root_00",
    )

    assert intent["seq"] == 1
    assert intent["prev_hash"] is None
    assert intent["hash"].startswith("sha256:")
    assert intent["fields"]["task_id"] == "task_auton_01"
    assert intent["fields"]["event"] == "AUTONOMOUS_TOOL_INTENT"

    # Phase 2: Tool execution result
    result_entry = ledger.commit_result(
        task_id="task_auton_01",
        step_id="step_01",
        tool_name="sys.inspect",
        intent_entry_hash=intent["hash"],
        result_data={"cpu_cores": 8, "total_gb": 32.0},
        evidence={"metrics_collected": True},
        status="SUCCESS",
        duration_ms=4.2,
    )

    assert result_entry["seq"] == 2
    assert result_entry["prev_hash"] == intent["hash"]
    assert result_entry["hash"].startswith("sha256:")
    assert result_entry["fields"]["status"] == "SUCCESS"
    assert result_entry["fields"]["intent_entry_hash"] == intent["hash"]

    # Verify provenance across the entire chain
    verification = ledger.verify_provenance()
    assert verification["entries"] == 2
    assert verification["hash_chain_valid"] is True
    assert len(verification["errors"]) == 0


def test_autonomous_ledger_tamper_detection(tmp_path: Path) -> None:
    """Any modification or forgery in the ledger causes hash chain verification to fail."""
    ledger_file = tmp_path / "tamper_ledger.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_file)

    intent = ledger.commit_intent(
        task_id="task_secure_01",
        step_id="step_01",
        tool_name="cmd.run",
        params={"command": "git status"},
        capability_token={"token_id": "tok_test", "signature": "sig_000"},
    )
    ledger.commit_result(
        task_id="task_secure_01",
        step_id="step_01",
        tool_name="cmd.run",
        intent_entry_hash=intent["hash"],
        result_data={"returncode": 0},
        evidence={"stdout": "clean"},
        status="SUCCESS",
        duration_ms=15.0,
    )

    # Confirm valid before tamper
    assert ledger.verify_provenance()["hash_chain_valid"] is True

    # Tamper with the ledger: modify a field in line 1 without updating the hash
    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    tampered_entry = json.loads(lines[0])
    tampered_entry["fields"]["task_id"] = "task_forged_99"
    lines[0] = json.dumps(tampered_entry, ensure_ascii=False, sort_keys=True)
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Verification must catch the tamper
    check = ledger.verify_provenance()
    assert check["hash_chain_valid"] is False
    assert any("hash:1" in err for err in check["errors"])


def test_autonomous_ledger_redacts_tokens(tmp_path: Path) -> None:
    """Confidential parameters such as tokens and passwords are automatically redacted in ledger records."""
    ledger_file = tmp_path / "redact_ledger.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_file)

    # Canary credential values are generated at runtime so no literal
    # credential pattern exists in test source; the assertions below
    # compare against the same generated values (strength preserved).
    canary_api_key = f"sk-{os.urandom(10).hex()}"
    canary_password = f"super-secret-{os.urandom(10).hex()}"
    canary_token = f"bearer sk-{os.urandom(8).hex()}"

    ledger.commit_intent(
        task_id="task_redact_01",
        step_id="step_01",
        tool_name="sys.inspect",
        params={
            "api_key": canary_api_key,
            "password": canary_password,
            "token": canary_token,
            "safe_option": "verbose",
        },
        capability_token={"token_id": "tok_redact", "signature": "sig_redact"},
    )

    record_line = ledger_file.read_text(encoding="utf-8").strip()
    # Raw credentials must NOT appear in plaintext
    assert canary_api_key not in record_line
    assert canary_password not in record_line
    assert canary_token not in record_line
    assert "[REDACTED]" in record_line or "[REDACTED_STRING]" in record_line


def test_provenance_block_deterministic_hashing() -> None:
    """ProvenanceBlock produces deterministic cryptographic digests and detects perturbations."""
    block1 = ProvenanceBlock(
        block_index=1,
        prev_block_hash=None,
        task_id="t1",
        step_id="s1",
        tool_name="sys.inspect",
        input_sha256="sha256:1111",
        capability_token_id="tok_1",
        capability_token_hash="sha256:2222",
        output_sha256="sha256:3333",
        status="SUCCESS",
        duration_ms=10.0,
        timestamp=1000.0,
    )

    h1 = block1.compute_hash()
    h2 = block1.compute_hash()
    assert h1 == h2
    assert h1.startswith("sha256:")

    # Perturbed block
    block_altered = ProvenanceBlock(
        block_index=1,
        prev_block_hash=None,
        task_id="t1",
        step_id="s1",
        tool_name="sys.inspect",
        input_sha256="sha256:1111",
        capability_token_id="tok_1",
        capability_token_hash="sha256:2222",
        output_sha256="sha256:3333",
        status="FAILED",  # Changed
        duration_ms=10.0,
        timestamp=1000.0,
    )
    assert block_altered.compute_hash() != h1


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


def test_autonomous_ledger_hmac_stripping_rejected(tmp_path: Path) -> None:
    """Verifies that deleting hmac_sha256 from a record causes verify_provenance to fail closed."""
    ledger_file = tmp_path / "strip_hmac.jsonl"
    ledger = AutonomousAuditLedger(ledger_path=ledger_file, hmac_key="secret-key-32b")
    intent = ledger.commit_intent("t1", "s1", "pc.status", {}, {"token_id": "tok", "signature": "sig"})
    ledger.commit_result("t1", "s1", "pc.status", intent["hash"], {}, {}, "SUCCESS", 1.0)

    # Initial provenance is valid
    assert ledger.verify_provenance()["hash_chain_valid"] is True

    # Attacker strips hmac_sha256 from intent entry and recalculates bare SHA-256 hash chain
    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])

    del entry1["fields"]["hmac_sha256"]
    body1 = {k: v for k, v in entry1.items() if k != "hash"}
    entry1["hash"] = "sha256:" + hashlib.sha256(json.dumps(body1, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    entry2["prev_hash"] = entry1["hash"]
    body2 = {k: v for k, v in entry2.items() if k != "hash"}
    entry2["hash"] = "sha256:" + hashlib.sha256(json.dumps(body2, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    ledger_file.write_text(json.dumps(entry1, sort_keys=True) + "\n" + json.dumps(entry2, sort_keys=True) + "\n", encoding="utf-8")

    verification = ledger.verify_provenance()
    assert verification["hash_chain_valid"] is False
    assert any("missing_hmac_intent:1" in err for err in verification["errors"])

