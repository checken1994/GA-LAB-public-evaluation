"""Regression pin for A2 AUDIT-F-05 — hands completion receipt self-attestation labeling.

The TaskKernelHandsBridge mints its completion receipt in the same process that
executed the work (executor self-attestation). The kernel's fail-closed receipt
gate (verify_verifier_receipt) only accepts verdict="VERIFIED" for a COMPLETED
commit, so the independent-vs-self distinction is carried by the verifier
identity recorded in the kernel journal and by the additive
``verificationProvenance`` response label. These pins lock that contract:

- the journal's TASK_COMPLETED payload must name the attesting subject as the
  executor itself (``hands-executor-self-verifier-v1``), never an independent
  verifier identity;
- the bridge response must carry ``verificationProvenance == "EXECUTOR_SELF_VERIFIED"``;
- the kernel flow itself must remain intact (COMPLETED with a signed receipt).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest

from scp.hands.hands_executor import HandsExecutor
from scp.hands.task_kernel_bridge import (
    EXECUTOR_SELF_VERIFIED,
    EXECUTOR_SELF_VERIFIED_VERIFIER_ID,
    TaskKernelHandsBridge,
)
from scp.pc_control.pc_controller import PCController
from scp.security.capability_epoch import CapabilityAuthority
from scp.task_kernel import TaskKernel


@pytest.fixture
def bridge_env(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cap_auth = CapabilityAuthority(tmp_path / "capability_state.json")
    executor = HandsExecutor(
        controller=PCController(working_dir=workspace),
        capability_authority=cap_auth,
        data_dir=tmp_path / "hands_data",
    )
    bridge = TaskKernelHandsBridge(executor, db_path=tmp_path / "kernel.sqlite3")
    return bridge, cap_auth, workspace


def test_mutating_action_receipt_is_labeled_executor_self_verified(bridge_env):
    bridge, cap_auth, workspace = bridge_env
    target = workspace / "selfattest_artifact.txt"
    request_key = f"selfattest-{uuid.uuid4().hex}"
    token = cap_auth.issue("hands:pc.write_file")
    confirmation_id = bridge.executor.controller.human_store.record_confirmation(
        action="pc.write_file", target=str(target.resolve()), ttl_seconds=60,
    )

    result = asyncio.run(
        bridge.execute(
            action="pc.write_file",
            params={"path": str(target), "content": "self-attested", "confirmation_id": confirmation_id},
            capability_level=3,
            approved=True,
            request_key=request_key,
            capability_token=token,
        )
    )
    assert result.get("success") is True, f"execution failed: {result}"
    task_id = result["kernel"]["taskId"]
    assert result["kernel"]["state"] == "COMPLETED"
    # Honest provenance label on the consumer-facing response.
    assert result["kernel"]["verificationProvenance"] == EXECUTOR_SELF_VERIFIED

    kernel = TaskKernel(str(bridge.data_dir.parent / "kernel.sqlite3"))
    try:
        events = kernel.get_events(task_id)
        completed = [e for e in events if e["type"] == "TASK_COMPLETED"]
        assert len(completed) == 1
        payload = json.loads(completed[0]["payload_json"])
        assert payload["verifier_id"] == EXECUTOR_SELF_VERIFIED_VERIFIER_ID, (
            "hands completion receipt must carry the executor self-attestation "
            "verifier identity, not an independent-verifier identity"
        )
        assert payload["verifier_verdict"] == "VERIFIED"
    finally:
        kernel.close()
