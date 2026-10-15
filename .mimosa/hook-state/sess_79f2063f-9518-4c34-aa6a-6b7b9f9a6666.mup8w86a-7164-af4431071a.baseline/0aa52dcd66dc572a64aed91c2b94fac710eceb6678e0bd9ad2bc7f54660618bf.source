# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from scp.kernel_storage import StorageIntegrityError
from scp.security.capability_epoch import CapabilityToken, parse_capability_token
from scp.task_kernel import KernelError, TaskKernel, stable_hash

logger = logging.getLogger(__name__)



class TaskKernelHandsBridge:
    """Durably wrap mutating Hands actions with the TaskKernel lifecycle.

    Read-only and dry-run actions remain on the existing executor path. A real
    mutating action gets a kernel task, lease, idempotency claim and a
    pre-dispatch checkpoint. A verified result is committed. If the action
    returns an ambiguous result or raises after dispatch started, the bridge
    records ``UNKNOWN`` with a stable local request identity; retry then
    requires explicit reconciliation.
    """

    def __init__(
        self,
        executor: Any,
        kernel: TaskKernel | None = None,
        db_path: str | Path | None = None,
        worker_id: str = "hands-route-worker",
    ) -> None:
        self.executor = executor
        if kernel is not None:
            self.kernel = kernel
            self._owns_kernel = False
        else:
            root = Path(db_path or Path(executor.data_dir) / "task_kernel.sqlite3")
            self.kernel = TaskKernel(root)
            self._owns_kernel = True
        self.worker_id = worker_id
        # Lease TTL for the mutating dispatch. Kept as an attribute so the
        # heartbeat loop below can renew on the same cadence; default matches
        # the historical hard-coded 60s.
        self.lease_ttl_seconds = 60.0
        self.data_dir = executor.data_dir
        self.registry = executor.registry

    def _audit(self, event: str, payload: dict[str, Any]) -> None:
        self.executor._audit(event, payload)

    async def rollback(
        self,
        checkpoint_id: str,
        capability_level: int = 3,
        approved: bool = False,
        capability_token: CapabilityToken | Any = None,
    ) -> dict[str, Any]:
        token = parse_capability_token(capability_token)
        return await self.executor.rollback(
            checkpoint_id,
            capability_level,
            approved,
            capability_token=token,
        )



    def close(self) -> None:

        if self._owns_kernel:

            self.kernel.close()



    @staticmethod

    def _task_id(request_key: str | None) -> str:

        if request_key:

            digest = hashlib.sha256(request_key.encode("utf-8")).hexdigest()[:32]

            return f"hands-{digest}"

        return "hands-" + secrets.token_hex(16)



    @staticmethod

    def _planned_action(action: str, params: dict[str, Any]) -> dict[str, Any]:

        # Preserve no raw command/content in the durable kernel ledger.

        return {

            "action": action,

            "params_hash": stable_hash(params),

            "resource_identity": stable_hash({"action": action, "params": params}),

        }



    @staticmethod

    def _evidence_ref(task_id: str, result: dict[str, Any]) -> str:

        digest = hashlib.sha256(

            json.dumps(result, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")

        ).hexdigest()[:24]

        return f"hands://{task_id}/result/{digest}"



    @staticmethod
    def _policy_blocked_before_dispatch(result: dict[str, Any]) -> bool:
        error = str(result.get("error", "")).lower()
        return any(
            marker in error
            for marker in (
                "unknown hands action",
                "capability token is revoked",
                "capability revoked before dispatch",
                "capabilityrequired",
                "capability required",
                "capabilityscopemismatch",
                "scope mismatch",
                "caller must provide an authorized capability token",
                "kill switch is engaged",
                "requires capability",
                "explicit approval required",
                "outside safe workspace",
                "unauthorized",
            )
        )



    @staticmethod

    def _capability_epoch(executor: Any) -> int:

        status = executor.capability_authority.status()

        return int(status.get("epoch", 0)) if isinstance(status, dict) else 0



    def _public_kernel(self, task_id: str, lease_id: str | None = None) -> dict[str, Any]:

        task = self.kernel.get_task(task_id)

        task_state = task.get("state") if isinstance(task, dict) else task["state"]

        result = {
            "taskId": task_id,
            "state": task_state,
            "taskState": task_state,
            "version": task.get("version") if isinstance(task, dict) else task["version"],
            "requiresRecovery": False,
        }

        if lease_id:

            result["leaseId"] = lease_id

        return result



    def _unknown_result(

        self,

        task_id: str,

        lease_id: str,

        action: str,

        planned_action: dict[str, Any],

        logical_key: str,

        reason: str,

        checkpoint_id: str | None = None,

    ) -> dict[str, Any]:

        provider_request_id = f"hands-local:{task_id}:{action}"

        unknown = self.kernel.record_action_dispatched(

            task_id,

            lease_id,

            action,

            planned_action,

            self._capability_epoch(self.executor),

            logical_key,

            provider_request_id,

            pre_observation_ref=f"hands://{task_id}/pre",

        )

        return {

            "success": False,

            "action": action,

            "error": reason,

            "requiresRecovery": True,

            "safeToRetry": False,

            "kernel": {

                "taskId": task_id,

                "state": "UNKNOWN",

                "checkpointId": unknown.get("checkpoint_id") or checkpoint_id,

                "providerRequestId": provider_request_id,

            },

        }



    async def _heartbeat_until_finished(
        self,
        task_id: str,
        lease_id: str,
        ttl_seconds: float,
        stop: asyncio.Event,
    ) -> None:
        """Keep the lease alive while the awaited dispatch is in flight.

        A mutating Hands action may legitimately run longer than the lease
        TTL; without a heartbeat the lease expires mid-flight and even a
        VERIFIED result can no longer be committed (fail-closed into
        UNKNOWN). The loop renews expires_at/heartbeat_at on the kernel and
        stops as soon as lease authority is gone (KernelError) or the
        dispatch finishes.
        """
        interval = max(0.2, ttl_seconds / 3.0)
        while True:
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                return
            except asyncio.TimeoutError:
                logger.debug('TaskKernelHandsBridge._heartbeat_until_finished: asyncio.TimeoutError ignored', exc_info=True)
            try:
                self.kernel.heartbeat(task_id, lease_id, extend_seconds=ttl_seconds)
            except KernelError:
                logger.debug('TaskKernelHandsBridge._heartbeat_until_finished: KernelError ignored', exc_info=True)
                return


    async def execute(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        capability_level: int = 0,
        approved: bool = False,
        dry_run: bool = False,
        request_key: str | None = None,
        capability_token: CapabilityToken | Any = None,
    ) -> dict[str, Any]:
        token = parse_capability_token(capability_token)
        params = params or {}
        if token is None:
            # [M4 FIX 2026-09-11] Fail-closed ordering: an unauthorized Hands
            # request is rejected BEFORE action resolution and BEFORE any
            # TaskKernel state mutation (task/lease/idempotency/checkpoint).
            # Mirrors the executor FA-05 contract and the PCController PEP:
            # a missing capability token is a PermissionError, never a KeyError
            # from the registry and never a kernel side effect.
            raise PermissionError(
                "CapabilityRequiredError: Hands action requires an authorized capability token (FA-05)"
            )
        definition = self.executor.registry.require(action)
        if not definition.mutates_state or dry_run:
            return await self.executor.execute(
                action, params, capability_level, approved, dry_run, capability_token=token
            )



        task_id = self._task_id(request_key)

        planned_action = self._planned_action(action, params)

        resource_identity = planned_action["resource_identity"]

        logical_key = ""

        lease_id: str | None = None

        lease_active = False

        dispatch_started = False

        try:

            created = True

            try:

                self.kernel.create_task(

                    task_id,

                    "hands-route",

                    f"execute {action}",

                    definition.risk.upper() if definition.risk.upper() in {"R0", "R1", "R2", "R3"} else "R1",

                    input_hash=stable_hash({"action": action, "params_hash": planned_action["params_hash"]}),

                )

            # [P1 FIX 2026-09-05] kernel_storage translates the backend
            # UNIQUE violation into StorageIntegrityError (RuntimeError), so
            # catching sqlite3.IntegrityError here was dead code and the
            # replayed response could never fire. Accept both the neutral
            # type and a raw backend IntegrityError for custom storage.
            except (StorageIntegrityError, sqlite3.IntegrityError):

                logger.debug('TaskKernelHandsBridge.execute: StorageIntegrityError, sqlite3.IntegrityError ignored', exc_info=True)
                created = False

                existing = self.kernel.get_task(task_id)

                if existing["state"] != "QUEUED":

                    return {

                        "success": False,

                        "action": action,

                        "error": "Stable Hands request exists and is not retryable; inspect kernel state",

                        "safeToRetry": False,

                        "replayed": True,

                        "kernel": self._public_kernel(task_id),

                    }

            if created:

                for state in ("PLANNING", "READY", "QUEUED"):

                    self.kernel.transition(task_id, state, actor="hands-kernel-bridge", reason="hands_side_effect_lifecycle")

            lease = self.kernel.claim(task_id, self.worker_id, ttl_seconds=self.lease_ttl_seconds)

            lease_id = lease.lease_id

            lease_active = True

            self.kernel.start(task_id, lease.lease_id)

            logical_key, claimed = self.kernel.idempotency_claim(

                task_id, action, f"hands.{action}", resource_identity

            )

            if not claimed:

                return {

                    "success": False,

                    "action": action,

                    "error": "Logical Hands action already claimed",

                    "safeToRetry": False,

                    "kernel": self._public_kernel(task_id, lease.lease_id),

                }

            checkpoint_id = self.kernel.checkpoint(
                task_id,
                lease.lease_id,
                action,
                "WAITING_TOOL",
                planned_action,
                token.epoch if token else self._capability_epoch(self.executor),
                logical_key,
                pre_observation_ref=f"hands://{task_id}/pre",
            )

            # From this call onward a driver may have performed a side effect;
            # any exception must therefore be treated as unknown, not retryable.
            dispatch_started = True

            # [P1 FIX 2026-09-05] Renew the lease while the driver runs so a
            # >TTL action cannot lose its lease mid-flight. Heartbeats stop
            # before the post-dispatch kernel writes, which stay synchronous.
            stop_heartbeat = asyncio.Event()

            heartbeat_task = asyncio.create_task(
                self._heartbeat_until_finished(
                    task_id, lease.lease_id, self.lease_ttl_seconds, stop_heartbeat
                )
            )

            try:
                result = await self.executor.execute(action, params, capability_level, approved, False, capability_token=token)

            finally:

                stop_heartbeat.set()

                await asyncio.gather(heartbeat_task, return_exceptions=True)

            if self._policy_blocked_before_dispatch(result):

                self.kernel.commit_failed(
                    task_id=task_id,
                    lease_id=lease.lease_id,
                    actor=self.worker_id,
                    failure_classification="FATAL",
                    indictment_ref=f"hands://{task_id}/policy_denied/{action}",
                    details={"action": action, "reason": "hands_policy_denied_before_dispatch"},
                )

                lease_active = False

                return {
                    **result,
                    "requiresRecovery": False,
                    "safeToRetry": False,
                    "kernel": self._public_kernel(task_id, lease.lease_id),
                }



            if bool(result.get("success")) and bool((result.get("verification") or {}).get("passed")):

                self.kernel.transition(task_id, "VERIFYING", actor="hands-kernel-bridge", reason="hands_result_observed")

                evidence_ref = self._evidence_ref(task_id, result)

                self.kernel.idempotency_complete(logical_key, evidence_ref)

                import time

                from scp.core.verifier_receipt import VerifierReceipt, sign_verifier_receipt

                receipt = sign_verifier_receipt(
                    VerifierReceipt(
                        task_id=task_id,
                        verifier_id="hands-kernel-result-verifier-v1",
                        verdict="VERIFIED",
                        evidence_ref=evidence_ref,
                        issued_at=time.time(),
                    )
                )

                final_task = self.kernel.commit_verification_result(
                    task_id,
                    lease.lease_id,
                    receipt,
                )

                lease_active = False

                return {

                    **result,

                    "kernel": {

                        "taskId": task_id,

                        "state": final_task["state"],

                        "version": final_task["version"],

                        "checkpointId": checkpoint_id,

                        "evidenceRef": evidence_ref,

                    },

                }



            return self._unknown_result(

                task_id,

                lease.lease_id,

                action,

                planned_action,

                logical_key,

                str(result.get("error") or "Mutating Hands result was not verified; reconcile required"),

                checkpoint_id,

            )

        except Exception as exc:

            logger.warning('TaskKernelHandsBridge.execute failed (task %s): %s', task_id, exc, exc_info=True)

            if dispatch_started and lease_id and logical_key:

                try:

                    return self._unknown_result(

                        task_id,

                        lease_id,

                        action,

                        planned_action,

                        logical_key,

                        f"Hands action response unknown after dispatch: {type(exc).__name__}",

                    )

                except Exception:

                    logger.debug('TaskKernelHandsBridge.execute: unknown-state persist failed', exc_info=True)

                    return {

                        "success": False,

                        "action": action,

                        "error": f"Hands bridge could not persist unknown state: {type(exc).__name__}",

                        "requiresRecovery": True,

                        "safeToRetry": False,

                        "kernel": self._public_kernel(task_id, lease_id),

                    }

            try:

                if lease_id and lease_active:

                    self.kernel.commit_failed(
                        task_id=task_id,
                        lease_id=lease_id,
                        actor=self.worker_id,
                        failure_classification="FATAL",
                        indictment_ref=f"hands://{task_id}/pre_dispatch_failure/{type(exc).__name__}",
                        details={"error": str(exc), "errorType": type(exc).__name__},
                    )

            except Exception:

                logger.warning('TaskKernelHandsBridge.execute: Exception not handled', exc_info=True)

            return {

                "success": False,

                "action": action,

                "error": f"Hands kernel bridge failed before dispatch: {type(exc).__name__}",

                "safeToRetry": False,

                "kernel": self._public_kernel(task_id, lease_id) if lease_id else {"taskId": task_id, "state": "FAILED"},

            }

        finally:

            if lease_id and lease_active:

                try:

                    self.kernel.release(task_id, lease_id)

                except KernelError:

                    logger.debug('TaskKernelHandsBridge.execute: KernelError ignored', exc_info=True)



    def reconcile_unknown(

        self,

        task_id: str,

        checkpoint_id: str,

        outcome: str,

        evidence_ref: str,

        verifier_id: str | None = None,

    ) -> dict[str, Any]:

        self.kernel.enter_reconciling(task_id, checkpoint_id, reason="hands_reconcile_request")

        return self.kernel.reconcile_unknown(task_id, checkpoint_id, outcome, evidence_ref, verifier_id)

