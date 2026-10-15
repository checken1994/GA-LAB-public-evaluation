"""[Agent2-KernelKeeper regression 2026-09-29, round 2] Transition-map
authority: every tasks-state write must respect ALLOWED_TRANSITIONS.

The follow-up audit of 77d44816 found that commit_failed() and
set_task_kill() write the state column with raw UPDATEs that bypass the
transition map, producing journal edges that ALLOWED_TRANSITIONS forbids
(observed by direct probe at HEAD 0d61f32c):

    VERIFYING      -> CANCELLED         (via set_task_kill, kill during verify)
    RECOVERING     -> CANCELLED         (via set_task_kill, kill during recovery)
    VERIFYING      -> RETRY_SCHEDULED   (via commit_failed RETRYABLE)
    LEASED         -> UNKNOWN           (via commit_failed UNKNOWN-class)

rebuild_projection() replays the journal with NO map validation, so any
consumer re-deriving state from events silently inherits these out-of-law
edges: the map contract ("documented machine and code must agree",
scp-task-kernel-review skill) is violated by the kernel's own writers.
Fix: validate the edge against ALLOWED_TRANSITIONS inside the commit; on
violation, fail-closed by routing the decision through the nearest legal
edge preserving the safety intent (kill -> FAILED, uncertain -> RECOVERING)
and recording the reroute in the journal reason/payload. The old code fails
every test below (illegal edge committed, no reroute visible); the new code
commits only legal edges.
"""
from __future__ import annotations

import json

import pytest

from scp.task_kernel import TaskKernel
from scp.task_kernel_parts.definitions import ALLOWED_TRANSITIONS, InvalidTransition


def _drive(kernel: TaskKernel, task_id: str, target: str):
    kernel.create_task(task_id, "probe", "goal")
    for state in ("PLANNING", "READY", "QUEUED"):
        kernel.transition(task_id, state)
    lease = kernel.claim(task_id, "worker", ttl_seconds=60)
    if target == "LEASED":
        return lease
    kernel.start(task_id, lease.lease_id)
    if target == "RUNNING":
        return lease
    if target == "RECOVERING":
        kernel.transition(task_id, "RECOVERING", lease_id=lease.lease_id)
        return lease
    kernel.transition(task_id, "VERIFYING", lease_id=lease.lease_id)
    return lease


def _last_event(kernel: TaskKernel, task_id: str) -> dict:
    return kernel.get_events(task_id)[-1]


def _edge_is_legal(edge: tuple[str, str]) -> bool:
    return edge[1] in ALLOWED_TRANSITIONS.get(edge[0], set())


def _event_payload(event: dict) -> dict:
    return json.loads(event["payload_json"])


def test_kill_from_verifying_records_legal_edge(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "kill-verifying.sqlite3")
    try:
        _drive(kernel, "kv-1", "VERIFYING")
        task = kernel.set_task_kill("kv-1", actor="operator")
        # The kill still wins — but only through a legal edge.
        assert task["state"] in {"CANCELLED", "FAILED"}
        event = _last_event(kernel, "kv-1")
        edge = (event["from_state"], event["to_state"])
        assert _edge_is_legal(edge), f"out-of-law edge committed: {edge}"
        assert edge == ("VERIFYING", "FAILED")
        assert "kill_reroute" in event["reason"]
        assert kernel.verify_journal("kv-1")["hash_chain_valid"] is True
        assert kernel.get_task("kv-1")["active_lease_id"] is None
    finally:
        kernel.close()


def test_kill_from_recovering_records_legal_edge(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "kill-recovering.sqlite3")
    try:
        _drive(kernel, "kr-1", "RECOVERING")
        task = kernel.set_task_kill("kr-1", actor="operator")
        assert task["state"] in {"CANCELLED", "FAILED"}
        event = _last_event(kernel, "kr-1")
        edge = (event["from_state"], event["to_state"])
        assert _edge_is_legal(edge), f"out-of-law edge committed: {edge}"
        assert edge == ("RECOVERING", "FAILED")
        assert "kill_reroute" in event["reason"]
        assert kernel.verify_journal("kr-1")["hash_chain_valid"] is True
    finally:
        kernel.close()


def test_kill_from_queued_stays_cancelled(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "kill-queued.sqlite3")
    try:
        kernel.create_task("kq-1", "probe", "goal")
        for state in ("PLANNING", "READY", "QUEUED"):
            kernel.transition("kq-1", state)
        task = kernel.set_task_kill("kq-1", actor="operator")
        # QUEUED -> CANCELLED is legal: behavior must stay exactly as before.
        assert task["state"] == "CANCELLED"
        event = _last_event(kernel, "kq-1")
        assert (event["from_state"], event["to_state"]) == ("QUEUED", "CANCELLED")
        assert event["reason"] == "task_kill"
    finally:
        kernel.close()


def test_retryable_failure_from_verifying_records_legal_edge(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "retry-verifying.sqlite3")
    try:
        lease = _drive(kernel, "rv-1", "VERIFYING")
        task = kernel.commit_failed(
            "rv-1",
            lease.lease_id,
            actor="worker",
            failure_classification="RETRYABLE",
            indictment_ref="probe://rv-1",
        )
        # The retry contract (RUNNING/WAITING_TOOL/VERIFYING -> RETRY_SCHEDULED
        # on a retryable classification with budget left) is now pinned INTO
        # ALLOWED_TRANSITIONS, so the raw commit and the map agree: the edge
        # commits unchanged and no reroute is recorded. Reverting the map
        # edges (old definitions.py) fails this test via the guard reroute.
        assert task["state"] == "RETRY_SCHEDULED"
        event = _last_event(kernel, "rv-1")
        edge = (event["from_state"], event["to_state"])
        assert edge == ("VERIFYING", "RETRY_SCHEDULED")
        assert _edge_is_legal(edge), f"edge missing from map: {edge}"
        assert "transition_reroute" not in event["reason"]
        payload = _event_payload(event)
        assert payload["attempts"] == 1
        assert payload["max_attempts"] >= 2
        assert kernel.verify_journal("rv-1")["hash_chain_valid"] is True

        # Map/code agreement must hold for the whole amended retry contract.
        from scp.task_kernel_parts.definitions import ALLOWED_TRANSITIONS as AT

        for src in ("RUNNING", "WAITING_TOOL", "VERIFYING"):
            assert "RETRY_SCHEDULED" in AT[src], f"map regression: {src} lost RETRY_SCHEDULED"
    finally:
        kernel.close()


def test_uncertain_failure_from_leased_records_legal_edge(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "uncertain-leased.sqlite3")
    try:
        lease = _drive(kernel, "ul-1", "LEASED")
        task = kernel.commit_failed(
            "ul-1",
            lease.lease_id,
            actor="worker",
            failure_classification="UNKNOWN",
            indictment_ref="probe://ul-1",
        )
        # Old code: LEASED -> UNKNOWN (out of law, bypasses reconcile
        # ownership). The nearest legal edge preserving the recovery owner is
        # LEASED -> RECOVERING (matches recovery_decision('LOST_RESPONSE', ...)).
        assert task["state"] == "RECOVERING"
        event = _last_event(kernel, "ul-1")
        edge = (event["from_state"], event["to_state"])
        assert _edge_is_legal(edge), f"out-of-law edge committed: {edge}"
        assert edge == ("LEASED", "RECOVERING")
        assert "transition_reroute" in event["reason"]
        assert _event_payload(event)["planned_retry"] == "UNKNOWN"
        assert kernel.verify_journal("ul-1")["hash_chain_valid"] is True
    finally:
        kernel.close()


# ---------------------------------------------------------------------------
# [SECOND-PASS FIX 2026-09-30] Docstring-vs-reality pin for _legal_or_nearest:
# the "nearest legal edge" reroute never INVENTS an edge. VERIFYING and
# CHECKPOINTED carry no UNKNOWN/RECOVERING edge in ALLOWED_TRANSITIONS, so an
# UNKNOWN-class commit_failed from those states RAISES InvalidTransition
# (fail-closed) — nothing is committed, no out-of-law edge reaches the
# journal. Probe-verified caller census: no runtime caller sends this shape
# today, so the documented machine stays unchanged (see the
# _legal_or_nearest docstring decision note).
# ---------------------------------------------------------------------------

def test_uncertain_failure_from_verifying_fails_closed(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "uncertain-verifying.sqlite3")
    try:
        lease = _drive(kernel, "uv-1", "VERIFYING")
        with pytest.raises(InvalidTransition):
            kernel.commit_failed(
                "uv-1",
                lease.lease_id,
                actor="worker",
                failure_classification="UNKNOWN",
                indictment_ref="probe://uv-1",
            )
        # Fail-closed: nothing moved, the journal stays legal and intact.
        assert kernel.get_task("uv-1")["state"] == "VERIFYING"
        assert kernel.verify_journal("uv-1")["hash_chain_valid"] is True
    finally:
        kernel.close()


def test_uncertain_failure_from_checkpointed_fails_closed(tmp_path) -> None:
    kernel = TaskKernel(tmp_path / "uncertain-checkpointed.sqlite3")
    try:
        lease = _drive(kernel, "uc-1", "RUNNING")
        kernel.transition("uc-1", "CHECKPOINTED", lease_id=lease.lease_id)
        with pytest.raises(InvalidTransition):
            kernel.commit_failed(
                "uc-1",
                lease.lease_id,
                actor="worker",
                failure_classification="UNKNOWN",
                indictment_ref="probe://uc-1",
            )
        assert kernel.get_task("uc-1")["state"] == "CHECKPOINTED"
        assert kernel.verify_journal("uc-1")["hash_chain_valid"] is True
    finally:
        kernel.close()


def test_legal_or_nearest_docstring_documents_raising_reality() -> None:
    """Docstring honesty tripwire [SECOND-PASS 2026-09-30]: _legal_or_nearest
    must document that the reroute NEVER invents a new edge and that a target
    with no nearest legal edge RAISES InvalidTransition. The old wording
    ('reroute to the NEAREST LEGAL edge' unconditionally) implied a reroute
    always happens — contradicted by the probe-verified VERIFYING/CHECKPOINTED
    + UNKNOWN-class raising reality."""
    import inspect

    doc = inspect.getdoc(TaskKernel._legal_or_nearest)
    assert doc is not None
    assert "NEVER invents a new edge" in doc
    assert "RAISES InvalidTransition" in doc
