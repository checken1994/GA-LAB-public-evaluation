import asyncio
import hashlib
import uuid
from pathlib import Path

from scp.hands.hands_executor import HandsExecutor
from scp.hands.task_kernel_bridge import TaskKernelHandsBridge
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority
from scp.task_kernel import TaskKernel
from scp.verifier import IndependentVerifier

# ==============================================================================
# T09 - GOLDEN A (AGENT OS EXECUTION FLOW) - C-LEVEL, REAL PRODUCTION PATH
# ==============================================================================
# A real mutating action crosses the full production execution path:
#   TaskKernelHandsBridge -> HandsExecutor -> PCController -> real filesystem
# with kernel task lifecycle (create -> lease -> start -> idempotency claim ->
# checkpoint -> dispatch -> verify -> commit) and the post-state is judged by
# the independent verifier. No stub replaces any boundary component.
# ==============================================================================


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_golden_a_agent_os_real_execution_flow(tmp_path):
    """Golden A: create task -> capability -> bounded action -> real observation -> durable evidence."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cap_state = tmp_path / "capability_state.json"
    cap_auth = CapabilityAuthority(cap_state)
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=tmp_path / "hands_data",
    )
    bridge = TaskKernelHandsBridge(executor, db_path=tmp_path / "kernel.sqlite3")

    target = workspace / "golden_artifact.txt"
    content = "real_state_written_by_golden_a"
    request_key = f"golden-a-{uuid.uuid4().hex}"
    token = cap_auth.issue("hands:pc.write_file")
    confirmation_id = executor.controller.human_store.record_confirmation(
        action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
    )

    result = asyncio.run(
        bridge.execute(
            action="pc.write_file",
            params={"path": str(target), "content": content, "confirmation_id": confirmation_id},
            capability_level=3,
            approved=True,
            request_key=request_key,
            capability_token=token,
        )
    )

    assert result.get("success") is True, (
        f"Golden A execution failed: {result.get('error')!r} (result={result})"
    )
    kernel_info = result["kernel"]
    assert kernel_info["state"] == "COMPLETED", f"Task did not complete: {kernel_info}"
    assert kernel_info["evidenceRef"], "No durable evidence reference recorded"
    assert kernel_info["checkpointId"], "No pre-dispatch checkpoint recorded"

    # Real post-state on the filesystem (not a simulated observation).
    assert target.is_file(), "Agent OS failed to modify reality"
    assert target.read_text(encoding="utf-8") == content

    # Durable kernel state + tamper-evident journal, reloaded from disk.
    kernel = TaskKernel(str(tmp_path / "kernel.sqlite3"))
    task = kernel.get_task(kernel_info["taskId"])
    assert task["state"] == "COMPLETED"
    journal = kernel.verify_journal(kernel_info["taskId"])
    assert journal["hash_chain_valid"] is True, f"Journal hash chain broken: {journal}"
    assert journal["event_count"] > 0
    checkpoint = kernel.get_checkpoint(kernel_info["checkpointId"])
    assert checkpoint["task_id"] == kernel_info["taskId"]

    # Independent verification of the real post-state.
    verifier = IndependentVerifier()
    digest = _sha256_file(target)
    verified = verifier.verify(
        {"all": [{"kind": "artifact_hash", "value": digest}], "evidence_required": True},
        {"artifact_hash": digest, "evidence_ref": kernel_info["evidenceRef"]},
    )
    assert verified.verdict == "VERIFIED"

    # A tampered post-state must be rejected (PASS != TRUE).
    tampered = verifier.verify(
        {"all": [{"kind": "artifact_hash", "value": digest}], "evidence_required": True},
        {"artifact_hash": "0" * 64, "evidence_ref": kernel_info["evidenceRef"]},
    )
    assert tampered.verdict == "CONTRADICTED"

    # Idempotency: replaying the same logical request must not re-execute the
    # side effect (duplicate-side-effect guard at the real boundary).
    replay = asyncio.run(
        bridge.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "overwritten_by_replay", "confirmation_id": confirmation_id},
            capability_level=3,
            approved=True,
            request_key=request_key,
            capability_token=token,
        )
    )
    assert replay.get("success") is False, f"Replay executed the side effect again: {replay}"
    assert replay.get("safeToRetry") is False
    assert target.read_text(encoding="utf-8") == content, (
        "Replay mutated reality - idempotency guard is broken"
    )
