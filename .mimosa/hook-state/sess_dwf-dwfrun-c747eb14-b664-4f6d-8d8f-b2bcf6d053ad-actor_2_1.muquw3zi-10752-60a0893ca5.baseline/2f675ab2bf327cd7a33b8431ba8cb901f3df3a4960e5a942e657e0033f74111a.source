from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from .task_kernel import TaskKernel
except ImportError:
    from task_kernel import TaskKernel


class RecoveryManager:
    """Classifies interruptions and moves the task to a safe kernel state."""

    def __init__(self, kernel: TaskKernel):
        self.kernel = kernel

    def classify(self, reason: str, action_dispatched: bool = False, side_effect_risk: str = "R0") -> dict[str, Any]:
        return asdict(TaskKernel.recovery_decision(reason, action_dispatched, side_effect_risk))

    def apply(self, task_id: str, reason: str, action_dispatched: bool = False, side_effect_risk: str = "R0") -> dict[str, Any]:
        decision = TaskKernel.recovery_decision(reason, action_dispatched, side_effect_risk)
        task = self.kernel.get_task(task_id)
        target = decision.next_state
        if target == "RECONCILING":
            if task["state"] == "WAITING_TOOL":
                self.kernel.transition(task_id, "UNKNOWN", actor="recovery", reason=reason, payload={"safe_to_retry": False})
                task = self.kernel.get_task(task_id)
            if task["state"] == "UNKNOWN":
                self.kernel.transition(task_id, "RECONCILING", actor="recovery", reason=decision.reason, payload={"required_evidence": decision.required_evidence})
        elif target == "QUEUED":
            if task["state"] in {"RUNNING", "WAITING_TOOL", "RECOVERING"}:
                self.kernel.transition(task_id, "RECOVERING", actor="recovery", reason=decision.reason)
                task = self.kernel.get_task(task_id)
            if task["state"] == "RECOVERING":
                self.kernel.transition(task_id, "QUEUED", actor="recovery", reason="bounded_retry")
        elif target == "FAILED":
            if task["state"] not in {"FAILED", "CANCELLED", "COMPLETED"}:
                self.kernel.transition(task_id, "FAILED", actor="recovery", reason=decision.reason)
        elif target == "HUMAN_REVIEW":
            if task["state"] in {"WAITING_TOOL", "UNKNOWN", "RECOVERING", "RECONCILING", "RUNNING"}:
                self.kernel.transition(task_id, "HUMAN_REVIEW", actor="recovery", reason=decision.reason)
        return {"task_id": task_id, "decision": asdict(decision), "task": self.kernel.get_task(task_id)}
