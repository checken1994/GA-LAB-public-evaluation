"""Idempotency engine for durable TaskKernel."""
from __future__ import annotations

from typing import Any

from scp.task_kernel_parts.definitions import (
    KernelError,
    NotFound,
    OptimisticLockError,
    StaleLease,
    now_iso,
    stable_hash,
)


class IdempotencyEngine:
    def __init__(self, kernel: Any) -> None:
        self.kernel = kernel

    @property
    def conn(self):
        return self.kernel.conn

    def claim(
        self,
        task_id: str,
        step_id: str,
        action_type: str,
        resource_identity: str,
        expected_version: int | None = None,
    ) -> tuple[str, bool]:
        logical_key = stable_hash(
            {
                "task_id": task_id,
                "step_id": step_id,
                "action_type": action_type,
                "resource_identity": resource_identity,
            }
        )
        lease_id = getattr(self.kernel, "_bound_leases", {}).get(task_id)
        if not lease_id:
            # Recovery/read-only duplicate check is safe without lease authority.
            # Never turn RETRYABLE into CLAIMED and never create a new row here.
            row = self.conn.execute(
                "SELECT logical_key FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            if row:
                return logical_key, False
            raise StaleLease("idempotency claim requires active lease authority")

        self.kernel._begin()
        try:
            self.kernel._assert_lease(lease_id, task_id)
            task = self.kernel._task(task_id)
            if task["active_lease_id"] != lease_id:
                raise StaleLease(f"lease {lease_id} does not match active task lease {task['active_lease_id']}")
            row = self.conn.execute(
                "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            if row:
                current_version = int(row["version"]) if "version" in row.keys() else 1
                if expected_version is not None and current_version != expected_version:
                    raise OptimisticLockError(
                        f"concurrency conflict claiming idempotency {logical_key}: expected version {expected_version}, found {current_version}",
                        table="idempotency",
                        entity_id=logical_key,
                        expected_version=expected_version,
                    )
                if row["status"] == "RETRYABLE":
                    target_version = expected_version if expected_version is not None else current_version
                    cur = self.conn.execute(
                        "UPDATE idempotency SET status='CLAIMED',result_ref=NULL,version=version+1 WHERE logical_key=? AND status='RETRYABLE' AND version=?",
                        (logical_key, target_version),
                    )
                    if cur.rowcount == 1:
                        self.kernel._commit()
                        return logical_key, True
                    if expected_version is not None:
                        raise OptimisticLockError(
                            f"concurrency conflict claiming idempotency {logical_key}",
                            table="idempotency",
                            entity_id=logical_key,
                            expected_version=target_version,
                        )
                    self.kernel._commit()
                    return logical_key, False
                self.kernel._commit()
                return logical_key, False
            self.conn.execute(
                "INSERT INTO idempotency(logical_key,task_id,step_id,action_type,resource_identity,status,created_at,version) VALUES (?,?,?,?,?,?,?,1)",
                (logical_key, task_id, step_id, action_type, resource_identity, "CLAIMED", now_iso()),
            )
            self.kernel._commit()
            return logical_key, True
        except Exception:
            self.kernel._rollback()
            raise

    def complete(
        self,
        logical_key: str,
        result_ref: str,
        expected_version: int | None = None,
    ) -> None:
        if not logical_key or not result_ref:
            raise KernelError("invalid idempotency completion")
        self.kernel._begin()
        try:
            row = self.conn.execute(
                "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
            ).fetchone()
            if not row:
                raise KernelError("idempotency key not found")
            tid = str(row["task_id"])
            lease_id = getattr(self.kernel, "_bound_leases", {}).get(tid)
            if not lease_id:
                raise StaleLease("idempotency completion requires active lease authority")
            self.kernel._assert_lease(lease_id, tid)
            task = self.kernel._task(tid)
            if task["active_lease_id"] != lease_id:
                raise StaleLease(f"lease {lease_id} does not match active task lease {task['active_lease_id']}")

            current_version = int(row["version"]) if "version" in row.keys() else 1
            if expected_version is not None and current_version != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict on idempotency {logical_key}: expected version {expected_version}, found {current_version}",
                    table="idempotency",
                    entity_id=logical_key,
                    expected_version=expected_version,
                )
            target_version = expected_version if expected_version is not None else current_version

            if row["status"] == "COMPLETED":
                if row["result_ref"] != result_ref:
                    raise KernelError("idempotency result mismatch")
                self.kernel._commit()
                return
            if row["status"] != "CLAIMED":
                raise KernelError(f"invalid idempotency status: {row['status']}")
            cur = self.conn.execute(
                "UPDATE idempotency SET status='COMPLETED',result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED' AND version=?",
                (result_ref, logical_key, target_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict completing idempotency {logical_key}",
                    table="idempotency",
                    entity_id=logical_key,
                    expected_version=target_version,
                )
            self.kernel._commit()
        except Exception:
            self.kernel._rollback()
            raise

    def status(self, logical_key: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM idempotency WHERE logical_key=?", (logical_key,)
        ).fetchone()
        if not row:
            raise NotFound(logical_key)
        return dict(row)
