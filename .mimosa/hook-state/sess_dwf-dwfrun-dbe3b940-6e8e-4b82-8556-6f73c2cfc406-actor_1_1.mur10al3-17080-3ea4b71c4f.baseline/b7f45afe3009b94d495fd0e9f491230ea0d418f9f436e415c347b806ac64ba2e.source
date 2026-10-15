# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
from __future__ import annotations

from scp.core.capability_token import verify_token
from scp.security.capability_epoch import parse_capability_token

"""SCP Hands v3.6.1 bounded planner and plan runner.

The planner is deterministic and explicit. It accepts only registered Hands
actions, evaluates a small allowlisted condition language, retries bounded
failures, records evidence, and requires approval before risky steps.
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from typing import Any

from .hands_executor import HandsExecutor

logger = logging.getLogger(__name__)


PLAN_VERSION = "3.7"
PLAN_STATES = {"PLANNED", "RUNNING", "WAITING_APPROVAL", "VERIFIED", "FAILED", "ROLLED_BACK", "COMPLETED", "UNKNOWN", "HUMAN_REVIEW"}
STEP_STATES = {"PLANNED", "RUNNING", "WAITING_APPROVAL", "VERIFIED", "FAILED", "ROLLED_BACK", "UNKNOWN", "HUMAN_REVIEW"}
RECOVERY_DECISIONS = {"NOT_APPLIED", "APPLIED", "PARTIAL", "CONFLICT", "UNKNOWN"}
PRECONDITION_TYPES = {"always", "previous_steps_verified", "plan_state", "step_state"}
POSTCONDITION_TYPES = {"verification_passed", "success", "text_contains", "url_prefix", "evidence_field_equals", "field_equals"}
RETRY_TYPES = {"verification_failed", "execution_error", "always"}


class HandsPlanner:
    """Persisted, sequential Planner for the existing Hands Executor."""

    def __init__(self, executor: HandsExecutor | None = None, autonomous_governor: Any = None) -> None:
        self.executor = executor or HandsExecutor()
        self.data_dir = self.executor.data_dir
        self.plan_path = self.data_dir / "plans.jsonl"
        self.lease_dir = self.data_dir / "leases"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lease_dir.mkdir(parents=True, exist_ok=True)
        self._journal_lock = threading.Lock()
        self._active_runs: set[str] = set()
        self._run_tokens: dict[str, str] = {}
        self._event_seq = 0
        self._previous_event_hash = ""
        self._restore_journal_state()
        if autonomous_governor is None:
            from scp.security.autonomous_governor import AutonomousCapabilityGovernor
            self.autonomous_governor = AutonomousCapabilityGovernor(getattr(self.executor, "capability_authority", None))
        else:
            self.autonomous_governor = autonomous_governor

    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _bounded_text(value: Any, limit: int = 5000) -> str:
        return str(value or "")[:limit]

    def _attach_governor_grant(self, step: dict[str, Any], plan: dict[str, Any]) -> None:
        """Bind a governor decision to the exact driver target for this step."""
        if step.get("confirmationId") or step.get("confirmation_id"):
            return
        from scp.security.confirmation_store import get_confirmation_store

        params = step.setdefault("params", {})
        action = str(step.get("action", ""))
        if action == "pc.write_file":
            target = str(self.executor.controller._resolve_path(str(params.get("path", ""))))
        elif action == "pc.execute":
            target = str(params.get("command", ""))
        elif action == "pc.rollback":
            target = str(params.get("checkpoint_id") or params.get("checkpointId") or "")
        else:
            target = json.dumps(params, sort_keys=True, default=str)
        grant_id = f"{plan.get('planId', 'plan')}:{step.get('stepId', 'step')}"
        confirmation_id = get_confirmation_store().record_governor_grant(
            action=action,
            target=target,
            grant_id=grant_id,
            metadata={"plan_id": plan.get("planId"), "step_id": step.get("stepId")},
        )
        step["confirmationId"] = confirmation_id
        params["confirmation_id"] = confirmation_id

    @staticmethod
    def _constant_time_equal(left: Any, right: Any) -> bool:
        left_text = str(left or "")
        right_text = str(right or "")
        if len(left_text) != len(right_text):
            return False
        difference = 0
        for left_char, right_char in zip(left_text, right_text, strict=True):
            difference |= ord(left_char) ^ ord(right_char)
        return difference == 0

    def _lease_path(self, plan_id: str) -> Any:
        safe_id = "".join(char for char in str(plan_id) if char.isalnum() or char in {"-", "_"})[:128]
        return self.lease_dir / f"{safe_id}.json"

    def _claim_lease(self, plan_id: str, ttl_seconds: int = 120) -> str | None:
        lease_path = self._lease_path(plan_id)
        now = self._now()
        try:
            if lease_path.exists():
                try:
                    current = json.loads(lease_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    logger.debug('HandsPlanner._claim_lease: OSError, json.JSONDecodeError ignored', exc_info=True)
                    current = {}
                if float(current.get("expiresAt", 0) or 0) > now:
                    return None
                stale_path = lease_path.with_name(f"{lease_path.stem}.expired-{uuid.uuid4().hex}.json")
                try:
                    os.replace(lease_path, stale_path)
                except FileNotFoundError:
                    logger.debug('HandsPlanner._claim_lease: FileNotFoundError ignored', exc_info=True)
                    return None
            token = uuid.uuid4().hex
            payload = {"planId": plan_id, "token": token, "ownerPid": os.getpid(), "startedAt": now, "heartbeatAt": now, "expiresAt": now + ttl_seconds}
            fd = os.open(str(lease_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=True)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    lease_path.unlink(missing_ok=True)
                except OSError:
                    logger.debug('HandsPlanner._claim_lease: OSError ignored', exc_info=True)
                raise
            return token
        except FileExistsError:
            logger.debug('HandsPlanner._claim_lease: FileExistsError ignored', exc_info=True)
            return None
        except OSError:
            logger.debug('HandsPlanner._claim_lease: OSError ignored', exc_info=True)
            return None

    def _lease_is_valid(self, plan_id: str, token: str) -> bool:
        try:
            lease = json.loads(self._lease_path(plan_id).read_text(encoding="utf-8"))
            return self._constant_time_equal(lease.get("token"), token) and float(lease.get("expiresAt", 0) or 0) > self._now()
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            logger.debug('HandsPlanner._lease_is_valid: OSError, json.JSONDecodeError, TypeError, ValueError ignored', exc_info=True)
            return False

    def _renew_lease(self, plan_id: str, token: str, ttl_seconds: int = 120) -> bool:
        lease_path = self._lease_path(plan_id)
        if not self._lease_is_valid(plan_id, token):
            return False
        try:
            lease = json.loads(lease_path.read_text(encoding="utf-8"))
            now = self._now()
            lease.update({"heartbeatAt": now, "expiresAt": now + ttl_seconds})
            temporary = lease_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            temporary.write_text(json.dumps(lease, ensure_ascii=True), encoding="utf-8")
            os.replace(temporary, lease_path)
            return True
        except (OSError, json.JSONDecodeError):
            logger.debug('HandsPlanner._renew_lease: OSError, json.JSONDecodeError ignored', exc_info=True)
            return False

    def _release_lease(self, plan_id: str, token: str) -> None:
        if not self._lease_is_valid(plan_id, token):
            return
        try:
            self._lease_path(plan_id).unlink(missing_ok=True)
        except OSError:
            logger.debug('HandsPlanner._release_lease: OSError ignored', exc_info=True)

    async def _lease_heartbeat(self, plan_id: str, token: str) -> None:
        while True:
            await asyncio.sleep(10)
            if not self._renew_lease(plan_id, token):
                return

    def _restore_journal_state(self) -> None:
        """Recover the last journal sequence/hash without trusting projection state."""
        if not self.plan_path.exists():
            return
        try:
            last_line = ""
            with self.plan_path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.strip():
                        last_line = line
            if last_line:
                record = json.loads(last_line)
                self._event_seq = int(record.get("eventSeq", 0) or 0)
                self._previous_event_hash = str(record.get("eventHash", "") or "")
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            # A corrupt journal is not silently repaired here. New writes continue
            # with sequence 0 and the audit/reality gate must report the corruption.
            logger.debug('HandsPlanner._restore_journal_state: OSError, TypeError, ValueError, json.JSONDecodeError ignored', exc_info=True)
            self._event_seq = 0
            self._previous_event_hash = ""

    def _record(self, event: str, plan: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
        record = {
            "timestamp": self._now(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "eventId": uuid.uuid4().hex,
            "planId": plan.get("planId"),
            "state": plan.get("state"),
            "goal": self._bounded_text(plan.get("goal"), 500),
            "stepCount": len(plan.get("steps", [])),
        }
        if extra:
            record.update(extra)
        with self._journal_lock:
            self._event_seq += 1
            record["eventSeq"] = self._event_seq
            record["previousEventHash"] = self._previous_event_hash
            canonical = json.dumps({"plan": plan, **record}, ensure_ascii=False, sort_keys=True, default=str)
            record["eventHash"] = hashlib.sha256(canonical.encode("utf-8", "replace")).hexdigest()
            journal_record = {"plan": plan, **record}
            with self.plan_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(journal_record, ensure_ascii=False, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._previous_event_hash = record["eventHash"]
        self.executor._audit(event, {key: value for key, value in record.items() if key != "event"})

    def _load_latest(self) -> dict[str, dict[str, Any]]:
        plans: dict[str, dict[str, Any]] = {}
        if not self.plan_path.exists():
            return plans
        for line in self.plan_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.debug('HandsPlanner._load_latest: json.JSONDecodeError ignored', exc_info=True)
                continue
            plan = record.get("plan")
            if isinstance(plan, dict) and plan.get("planId"):
                plans[str(plan["planId"])] = plan
        return plans

    def _save(self, plan: dict[str, Any], event: str, extra: dict[str, Any] | None = None) -> None:
        plan["updatedAt"] = self._now()
        self._record(event, plan, extra)

    def _get(self, plan_id: str) -> dict[str, Any] | None:
        return self._load_latest().get(plan_id)

    def _public_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(plan, ensure_ascii=False, default=str))

    @staticmethod
    def _validate_condition(raw: Any, label: str, allowed_types: set[str]) -> dict[str, Any]:
        if raw in (None, {}):
            return {"type": "always"}
        if not isinstance(raw, dict):
            raise ValueError(f"{label} must be an object")
        condition = dict(raw)
        condition_type = str(condition.get("type", "always")).strip()
        if condition_type not in allowed_types:
            raise ValueError(f"{label} has unsupported type: {condition_type}")
        if condition_type == "previous_steps_verified":
            step_ids = condition.get("stepIds", [])
            if not isinstance(step_ids, list) or not step_ids or any(not str(item).strip() for item in step_ids):
                raise ValueError(f"{label} requires a non-empty stepIds list")
            condition["stepIds"] = [str(item).strip() for item in step_ids]
        elif condition_type in {"plan_state", "step_state"}:
            if not str(condition.get("equals", "")).strip():
                raise ValueError(f"{label} requires equals")
            if condition_type == "step_state" and not str(condition.get("stepId", "")).strip():
                raise ValueError(f"{label} requires stepId")
        elif condition_type in {"text_contains", "url_prefix", "field_equals", "evidence_field_equals"}:
            if not str(condition.get("value", "")).strip() and condition_type != "field_equals":
                raise ValueError(f"{label} requires value")
            if condition_type in {"field_equals", "evidence_field_equals"} and not str(condition.get("path", "")).strip():
                raise ValueError(f"{label} requires path")
        return condition

    @staticmethod
    def _validate_retry(raw: Any, label: str) -> dict[str, Any]:
        if raw in (None, {}):
            return {"maxAttempts": 1, "backoffSeconds": 0.0, "on": "verification_failed"}
        if not isinstance(raw, dict):
            raise ValueError(f"{label} must be an object")
        try:
            max_attempts = max(1, min(int(raw.get("maxAttempts", 1)), 3))
            backoff = max(0.0, min(float(raw.get("backoffSeconds", 0)), 5.0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} has invalid numeric values") from exc
        retry_on = str(raw.get("on", raw.get("retryOn", "verification_failed"))).strip()
        if retry_on not in RETRY_TYPES:
            raise ValueError(f"{label} has unsupported on value: {retry_on}")
        return {"maxAttempts": max_attempts, "backoffSeconds": backoff, "on": retry_on}

    def _validate_step(self, raw: dict[str, Any], index: int, known_ids: set[str]) -> dict[str, Any]:
        action = str(raw.get("action", "")).strip()
        if len(action) < 3:
            raise ValueError(f"Step {index + 1} requires an action")
        definition = self.executor.registry.get(action)
        if definition is None:
            raise ValueError(f"Unknown Hands action: {action}")
        step_id = str(raw.get("stepId") or f"step-{index + 1:02d}").strip()
        if step_id in known_ids:
            raise ValueError(f"Duplicate stepId: {step_id}")
        depends_on = [str(item) for item in raw.get("dependsOn", [])]
        if any(item not in known_ids for item in depends_on):
            raise ValueError(f"Step {step_id} has a forward or unknown dependency")
        if step_id in depends_on:
            raise ValueError(f"Step {step_id} cannot depend on itself")
        params = raw.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"Step {step_id} params must be an object")
        precondition = self._validate_condition(raw.get("precondition"), f"Step {step_id} precondition", PRECONDITION_TYPES)
        postcondition = self._validate_condition(raw.get("postcondition"), f"Step {step_id} postcondition", POSTCONDITION_TYPES)
        for dependency_id in precondition.get("stepIds", []):
            if dependency_id not in known_ids:
                raise ValueError(f"Step {step_id} precondition references unknown step: {dependency_id}")
        if precondition.get("type") == "step_state" and precondition.get("stepId") not in known_ids:
            raise ValueError(f"Step {step_id} precondition references unknown step: {precondition.get('stepId')}")
        retry_policy = self._validate_retry(raw.get("retryPolicy"), f"Step {step_id} retryPolicy")
        raw_capability = max(0, min(int(raw.get("capabilityLevel", definition.capability_level)), 5))
        raw_token = raw.get("capabilityToken") if raw.get("capabilityToken") is not None else raw.get("capability_token")
        if raw_token is not None:
            parsed_token = parse_capability_token(raw_token)
            step_token: Any = parsed_token.to_dict() if parsed_token is not None else raw_token
        else:
            step_token = None
        return {
            "stepId": step_id,
            "action": action,
            "params": params,
            "capabilityLevel": raw_capability,
            "capabilityToken": step_token,
            "approved": bool(raw.get("approved", False)),
            "dryRun": bool(raw.get("dryRun", False)),
            "dependsOn": depends_on,
            "precondition": precondition,
            "postcondition": postcondition,
            "retryPolicy": retry_policy,
            "state": "PLANNED",
            "attempts": 0,
            "evidence": {},
            "error": "",
        }

    def create_plan(self, goal: str, steps: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        goal = self._bounded_text(goal, 1000).strip()
        if not goal:
            raise ValueError("Plan goal is required")
        if not isinstance(steps, list) or not steps or len(steps) > 20:
            raise ValueError("Plan must contain between 1 and 20 steps")
        normalized: list[dict[str, Any]] = []
        known_ids: set[str] = set()
        for index, raw in enumerate(steps):
            if not isinstance(raw, dict):
                raise ValueError(f"Step {index + 1} must be an object")
            step = self._validate_step(raw, index, known_ids)
            normalized.append(step)
            known_ids.add(step["stepId"])
        plan = {
            "planId": uuid.uuid4().hex,
            "version": PLAN_VERSION,
            "goal": goal,
            "state": "PLANNED",
            "createdAt": self._now(),
            "updatedAt": self._now(),
            "currentStepId": None,
            "completedStepCount": 0,
            "metadata": metadata if isinstance(metadata, dict) else {},
            "steps": normalized,
        }
        self._save(plan, "PLAN_CREATED")
        return self._public_plan(plan)

    def list_plans(self, limit: int = 20) -> list[dict[str, Any]]:
        plans = sorted(self._load_latest().values(), key=lambda item: float(item.get("updatedAt", 0)), reverse=True)
        return [self._public_plan(item) for item in plans[: max(1, min(limit, 100))]]

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._get(plan_id)
        return self._public_plan(plan) if plan else None

    def _summary(self, plan: dict[str, Any]) -> dict[str, Any]:
        steps = plan.get("steps", [])
        return {
            "planId": plan.get("planId"),
            "goal": plan.get("goal", ""),
            "state": plan.get("state", "PLANNED"),
            "currentStepId": plan.get("currentStepId"),
            "stepCount": len(steps),
            "completedStepCount": sum(1 for step in steps if step.get("state") == "VERIFIED"),
            "failedStepCount": sum(1 for step in steps if step.get("state") == "FAILED"),
            "waitingApprovalCount": sum(1 for step in steps if step.get("state") == "WAITING_APPROVAL"),
            "updatedAt": plan.get("updatedAt"),
        }

    @staticmethod
    def _read_path(source: Any, path: str) -> Any:
        current = source
        for part in [item for item in path.split(".") if item][:5]:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _evaluate_condition(self, condition: dict[str, Any], plan: dict[str, Any], result: dict[str, Any] | None = None) -> tuple[bool, str]:
        condition_type = str(condition.get("type", "always"))
        if condition_type == "always":
            return True, "always"
        if condition_type == "previous_steps_verified":
            states = {str(step.get("stepId")): step.get("state") for step in plan.get("steps", [])}
            missing = [step_id for step_id in condition.get("stepIds", []) if states.get(step_id) != "VERIFIED"]
            return (not missing, "all previous steps verified" if not missing else f"steps not verified: {', '.join(missing)}")
        if condition_type == "plan_state":
            expected = str(condition.get("equals"))
            return (plan.get("state") == expected, f"plan state is {plan.get('state')}, expected {expected}")
        if condition_type == "step_state":
            step_id = str(condition.get("stepId"))
            step = next((item for item in plan.get("steps", []) if str(item.get("stepId")) == step_id), None)
            expected = str(condition.get("equals"))
            actual = step.get("state") if step else None
            return (actual == expected, f"step {step_id} state is {actual}, expected {expected}")
        if result is None:
            return False, "postcondition needs an execution result"
        if condition_type == "verification_passed":
            actual = bool((result.get("verification") or {}).get("passed"))
            return actual, f"verification.passed={actual}"
        if condition_type == "success":
            actual = bool(result.get("success"))
            return actual, f"success={actual}"
        if condition_type == "text_contains":
            expected = str(condition.get("value", ""))
            text = str(result.get("text", ""))
            return expected in text, f"text contains expected={expected!r}"
        if condition_type == "url_prefix":
            expected = str(condition.get("value", ""))
            actual = str(result.get("url", ""))
            return actual.startswith(expected), f"url={actual!r}, prefix={expected!r}"
        if condition_type in {"field_equals", "evidence_field_equals"}:
            source = result.get("evidence", {}) if condition_type == "evidence_field_equals" else result
            actual = self._read_path(source, str(condition.get("path", "")))
            expected = condition.get("value")
            return actual == expected, f"{condition_type} {condition.get('path')}={actual!r}, expected={expected!r}"
        return False, f"unsupported condition type: {condition_type}"

    async def run_plan(self, plan_id: str, capability_level: int = 0, approved: bool = False, dry_run: bool = False, stop_on_failure: bool = True, capability_token: Any = "") -> dict[str, Any]:
        with self._journal_lock:
            if plan_id in self._active_runs:
                return {"success": False, "planId": plan_id, "error": "Plan run already active", "safeToRetry": False}
            lease_token = self._claim_lease(plan_id)
            if not lease_token:
                return {"success": False, "planId": plan_id, "error": "Plan lease is held by another worker", "safeToRetry": False, "errorCode": "LEASE_HELD"}
            self._active_runs.add(plan_id)
            self._run_tokens[plan_id] = lease_token
        heartbeat = asyncio.create_task(self._lease_heartbeat(plan_id, lease_token))
        try:
            return await self._run_plan_locked(plan_id, capability_level, approved, dry_run, stop_on_failure, capability_token)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            with self._journal_lock:
                self._active_runs.discard(plan_id)
                self._run_tokens.pop(plan_id, None)
                self._release_lease(plan_id, lease_token)

    def _run_lease_valid(self, plan_id: str) -> bool:
        token = self._run_tokens.get(plan_id)
        return bool(token and self._lease_is_valid(plan_id, token))

    async def _run_plan_locked(self, plan_id: str, capability_level: int = 0, approved: bool = False, dry_run: bool = False, stop_on_failure: bool = True, capability_token: Any = "") -> dict[str, Any]:
        plan = self._get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found", "planId": plan_id}
        if plan.get("state") in {"COMPLETED", "ROLLED_BACK"}:
            return {"success": False, "error": f"Plan is already {plan.get('state')}", "plan": self._public_plan(plan)}
        if plan.get("state") in {"UNKNOWN", "HUMAN_REVIEW"}:
            return {"success": False, "error": "Plan requires recovery decision before another side effect", "requiresRecovery": True, "safeToRetry": False, "plan": self._public_plan(plan)}
        if plan.get("state") == "RUNNING":
            plan["state"] = "HUMAN_REVIEW"
            self._save(plan, "PLAN_STALE_RUN_DETECTED", {"safeToRetry": False})
            return {"success": False, "error": "A previous run may have stopped mid-side-effect; reconciliation is required", "requiresRecovery": True, "safeToRetry": False, "plan": self._public_plan(plan)}
        plan["state"] = "RUNNING"
        self._save(plan, "PLAN_STARTED")
        last_result: dict[str, Any] = {}
        had_failure = False
        for step in plan.get("steps", []):
            if step.get("state") == "VERIFIED":
                continue
            plan["currentStepId"] = step["stepId"]
            precondition_ok, precondition_message = self._evaluate_condition(step.get("precondition", {"type": "always"}), plan)
            if not precondition_ok:
                step["state"] = "FAILED"
                step["error"] = f"Precondition failed: {precondition_message}"
                step["evidence"] = {"preconditionPassed": False, "preconditionMessage": precondition_message}
                plan["state"] = "FAILED"
                self._save(plan, "PLAN_STEP_PRECONDITION_FAILED", {"stepId": step["stepId"], "action": step["action"], "error": step["error"]})
                if stop_on_failure:
                    return {"success": False, "plan": self._public_plan(plan), "stepId": step["stepId"], "error": step["error"]}
                had_failure = True
                continue
            definition = self.executor.registry.require(step["action"])

            import os
            autonomous_mode = str(os.environ.get("SCP_AUTONOMOUS_MODE", "")).lower() in ("1", "true", "yes")
            if autonomous_mode and getattr(self, "autonomous_governor", None):
                granted, auth_token, reason = self.autonomous_governor.evaluate_and_grant_step(
                    step, plan, str(self.executor.data_dir.resolve())
                )
                if granted and auth_token:
                    step["capabilityToken"] = auth_token.to_dict()
                    step["_governor_granted"] = True
                    self._attach_governor_grant(step, plan)
                    self._save(plan, "PLAN_STEP_AUTONOMOUS_GRANT", {"stepId": step["stepId"], "reason": reason})
                else:
                    self._save(plan, "PLAN_STEP_AUTONOMOUS_DENY", {"stepId": step["stepId"], "reason": reason})

            step_token = (
                step.get("capabilityToken")
                or step.get("capability_token")
                or (capability_token.get(step["stepId"]) if isinstance(capability_token, dict) else None)
                or (capability_token.get(step["action"]) if isinstance(capability_token, dict) else None)
                or capability_token
            )
            parsed_step_token = parse_capability_token(step_token)

            token_is_valid = (
                parsed_step_token is not None
                or (isinstance(step_token, str) and "." in step_token and verify_token(step_token).get("valid", False))
            )
            requested_capability = max(int(capability_level), int(step.get("capabilityLevel", 0))) if token_is_valid else min(int(capability_level), int(step.get("capabilityLevel", 0)))

            # Elimination of approval self-attestation:
            # Approval must come from caller, governor grant, or HumanConfirmationStore.
            from scp.security.confirmation_store import get_confirmation_store
            conf_store = get_confirmation_store()
            # [F7-PLANNER fix] sequential per-step gate is the execution
            # point for this step: consume here (one cid = one step run).
            has_human_confirmation = conf_store.is_confirmed(
                action=step.get("action", ""),
                target=json.dumps(step.get("params", {}), sort_keys=True, default=str),
                confirmation_id=step.get("confirmationId") or step.get("confirmation_id"),
                consume=True,
            )
            governor_granted = bool(autonomous_mode and step.get("_governor_granted"))
            request_approved = bool(approved or has_human_confirmation or governor_granted)
            if requested_capability < definition.capability_level or (definition.requires_approval and not request_approved):
                if autonomous_mode:
                    step["state"] = "FAILED"
                    step["error"] = "Autonomous governor denied step execution: Capability or approval lacking"
                    plan["state"] = "FAILED"
                    self._save(plan, "PLAN_STEP_FAILED", {"stepId": step["stepId"], "action": step["action"], "error": step["error"]})
                    if stop_on_failure:
                        return {"success": False, "plan": self._public_plan(plan), "stepId": step["stepId"], "error": step["error"]}
                    had_failure = True
                    continue
                else:
                    step["state"] = "WAITING_APPROVAL"
                    step["error"] = "Explicit approval or higher capability is required"
                    plan["state"] = "WAITING_APPROVAL"
                    self._save(plan, "PLAN_STEP_WAITING_APPROVAL", {"stepId": step["stepId"], "action": step["action"]})
                    return {"success": False, "waitingApproval": True, "plan": self._public_plan(plan), "stepId": step["stepId"], "error": step["error"]}
            retry_policy = step.get("retryPolicy", {"maxAttempts": 1, "backoffSeconds": 0.0, "on": "verification_failed"})
            max_attempts = max(1, min(int(retry_policy.get("maxAttempts", 1)), 3))
            retry_on = str(retry_policy.get("on", "verification_failed"))
            while int(step.get("attempts", 0)) < max_attempts:
                if not self._run_lease_valid(plan_id):
                    step["state"] = "UNKNOWN"
                    step["error"] = "Lease lost before tool execution"
                    plan["state"] = "UNKNOWN"
                    self._save(plan, "PLAN_LEASE_LOST", {"stepId": step["stepId"], "safeToRetry": False})
                    return {"success": False, "requiresRecovery": True, "safeToRetry": False, "errorCode": "STALE_LEASE", "plan": self._public_plan(plan), "stepId": step["stepId"]}
                step["state"] = "RUNNING"
                step["attempts"] = int(step.get("attempts", 0)) + 1
                self._save(plan, "PLAN_STEP_STARTED", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"], "maxAttempts": max_attempts})
                try:
                    last_result = await self.executor.execute(
                        step["action"],
                        step.get("params", {}),
                        requested_capability,
                        request_approved,
                        dry_run or bool(step.get("dryRun", False)),
                        capability_token=parsed_step_token,
                    )
                except Exception as exc:
                    logger.warning("Planner step execution failed (plan %s): %s", plan_id, exc, exc_info=True)
                    last_result = {"success": False, "error": f"Planner executor error: {exc}", "verification": {"passed": False}}
                if not self._run_lease_valid(plan_id):
                    step["state"] = "UNKNOWN"
                    step["error"] = "Lease lost after tool execution; result requires reconciliation"
                    plan["state"] = "UNKNOWN"
                    self._save(plan, "PLAN_LEASE_LOST_AFTER_TOOL", {"stepId": step["stepId"], "safeToRetry": False})
                    return {"success": False, "requiresRecovery": True, "safeToRetry": False, "errorCode": "STALE_LEASE", "plan": self._public_plan(plan), "stepId": step["stepId"], "result": last_result}
                verification = last_result.get("verification") if isinstance(last_result.get("verification"), dict) else {}
                verification_passed = bool(verification.get("passed"))
                postcondition_ok, postcondition_message = self._evaluate_condition(step.get("postcondition", {"type": "verification_passed"}), plan, last_result)
                passed = bool(last_result.get("success")) and verification_passed and postcondition_ok
                step["evidence"] = {
                    "success": bool(last_result.get("success")),
                    "verificationPassed": verification_passed,
                    "postconditionPassed": postcondition_ok,
                    "postconditionMessage": postcondition_message,
                    "verificationRule": self._bounded_text(verification.get("rule"), 200),
                    "evidence": last_result.get("evidence", {}),
                    "url": self._bounded_text(last_result.get("url"), 500),
                    "path": self._bounded_text(last_result.get("path"), 500),
                    "durationMs": last_result.get("durationMs"),
                }
                step["checkpointId"] = last_result.get("checkpointId")
                step["error"] = self._bounded_text(last_result.get("error"), 1000)
                if passed:
                    step["state"] = "VERIFIED"
                    step["error"] = ""
                    self._save(plan, "PLAN_STEP_VERIFIED", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"]})
                    break
                failure_kind = "execution_error" if step["error"] else "verification_failed"
                definition_mutates = bool(definition.mutates_state)
                if definition_mutates:
                    step["state"] = "HUMAN_REVIEW"
                    step["recovery"] = {
                        "decision": "RECONCILE",
                        "reason": "MUTATING_ACTION_RESULT_NOT_VERIFIED",
                        "safeToRetry": False,
                        "requiredEvidence": ["postcondition", "provider_or_driver_state"],
                        "failureKind": failure_kind,
                    }
                    step["error"] = "Mutating action was not verified; automatic retry is blocked"
                    plan["state"] = "HUMAN_REVIEW"
                    self._save(plan, "PLAN_STEP_RECONCILE_REQUIRED", {"stepId": step["stepId"], "action": step["action"], "safeToRetry": False, "failureKind": failure_kind})
                    return {"success": False, "requiresRecovery": True, "safeToRetry": False, "plan": self._public_plan(plan), "stepId": step["stepId"], "result": last_result}
                can_retry = int(step.get("attempts", 0)) < max_attempts and retry_on in {failure_kind, "always"}
                if can_retry:
                    step["state"] = "RUNNING"
                    self._save(plan, "PLAN_STEP_RETRY", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"], "nextAttempt": int(step["attempts"]) + 1, "reason": failure_kind})
                    backoff = max(0.0, min(float(retry_policy.get("backoffSeconds", 0)), 5.0))
                    if backoff:
                        await asyncio.sleep(backoff)
                    continue
                step["state"] = "FAILED"
                plan["state"] = "FAILED"
                had_failure = True
                self._save(plan, "PLAN_STEP_FAILED", {"stepId": step["stepId"], "action": step["action"], "error": step["error"], "attempts": step["attempts"]})
                break
            if step.get("state") == "FAILED" and stop_on_failure:
                return {"success": False, "plan": self._public_plan(plan), "stepId": step["stepId"], "result": last_result}
        if had_failure:
            plan["state"] = "FAILED"
            self._save(plan, "PLAN_FAILED")
            return {"success": False, "plan": self._public_plan(plan), "result": last_result}
        plan["state"] = "COMPLETED"
        plan["currentStepId"] = None
        plan["completedStepCount"] = sum(1 for step in plan.get("steps", []) if step.get("state") == "VERIFIED")
        self._save(plan, "PLAN_COMPLETED")
        return {"success": True, "plan": self._public_plan(plan), "result": last_result}

    async def _run_dag_step(self, plan: dict[str, Any], step: dict[str, Any], capability_level: int, approved: bool, dry_run: bool, capability_token: Any = "") -> dict[str, Any]:
        """Execute one ready DAG node with the same evidence/approval contract."""
        definition = self.executor.registry.require(step["action"])

        import os
        autonomous_mode = str(os.environ.get("SCP_AUTONOMOUS_MODE", "")).lower() in ("1", "true", "yes")
        if autonomous_mode and getattr(self, "autonomous_governor", None):
            granted, auth_token, reason = self.autonomous_governor.evaluate_and_grant_step(
                step, plan, str(self.executor.data_dir.resolve())
            )
            if granted and auth_token:
                step["capabilityToken"] = auth_token.to_dict()
                # [AUDIT-FIX 2026-09-24] Mark the governor grant the same way
                # the sequential scheduler does. `approved` was a plan-embedded
                # self-attestation — never a valid approval source.
                step["_governor_granted"] = True
                self._attach_governor_grant(step, plan)
                self._save(plan, "PLAN_STEP_AUTONOMOUS_GRANT", {"stepId": step["stepId"], "reason": reason, "scheduler": "dag"})
            else:
                self._save(plan, "PLAN_STEP_AUTONOMOUS_DENY", {"stepId": step["stepId"], "reason": reason, "scheduler": "dag"})

        step_token = (
            step.get("capabilityToken")
            or step.get("capability_token")
            or (capability_token.get(step["stepId"]) if isinstance(capability_token, dict) else None)
            or (capability_token.get(step["action"]) if isinstance(capability_token, dict) else None)
            or capability_token
        )
        parsed_step_token = parse_capability_token(step_token)

        token_is_valid = (
            parsed_step_token is not None
            or (isinstance(step_token, str) and "." in step_token and verify_token(step_token).get("valid", False))
        )
        requested_capability = max(int(capability_level), int(step.get("capabilityLevel", 0))) if token_is_valid else min(int(capability_level), int(step.get("capabilityLevel", 0)))
        # [AUDIT-FIX 2026-09-24] Approval contract mirrors the sequential
        # scheduler: caller-supplied approved, an active HumanConfirmationStore
        # record, or a governor grant made THIS run. The plan-embedded
        # `step["approved"]` self-attestation is NEVER trusted (run_dag(
        # approved=False) with a tampered plan used to execute steps).
        from scp.security.confirmation_store import get_confirmation_store
        conf_store = get_confirmation_store()
        # [F7-PLANNER fix] the DAG step gate is the execution point: the
        # record is consumed here (single-use held; the lock-level gate
        # above only peeks).
        has_human_confirmation = conf_store.is_confirmed(
            action=step.get("action", ""),
            target=json.dumps(step.get("params", {}), sort_keys=True, default=str),
            confirmation_id=step.get("confirmationId") or step.get("confirmation_id"),
            consume=True,
        )
        governor_granted = bool(autonomous_mode and step.get("_governor_granted"))
        request_approved = bool(approved or has_human_confirmation or governor_granted)
        if requested_capability < definition.capability_level or (definition.requires_approval and not request_approved):
            if autonomous_mode:
                step["state"] = "FAILED"
                step["error"] = "Autonomous governor denied step execution: Capability or approval lacking"
                self._save(plan, "PLAN_STEP_FAILED", {"stepId": step["stepId"], "action": step["action"], "error": step["error"], "scheduler": "dag"})
                return {"success": False, "stepId": step["stepId"], "error": step["error"]}
            else:
                step["state"] = "WAITING_APPROVAL"
                step["error"] = "Explicit approval or higher capability is required"
                self._save(plan, "PLAN_STEP_WAITING_APPROVAL", {"stepId": step["stepId"], "action": step["action"], "scheduler": "dag"})
                return {"success": False, "waitingApproval": True, "stepId": step["stepId"], "error": step["error"]}
        retry_policy = step.get("retryPolicy", {"maxAttempts": 1, "backoffSeconds": 0.0, "on": "verification_failed"})
        max_attempts = max(1, min(int(retry_policy.get("maxAttempts", 1)), 3))
        retry_on = str(retry_policy.get("on", "verification_failed"))
        last_result: dict[str, Any] = {}
        while int(step.get("attempts", 0)) < max_attempts:
            if not self._run_lease_valid(str(plan.get("planId"))):
                step["state"] = "UNKNOWN"
                step["error"] = "Lease lost before tool execution"
                return {"success": False, "requiresRecovery": True, "safeToRetry": False, "errorCode": "STALE_LEASE", "stepId": step["stepId"]}
            step["state"] = "RUNNING"
            step["attempts"] = int(step.get("attempts", 0)) + 1
            self._save(plan, "PLAN_STEP_STARTED", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"], "maxAttempts": max_attempts, "scheduler": "dag"})
            try:
                last_result = await self.executor.execute(
                    step["action"],
                    step.get("params", {}),
                    requested_capability,
                    request_approved,
                    dry_run or bool(step.get("dryRun", False)),
                    capability_token=parsed_step_token,
                )
            except Exception as exc:
                logger.warning("Planner step execution failed (plan %s): %s", plan.get("planId"), exc, exc_info=True)
                last_result = {"success": False, "error": f"Planner executor error: {exc}", "verification": {"passed": False}}
            if not self._run_lease_valid(str(plan.get("planId"))):
                step["state"] = "UNKNOWN"
                step["error"] = "Lease lost after tool execution; result requires reconciliation"
                return {"success": False, "requiresRecovery": True, "safeToRetry": False, "errorCode": "STALE_LEASE", "stepId": step["stepId"], "result": last_result}
            verification = last_result.get("verification") if isinstance(last_result.get("verification"), dict) else {}
            postcondition_ok, postcondition_message = self._evaluate_condition(step.get("postcondition", {"type": "verification_passed"}), plan, last_result)
            passed = bool(last_result.get("success")) and bool(verification.get("passed")) and postcondition_ok
            step["evidence"] = {
                "success": bool(last_result.get("success")),
                "verificationPassed": bool(verification.get("passed")),
                "postconditionPassed": postcondition_ok,
                "postconditionMessage": postcondition_message,
                "verificationRule": self._bounded_text(verification.get("rule"), 200),
                "evidence": last_result.get("evidence", {}),
                "url": self._bounded_text(last_result.get("url"), 500),
                "path": self._bounded_text(last_result.get("path"), 500),
                "durationMs": last_result.get("durationMs"),
            }
            step["checkpointId"] = last_result.get("checkpointId")
            step["error"] = self._bounded_text(last_result.get("error"), 1000)
            if passed:
                step["state"] = "VERIFIED"
                step["error"] = ""
                self._save(plan, "PLAN_STEP_VERIFIED", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"], "scheduler": "dag"})
                return {"success": True, "stepId": step["stepId"], "result": last_result}
            failure_kind = "execution_error" if step["error"] else "verification_failed"
            if definition.mutates_state:
                step["state"] = "HUMAN_REVIEW"
                step["recovery"] = {
                    "decision": "RECONCILE",
                    "reason": "MUTATING_ACTION_RESULT_NOT_VERIFIED",
                    "safeToRetry": False,
                    "requiredEvidence": ["postcondition", "provider_or_driver_state"],
                    "failureKind": failure_kind,
                }
                step["error"] = "Mutating action was not verified; automatic retry is blocked"
                self._save(plan, "PLAN_STEP_RECONCILE_REQUIRED", {"stepId": step["stepId"], "action": step["action"], "scheduler": "dag", "safeToRetry": False, "failureKind": failure_kind})
                return {"success": False, "requiresRecovery": True, "safeToRetry": False, "stepId": step["stepId"], "result": last_result}
            can_retry = int(step.get("attempts", 0)) < max_attempts and retry_on in {failure_kind, "always"}
            if can_retry:
                self._save(plan, "PLAN_STEP_RETRY", {"stepId": step["stepId"], "action": step["action"], "attempt": step["attempts"], "nextAttempt": int(step["attempts"]) + 1, "reason": failure_kind, "scheduler": "dag"})
                backoff = max(0.0, min(float(retry_policy.get("backoffSeconds", 0)), 5.0))
                if backoff:
                    await asyncio.sleep(backoff)
                continue
            step["state"] = "FAILED"
            self._save(plan, "PLAN_STEP_FAILED", {"stepId": step["stepId"], "action": step["action"], "error": step["error"], "attempts": step["attempts"], "scheduler": "dag"})
            return {"success": False, "stepId": step["stepId"], "result": last_result, "error": step["error"]}
        return {"success": False, "stepId": step["stepId"], "error": "Retry budget exhausted"}

    async def run_dag(self, plan_id: str, capability_level: int = 0, approved: bool = False, dry_run: bool = False, max_parallel: int = 2, stop_on_failure: bool = True, capability_token: Any = "") -> dict[str, Any]:
        with self._journal_lock:
            if plan_id in self._active_runs:
                return {"success": False, "planId": plan_id, "error": "Plan run already active", "safeToRetry": False}
            lease_token = self._claim_lease(plan_id)
            if not lease_token:
                return {"success": False, "planId": plan_id, "error": "Plan lease is held by another worker", "safeToRetry": False, "errorCode": "LEASE_HELD"}
            self._active_runs.add(plan_id)
            self._run_tokens[plan_id] = lease_token
        heartbeat = asyncio.create_task(self._lease_heartbeat(plan_id, lease_token))
        try:
            return await self._run_dag_locked(plan_id, capability_level, approved, dry_run, max_parallel, stop_on_failure, capability_token)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            with self._journal_lock:
                self._active_runs.discard(plan_id)
                self._run_tokens.pop(plan_id, None)
                self._release_lease(plan_id, lease_token)

    async def _run_dag_locked(self, plan_id: str, capability_level: int = 0, approved: bool = False, dry_run: bool = False, max_parallel: int = 2, stop_on_failure: bool = True, capability_token: Any = "") -> dict[str, Any]:
        """Run topologically ready steps concurrently with bounded parallelism."""
        plan = self._get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found", "planId": plan_id}
        if plan.get("state") in {"COMPLETED", "ROLLED_BACK"}:
            return {"success": False, "error": f"Plan is already {plan.get('state')}", "plan": self._public_plan(plan)}
        if plan.get("state") in {"UNKNOWN", "HUMAN_REVIEW"}:
            return {"success": False, "error": "Plan requires recovery decision before another side effect", "requiresRecovery": True, "safeToRetry": False, "plan": self._public_plan(plan)}
        if plan.get("state") == "RUNNING":
            plan["state"] = "HUMAN_REVIEW"
            self._save(plan, "PLAN_STALE_RUN_DETECTED", {"scheduler": "dag", "safeToRetry": False})
            return {"success": False, "error": "A previous DAG run may have stopped mid-side-effect; reconciliation is required", "requiresRecovery": True, "safeToRetry": False, "plan": self._public_plan(plan)}
        max_parallel = max(1, min(int(max_parallel), 4))
        step_map = {str(step.get("stepId")): step for step in plan.get("steps", [])}
        pending = {step_id for step_id, step in step_map.items() if step.get("state") != "VERIFIED"}
        completed = {step_id for step_id, step in step_map.items() if step.get("state") == "VERIFIED"}
        plan["state"] = "RUNNING"
        plan["scheduler"] = "dag"
        plan["maxParallel"] = max_parallel
        self._save(plan, "PLAN_DAG_STARTED", {"maxParallel": max_parallel})
        running: dict[str, asyncio.Task] = {}
        last_results: dict[str, Any] = {}
        while pending or running:
            ready: list[str] = []
            for step_id in sorted(pending):
                step = step_map[step_id]
                dependencies = {str(item) for item in step.get("dependsOn", [])}
                if dependencies.issubset(completed):
                    precondition_ok, precondition_message = self._evaluate_condition(step.get("precondition", {"type": "always"}), plan)
                    if not precondition_ok:
                        step["state"] = "FAILED"
                        step["error"] = f"Precondition failed: {precondition_message}"
                        step["evidence"] = {"preconditionPassed": False, "preconditionMessage": precondition_message}
                        self._save(plan, "PLAN_STEP_PRECONDITION_FAILED", {"stepId": step_id, "action": step["action"], "scheduler": "dag"})
                        if stop_on_failure:
                            plan["state"] = "FAILED"
                            self._save(plan, "PLAN_FAILED", {"scheduler": "dag", "reason": "precondition"})
                            return {"success": False, "plan": self._public_plan(plan), "stepId": step_id, "error": step["error"]}
                        pending.remove(step_id)
                        continue
                    definition = self.executor.registry.require(step["action"])
                    step_token = (
                        step.get("capabilityToken")
                        or step.get("capability_token")
                        or (capability_token.get(step_id) if isinstance(capability_token, dict) else None)
                        or (capability_token.get(step["action"]) if isinstance(capability_token, dict) else None)
                        or capability_token
                    )
                    parsed_step_token = parse_capability_token(step_token)
                    token_is_valid = (
                        parsed_step_token is not None
                        or (isinstance(step_token, str) and "." in step_token and verify_token(step_token).get("valid", False))
                    )
                    requested_capability = max(int(capability_level), int(step.get("capabilityLevel", 0))) if token_is_valid else min(int(capability_level), int(step.get("capabilityLevel", 0)))
                    import os
                    autonomous_mode = str(os.environ.get("SCP_AUTONOMOUS_MODE", "")).lower() in ("1", "true", "yes")
                    # [AUDIT-FIX 2026-09-24] Same approval contract as the
                    # sequential scheduler and _run_dag_step: caller-supplied
                    # approved, HumanConfirmationStore record, or a governor
                    # grant made THIS run. The plan-embedded `approved` flag is
                    # NEVER trusted here. When the autonomous governor may still
                    # grant (autonomous_mode + governor present), the step stays
                    # "ready-pending-governor" and _run_dag_step performs the
                    # real governor evaluation + final approval check.
                    from scp.security.confirmation_store import get_confirmation_store
                    conf_store = get_confirmation_store()
                    # [F7-PLANNER fix] dispatch gate peeks: the consuming check
                    # happens inside _run_dag_step at the real execution point.
                    has_human_confirmation = conf_store.is_confirmed(
                        action=step.get("action", ""),
                        target=json.dumps(step.get("params", {}), sort_keys=True, default=str),
                        confirmation_id=step.get("confirmationId") or step.get("confirmation_id"),
                        consume=False,
                    )
                    governor_granted = bool(autonomous_mode and step.get("_governor_granted"))
                    request_approved = bool(approved or has_human_confirmation or governor_granted)
                    governor_pending = bool(
                        autonomous_mode
                        and getattr(self, "autonomous_governor", None)
                        and definition.requires_approval
                        and not request_approved
                    )
                    if requested_capability < definition.capability_level or (definition.requires_approval and not request_approved and not governor_pending):
                        if autonomous_mode:
                            step["state"] = "FAILED"
                            step["error"] = "Autonomous governor denied step execution: Capability or approval lacking"
                            plan["state"] = "FAILED"
                            self._save(plan, "PLAN_STEP_FAILED", {"stepId": step_id, "action": step["action"], "error": step["error"], "scheduler": "dag"})
                            if stop_on_failure:
                                return {"success": False, "plan": self._public_plan(plan), "stepId": step_id, "error": step["error"]}
                            pending.remove(step_id)
                            continue
                        else:
                            step["state"] = "WAITING_APPROVAL"
                            step["error"] = "Explicit approval or higher capability is required"
                            plan["state"] = "WAITING_APPROVAL"
                            self._save(plan, "PLAN_STEP_WAITING_APPROVAL", {"stepId": step_id, "action": step["action"], "scheduler": "dag"})
                            return {"success": False, "waitingApproval": True, "plan": self._public_plan(plan), "stepId": step_id, "error": step["error"]}
                    ready.append(step_id)
            slots = max_parallel - len(running)
            for step_id in ready[: max(0, slots)]:
                pending.remove(step_id)
                step = step_map[step_id]
                running[step_id] = asyncio.create_task(self._run_dag_step(plan, step, capability_level, approved, dry_run, capability_token=capability_token))
            if not running:
                unresolved = sorted(pending)
                plan["state"] = "FAILED"
                self._save(plan, "PLAN_FAILED", {"scheduler": "dag", "reason": "unresolved_dependencies", "steps": unresolved})
                return {"success": False, "plan": self._public_plan(plan), "error": f"Unresolved DAG dependencies: {', '.join(unresolved)}"}
            done, _ = await asyncio.wait(list(running.values()), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                step_id = str(result.get("stepId"))
                running.pop(step_id, None)
                last_results[step_id] = result
                if result.get("success") is True:
                    completed.add(step_id)
                elif stop_on_failure:
                    for other in running.values():
                        other.cancel()
                    if running:
                        await asyncio.gather(*running.values(), return_exceptions=True)
                    plan["state"] = "HUMAN_REVIEW" if result.get("requiresRecovery") else "FAILED"
                    self._save(plan, "PLAN_RECONCILE_REQUIRED" if result.get("requiresRecovery") else "PLAN_FAILED", {"scheduler": "dag", "reason": "step_failure", "stepId": step_id, "safeToRetry": bool(result.get("safeToRetry", False))})
                    return {"success": False, "plan": self._public_plan(plan), "stepId": step_id, "result": result, "requiresRecovery": bool(result.get("requiresRecovery")), "safeToRetry": bool(result.get("safeToRetry", False))}
        plan["state"] = "COMPLETED"
        plan["currentStepId"] = None
        plan["completedStepCount"] = sum(1 for step in plan.get("steps", []) if step.get("state") == "VERIFIED")
        self._save(plan, "PLAN_DAG_COMPLETED", {"maxParallel": max_parallel, "parallelSteps": max_parallel > 1})
        return {"success": True, "plan": self._public_plan(plan), "results": last_results}

    def recover_plan(self, plan_id: str, decision: str, evidence_ref: str, approved: bool = False) -> dict[str, Any]:
        """Reconcile an interrupted/uncertain plan before any new side effect."""
        plan = self._get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found", "planId": plan_id}
        decision = str(decision or "").strip().upper()
        evidence_ref = str(evidence_ref or "").strip()[:512]
        if decision not in RECOVERY_DECISIONS:
            return {"success": False, "error": f"Unsupported recovery decision: {decision}", "allowedDecisions": sorted(RECOVERY_DECISIONS)}
        if not approved:
            return {"success": False, "error": "Recovery requires explicit approval", "safeToRetry": False}
        if plan.get("state") not in {"UNKNOWN", "HUMAN_REVIEW"}:
            return {"success": False, "error": "Plan is not waiting for recovery", "state": plan.get("state"), "safeToRetry": False}
        if not evidence_ref:
            return {"success": False, "error": "Evidence reference is required", "safeToRetry": False}
        evidence_hash = hashlib.sha256(evidence_ref.encode("utf-8", "replace")).hexdigest()
        affected = [step for step in plan.get("steps", []) if step.get("state") in {"UNKNOWN", "HUMAN_REVIEW"}]
        if not affected:
            return {"success": False, "error": "No step is waiting for recovery", "safeToRetry": False}
        recovery = {
            "decision": decision,
            "evidenceRefSha256": evidence_hash,
            "evidenceProvided": True,
            "safeToRetry": decision == "NOT_APPLIED",
            "recordedAt": self._now(),
        }
        plan["recovery"] = recovery
        for step in affected:
            step["recovery"] = recovery
            if decision == "NOT_APPLIED":
                step["state"] = "PLANNED"
                step["attempts"] = 0
                step["error"] = ""
            else:
                step["state"] = "HUMAN_REVIEW"
        if decision == "NOT_APPLIED":
            plan["state"] = "PLANNED"
            plan["currentStepId"] = None
            self._save(plan, "PLAN_RECOVERY_RESUMED", {"decision": decision, "evidenceRefSha256": evidence_hash, "safeToRetry": True})
            return {"success": True, "plan": self._public_plan(plan), "decision": decision, "safeToRetry": True}
        plan["state"] = "HUMAN_REVIEW"
        self._save(plan, "PLAN_RECOVERY_RECORDED", {"decision": decision, "evidenceRefSha256": evidence_hash, "safeToRetry": False})
        return {"success": True, "plan": self._public_plan(plan), "decision": decision, "safeToRetry": False, "requiresHumanReview": True}

    async def rollback_plan(self, plan_id: str, capability_level: int = 3, approved: bool = False, capability_token: Any = None) -> dict[str, Any]:
        plan = self._get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found", "planId": plan_id}
        checkpoints = [step.get("checkpointId") for step in reversed(plan.get("steps", [])) if step.get("checkpointId")]
        if not checkpoints:
            return {"success": False, "error": "Plan has no reversible checkpoints", "plan": self._public_plan(plan)}
        rollback_results: list[dict[str, Any]] = []
        parsed_token = parse_capability_token(capability_token)
        for checkpoint_id in checkpoints:
            result = await self.executor.rollback(str(checkpoint_id), capability_level, approved, capability_token=parsed_token)
            rollback_results.append(result)
            if not result.get("success"):
                self._save(plan, "PLAN_ROLLBACK_FAILED", {"checkpointId": checkpoint_id, "error": result.get("error", "")})
                return {"success": False, "plan": self._public_plan(plan), "rollbackResults": rollback_results}
        for step in plan.get("steps", []):
            if step.get("checkpointId"):
                step["state"] = "ROLLED_BACK"
        plan["state"] = "ROLLED_BACK"
        plan["currentStepId"] = None
        self._save(plan, "PLAN_ROLLED_BACK", {"checkpointCount": len(rollback_results)})
        return {"success": True, "plan": self._public_plan(plan), "rollbackResults": rollback_results}

    def journal_integrity(self) -> dict[str, Any]:
        checked = 0
        legacy = 0
        errors: list[str] = []
        previous_hash = ""
        expected_seq = 1
        if not self.plan_path.exists():
            return {"valid": True, "checked": 0, "legacy": 0, "errors": []}
        try:
            lines = self.plan_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return {"valid": False, "checked": 0, "legacy": 0, "errors": [str(exc)]}
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"line {line_number}: invalid JSON")
                continue
            if "eventHash" not in record or "eventSeq" not in record:
                legacy += 1
                continue
            checked += 1
            if int(record.get("eventSeq", -1)) != expected_seq:
                errors.append(f"line {line_number}: event sequence mismatch")
            if str(record.get("previousEventHash", "")) != previous_hash:
                errors.append(f"line {line_number}: previous hash mismatch")
            supplied_hash = str(record.get("eventHash", ""))
            canonical = {key: value for key, value in record.items() if key != "eventHash"}
            calculated_hash = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8", "replace")).hexdigest()
            if supplied_hash != calculated_hash:
                errors.append(f"line {line_number}: event hash mismatch")
            previous_hash = supplied_hash
            expected_seq += 1
        return {"valid": not errors and legacy == 0, "checked": checked, "legacy": legacy, "errors": errors[:20]}

    def status(self) -> dict[str, Any]:
        plans = self.list_plans(20)
        active = next((item for item in plans if item.get("state") in {"PLANNED", "RUNNING", "WAITING_APPROVAL", "UNKNOWN", "HUMAN_REVIEW"}), None)
        return {
            "version": PLAN_VERSION,
            "planner": "online",
            "planCount": len(plans),
            "journal": self.journal_integrity(),
            "activePlan": active,
            "states": {state: sum(1 for plan in plans if plan.get("state") == state) for state in sorted(PLAN_STATES)},
        }
