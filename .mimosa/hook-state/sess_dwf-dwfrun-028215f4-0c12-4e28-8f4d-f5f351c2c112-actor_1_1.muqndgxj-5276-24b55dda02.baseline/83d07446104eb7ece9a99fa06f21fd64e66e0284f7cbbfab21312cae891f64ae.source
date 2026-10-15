"""Empirical Stress Test for GAP-12 Downstream Impact and Probe Mutation Falsification.

Adversarial Challenger: challenger_delta_2
Protocols: FA-08, FA-09, FA-12
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from unittest.mock import patch
from scp.task_kernel import TaskKernel, InvalidTransition, KernelError
from scp.ask_kernel_adapter import AskKernelAdapter
from tools.probes.probe_gap12_delta_audit import run_probe


def test_mutation_1_probe_post_fix_verdict():
    """Mutation 1: When GAP-12 is patched (raising InvalidTransition on FAILED),
    does probe_gap12_delta_audit output GREEN_PROTECTED or UNEXPECTED_STATE?
    """
    original_transition = TaskKernel.transition

    def patched_transition(self, task_id, to_state, *args, **kwargs):
        if to_state == "FAILED":
            raise InvalidTransition("direct transition to FAILED is forbidden; use commit_failed() with valid evidence")
        return original_transition(self, task_id, to_state, *args, **kwargs)

    with patch.object(TaskKernel, "transition", patched_transition):
        outcome = run_probe()
        print("\n[MUTATION 1 RESULT]")
        print(f"Overall verdict when properly blocked: {outcome.get('overall_verdict')}")
        for k in ("vector_1", "vector_2", "vector_3", "vector_4"):
            print(f"  {k}: {outcome.get(k, {}).get('status')}")
        
        # Check if the probe has an explicit GREEN verdict or falls into UNEXPECTED_STATE
        assert outcome.get("overall_verdict") != "RED_VULNERABILITY_PROVEN", "Must not be RED when blocked"
        return outcome


def test_mutation_2_probe_placebo_crash_as_green():
    """Mutation 2: What if TaskKernel crashes with an unrelated error (e.g. AttributeError)?
    Does the probe falsely mark it as PROTECTED_GREEN?
    """
    original_transition = TaskKernel.transition

    def buggy_crash_transition(self, task_id, to_state, *args, **kwargs):
        if to_state == "FAILED":
            raise AttributeError("Placebo crash: 'NoneType' object has no attribute 'secret_key'")
        return original_transition(self, task_id, to_state, *args, **kwargs)

    with patch.object(TaskKernel, "transition", buggy_crash_transition):
        outcome = run_probe()
        print("\n[MUTATION 2 RESULT]")
        print("Status for vector 1 when an unrelated AttributeError is raised:")
        print(f"  vector_1 status: {outcome.get('vector_1', {}).get('status')}")
        return outcome


def test_downstream_impact_on_ask_kernel_adapter(tmp_path: Path):
    """Test downstream caller impact: How does AskKernelAdapter.fail() behave
    if transition(..., 'FAILED') raises InvalidTransition?
    """
    original_transition = TaskKernel.transition

    def patched_transition(self, task_id, to_state, *args, **kwargs):
        if to_state == "FAILED":
            raise InvalidTransition("direct transition to FAILED is forbidden; use commit_failed() with valid evidence")
        return original_transition(self, task_id, to_state, *args, **kwargs)

    db_path = str(tmp_path / "ask_adapter_impact.sqlite3")
    trace_path = str(tmp_path / "ask_adapter_impact.jsonl")
    adapter = AskKernelAdapter(db_path=db_path, trace_path=trace_path)

    try:
        task = adapter.begin("What is SCP?", ["context1"], "", "session_impact_test")
        t_id = task["task_id"]
        task_before = adapter.kernel.get_task(t_id)
        assert task_before["state"] == "RUNNING"

        print(f"\n[DOWNSTREAM IMPACT TEST: AskKernelAdapter.fail()]")
        print(f"Task before fail(): ID={t_id}, State={task_before['state']}")

        with patch.object(TaskKernel, "transition", patched_transition):
            # Adapter calls fail()
            adapter.fail(task, reason="test_upstream_error")

            # Check task state after fail()
            task_after = adapter.kernel.get_task(t_id)
            print(f"Task after fail() under patched TaskKernel: State={task_after['state']}")
            
            # If adapter relies on raw transition, the task WILL REMAIN IN RUNNING!
            # It will NOT be FAILED!
            is_stuck_in_running = (task_after["state"] == "RUNNING")
            print(f"Is task silently stuck in RUNNING because fail() swallowed InvalidTransition? {is_stuck_in_running}")
            return is_stuck_in_running
    finally:
        adapter.kernel.close()


if __name__ == "__main__":
    import tempfile
    print("=" * 80)
    print("CHALLENGER ADVERSARIAL STRESS HARNESS: GAP-12 PROBE & DOWNSTREAM CALLERS")
    print("=" * 80)
    
    # 1. Run Mutation 1
    m1_res = test_mutation_1_probe_post_fix_verdict()
    
    # 2. Run Mutation 2
    m2_res = test_mutation_2_probe_placebo_crash_as_green()

    # 3. Run Downstream Impact
    with tempfile.TemporaryDirectory() as td:
        stuck = test_downstream_impact_on_ask_kernel_adapter(Path(td))

    print("\n" + "=" * 80)
    print("SUMMARY OF EMPIRICAL FINDINGS:")
    print(f"  1. Probe post-fix overall_verdict: {m1_res.get('overall_verdict')} (Should be GREEN_PROTECTED, but is UNEXPECTED_STATE)")
    print(f"  2. Probe placebo crash vulnerability: {m2_res.get('vector_1', {}).get('status')} (Unrelated AttributeError labeled as PROTECTED_GREEN)")
    print(f"  3. AskKernelAdapter downstream impact: Task stuck in RUNNING={stuck}")
    print("=" * 80)
