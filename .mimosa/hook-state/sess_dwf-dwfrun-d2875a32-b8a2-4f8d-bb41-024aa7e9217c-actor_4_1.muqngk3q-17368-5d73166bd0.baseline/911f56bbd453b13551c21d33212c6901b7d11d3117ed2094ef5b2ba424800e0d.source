# SCP CIRCUIT: M05 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M05-closure.json)
"""Bounded SCP agent runner.

This module is deliberately small: it composes the existing GoalParser,
HandsPlanner and HandsExecutor instead of introducing a new framework. The
model may propose an allowlisted plan, but it never grants approval or runs
arbitrary tools. Execution remains deterministic and policy-gated.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scp.core.agent_autofix_adapter import AutoFixAdapter
from scp.core.request_run_ledger import RequestRunLedger
from scp.interfaces.hands import IGoalParser, IHandsExecutor, IHandsPlanner

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Compose proposal, bounded execution, evidence and approval resume."""

    VERSION = "1.0"
    APPROVAL_TTL_SECONDS = 300

    def __init__(
        self,
        executor: IHandsExecutor | None = None,
        planner: IHandsPlanner | None = None,
        goal_parser: IGoalParser | None = None,
        ledger: RequestRunLedger | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        if executor is None:
            from scp.hands.hands_executor import HandsExecutor
            executor = HandsExecutor()
        if planner is None:
            from scp.hands.planner import HandsPlanner
            planner = HandsPlanner(executor)
        if goal_parser is None:
            from scp.hands.goal_parser import GoalParser
            goal_parser = GoalParser(planner)
        self.executor = executor
        self.planner = planner
        self.goal_parser = goal_parser
        self.ledger = ledger or RequestRunLedger()
        self.autofix = AutoFixAdapter(ledger=self.ledger)
        raw_path = str(state_path or os.environ.get("SCP_AGENT_RUN_STATE_PATH", "data/agent_runs.jsonl"))
        self.state_path = Path(raw_path)
        if not self.state_path.is_absolute():
            self.state_path = Path.cwd() / self.state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash(value: Any) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8", "replace")).hexdigest()

    @staticmethod
    def _bounded(value: Any, limit: int = 500) -> str:
        return str(value or "")[:limit]

    def _append_state(self, record: dict[str, Any]) -> bool:
        safe = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "orchestrator_version": self.VERSION,
            **record,
        }
        # Do not persist raw goals, prompts, answers or tool payloads here.
        safe.pop("goal", None)
        safe.pop("prompt", None)
        safe.pop("answer", None)
        try:
            with self.state_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("agent orchestrator: state append failed for %s: %s", self.state_path, exc, exc_info=True)
            return False

    def _latest_state(self, agent_run_id: str) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        if not self.state_path.exists():
            return None
        try:
            for line in self.state_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    # Corrupt state line must be visible; skipping keeps the
                    # reader resilient but a silent skip would hide corruption.
                    logger.warning("agent orchestrator: corrupt line in state ledger %s", self.state_path, exc_info=True)
                    continue
                if item.get("agent_run_id") == agent_run_id:
                    latest = item
        except OSError as exc:
            logger.warning("agent orchestrator: state read failed for %s: %s", self.state_path, exc, exc_info=True)
            return None
        return latest

    def _plan_hash(self, plan: dict[str, Any]) -> str:
        steps = []
        for step in plan.get("steps", []):
            steps.append(
                {
                    "stepId": str(step.get("stepId", "")),
                    "action": str(step.get("action", "")),
                    "params": step.get("params", {}),
                    "capabilityLevel": int(step.get("capabilityLevel", 0)),
                }
            )
        return self._hash({"planId": plan.get("planId"), "steps": steps})

    def _approval_preview(self, plan: dict[str, Any]) -> dict[str, Any] | None:
        pending = []
        for step in plan.get("steps", []):
            if step.get("state") == "VERIFIED":
                continue
            definition = self.executor.registry.get(str(step.get("action", "")))
            if definition and definition.requires_approval:
                pending.append(
                    {
                        "stepId": step.get("stepId"),
                        "action": step.get("action"),
                        "risk": definition.risk,
                        "capabilityLevel": definition.capability_level,
                        "paramsHash": self._hash(step.get("params", {})),
                    }
                )
        if not pending:
            return None
        return {
            "approvalId": f"approval-{uuid.uuid4().hex}",
            "expiresAt": time.time() + self.APPROVAL_TTL_SECONDS,
            "planHash": self._plan_hash(plan),
            "steps": pending,
        }

    def _begin(self, goal: str, *, action: str, risk_class: str, parent_trace_id: str | None) -> Any:
        run = self.ledger.begin(
            SimpleNamespace(source="agent_orchestrator", domain="agent", message=goal),
            action=action,
            risk_class=risk_class,
            decision_source="agent_orchestrator",
        )
        if run.ledger_write_ok:
            self.ledger.stage(run, "agent_received", "RUNNING", parent_trace_id=parent_trace_id or "")
        return run

    async def propose(self, goal: str, *, parent_trace_id: str | None = None) -> dict[str, Any]:
        goal = str(goal or "").strip()
        run = self._begin(goal, action="agent_plan", risk_class="normal", parent_trace_id=parent_trace_id)
        if not run.ledger_write_ok:
            return {"success": False, "status": "DB_WRITE_FAILED", "agent_run_id": run.run_id, "trace_id": run.trace_id}
        try:
            self.ledger.stage(run, "planning", "RUNNING", parent_trace_id=parent_trace_id or "")
            parsed = await self.goal_parser.parse(goal)
            if not parsed.get("success"):
                self.ledger.finish(run, "UNKNOWN", result={"verdict": "UNKNOWN"}, planning_status="FAILED")
                return {"success": False, "status": "PLANNING_FAILED", "agent_run_id": run.run_id, "trace_id": run.trace_id, **parsed}
            plan = parsed.get("plan") if isinstance(parsed.get("plan"), dict) else {}
            plan_hash = self._plan_hash(plan)
            self._append_state(
                {
                    "agent_run_id": run.run_id,
                    "trace_id": run.trace_id,
                    "parent_trace_id": parent_trace_id,
                    "event": "PLAN_PROPOSED",
                    "status": "PLAN_READY",
                    "plan_id": plan.get("planId"),
                    "plan_hash": plan_hash,
                    "lineage": parsed.get("lineage"),
                    "step_count": len(plan.get("steps", [])),
                }
            )
            self.ledger.stage(run, "plan_ready", "RUNNING", plan_id=plan.get("planId"), plan_hash=plan_hash, step_count=len(plan.get("steps", [])))
            terminal, ledger_ok = self.ledger.finish(run, "UNKNOWN", result={"verdict": "UNKNOWN"}, plan_id=plan.get("planId"), orchestration_status="PLAN_READY")
            return {
                "success": True,
                "status": "PLAN_READY",
                "agent_run_id": run.run_id,
                "trace_id": run.trace_id,
                "parent_trace_id": parent_trace_id,
                "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED",
                "terminal_status": terminal,
                **parsed,
            }
        except Exception as exc:
            logger.debug(f"propose ignored: {exc}", exc_info=True)
            terminal, ledger_ok = self.ledger.finish(run, "INTERNAL_FAILED", error=exc, orchestration_status="PLANNING_FAILED")
            return {"success": False, "status": "INTERNAL_FAILED", "agent_run_id": run.run_id, "trace_id": run.trace_id, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal, "error": self._bounded(exc, 300)}

    async def run(
        self,
        *,
        goal: str | None = None,
        plan_id: str | None = None,
        execute: bool = False,
        capability_level: int = 0,
        approved: bool = False,
        dry_run: bool = False,
        parent_trace_id: str | None = None,
        agent_run_id: str | None = None,
    ) -> dict[str, Any]:
        if not plan_id:
            if not goal:
                return {"success": False, "status": "INVALID_REQUEST", "error": "goal or plan_id is required"}
            proposal = await self.propose(goal, parent_trace_id=parent_trace_id)
            if not proposal.get("success") or not execute:
                return proposal
            plan_id = str((proposal.get("plan") or {}).get("planId", ""))
            agent_run_id = str(proposal.get("agent_run_id", ""))
        plan = self.planner.get_plan(str(plan_id))
        if not plan:
            return {"success": False, "status": "PLAN_NOT_FOUND", "plan_id": plan_id}
        goal_text = str(plan.get("goal", ""))
        run = self._begin(goal_text, action="agent_run", risk_class="high", parent_trace_id=parent_trace_id)
        if not run.ledger_write_ok:
            return {"success": False, "status": "DB_WRITE_FAILED", "agent_run_id": run.run_id, "trace_id": run.trace_id}
        try:
            self.ledger.stage(run, "execution_start", "RUNNING", plan_id=plan_id, parent_trace_id=parent_trace_id or "")
            result = await self.planner.run_plan(str(plan_id), capability_level, approved, dry_run, True)
            current_plan = result.get("plan") if isinstance(result.get("plan"), dict) else self.planner.get_plan(str(plan_id)) or plan
            if result.get("waitingApproval"):
                approval = self._approval_preview(current_plan)
                self._append_state({"agent_run_id": agent_run_id or run.run_id, "trace_id": run.trace_id, "parent_trace_id": parent_trace_id, "event": "WAITING_APPROVAL", "status": "WAITING_APPROVAL", "plan_id": plan_id, "plan_hash": self._plan_hash(current_plan), "approval": approval})
                terminal, ledger_ok = self.ledger.finish(run, "UNKNOWN", result={"verdict": "UNKNOWN"}, plan_id=plan_id, orchestration_status="WAITING_APPROVAL")
                return {"success": False, "status": "WAITING_APPROVAL", "agent_run_id": agent_run_id or run.run_id, "trace_id": run.trace_id, "plan": current_plan, "approval": approval, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
            status = "COMPLETED" if result.get("success") else "FAILED"
            terminal_status = "SUCCESS" if result.get("success") else "INTERNAL_FAILED"
            terminal, ledger_ok = self.ledger.finish(run, terminal_status, result={"verdict": "PASS" if result.get("success") else "FAIL"}, plan_id=plan_id, orchestration_status=status)
            self._append_state({"agent_run_id": agent_run_id or run.run_id, "trace_id": run.trace_id, "parent_trace_id": parent_trace_id, "event": status, "status": status, "plan_id": plan_id, "plan_hash": self._plan_hash(current_plan), "result_success": bool(result.get("success"))})
            return {"success": bool(result.get("success")), "status": status, "agent_run_id": agent_run_id or run.run_id, "trace_id": run.trace_id, "plan": current_plan, "result": result, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal}
        except Exception as exc:
            logger.debug(f"run ignored: {exc}", exc_info=True)
            terminal, ledger_ok = self.ledger.finish(run, "INTERNAL_FAILED", error=exc, plan_id=plan_id, orchestration_status="FAILED")
            return {"success": False, "status": "INTERNAL_FAILED", "agent_run_id": agent_run_id or run.run_id, "trace_id": run.trace_id, "ledger_status": "OK" if ledger_ok else "DB_WRITE_FAILED", "terminal_status": terminal, "error": self._bounded(exc, 300)}

    async def resume(self, agent_run_id: str, approval_id: str, *, capability_level: int = 0, parent_trace_id: str | None = None) -> dict[str, Any]:
        state = self._latest_state(str(agent_run_id))
        if not state or state.get("status") != "WAITING_APPROVAL":
            return {"success": False, "status": "APPROVAL_NOT_FOUND", "agent_run_id": agent_run_id}
        approval = state.get("approval") if isinstance(state.get("approval"), dict) else {}
        if approval.get("approvalId") != approval_id:
            return {"success": False, "status": "APPROVAL_MISMATCH", "agent_run_id": agent_run_id}
        if float(approval.get("expiresAt", 0)) < time.time():
            return {"success": False, "status": "APPROVAL_EXPIRED", "agent_run_id": agent_run_id}
        plan_id = str(state.get("plan_id", ""))
        plan = self.planner.get_plan(plan_id)
        if not plan or self._plan_hash(plan) != str(approval.get("planHash", "")):
            return {"success": False, "status": "APPROVAL_PLAN_CHANGED", "agent_run_id": agent_run_id, "plan_id": plan_id}
        return await self.run(plan_id=plan_id, execute=True, capability_level=capability_level, approved=True, parent_trace_id=parent_trace_id or state.get("trace_id"), agent_run_id=agent_run_id)

    async def autofix_propose(self, payload: dict[str, Any], *, parent_trace_id: str | None = None) -> dict[str, Any]:
        return await self.autofix.propose(payload, parent_trace_id=parent_trace_id)

    async def autofix_apply(self, proposal_id: str, payload: dict[str, Any], *, parent_trace_id: str | None = None) -> dict[str, Any]:
        return await self.autofix.apply(proposal_id, payload, parent_trace_id=parent_trace_id)

    async def autofix_resume(self, proposal_id: str, permission_request_id: str, *, parent_trace_id: str | None = None) -> dict[str, Any]:
        return await self.autofix.resume(proposal_id, permission_request_id, parent_trace_id=parent_trace_id)

    def status(self, limit: int = 20) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        if self.state_path.exists():
            try:
                for line in self.state_path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, min(int(limit), 100)) :]:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Corrupt state line must be visible, not silently dropped
                        # from the reported recentRuns history.
                        logger.warning("agent orchestrator: corrupt line in state ledger %s", self.state_path, exc_info=True)
                        continue
            except OSError as exc:
                # silent-by-design: status() is a best-effort report; an unread
                # state file must not fail the whole status payload.
                logger.warning("agent orchestrator: state read failed for %s: %s", self.state_path, exc, exc_info=True)
        return {"version": self.VERSION, "orchestrator": "online", "statePath": str(self.state_path), "recentRuns": rows}


__all__ = ["AgentOrchestrator"]
