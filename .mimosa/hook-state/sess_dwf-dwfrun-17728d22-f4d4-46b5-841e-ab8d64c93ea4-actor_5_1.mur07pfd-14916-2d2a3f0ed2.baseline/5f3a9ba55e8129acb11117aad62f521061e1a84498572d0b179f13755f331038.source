from __future__ import annotations

import json

import pytest

from scp.task_kernel import KernelError, TaskKernel


def _reconciling_task(kernel: TaskKernel, task_id: str = "reconcile-1") -> tuple[str, str]:
    kernel.create_task(task_id, "recovery-test", "reconcile uncertain external write", "R2")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state, actor="recovery-test", reason="setup")
    lease = kernel.claim(task_id, "worker-before-loss", ttl_seconds=300)
    kernel.start(task_id, lease.lease_id)
    logical_key, claimed = kernel.idempotency_claim(
        task_id, "submit", "external.submit", "remote-object-1"
    )
    assert claimed is True
    dispatched = kernel.record_action_dispatched(
        task_id,
        lease.lease_id,
        "submit",
        {"action": "submit", "resource": "remote-object-1"},
        0,
        logical_key,
        "provider-request-123",
        pre_observation_ref="evidence://pre",
    )
    checkpoint_id = str(dispatched["checkpoint_id"])
    kernel.release(task_id, lease.lease_id)
    kernel.enter_reconciling(task_id, checkpoint_id, reason="response_lost")
    assert kernel.get_task(task_id)["state"] == "RECONCILING"
    return checkpoint_id, logical_key


@pytest.mark.parametrize(
    ("outcome", "expected_status", "expected_event"),
    [
        ("PARTIAL", "RECONCILED_PARTIAL", "RECONCILE_PARTIAL"),
        ("CONFLICT", "RECONCILED_CONFLICT", "RECONCILE_CONFLICT"),
    ],
)
def test_ambiguous_reconciliation_outcomes_are_durable_and_never_retryable(
    tmp_path, outcome: str, expected_status: str, expected_event: str
) -> None:
    db_path = tmp_path / f"{outcome.lower()}.sqlite3"
    kernel = TaskKernel(db_path)
    try:
        checkpoint_id, logical_key = _reconciling_task(kernel)
        task = kernel.reconcile_unknown(
            "reconcile-1",
            checkpoint_id,
            outcome,
            f"evidence://{outcome.lower()}",
            "independent-state-verifier",
        )

        assert task["state"] == "HUMAN_REVIEW"
        idem = kernel.idempotency_status(logical_key)
        assert idem["status"] == expected_status
        assert idem["result_ref"] == f"evidence://{outcome.lower()}"

        events = kernel.get_events("reconcile-1")
        assert events[-1]["type"] == expected_event
        payload = json.loads(events[-1]["payload_json"])
        assert payload["outcome"] == outcome
        assert payload["safe_to_retry"] is False
        assert payload["verifier_id"] == "independent-state-verifier"

        # A fresh recovery context may read the duplicate, but cannot re-claim it.
        reader = TaskKernel(db_path)
        try:
            same_key, claimed_again = reader.idempotency_claim(
                "reconcile-1", "submit", "external.submit", "remote-object-1"
            )
            assert same_key == logical_key
            assert claimed_again is False
            assert reader.idempotency_status(logical_key)["status"] == expected_status
        finally:
            reader.close()
    finally:
        kernel.close()


@pytest.mark.parametrize("outcome", ["PARTIAL", "CONFLICT"])
def test_ambiguous_reconciliation_requires_independent_verifier(tmp_path, outcome: str) -> None:
    kernel = TaskKernel(tmp_path / f"missing-verifier-{outcome.lower()}.sqlite3")
    try:
        checkpoint_id, logical_key = _reconciling_task(kernel)
        with pytest.raises(KernelError, match="requires verifier"):
            kernel.reconcile_unknown(
                "reconcile-1",
                checkpoint_id,
                outcome,
                "evidence://read-only-provider-state",
                None,
            )

        assert kernel.get_task("reconcile-1")["state"] == "RECONCILING"
        idem = kernel.idempotency_status(logical_key)
        assert idem["status"] == "CLAIMED"
        assert idem["result_ref"] is None
    finally:
        kernel.close()


def test_lowercase_partial_is_normalized_without_becoming_retryable(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "normalized.sqlite3")
    try:
        checkpoint_id, logical_key = _reconciling_task(kernel)
        task = kernel.reconcile_unknown(
            "reconcile-1",
            checkpoint_id,
            "partial",
            "evidence://partial-normalized",
            "independent-state-verifier",
        )
        assert task["state"] == "HUMAN_REVIEW"
        assert kernel.idempotency_status(logical_key)["status"] == "RECONCILED_PARTIAL"
    finally:
        kernel.close()
