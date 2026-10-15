"""[F-03 regression 2026-09-25] Checkpoint finalization at the task boundary.

Runtime audit RUNTIME-AUDIT-20260925-0411 finding F-03 (LOW): the 'rag-read'
checkpoint of every /ask task stayed state='RUNNING' with NULL
post_observation_ref / verifier_verdict after the task reached COMPLETED or
HUMAN_REVIEW — the physical checkpoints artifact stayed weaker than the events
chain (verifier evidence only lived in the events table).

Fix under test:
  * TaskKernel.finalize_checkpoint() closes a checkpoint row at the moment the
    task outcome is committed; only evidence the caller actually has is
    recorded (nothing fabricated), payload_hash is recomputed so the row stays
    self-verifiable via validate_checkpoint, and a checkpoint that cannot be
    finalized records the reason IN the row instead of a bare RUNNING.
  * AskKernelAdapter.finalize()/fail() project the committed outcome
    (COMPLETED / HUMAN_REVIEW / FAILED) onto the checkpoint row.

FA-13: the terminal-boundary checkpoint branch previously had NO test; these
tests close that unproven branch.
"""
from __future__ import annotations

import json

import pytest

from scp.ask_kernel_adapter import AskKernelAdapter
from scp.task_kernel import KernelError
from scp.task_kernel_parts.taskkernel import CheckpointCorrupt


@pytest.fixture(autouse=True)
def _no_crosscheck(monkeypatch):
    monkeypatch.setenv("SCP_MULTI_LLM_CROSSCHECK", "0")


@pytest.fixture()
def judge_gate(monkeypatch):
    """Hermetic semantic judge (same seam as test_ask_trace_ledger_final_decision)."""
    import scp.runtime.judge_llm as judge_mod

    state = {"pass": True, "calls": 0}

    async def _fake_judge(question: str, ai_answer: str, context: str = "") -> bool:
        state["calls"] += 1
        return state["pass"]

    monkeypatch.setattr(judge_mod, "_llm_judge_async", _fake_judge)
    return state


class DummyReq:
    question = "what color is the sky?"
    contexts = ["sky is blue"]
    retrieved_context = ""
    session_id = "checkpoint-finalization-test"


JUDGE_LEVEL_RESPONSE = {
    "final_answer": "The sky is blue",
    "verdict": "PASS",
    "governance_decision": "UPHOLD",
    "v98_classification": {"provenance": "input_context_only"},
}


def _make_adapter(tmp_path) -> AskKernelAdapter:
    return AskKernelAdapter(
        db_path=str(tmp_path / "kernel.sqlite3"),
        trace_path=str(tmp_path / "adapter_trace.jsonl"),
    )


def _read_checkpoint(adapter: AskKernelAdapter, checkpoint_id: str) -> dict:
    row = adapter.kernel.get_checkpoint(checkpoint_id)
    assert row is not None, "checkpoint row missing"
    return row


@pytest.mark.asyncio
async def test_completed_ask_finalizes_checkpoint_row(judge_gate, monkeypatch, tmp_path):
    """Core F-03 rule: after a COMPLETED ask the checkpoint row must be
    terminal with the verifier evidence that finalize actually computed —
    never a bare RUNNING with NULL post_ref/verifier_verdict."""
    monkeypatch.chdir(tmp_path)
    judge_gate["pass"] = True
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE), req)

        assert result["task"]["state"] == "COMPLETED"
        row = _read_checkpoint(adapter, task["checkpoint_id"])
        # F-03 core assertion: terminal, not RUNNING
        assert row["state"] == "COMPLETED"
        assert row["state"] != "RUNNING"
        # Evidence recorded from the verification result finalize computed
        assert row["verifier_verdict"] == "VERIFIED"
        assert str(row["post_observation_ref"]).startswith(f"ask://{task['task_id']}/response/")
        # The row stays self-verifiable (payload_hash recomputed, not stale)
        validated = adapter.kernel.validate_checkpoint(
            task["checkpoint_id"], task["checkpoint_planned_action"]
        )
        assert validated["state"] == "COMPLETED"
        tool_result = json.loads(row["tool_result_json"])
        assert tool_result["final_task_state"] == "COMPLETED"
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_escalated_ask_finalizes_checkpoint_to_human_review(judge_gate, monkeypatch, tmp_path):
    """The injection-run shape (audit task ask-4661675b): kernel HUMAN_REVIEW
    must also be projected onto the checkpoint row, with the CONTRADICTED
    verification verdict recorded — not left RUNNING."""
    monkeypatch.chdir(tmp_path)
    judge_gate["pass"] = False  # verification CONTRADICTED -> fail-closed escalation
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE), req)

        assert result["task"]["state"] == "HUMAN_REVIEW"
        row = _read_checkpoint(adapter, task["checkpoint_id"])
        assert row["state"] == "HUMAN_REVIEW"
        assert row["state"] != "RUNNING"
        assert row["verifier_verdict"] == "CONTRADICTED"
        assert str(row["post_observation_ref"]).startswith(f"ask://{task['task_id']}/")
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_finalize_checkpoint_rejects_wrong_planned_action(judge_gate, monkeypatch, tmp_path):
    """Fail-closed: finalize_checkpoint without the exact planned_action
    (hash mismatch) must raise CheckpointCorrupt and leave the row unchanged —
    no blind checkpoint mutation."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        with pytest.raises(CheckpointCorrupt):
            adapter.kernel.finalize_checkpoint(
                task["task_id"],
                task["checkpoint_id"],
                planned_action={"operation": "forged-action"},
                verifier_verdict="VERIFIED",
            )
        row = _read_checkpoint(adapter, task["checkpoint_id"])
        assert row["state"] == "RUNNING"  # untouched
        assert row["verifier_verdict"] is None
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_undecided_task_records_block_reason_in_row(judge_gate, monkeypatch, tmp_path):
    """Fail-closed visibility: a checkpoint that legitimately cannot be
    finalized (task still RUNNING — crash/timeout path) must record WHY in its
    row instead of leaving a bare unexplained RUNNING."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = adapter.kernel.finalize_checkpoint(
            task["task_id"],
            task["checkpoint_id"],
            planned_action=task["checkpoint_planned_action"],
            note="worker_died_before_response",
        )
        assert result["finalization"] == "blocked_task_not_decided"
        row = _read_checkpoint(adapter, task["checkpoint_id"])
        assert row["state"] == "RUNNING"  # honest: task has NOT decided
        blocked = json.loads(row["tool_result_json"])
        assert blocked["finalization"] == "BLOCKED"
        assert "task_state=RUNNING" in blocked["finalization_reason"]
        assert "worker_died_before_response" in blocked["finalization_reason"]
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_fail_path_also_finalizes_checkpoint(judge_gate, monkeypatch, tmp_path):
    """The adapter fail() path (run_rag exception) must also close the
    checkpoint row against the FAILED task — with NO fabricated verifier
    verdict (none exists on this path)."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        adapter.fail(task, "ask_rag_exception")

        row = _read_checkpoint(adapter, task["checkpoint_id"])
        assert row["state"] in {"FAILED", "CANCELLED"}
        assert row["state"] != "RUNNING"
        assert row["verifier_verdict"] is None  # nothing fabricated on the failure path
        blocked = json.loads(row["tool_result_json"])
        assert blocked["final_task_state"] == row["state"]
        assert str(row["post_observation_ref"]).endswith("/failure/ask_rag_exception")
    finally:
        adapter.kernel.close()


def test_finalize_checkpoint_requires_evidence_or_note(judge_gate, monkeypatch, tmp_path):
    """Fail-closed guard: finalizing with NO evidence fields and NO note would
    be a no-data write — must be rejected outright."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        with pytest.raises(KernelError):
            adapter.kernel.finalize_checkpoint(
                task["task_id"],
                task["checkpoint_id"],
                planned_action=task["checkpoint_planned_action"],
            )
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_finalize_checkpoint_unknown_cp_and_task_mismatch(judge_gate, monkeypatch, tmp_path):
    """Fail-closed guards: unknown checkpoint_id -> CheckpointCorrupt;
    checkpoint_id belonging to another task -> KernelError."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        with pytest.raises(CheckpointCorrupt):
            adapter.kernel.finalize_checkpoint(
                task["task_id"],
                "cp_does_not_exist",
                planned_action=task["checkpoint_planned_action"],
                verifier_verdict="VERIFIED",
            )
        other_task = adapter.begin("a different question entirely", [], "", "other-session")
        with pytest.raises(KernelError):
            adapter.kernel.finalize_checkpoint(
                other_task["task_id"],
                task["checkpoint_id"],  # belongs to the FIRST task
                planned_action=task["checkpoint_planned_action"],
                verifier_verdict="VERIFIED",
            )
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_unknown_checkpoint_is_left_to_reconcile(judge_gate, monkeypatch, tmp_path):
    """A side-effect-UNKNOWN checkpoint is owned by the reconcile contract —
    finalize_checkpoint must refuse to claim a terminal outcome for it."""
    monkeypatch.chdir(tmp_path)
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        dispatched = adapter.kernel.record_action_dispatched(
            task["task_id"],
            task["lease_id"],
            "rag-read",
            task["checkpoint_planned_action"],
            0,
            task["input_hash"],
            "provider-req-unknown-1",
        )
        assert dispatched["state"] == "UNKNOWN"
        result = adapter.kernel.finalize_checkpoint(
            task["task_id"],
            dispatched["checkpoint_id"],
            planned_action=task["checkpoint_planned_action"],
            verifier_verdict="VERIFIED",
        )
        assert result["finalization"] == "owned_by_reconcile"
        row = _read_checkpoint(adapter, dispatched["checkpoint_id"])
        assert row["state"] == "UNKNOWN"  # untouched — reconcile owns it
        assert row["verifier_verdict"] is None
    finally:
        adapter.kernel.close()


@pytest.mark.asyncio
async def test_checkpoint_finalization_is_idempotent(judge_gate, monkeypatch, tmp_path):
    """A second finalization of the same checkpoint is an idempotent no-op —
    the recorded decision is never rewritten."""
    monkeypatch.chdir(tmp_path)
    judge_gate["pass"] = True
    adapter = _make_adapter(tmp_path)
    try:
        req = DummyReq()
        task = adapter.begin(req.question, list(req.contexts), req.retrieved_context, req.session_id)
        result = await adapter.finalize(task, dict(JUDGE_LEVEL_RESPONSE), req)
        assert result["task"]["state"] == "COMPLETED"
        first = _read_checkpoint(adapter, task["checkpoint_id"])

        again = adapter.kernel.finalize_checkpoint(
            task["task_id"],
            task["checkpoint_id"],
            planned_action=task["checkpoint_planned_action"],
            verifier_verdict="FORGED-REWRITE-ATTEMPT",
            post_observation_ref="ask://forged/post",
        )
        assert again["finalization"] == "already_final"
        second = _read_checkpoint(adapter, task["checkpoint_id"])
        assert second["verifier_verdict"] == first["verifier_verdict"] == "VERIFIED"
        assert second["post_observation_ref"] == first["post_observation_ref"]
        assert second["state"] == "COMPLETED"
    finally:
        adapter.kernel.close()
