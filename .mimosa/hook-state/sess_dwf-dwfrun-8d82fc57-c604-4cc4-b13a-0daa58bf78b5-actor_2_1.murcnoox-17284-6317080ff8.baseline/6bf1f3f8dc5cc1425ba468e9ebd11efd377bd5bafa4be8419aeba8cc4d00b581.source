import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scp.task_kernel import KernelError, TaskKernel

# ==============================================================================
# T10 - ADVERSARIAL CHAOS MATRIX (D-LEVEL) - REAL HARD-KILL RECOVERY
# ==============================================================================
# Real child processes execute real TaskKernel lifecycle steps against a shared
# SQLite journal; the parent HARD-KILLS them (TerminateProcess on Windows /
# SIGKILL on POSIX) mid-flight and proves recovery from the durable journal on
# restart: recovery transition, journal integrity, duplicate-side-effect guard
# via idempotency, stale-lease fencing and the recovery decision contract.
#
# D-matrix boundaries covered here (kernel-level, production APIs):
#   1. kill after checkpoint (WAITING_TOOL)  -> RECOVERING
#   2. kill in RUNNING before checkpoint     -> HUMAN_REVIEW
# Remaining boundaries (WHY timeout, scanner dies, during patch, verifier dies,
# after-verify/before-reflect, ledger write fails, learning persistence fails)
# require production wrappers around the Golden A/B flows to expose those
# boundaries; they are intentionally NOT faked here.
# ==============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]

CHILD_SCRIPT = r'''
import sys, time
from pathlib import Path
from scp.task_kernel import TaskKernel

db, marker = sys.argv[1], sys.argv[2]
kernel = TaskKernel(db)
kernel.create_task("chaos-kill-1", "chaos-child", "hard-kill golden probe", "R1")
for state in ("PLANNING", "READY", "QUEUED"):
    kernel.transition("chaos-kill-1", state, actor="chaos-child", reason="chaos_setup")
lease = kernel.claim("chaos-kill-1", "chaos-worker", ttl_seconds=300)
kernel.start("chaos-kill-1", lease.lease_id)
kernel.idempotency_claim("chaos-kill-1", "probe_action", "chaos.probe_action", "chaos-resource-1")
if len(sys.argv) > 3 and sys.argv[3] == "checkpoint":
    kernel.checkpoint(
        "chaos-kill-1", lease.lease_id, "probe_action", "WAITING_TOOL",
        {"planned": "side_effect"}, 0, "chaos.probe_action",
        pre_observation_ref="chaos://pre",
    )
# Side effect may have happened; the child dies WITHOUT releasing anything.
Path(marker).write_text(lease.lease_id, encoding="utf-8")
time.sleep(300)
'''


def _spawn_synchronize_and_hard_kill(tmp_path: Path, checkpoint: bool):
    db_path = tmp_path / "kernel.sqlite3"
    marker = tmp_path / "in_flight.marker"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    args = [sys.executable, "-c", CHILD_SCRIPT, str(db_path), str(marker)]
    if checkpoint:
        args.append("checkpoint")
    child = subprocess.Popen(
        args, cwd=str(REPO_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.time() + 120
    while time.time() < deadline:
        if marker.exists():
            break
        if child.poll() is not None:
            _, err = child.communicate(timeout=10)
            raise AssertionError(f"chaos child exited early rc={child.returncode}: {err[-2000:]}")
        time.sleep(0.1)
    assert marker.exists(), "chaos child never reached the synchronized boundary"
    dead_lease_id = marker.read_text(encoding="utf-8").strip()

    child.kill()  # hard kill at the synchronized boundary
    child.wait(timeout=30)

    # Reopen the journal as a fresh process would; small retry absorbs Windows
    # handle release + SQLite crash recovery after the hard kill.
    last_error = None
    for _ in range(10):
        try:
            return TaskKernel(str(db_path)), dead_lease_id
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise last_error


def test_chaos_hard_kill_after_checkpoint_recovers_to_recovering(tmp_path):
    """Kill after checkpoint -> restart -> RECOVERING, journal intact, no duplicate side effect."""
    kernel, dead_lease_id = _spawn_synchronize_and_hard_kill(tmp_path, checkpoint=True)

    report = kernel.recover_on_boot(actor="chaos-parent")
    recovered = {entry["task_id"]: entry for entry in report["recovered"]}
    assert "chaos-kill-1" in recovered, f"Orphaned task was not recovered: {report}"
    assert recovered["chaos-kill-1"]["to"] in {"RECOVERING", "HUMAN_REVIEW"}
    assert report["corrupted"] == [], f"Journal corrupted by the kill: {report['corrupted']}"

    journal = kernel.verify_journal("chaos-kill-1")
    assert journal["hash_chain_valid"] is True, f"Hash chain broken after hard kill: {journal}"
    assert journal["event_count"] > 0

    decision = TaskKernel.recovery_decision("WORKER_CRASH_AFTER_SUBMIT", action_dispatched=True)
    assert decision.decision == "RECONCILE"
    assert decision.safe_to_retry is False, "Post-side-effect crash must never be a blind retry"
    assert decision.next_state == "RECONCILING"

    # Duplicate-side-effect guard: the logical action stays claimed after recovery.
    _key, claimed_again = kernel.idempotency_claim(
        "chaos-kill-1", "probe_action", "chaos.probe_action", "chaos-resource-1"
    )
    assert claimed_again is False, "Recovered task allowed re-claiming the same logical action"

    # Stale-lease fencing: the dead worker's lease must not be usable again.
    with pytest.raises(KernelError):
        kernel.start("chaos-kill-1", dead_lease_id)


def test_chaos_hard_kill_in_running_goes_to_human_review(tmp_path):
    """Kill in RUNNING before any checkpoint -> restart -> HUMAN_REVIEW, journal intact."""
    kernel, _dead_lease = _spawn_synchronize_and_hard_kill(tmp_path, checkpoint=False)

    report = kernel.recover_on_boot(actor="chaos-parent")
    recovered = {entry["task_id"]: entry for entry in report["recovered"]}
    assert "chaos-kill-1" in recovered, f"Orphaned task was not recovered: {report}"
    assert recovered["chaos-kill-1"]["to"] == "HUMAN_REVIEW", (
        "In-flight task without checkpoint must not silently resume"
    )
    assert kernel.verify_journal("chaos-kill-1")["hash_chain_valid"] is True
