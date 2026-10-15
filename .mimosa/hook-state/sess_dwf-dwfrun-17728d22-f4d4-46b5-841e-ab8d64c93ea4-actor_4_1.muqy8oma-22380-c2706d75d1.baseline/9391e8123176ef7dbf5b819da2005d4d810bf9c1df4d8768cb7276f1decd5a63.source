# Auto-extracted from task_kernel.py
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from scp.kernel_storage import KernelStorage, StorageIntegrityError, make_storage

logger = logging.getLogger(__name__)

from scp.task_kernel_parts.definitions import (
    ALLOWED_TRANSITIONS,
    STATES,
    TERMINAL,
    CheckpointCorrupt,
    InvalidTransition,
    KernelError,
    KillSwitchActive,
    Lease,
    NotFound,
    OptimisticLockError,
    RecoveryDecision,
    StaleLease,
    _assert_checkpoint_safe,
    now_iso,
    stable_hash,
)
from scp.task_kernel_parts.idempotency import IdempotencyEngine


def verify_approval_authority(
    token: Any,
    task_id: str,
    secret: bytes,
    max_skew_seconds: float = 300.0,
) -> dict[str, Any]:
    """Verify an approval token or operator signature fail-closed (GAP-13).

    Returns a dict with verification metadata:
        {"token_type": str, "token_id": str, "actor": str, "scope": str, "signature": str}
    Raises InvalidTokenSignatureError, InvalidTransition, or PermissionError on any failure.
    """
    from scp.core.capability_token import InvalidTokenSignatureError
    from scp.task_kernel import InvalidTransition

    if token is None or token == "":
        raise InvalidTokenSignatureError("Approval token is missing or empty (GAP-13/FA-04)")
    if isinstance(token, str) and not token.strip():
        raise InvalidTokenSignatureError("Approval token is missing or empty (GAP-13/FA-04)")

    # Branch A: Compact string token (mint_token format "payload_b64.sig")
    if isinstance(token, str) and "." in token and not token.strip().startswith("{"):
        from scp.core.capability_token import verify_token

        res = verify_token(token.strip(), required_scope="*")
        if not res.get("valid"):
            err_msg = res.get("error", "Invalid capability token")
            if "expired" in err_msg.lower():
                raise InvalidTransition(f"Capability token has expired: {err_msg}")
            raise InvalidTokenSignatureError(f"Invalid capability token: {err_msg}")
        payload = res.get("payload", {})
        scope = payload.get("scope", "")
        if scope not in {"approval:grant", f"approval:grant:{task_id}", "*"}:
            raise InvalidTransition(
                f"Capability token scope '{scope}' does not authorize 'approval:grant' for task '{task_id}'"
            )
        now_ts = time.time()
        iat = float(payload.get("iat", 0.0))
        if iat > now_ts + 60.0:
            raise InvalidTokenSignatureError("Token issue time is in the future")
        return {
            "token_type": "compact_mint_token",
            "token_id": str(payload.get("iat", "")),
            "actor": payload.get("iss", "unknown"),
            "scope": scope,
            "signature": token.strip().split(".", 1)[1],
        }

    # Branch B: CapabilityToken instance, dict, or JSON string with epoch
    from scp.security.capability_epoch import parse_capability_token

    cap_token = parse_capability_token(token)
    if cap_token is not None:
        if not cap_token.signature or not cap_token.signature.strip():
            raise InvalidTokenSignatureError("Capability token is unsigned (GAP-08/FA-04)")
        from scp.core.capability_token import verify_token_signature

        verify_token_signature(
            secret=secret,
            subject=cap_token.subject,
            epoch=cap_token.epoch,
            token_id=cap_token.token_id,
            issued_at=cap_token.issued_at,
            signature=cap_token.signature,
        )
        if cap_token.subject not in {"approval:grant", f"approval:grant:{task_id}", "*"}:
            raise InvalidTransition(
                f"CapabilityToken subject '{cap_token.subject}' does not authorize 'approval:grant' for task '{task_id}'"
            )
        now_ts = time.time()
        if cap_token.issued_at > now_ts + 60.0:
            raise InvalidTokenSignatureError("Capability token issued_at is in the future")
        return {
            "token_type": "capability_token_epoch",
            "token_id": cap_token.token_id,
            "actor": "capability_authority",
            "scope": cap_token.subject,
            "signature": cap_token.signature,
        }

    # Branch C: Operator Signature Dictionary
    if isinstance(token, dict) and "signature" in token:
        actor = str(token.get("actor") or token.get("operator", "")).strip()
        sig = str(token.get("signature", "")).strip()
        ts_val = token.get("timestamp")
        task_in_token = token.get("task_id")
        if task_in_token and str(task_in_token).strip() != task_id:
            raise InvalidTransition(
                f"Operator signature task_id '{task_in_token}' does not match '{task_id}'"
            )
        if not actor or not sig or ts_val is None:
            raise InvalidTokenSignatureError("Malformed operator signature structure")
        try:
            timestamp = float(ts_val)
        except (TypeError, ValueError):
            raise InvalidTokenSignatureError("Invalid timestamp in operator signature")
        now_ts = time.time()
        if now_ts - timestamp > max_skew_seconds:
            raise InvalidTransition("Operator approval signature has expired")
        if timestamp > now_ts + 60.0:
            raise InvalidTokenSignatureError("Operator approval timestamp is in the future")

        canonical = f"operator_approval:{task_id}:{actor}:{timestamp:.6f}".encode()
        expected_sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise InvalidTokenSignatureError("Operator approval signature verification failed")
        return {
            "token_type": "operator_signature",
            "token_id": f"op_{actor}_{int(timestamp)}",
            "actor": actor,
            "scope": "approval:grant",
            "signature": sig,
        }

    raise InvalidTokenSignatureError("Unsupported or malformed approval token format")


__all__ = ["TaskKernel", "OptimisticLockError", "verify_approval_authority"]

class TaskKernel:
    """Small durable kernel. The journal is authoritative; tasks is a rebuildable projection.

    [CHAIN-AUDIT FIX 2026-08-29] Per-thread connections thay vì 1 shared
    connection: thực nghiệm 40-100 luồng đồng thời cho thấy shared connection
    làm SELECT đọc "nhìn thấy" snapshot cũ (row vừa commit vẫn invisible) →
    NotFound → ~8-16% task chết dưới tải. Mỗi thread có connection riêng
    (WAL sinh tồn đa connection), transaction không còn dính chéo thread.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        storage: KernelStorage | None = None,
        autonomous_mode: bool | None = None,
    ) -> None:
        """Initialise the kernel.

        Backward-compat: TaskKernel(db_path) still works.
        DI-ready: TaskKernel(storage=my_storage) injects a custom backend.
        Future: when TaskKernel is fully decoupled, the db_path arg will be removed.
        """
        if storage is not None:
            self._storage = storage
            self.db_path = getattr(storage, 'db_path', str(db_path or ''))
        else:
            if db_path is None:
                raise ValueError('Either db_path or storage= must be provided')
            self._storage = make_storage(db_path)
            self.db_path = str(db_path)
        self._bound_leases: dict[str, str] = {}
        self._system_authority: bool = False
        if autonomous_mode is not None:
            self.autonomous_mode = bool(autonomous_mode)
        else:
            self.autonomous_mode = os.environ.get("SCP_AUTONOMOUS_MODE", "").strip().lower() in {"1", "true", "yes"}
        self._schema()
        self._idempotency = IdempotencyEngine(self)

    @property
    def conn(self) -> KernelStorage:
        """Backward-compatible query facade backed by the injected storage."""
        return self._storage

    def close(self) -> None:
        if hasattr(self, "_bound_leases"):
            self._bound_leases.clear()
        self._storage.close()

    def _schema(self) -> None:
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS control (
                id INTEGER PRIMARY KEY CHECK (id=1),
                global_kill INTEGER NOT NULL DEFAULT 0,
                global_kill_epoch INTEGER NOT NULL DEFAULT 0
            );
            INSERT OR IGNORE INTO control(id) VALUES(1);
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                goal TEXT NOT NULL,
                risk_tier TEXT NOT NULL,
                deadline_ms INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                input_hash TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 5,
                state TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                active_lease_id TEXT,
                active_fencing_token INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                actor TEXT NOT NULL,
                reason TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                policy_hash TEXT,
                prev_event_hash TEXT,
                event_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(task_id, seq)
            );
            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                heartbeat_at REAL NOT NULL,
                fencing_token INTEGER NOT NULL,
                global_kill_epoch INTEGER NOT NULL,
                released INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_leases_task ON leases(task_id, fencing_token);
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                state TEXT NOT NULL,
                planned_action_hash TEXT NOT NULL,
                capability_epoch INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL,
                pre_observation_ref TEXT,
                post_observation_ref TEXT,
                tool_result_json TEXT,
                verifier_verdict TEXT,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency (
                logical_key TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                resource_identity TEXT NOT NULL,
                status TEXT NOT NULL,
                result_ref TEXT,
                created_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS queue_accounts (
                owner TEXT PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 0,
                dispatch_count INTEGER NOT NULL DEFAULT 0,
                last_dispatch_at REAL NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1
            );
            ''')
        task_columns = {row['name'] for row in self.conn.execute('PRAGMA table_info(tasks)').fetchall()}
        if 'priority' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 5')
        if 'active_lease_id' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN active_lease_id TEXT')
        if 'active_fencing_token' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN active_fencing_token INTEGER NOT NULL DEFAULT 0')
        if 'version' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
        if 'attempts' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
        if 'error' not in task_columns:
            self.conn.execute('ALTER TABLE tasks ADD COLUMN error TEXT')

        # [SEC-S4] Table names are compile-time constants of the kernel schema.
        # PRAGMA/ALTER identifiers cannot be bound as SQL parameters, so each
        # migration statement is a compile-time literal per table — the loop
        # dispatches on the constant name and executes only literal SQL text
        # (defense-in-depth against future refactors).
        for table in ('leases', 'idempotency', 'queue_accounts'):
            if table == 'leases':
                cols = {row['name'] for row in self.conn.execute('PRAGMA table_info("leases")').fetchall()}
                if 'version' not in cols:
                    self.conn.execute('ALTER TABLE "leases" ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
            elif table == 'idempotency':
                cols = {row['name'] for row in self.conn.execute('PRAGMA table_info("idempotency")').fetchall()}
                if 'version' not in cols:
                    self.conn.execute('ALTER TABLE "idempotency" ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
            elif table == 'queue_accounts':
                cols = {row['name'] for row in self.conn.execute('PRAGMA table_info("queue_accounts")').fetchall()}
                if 'version' not in cols:
                    self.conn.execute('ALTER TABLE "queue_accounts" ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
            else:
                raise KernelError('unsafe kernel table identifier')

    def _begin(self) -> None:
        """Acquire the write slot + BEGIN IMMEDIATE, với bounded retry trên
        'database is locked' (multi-connection WAL contention khi hệ thống
        đang chạy phụ trợ khác cùng lúc). Đã hết retry → raise, fail-closed."""
        self._storage.begin()

    def _commit(self) -> None:
        self._storage.commit()

    def _rollback(self) -> None:
        self._storage.rollback()

    def _control(self) -> Any:
        return self.conn.execute('SELECT * FROM control WHERE id=1').fetchone()

    def _task(self, task_id: str) -> Any:
        row = self.conn.execute('SELECT * FROM tasks WHERE task_id=?', (task_id,)).fetchone()
        if not row:
            raise NotFound(task_id)
        return row

    def _append_event(self, task_id: str, event_type: str, from_state: str | None, to_state: str | None, actor: str, reason: str, payload: dict[str, Any] | None=None, policy_hash: str | None=None, event_id: str | None=None) -> dict[str, Any]:
        event_id = event_id or 'evt_' + secrets.token_hex(12)
        payload = payload or {}
        previous = self.conn.execute('SELECT seq,event_hash FROM events WHERE task_id=? ORDER BY seq DESC LIMIT 1', (task_id,)).fetchone()
        seq = int(previous['seq'] + 1) if previous else 1
        prev_hash = previous['event_hash'] if previous else None
        body = {'event_id': event_id, 'task_id': task_id, 'seq': seq, 'type': event_type, 'from_state': from_state, 'to_state': to_state, 'actor': actor, 'reason': reason, 'payload': payload, 'policy_hash': policy_hash, 'prev_event_hash': prev_hash}
        event_hash = stable_hash(body)
        row = {'event_id': event_id, 'task_id': task_id, 'seq': seq, 'type': event_type, 'from_state': from_state, 'to_state': to_state, 'actor': actor, 'reason': reason, 'payload_json': json.dumps(payload, ensure_ascii=False, sort_keys=True), 'policy_hash': policy_hash, 'prev_event_hash': prev_hash, 'event_hash': event_hash, 'created_at': now_iso()}
        try:
            self.conn.execute('INSERT INTO events(event_id,task_id,seq,type,from_state,to_state,actor,reason,payload_json,policy_hash,prev_event_hash,event_hash,created_at) VALUES (:event_id,:task_id,:seq,:type,:from_state,:to_state,:actor,:reason,:payload_json,:policy_hash,:prev_event_hash,:event_hash,:created_at)', row)
        except StorageIntegrityError:
            existing = self.conn.execute('SELECT * FROM events WHERE event_id=?', (event_id,)).fetchone()
            if existing:
                return dict(existing)
            raise
        return row

    def create_task(self, task_id: str, owner: str, goal: str, risk_tier: str='R0', deadline_ms: int=120000, max_attempts: int=3, input_hash: str | None=None, priority: int=5) -> dict[str, Any]:
        if not task_id or not owner or (not goal) or (deadline_ms <= 0) or (max_attempts <= 0):
            raise KernelError('invalid task contract')
        if not isinstance(priority, int) or not 0 <= priority <= 100:
            raise KernelError('invalid task priority')
        if risk_tier not in {'R0', 'R1', 'R2', 'R3'}:
            raise KernelError('invalid risk tier')
        created = now_iso()
        input_hash = input_hash or stable_hash({'goal': goal})
        self._begin()
        try:
            self.conn.execute('INSERT INTO tasks(task_id,owner,goal,risk_tier,deadline_ms,max_attempts,input_hash,priority,state,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (task_id, owner, goal, risk_tier, deadline_ms, max_attempts, input_hash, priority, 'CREATED', created, created))
            self._append_event(task_id, 'TASK_CREATED', None, 'CREATED', 'kernel', 'task_created', {'input_hash': input_hash})
            self._commit()
        except Exception:
            self._rollback()
            raise
        return self.get_task(task_id)

    def transition(
        self,
        task_id: str,
        to_state: str,
        actor: str = "kernel",
        reason: str = "",
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        lease_id: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        if to_state not in STATES and to_state != "WAITING_APPROVAL":
            raise InvalidTransition(f"unknown target state {to_state}")
        if to_state in ("COMPLETED", "FAILED"):
            raise InvalidTransition(
                f"direct transition to {to_state} is forbidden; use commit_{to_state.lower()}() with valid evidence"
            )
        self._begin()
        try:
            if event_id:
                existing = self.conn.execute(
                    "SELECT * FROM events WHERE event_id=?", (event_id,)
                ).fetchone()
                if existing:
                    if existing["task_id"] != task_id or existing["to_state"] != to_state:
                        raise InvalidTransition("event_id reused for a different transition")
                    self._commit()
                    return self.get_task(task_id)
            task = self._task(task_id)
            if expected_version is not None and int(task["version"]) != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict on task {task_id}: expected version {expected_version}, found {task['version']}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=expected_version,
                )
            cur_version = int(task["version"])
            old = task["state"]

            if old == "HUMAN_REVIEW" and to_state == "HUMAN_REVIEW":

                self._rollback()

                return self.get_task(task_id)
            if old == "WAITING_APPROVAL" and to_state == "READY":
                raise InvalidTransition(
                    "direct transition from WAITING_APPROVAL to READY is forbidden; use commit_approval() with valid capability token"
                )
            if to_state not in ALLOWED_TRANSITIONS.get(old, set()):
                raise InvalidTransition(f"{old}->{to_state}")
            if old in TERMINAL:
                raise InvalidTransition("terminal task is immutable")

            if to_state in ("COMPLETED", "FAILED", "RUNNING", "CHECKPOINTED", "VERIFYING"):
                try:
                    from scp.meta.why_gate import WhyDecision, get_why_gate

                    why_res = get_why_gate().gate(
                        action_type="kernel_transition",
                        action_desc=f"Transition {task_id} from {old} to {to_state} by {actor}",
                        context=reason,
                        llm_enabled=False,
                    )
                    if why_res.decision == WhyDecision.REJECT:
                        raise InvalidTransition(
                            f"WHY Gate REJECTED this kernel transition: {why_res.falsification_reason}"
                        )
                except InvalidTransition:
                    raise
                except Exception as why_err:
                    logger.debug("WHY Gate crashed during transition %s -> %s (fail-closed): %s", task_id, to_state, why_err, exc_info=True)
                    raise InvalidTransition(f"WHY Gate crashed, fail-closed: {why_err}")

            # Lease Authority Gate (INV-01)
            caller_lease = lease_id or getattr(self, "_bound_leases", {}).get(task_id)
            is_system = getattr(self, "_system_authority", False)

            if is_system:
                new_lease_id = None
                new_fencing_token = 0
            else:
                is_leased_state = old in {"LEASED", "RUNNING", "WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "UNKNOWN"}
                has_active_lease = bool(task["active_lease_id"])
                if is_leased_state or has_active_lease:
                    bound = getattr(self, "_bound_leases", {}).get(task_id)
                    if not caller_lease:
                        raise StaleLease(f"transition from {old} requires active lease authority")
                    if bound and caller_lease != bound:
                        raise StaleLease(f"caller lease {caller_lease} does not match bound instance lease {bound}")
                    if not bound:
                        raise StaleLease(f"kernel instance does not possess active lease authority for task {task_id}")
                    if task["active_lease_id"] and caller_lease != task["active_lease_id"]:
                        raise StaleLease(
                            f"caller lease {caller_lease} does not match active task lease {task['active_lease_id']}"
                        )
                    lease_row = self._assert_lease(caller_lease, task_id)
                    token = int(lease_row["fencing_token"])
                elif caller_lease:
                    lease_row = self._assert_lease(caller_lease, task_id)
                    token = int(lease_row["fencing_token"])
                else:
                    token = 0

                if to_state in {"RUNNING", "WAITING_TOOL", "VERIFYING", "CHECKPOINTED"}:
                    new_lease_id = caller_lease
                    new_fencing_token = token
                else:
                    new_lease_id = None
                    new_fencing_token = 0
                    if caller_lease:
                        self.conn.execute("UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0", (caller_lease,))
                        self.conn.execute(
                            "UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?",
                            (task["owner"],),
                        )
                        if hasattr(self, "_bound_leases"):
                            self._bound_leases.pop(task_id, None)

            cur = self.conn.execute(
                "UPDATE tasks SET state=?,version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=?",
                (to_state, new_lease_id, new_fencing_token, now_iso(), task_id, cur_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict transitioning task {task_id}: expected version {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=cur_version,
                )

            self._append_event(
                task_id,
                "STATE_TRANSITION",
                old,
                to_state,
                actor,
                reason or f"{old}->{to_state}",
                payload,
                event_id=event_id,
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        return self.get_task(task_id)

    def _assert_not_killed(self) -> Any:
        control = self._control()
        if control['global_kill']:
            raise KillSwitchActive('global kill switch active')
        return control

    def claim(self, task_id: str, worker_id: str, attempt_id: str | None=None, ttl_seconds: float=30.0) -> Lease:
        if ttl_seconds <= 0 or not worker_id:
            raise KernelError('invalid lease contract')
        self._begin()
        try:
            control = self._assert_not_killed()
            task = self._task(task_id)
            created_at = datetime.fromisoformat(task['created_at']).timestamp()
            if time.time() >= created_at + int(task['deadline_ms']) / 1000.0:
                raise KernelError('task deadline exceeded')
            if task['state'] != 'QUEUED':
                raise KernelError(f"task not queueable: {task['state']}")
            attempt_id = attempt_id or 'attempt_' + secrets.token_hex(8)
            old = self.conn.execute('SELECT COALESCE(MAX(fencing_token),0) AS n FROM leases WHERE task_id=?', (task_id,)).fetchone()['n']
            token = int(old) + 1
            now = time.time()
            lease_id = 'lease_' + secrets.token_hex(12)
            cur = self.conn.execute("UPDATE tasks SET state='LEASED',version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=?", (lease_id, token, now_iso(), task_id, task['version']))
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict claiming task {task_id}")
            self.conn.execute('INSERT INTO leases(lease_id,task_id,attempt_id,worker_id,issued_at,expires_at,heartbeat_at,fencing_token,global_kill_epoch) VALUES (?,?,?,?,?,?,?,?,?)', (lease_id, task_id, attempt_id, worker_id, now, now + ttl_seconds, now, token, control['global_kill_epoch']))
            self.conn.execute('INSERT INTO queue_accounts(owner,active,dispatch_count,last_dispatch_at) VALUES (?,?,?,?) ON CONFLICT(owner) DO UPDATE SET active=active+1,dispatch_count=dispatch_count+1,last_dispatch_at=excluded.last_dispatch_at', (task['owner'], 1, 1, now))
            self._bound_leases[task_id] = lease_id
            self._append_event(task_id, 'LEASE_GRANTED', 'QUEUED', 'LEASED', 'kernel', 'lease_granted', {'lease_id': lease_id, 'fencing_token': token, 'worker_id': worker_id})
            self._commit()
            return Lease(lease_id, task_id, attempt_id, worker_id, now + ttl_seconds, token, control['global_kill_epoch'])
        except Exception:
            self._rollback()
            raise

    def claim_next(self, worker_id: str, max_active_per_owner: int=1, ttl_seconds: float=30.0, now: float | None=None) -> Lease | None:
        """Claim one queued task using priority + owner fair-share + deadline guards."""
        if not worker_id or max_active_per_owner <= 0 or ttl_seconds <= 0:
            raise KernelError('invalid queue claim contract')
        now = time.time() if now is None else float(now)
        self._begin()
        try:
            control = self._assert_not_killed()
            candidates = self.conn.execute("\n                SELECT t.*, COALESCE(a.active,0) AS owner_active,\n                       COALESCE(a.dispatch_count,0) AS owner_dispatch_count,\n                       COALESCE(a.last_dispatch_at,0) AS owner_last_dispatch_at\n                FROM tasks t LEFT JOIN queue_accounts a ON a.owner=t.owner\n                WHERE t.state='QUEUED'\n                ORDER BY t.priority ASC, owner_dispatch_count ASC,\n                         owner_last_dispatch_at ASC, t.created_at ASC, t.task_id ASC\n                ").fetchall()
            for task in candidates:
                created_at = datetime.fromisoformat(task['created_at']).timestamp()
                if now >= created_at + int(task['deadline_ms']) / 1000.0:
                    cur = self.conn.execute(
                        "UPDATE tasks SET state='FAILED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                        (now_iso(), task['task_id'], task['version']),
                    )
                    if cur.rowcount != 1:
                        continue
                    self._append_event(task['task_id'], 'DEADLINE_EXPIRED', 'QUEUED', 'FAILED', 'kernel', 'queue_deadline_guard', {'deadline_ms': task['deadline_ms']})
                    continue
                if int(task['owner_active']) >= max_active_per_owner:
                    continue
                attempt_id = 'attempt_' + secrets.token_hex(8)
                latest = self.conn.execute('SELECT COALESCE(MAX(fencing_token),0) AS n FROM leases WHERE task_id=?', (task['task_id'],)).fetchone()['n']
                fencing_token = int(latest) + 1
                lease_id = 'lease_' + secrets.token_hex(12)
                expires_at = now + ttl_seconds
                cur = self.conn.execute("UPDATE tasks SET state='LEASED',version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=?", (lease_id, fencing_token, now_iso(), task['task_id'], task['version']))
                if cur.rowcount != 1:
                    continue
                self.conn.execute('INSERT INTO leases(lease_id,task_id,attempt_id,worker_id,issued_at,expires_at,heartbeat_at,fencing_token,global_kill_epoch) VALUES (?,?,?,?,?,?,?,?,?)', (lease_id, task['task_id'], attempt_id, worker_id, now, expires_at, now, fencing_token, control['global_kill_epoch']))
                self.conn.execute('INSERT INTO queue_accounts(owner,active,dispatch_count,last_dispatch_at) VALUES (?,?,?,?) ON CONFLICT(owner) DO UPDATE SET active=active+1,dispatch_count=dispatch_count+1,last_dispatch_at=excluded.last_dispatch_at', (task['owner'], 1, 1, now))
                self._bound_leases[task['task_id']] = lease_id
                self._append_event(task['task_id'], 'LEASE_GRANTED', 'QUEUED', 'LEASED', 'kernel', 'fair_queue_claim', {'lease_id': lease_id, 'fencing_token': fencing_token, 'worker_id': worker_id})
                self._commit()
                return Lease(lease_id, task['task_id'], attempt_id, worker_id, expires_at, fencing_token, control['global_kill_epoch'])
            self._commit()
            return None
        except Exception:
            self._rollback()
            raise

    def queue_status(self) -> dict[str, Any]:
        rows = self.conn.execute('SELECT owner,active,dispatch_count,last_dispatch_at FROM queue_accounts ORDER BY owner').fetchall()
        queued = self.conn.execute("SELECT COUNT(*) AS n FROM tasks WHERE state='QUEUED'").fetchone()['n']
        return {'queued': int(queued), 'owners': [dict(row) for row in rows]}

    def _lease(self, lease_id: str) -> Any:
        row = self.conn.execute('SELECT * FROM leases WHERE lease_id=?', (lease_id,)).fetchone()
        if not row:
            raise StaleLease(lease_id)
        return row

    def _assert_lease(self, lease_id: str, task_id: str, actor: str | None = None) -> Any:
        lease = self._lease(lease_id)
        control = self._control()
        now = time.time()
        if lease['task_id'] != task_id or lease['released'] or lease['expires_at'] <= now or (lease['global_kill_epoch'] != control['global_kill_epoch']) or control['global_kill']:
            if lease['released']:
                raise OptimisticLockError(
                    f"lease {lease_id} has already been released",
                    table="leases",
                    entity_id=lease_id,
                )
            raise StaleLease(lease_id)
        latest = self.conn.execute('SELECT COALESCE(MAX(fencing_token), 0) AS n FROM leases WHERE task_id=?', (task_id,)).fetchone()['n']
        if int(lease['fencing_token']) != int(latest):
            raise StaleLease(lease_id)
        if actor is not None and str(actor).strip():
            if lease['worker_id'] != str(actor).strip():
                raise InvalidTransition(f"actor '{actor}' does not match lease worker '{lease['worker_id']}'")
        return lease

    def start(self, task_id: str, lease_id: str) -> dict[str, Any]:
        self._begin()
        try:
            lease = self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task['state'] != 'LEASED':
                raise InvalidTransition(f"{task['state']}->RUNNING")
            if task['active_lease_id'] and task['active_lease_id'] != lease_id:
                raise StaleLease(f"start lease {lease_id} does not match active task lease {task['active_lease_id']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority to start task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            cur = self.conn.execute(
                "UPDATE tasks SET state='RUNNING',version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=? AND (active_lease_id=? OR active_lease_id IS NULL)",
                (lease_id, int(lease['fencing_token']), now_iso(), task_id, task['version'], lease_id)
            )
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict starting task {task_id}")
            self._bound_leases[task_id] = lease_id
            self._append_event(task_id, 'WORKER_STARTED', 'LEASED', 'RUNNING', 'worker', 'lease_valid', {'lease_id': lease_id})
            self._commit()
        except Exception:
            self._rollback()
            raise
        return self.get_task(task_id)

    def heartbeat(self, task_id: str, lease_id: str, extend_seconds: float=30.0, expected_version: int | None=None) -> Lease:
        self._begin()
        try:
            lease = self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task['active_lease_id'] != lease_id:
                raise StaleLease(f"heartbeat lease {lease_id} does not match active task lease {task['active_lease_id']}")
            if task['state'] not in {"LEASED", "RUNNING", "WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "UNKNOWN"}:
                raise StaleLease(f"cannot heartbeat task in non-leased state {task['state']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority for task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            current_lease_version = int(lease['version']) if 'version' in lease.keys() else 1
            if expected_version is not None and current_lease_version != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict on lease {lease_id}: expected version {expected_version}, found {current_lease_version}",
                    table="leases",
                    entity_id=lease_id,
                    expected_version=expected_version,
                )
            target_version = expected_version if expected_version is not None else current_lease_version
            now = time.time()
            expires = now + extend_seconds
            cur = self.conn.execute(
                'UPDATE leases SET heartbeat_at=?,expires_at=?,version=version+1 WHERE lease_id=? AND released=0 AND version=?',
                (now, expires, lease_id, target_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict heartbeating lease {lease_id} (version mismatch or lease released)",
                    table="leases",
                    entity_id=lease_id,
                    expected_version=target_version,
                )
            self._commit()
            return Lease(lease['lease_id'], lease['task_id'], lease['attempt_id'], lease['worker_id'], expires, lease['fencing_token'], lease['global_kill_epoch'])
        except Exception:
            self._rollback()
            raise

    # [S20] States in which a live lease still carries execution authority and
    # an expiry-only renewal is meaningful. Terminal/recovery states are
    # excluded: once expire_leases/boot-recovery moved the task, the holder's
    # authority is gone and renew must refuse (finalize then routes
    # fail-closed through the state-race path).
    _RENEWABLE_LEASE_STATES = frozenset({"LEASED", "RUNNING", "WAITING_TOOL", "VERIFYING"})

    def renew_lease(self, task_id: str, lease_id: str, fencing_token: int, ttl_seconds: float | None = None) -> bool:
        """[S20] Expiry-only lease renewal for long-running holders (slow LLM
        providers whose latency legitimately exceeds the claim TTL).

        NOT a replacement for crash detection: this only moves ``expires_at``
        (and ``heartbeat_at``) forward on the CURRENT live attempt. The caller
        must present ``lease_id`` + ``fencing_token`` that match the task's
        active lease and the highest fencing token ever issued for the task —
        a previous (fenced-off) holder is refused fail-closed, so a zombie
        worker can never keep a revoked attempt alive.

        Returns False (never raises) when:
          * the lease row does not exist, belongs to another task, is already
            released, or has already expired (no resurrection — once the
            watchdog swept it, authority is gone);
          * the presented fencing token does not match the lease row or is not
            the latest token for the task (stale attempt);
          * the task's active_lease_id no longer points at this lease, the
            task sits in a non-renewable state (terminal/RECOVERING/
            RECONCILING/UNKNOWN/...), a global kill is active, or the lease's
            global_kill epoch was bumped;
          * an optimistic lease-version conflict raced the update.

        Deliberately does NOT touch the tasks row: no state change, no
        state-machine version bump, no event (the leases table version is the
        existing per-row OCC counter, same pattern as heartbeat()).
        """
        if not task_id or not lease_id:
            return False
        try:
            presented_token = int(fencing_token)
        except (TypeError, ValueError):
            return False
        if ttl_seconds is not None:
            try:
                presented_ttl = float(ttl_seconds)
            except (TypeError, ValueError):
                return False
            if presented_ttl <= 0:
                return False
        else:
            presented_ttl = None
        self._begin()
        try:
            lease = self.conn.execute('SELECT * FROM leases WHERE lease_id=?', (lease_id,)).fetchone()
            if lease is None or str(lease['task_id']) != str(task_id):
                self._commit()
                return False
            now = time.time()
            if int(lease['released']) != 0 or float(lease['expires_at']) <= now:
                # released or already expired: no resurrection.
                self._commit()
                return False
            if int(lease['fencing_token']) != presented_token:
                self._commit()
                return False
            latest = self.conn.execute('SELECT COALESCE(MAX(fencing_token), 0) AS n FROM leases WHERE task_id=?', (task_id,)).fetchone()['n']
            if presented_token != int(latest):
                # a newer attempt exists: this caller is a stale holder.
                self._commit()
                return False
            control = self._control()
            if int(control['global_kill']) != 0 or int(lease['global_kill_epoch']) != int(control['global_kill_epoch']):
                self._commit()
                return False
            task = self.conn.execute('SELECT * FROM tasks WHERE task_id=?', (task_id,)).fetchone()
            if task is None:
                self._commit()
                return False
            if (task['active_lease_id'] is None or str(task['active_lease_id']) != str(lease_id)) or str(task['state']) not in self._RENEWABLE_LEASE_STATES:
                self._commit()
                return False
            extend = presented_ttl if presented_ttl is not None else (float(lease['expires_at']) - float(lease['issued_at']))
            if extend <= 0:
                self._commit()
                return False
            expires = now + extend
            lease_version = int(lease['version']) if 'version' in lease.keys() else 1
            cur = self.conn.execute(
                'UPDATE leases SET heartbeat_at=?,expires_at=?,version=version+1 WHERE lease_id=? AND released=0 AND version=?',
                (now, expires, lease_id, lease_version),
            )
            if cur.rowcount != 1:
                self._commit()
                return False
            self._commit()
            return True
        except Exception:
            self._rollback()
            raise

    def expire_leases(self, now: float | None = None) -> list[str]:
        now = now or time.time()
        expired = []
        candidates = self.conn.execute(
            'SELECT * FROM leases WHERE released=0 AND expires_at<=?', (now,)
        ).fetchall()

        for lease in candidates:
            # [SEC-R3-01] Isolate transaction per expired lease so a single conflict
            # does not roll back the entire sweep or starve the watchdog.
            self._begin()
            try:
                task = self._task(lease['task_id'])
                cur_state = task['state']
                # [SEC-R3-02] Enforce task['active_lease_id'] == lease['lease_id'] before reclaim:
                # If the lease being swept is not the currently active lease of the task,
                # do NOT modify task state, do NOT clear active_lease_id.
                is_active_lease = (task['active_lease_id'] == lease['lease_id'])
                if is_active_lease:
                    if cur_state in {'LEASED', 'RUNNING', 'WAITING_TOOL'}:
                        old = cur_state
                        cur = self.conn.execute(
                            "UPDATE tasks SET state='RECOVERING',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                            (now_iso(), task['task_id'], task['version']),
                        )
                        if cur.rowcount == 0:
                            raise OptimisticLockError(
                                f"Task {task['task_id']} modified concurrently",
                                table="tasks",
                                entity_id=task['task_id'],
                            )
                        self._append_event(task['task_id'], 'LEASE_EXPIRED', old, 'RECOVERING', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
                    elif cur_state == 'VERIFYING':
                        if self.autonomous_mode:
                            cur = self.conn.execute(
                                "UPDATE tasks SET state='FAILED',error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                                ("verification_lease_expired", now_iso(), task['task_id'], task['version']),
                            )
                            if cur.rowcount == 0:
                                raise OptimisticLockError(
                                    f"Task {task['task_id']} modified concurrently",
                                    table="tasks",
                                    entity_id=task['task_id'],
                                )
                            self._append_event(
                                task['task_id'],
                                'LEASE_EXPIRED',
                                cur_state,
                                'FAILED',
                                'kernel:autonomous',
                                'heartbeat_expired_autonomous',
                                {'lease_id': lease['lease_id'], 'autonomous': True},
                            )
                        else:
                            cur = self.conn.execute(
                                "UPDATE tasks SET state='HUMAN_REVIEW',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                                (now_iso(), task['task_id'], task['version']),
                            )
                            if cur.rowcount == 0:
                                raise OptimisticLockError(
                                    f"Task {task['task_id']} modified concurrently",
                                    table="tasks",
                                    entity_id=task['task_id'],
                                )
                            self._append_event(task['task_id'], 'LEASE_EXPIRED', cur_state, 'HUMAN_REVIEW', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
                    elif cur_state == 'CHECKPOINTED':
                        cur = self.conn.execute(
                            "UPDATE tasks SET state='QUEUED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                            (now_iso(), task['task_id'], task['version']),
                        )
                        if cur.rowcount == 0:
                            raise OptimisticLockError(
                                f"Task {task['task_id']} modified concurrently",
                                table="tasks",
                                entity_id=task['task_id'],
                            )
                        self._append_event(task['task_id'], 'LEASE_EXPIRED', cur_state, 'QUEUED', 'kernel', 'heartbeat_expired', {'lease_id': lease['lease_id']})
                    else:
                        cur = self.conn.execute(
                            "UPDATE tasks SET active_lease_id=NULL,active_fencing_token=0,version=version+1,updated_at=? WHERE task_id=? AND version=?",
                            (now_iso(), task['task_id'], task['version']),
                        )
                        if cur.rowcount == 0:
                            raise OptimisticLockError(
                                f"Task {task['task_id']} modified concurrently",
                                table="tasks",
                                entity_id=task['task_id'],
                            )
                else:
                    logger.info(
                        "expire_leases: lease %s expired for task %s, but active_lease_id is %s; preserving active task",
                        lease['lease_id'], task['task_id'], task['active_lease_id']
                    )

                # [SEC-R3-01] Validate cur_lease.rowcount > 0
                cur_lease = self.conn.execute(
                    'UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0',
                    (lease['lease_id'],),
                )
                if cur_lease.rowcount == 0:
                    raise OptimisticLockError(
                        f"Lease {lease['lease_id']} modified concurrently or already released",
                        table="leases",
                        entity_id=lease['lease_id'],
                    )

                owner = self._task(lease['task_id'])['owner']
                # [SEC-R3-01] Validate cur_acc.rowcount > 0
                cur_acc = self.conn.execute(
                    'UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?',
                    (owner,),
                )
                if cur_acc.rowcount == 0:
                    raise OptimisticLockError(
                        f"Queue account for owner {owner} modified concurrently or not found",
                        table="queue_accounts",
                        entity_id=owner,
                    )

                if is_active_lease and hasattr(self, '_bound_leases'):
                    self._bound_leases.pop(lease['task_id'], None)

                self._commit()
                expired.append(lease['lease_id'])
            except OptimisticLockError as ole:
                self._rollback()
                logger.warning("OCC conflict during lease expiration for lease %s: %s", lease['lease_id'], ole)
            except Exception:
                self._rollback()
                raise

        return expired

    def release(self, task_id: str, lease_id: str, expected_version: int | None=None) -> None:
        self._begin()
        try:
            self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task["active_lease_id"] != lease_id:
                raise StaleLease(f"release lease {lease_id} does not match active task lease {task['active_lease_id']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority for task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            lease = self._lease(lease_id)
            current_lease_version = int(lease['version']) if 'version' in lease.keys() else 1
            if expected_version is not None and current_lease_version != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict releasing lease {lease_id}: expected version {expected_version}, found {current_lease_version}",
                    table="leases",
                    entity_id=lease_id,
                    expected_version=expected_version,
                )
            target_version = expected_version if expected_version is not None else current_lease_version
            cur = self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0 AND version=?', (lease_id, target_version))
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict releasing lease {lease_id}",
                    table="leases",
                    entity_id=lease_id,
                    expected_version=target_version,
                )
            cur = self.conn.execute(
                'UPDATE tasks SET active_lease_id=NULL,active_fencing_token=0,version=version+1,updated_at=? WHERE task_id=? AND version=?',
                (now_iso(), task_id, task['version']),
            )
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict releasing lease on task {task_id}")
            self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
            self._append_event(task_id, 'LEASE_RELEASED', None, None, 'kernel', 'worker_release', {'lease_id': lease_id})
            if hasattr(self, '_bound_leases'):
                self._bound_leases.pop(task_id, None)
            self._commit()
        except Exception:
            self._rollback()
            raise

    def checkpoint(self, task_id: str, lease_id: str, step_id: str, state: str, planned_action: Any, capability_epoch: int, idempotency_key: str, pre_observation_ref: str | None=None, post_observation_ref: str | None=None, tool_result: Any | None=None, verifier_verdict: str | None=None) -> str:
        if state not in STATES:
            raise CheckpointCorrupt('invalid checkpoint state')
        _assert_checkpoint_safe({'planned_action': planned_action, 'pre_observation_ref': pre_observation_ref, 'post_observation_ref': post_observation_ref, 'tool_result': tool_result})
        self._begin()
        try:
            lease = self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task['state'] not in {'RUNNING', 'WAITING_TOOL', 'VERIFYING', 'CHECKPOINTED'}:
                raise InvalidTransition(f"cannot checkpoint task in state {task['state']}")
            if task['active_lease_id'] != lease_id:
                raise StaleLease(f"checkpoint lease {lease_id} does not match active task lease {task['active_lease_id']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority for task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            payload = {'task_id': task_id, 'attempt_id': lease['attempt_id'], 'step_id': step_id, 'state': state, 'planned_action': planned_action, 'capability_epoch': capability_epoch, 'idempotency_key': idempotency_key, 'pre_observation_ref': pre_observation_ref, 'post_observation_ref': post_observation_ref, 'tool_result': tool_result, 'verifier_verdict': verifier_verdict}
            cp_id = 'cp_' + secrets.token_hex(10)
            payload_hash = stable_hash(payload)
            self.conn.execute('INSERT INTO checkpoints(checkpoint_id,task_id,attempt_id,step_id,state,planned_action_hash,capability_epoch,idempotency_key,pre_observation_ref,post_observation_ref,tool_result_json,verifier_verdict,payload_hash,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (cp_id, task_id, lease['attempt_id'], step_id, state, stable_hash(planned_action), capability_epoch, idempotency_key, pre_observation_ref, post_observation_ref, json.dumps(tool_result, ensure_ascii=False, sort_keys=True) if tool_result is not None else None, verifier_verdict, payload_hash, now_iso()))
            # [P1 FIX 2026-09-05] A checkpoint is a snapshot, not a state
            # transition: to_state must stay NULL. rebuild_projection derives
            # the task state from the last non-null to_state, so a non-NULL
            # value here would project the checkpoint snapshot state (e.g.
            # WAITING_TOOL) after a crash even though the tasks table never
            # transitioned there. The authoritative checkpoint state lives in
            # the checkpoints row ('state' column), not in the projection.
            self._append_event(task_id, 'CHECKPOINT_WRITTEN', None, None, 'kernel', 'checkpoint_written', {'checkpoint_id': cp_id, 'payload_hash': payload_hash, 'idempotency_key': idempotency_key})
            self._commit()
            return cp_id
        except Exception:
            self._rollback()
            raise

    @staticmethod
    def _rebuild_checkpoint_payload(row: Any, state: str, planned_action: Any, post_observation_ref: str | None, tool_result: Any, verifier_verdict: str | None) -> dict[str, Any]:
        """Rebuild the stable_hash payload of a checkpoint row with the EXACT
        shape used by checkpoint() / validate_checkpoint(), so a row updated by
        finalize_checkpoint keeps a self-verifying payload_hash."""
        return {
            'task_id': row['task_id'], 'attempt_id': row['attempt_id'], 'step_id': row['step_id'],
            'state': state, 'planned_action': planned_action, 'capability_epoch': row['capability_epoch'],
            'idempotency_key': row['idempotency_key'], 'pre_observation_ref': row['pre_observation_ref'],
            'post_observation_ref': post_observation_ref, 'tool_result': tool_result,
            'verifier_verdict': verifier_verdict,
        }

    def finalize_checkpoint(
        self,
        task_id: str,
        checkpoint_id: str,
        *,
        planned_action: Any,
        verifier_verdict: str | None = None,
        post_observation_ref: str | None = None,
        tool_result: Any | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """[F-03 2026-09-25] Finalize a checkpoint at the task's terminal boundary.

        Runtime audit RUNTIME-AUDIT-20260925-0411 F-03: ask checkpoints stayed
        state='RUNNING' with NULL post_observation_ref / verifier_verdict after
        the task reached COMPLETED / HUMAN_REVIEW — the physical checkpoint
        artifact stayed weaker than the event chain. The task outcome must be
        projected onto the checkpoint row at the moment it is committed.

        Fail-closed contract:
          * the caller must present the exact ``planned_action`` the checkpoint
            was written with (hash match) — no blind row mutation;
          * only fields the caller actually has are recorded — missing evidence
            stays NULL (nothing fabricated); when the checkpoint legitimately
            cannot be finalized (task not yet decided) the reason is recorded
            IN the row (tool_result_json) instead of leaving a bare RUNNING;
          * 'UNKNOWN' checkpoints are owned by the reconcile contract
            (record_action_dispatched / reconcile_unknown) and are never
            touched here; already-decided rows are idempotent no-ops;
          * payload_hash is recomputed from the updated row (same payload shape
            as validate_checkpoint) so the row stays self-verifiable;
          * the journal event carries from_state/to_state=None (same rule as
            CHECKPOINT_WRITTEN): a checkpoint finalization is a snapshot
            update, NEVER a task state transition (P1 projection rule).
        """
        if note is None and verifier_verdict is None and post_observation_ref is None and tool_result is None:
            raise KernelError('finalize_checkpoint requires evidence fields or a note (no fabricated data)')
        _assert_checkpoint_safe({'post_observation_ref': post_observation_ref, 'tool_result': tool_result, 'verifier_verdict': verifier_verdict, 'note': note})
        self._begin()
        try:
            row = self.conn.execute('SELECT * FROM checkpoints WHERE checkpoint_id=?', (checkpoint_id,)).fetchone()
            if not row:
                raise CheckpointCorrupt(checkpoint_id)
            if row['task_id'] != task_id:
                raise KernelError('checkpoint task mismatch')
            if row['planned_action_hash'] != stable_hash(planned_action):
                raise CheckpointCorrupt('planned action hash mismatch')
            if row['state'] in TERMINAL or row['state'] == 'HUMAN_REVIEW':
                self._commit()
                result = dict(row)
                result['finalization'] = 'already_final'
                return result
            if row['state'] == 'UNKNOWN':
                # The side-effect-unknown reconcile flow owns these rows; a
                # terminal claim here would race reconcile_unknown.
                self._commit()
                result = dict(row)
                result['finalization'] = 'owned_by_reconcile'
                return result
            task = self._task(task_id)
            if task['state'] not in TERMINAL and task['state'] != 'HUMAN_REVIEW':
                # Task has not reached a decision — claiming a terminal outcome
                # would be fabrication. Record WHY the row stays non-terminal
                # (fail-closed visibility) instead of a bare RUNNING.
                blocked = dict(tool_result) if isinstance(tool_result, dict) else {}
                blocked['finalization'] = 'BLOCKED'
                blocked['finalization_reason'] = f"task_state={task['state']}" + (f"; note={note}" if note else "")
                payload = self._rebuild_checkpoint_payload(row, row['state'], planned_action, row['post_observation_ref'], blocked, row['verifier_verdict'])
                self.conn.execute('UPDATE checkpoints SET tool_result_json=?, payload_hash=? WHERE checkpoint_id=?', (json.dumps(blocked, ensure_ascii=False, sort_keys=True), stable_hash(payload), checkpoint_id))
                self._append_event(task_id, 'CHECKPOINT_FINALIZED', None, None, 'kernel', 'checkpoint_finalization_blocked', {'checkpoint_id': checkpoint_id, 'task_state': task['state'], 'note': note})
                self._commit()
                result = self.get_checkpoint(checkpoint_id)
                result['finalization'] = 'blocked_task_not_decided'
                return result
            from_state = row['state']
            new_post = post_observation_ref if post_observation_ref is not None else row['post_observation_ref']
            new_verdict = verifier_verdict if verifier_verdict is not None else row['verifier_verdict']
            if tool_result is not None:
                new_tool = tool_result
            else:
                new_tool = json.loads(row['tool_result_json']) if row['tool_result_json'] else None
            payload = self._rebuild_checkpoint_payload(row, task['state'], planned_action, new_post, new_tool, new_verdict)
            self.conn.execute('UPDATE checkpoints SET state=?, post_observation_ref=?, verifier_verdict=?, tool_result_json=?, payload_hash=? WHERE checkpoint_id=?', (task['state'], new_post, new_verdict, json.dumps(new_tool, ensure_ascii=False, sort_keys=True) if new_tool is not None else None, stable_hash(payload), checkpoint_id))
            self._append_event(task_id, 'CHECKPOINT_FINALIZED', None, None, 'kernel', 'checkpoint_finalized', {'checkpoint_id': checkpoint_id, 'from_state': from_state, 'to_state': task['state'], 'verifier_verdict': new_verdict, 'note': note})
            self._commit()
            result = self.get_checkpoint(checkpoint_id)
            result['finalization'] = 'finalized'
            return result
        except Exception:
            self._rollback()
            raise

    def record_action_dispatched(self, task_id: str, lease_id: str, step_id: str, planned_action: Any, capability_epoch: int, idempotency_key: str, provider_request_id: str, pre_observation_ref: str | None=None) -> dict[str, Any]:
        """Persist the side-effect boundary before a provider response is trusted."""
        if not step_id or not idempotency_key or (not str(provider_request_id).strip()):
            raise KernelError('dispatch requires step, idempotency key and provider request')
        _assert_checkpoint_safe({'planned_action': planned_action, 'pre_observation_ref': pre_observation_ref, 'provider_request_id': provider_request_id})
        self._begin()
        try:
            lease = self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task['state'] not in {'RUNNING', 'WAITING_TOOL'}:
                raise InvalidTransition(f"{task['state']}->UNKNOWN")
            if task['active_lease_id'] != lease_id:
                raise StaleLease(f"dispatch lease {lease_id} does not match active task lease {task['active_lease_id']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority for task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            existing = self.conn.execute("SELECT * FROM checkpoints WHERE task_id=? AND attempt_id=? AND step_id=? AND idempotency_key=? AND state='UNKNOWN' ORDER BY created_at DESC LIMIT 1", (task_id, lease['attempt_id'], step_id, idempotency_key)).fetchone()
            if existing:
                existing_result = json.loads(existing['tool_result_json'] or '{}')
                if existing_result.get('provider_request_id') != str(provider_request_id):
                    raise KernelError('idempotency key reused with different provider request')
                self._commit()
                result = dict(existing)
                result['dispatch_status'] = 'UNKNOWN'
                result['provider_request_id'] = existing_result.get('provider_request_id')
                return result
            tool_result = {'dispatch_status': 'UNKNOWN', 'provider_request_id': str(provider_request_id), 'planned_action': planned_action}
            payload = {'task_id': task_id, 'attempt_id': lease['attempt_id'], 'step_id': step_id, 'state': 'UNKNOWN', 'planned_action': planned_action, 'capability_epoch': capability_epoch, 'idempotency_key': idempotency_key, 'pre_observation_ref': pre_observation_ref, 'post_observation_ref': None, 'tool_result': tool_result, 'verifier_verdict': None}
            checkpoint_id = 'cp_' + secrets.token_hex(10)
            payload_hash = stable_hash(payload)
            self.conn.execute('INSERT INTO checkpoints(checkpoint_id,task_id,attempt_id,step_id,state,planned_action_hash,capability_epoch,idempotency_key,pre_observation_ref,post_observation_ref,tool_result_json,verifier_verdict,payload_hash,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (checkpoint_id, task_id, lease['attempt_id'], step_id, 'UNKNOWN', stable_hash(planned_action), capability_epoch, idempotency_key, pre_observation_ref, None, json.dumps(tool_result, ensure_ascii=False, sort_keys=True), None, payload_hash, now_iso()))
            old_state = task['state']
            cur = self.conn.execute("UPDATE tasks SET state='UNKNOWN',version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=?", (lease_id, int(lease['fencing_token']), now_iso(), task_id, task['version']))
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict on task {task_id}")
            self._append_event(task_id, 'ACTION_DISPATCHED', old_state, 'UNKNOWN', 'worker', 'side_effect_response_unknown', {'checkpoint_id': checkpoint_id, 'step_id': step_id, 'idempotency_key': idempotency_key, 'provider_request_id': str(provider_request_id)})
            self._commit()
            result = self.get_checkpoint(checkpoint_id)
            result['dispatch_status'] = 'UNKNOWN'
            result['provider_request_id'] = str(provider_request_id)
            return result
        except Exception:
            self._rollback()
            raise

    def _load_reconcile_checkpoint(self, task_id: str, checkpoint_id: str) -> dict[str, Any]:
        checkpoint = self.conn.execute('SELECT * FROM checkpoints WHERE checkpoint_id=?', (checkpoint_id,)).fetchone()
        if not checkpoint or checkpoint['task_id'] != task_id:
            raise KernelError('checkpoint task mismatch')
        if checkpoint['state'] != 'UNKNOWN':
            raise KernelError('reconcile requires UNKNOWN checkpoint')
        try:
            tool_result = json.loads(checkpoint['tool_result_json'] or '{}')
        except (TypeError, ValueError) as exc:
            raise KernelError('checkpoint integrity: invalid tool result JSON') from exc
        if 'planned_action' not in tool_result:
            raise KernelError('checkpoint integrity: planned action unavailable')
        try:
            self.validate_checkpoint(checkpoint_id, tool_result['planned_action'])
        except CheckpointCorrupt as exc:
            raise KernelError(f'checkpoint integrity: {exc}') from exc
        return dict(checkpoint)

    def enter_reconciling(self, task_id: str, checkpoint_id: str, reason: str='reconcile_required') -> dict[str, Any]:
        self._begin()
        try:
            task = self._task(task_id)
            self._load_reconcile_checkpoint(task_id, checkpoint_id)
            if task['state'] == 'RECONCILING':
                self._commit()
                return dict(task)
            if task['state'] != 'UNKNOWN':
                raise InvalidTransition(f"{task['state']}->RECONCILING")
            cur = self.conn.execute("UPDATE tasks SET state='RECONCILING',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task_id, task['version']))
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict entering reconciling task {task_id}")
            active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (task_id,)).fetchall()
            if active_leases:
                self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (task_id,))
                for _ in active_leases:
                    self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
            if hasattr(self, '_bound_leases'):
                self._bound_leases.pop(task_id, None)
            self._append_event(task_id, 'RECONCILE_STARTED', 'UNKNOWN', 'RECONCILING', 'kernel', reason or 'reconcile_required', {'checkpoint_id': checkpoint_id})
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def reconcile_unknown(self, task_id: str, checkpoint_id: str, outcome: str, evidence_ref: str, verifier_id: str | None=None) -> dict[str, Any]:
        """Reconcile an uncertain side effect without auto-completing the task."""
        normalized = str(outcome or "").strip().upper()
        if normalized in {"PARTIAL", "CONFLICT"}:
            if not evidence_ref or not str(evidence_ref).strip():
                raise KernelError("reconcile evidence is required")
            if not verifier_id or not str(verifier_id).strip():
                raise KernelError(f"{normalized} reconciliation requires verifier")
            _assert_checkpoint_safe({"evidence_ref": evidence_ref, "verifier_id": verifier_id})
            self._begin()
            try:
                task = self._task(task_id)
                checkpoint = self._load_reconcile_checkpoint(task_id, checkpoint_id)
                if task["state"] != "RECONCILING":
                    raise InvalidTransition(f"{task['state']}->reconcile_outcome")
                idem = self.conn.execute(
                    "SELECT * FROM idempotency WHERE logical_key=?",
                    (checkpoint["idempotency_key"],),
                ).fetchone()
                if not idem:
                    raise KernelError("reconcile idempotency key not found")
                if idem["status"] != "CLAIMED":
                    raise KernelError("reconcile idempotency status is not CLAIMED")

                status = f"RECONCILED_{normalized}"
                event_type = f"RECONCILE_{normalized}"
                cur_idem_version = int(idem["version"]) if "version" in idem.keys() else 1
                cur_idem = self.conn.execute(
                    "UPDATE idempotency SET status=?,result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED' AND version=?",
                    (status, evidence_ref, checkpoint["idempotency_key"], cur_idem_version),
                )
                if cur_idem.rowcount != 1:
                    raise OptimisticLockError(
                        f"concurrency conflict reconciling idempotency key {checkpoint['idempotency_key']}",
                        table="idempotency",
                        entity_id=checkpoint["idempotency_key"],
                        expected_version=cur_idem_version,
                    )
                cur = self.conn.execute(
                    "UPDATE tasks SET state='HUMAN_REVIEW',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                    (now_iso(), task_id, task["version"]),
                )
                if cur.rowcount != 1:
                    raise StaleLease(f"concurrency conflict reconciling task {task_id}")
                active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (task_id,)).fetchall()
                if active_leases:
                    self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (task_id,))
                    for _ in active_leases:
                        self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
                if hasattr(self, '_bound_leases'):
                    self._bound_leases.pop(task_id, None)
                self._append_event(
                    task_id,
                    event_type,
                    task["state"],
                    "HUMAN_REVIEW",
                    str(verifier_id),
                    "reconcile_outcome_recorded",
                    {
                        "checkpoint_id": checkpoint_id,
                        "outcome": normalized,
                        "evidence_ref": evidence_ref,
                        "verifier_id": verifier_id,
                        "safe_to_retry": False,
                    },
                )
                self._commit()
                return self.get_task(task_id)
            except Exception:
                self._rollback()
                raise
        if outcome not in {'NOT_APPLIED', 'APPLIED', 'UNKNOWN'}:
            raise KernelError('invalid reconcile outcome')
        if not evidence_ref or not str(evidence_ref).strip():
            raise KernelError('reconcile evidence is required')
        if outcome in {'APPLIED', 'UNKNOWN'} and (not verifier_id):
            raise KernelError('reconcile verifier is required')
        _assert_checkpoint_safe({'evidence_ref': evidence_ref, 'verifier_id': verifier_id})
        self._begin()
        try:
            task = self._task(task_id)
            checkpoint = self._load_reconcile_checkpoint(task_id, checkpoint_id)
            if task['state'] != 'RECONCILING':
                raise InvalidTransition(f"{task['state']}->reconcile_outcome")
            idem = self.conn.execute('SELECT * FROM idempotency WHERE logical_key=?', (checkpoint['idempotency_key'],)).fetchone()
            if not idem:
                raise KernelError('reconcile idempotency key not found')
            old_state = task['state']
            idem_version = int(idem['version']) if 'version' in idem.keys() else 1
            if outcome == 'NOT_APPLIED':
                if idem['status'] != 'CLAIMED':
                    raise KernelError('reconcile idempotency status is not CLAIMED')
                cur_idem = self.conn.execute("UPDATE idempotency SET status='RETRYABLE',result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED' AND version=?", (evidence_ref, checkpoint['idempotency_key'], idem_version))
                if cur_idem.rowcount != 1:
                    raise OptimisticLockError(f"concurrency conflict reconciling idempotency key {checkpoint['idempotency_key']}", table="idempotency", entity_id=checkpoint['idempotency_key'], expected_version=idem_version)
                next_state = 'QUEUED'
                event_type = 'RECONCILE_NOT_APPLIED'
            elif outcome == 'APPLIED':
                cur_idem = self.conn.execute("UPDATE idempotency SET status='RECONCILED_APPLIED',result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED' AND version=?", (evidence_ref, checkpoint['idempotency_key'], idem_version))
                if cur_idem.rowcount != 1:
                    raise OptimisticLockError(f"concurrency conflict reconciling idempotency key {checkpoint['idempotency_key']}", table="idempotency", entity_id=checkpoint['idempotency_key'], expected_version=idem_version)
                if self.autonomous_mode and evidence_ref:
                    next_state = 'QUEUED'
                    event_type = 'RECONCILE_APPLIED_AUTONOMOUS'
                else:
                    next_state = 'HUMAN_REVIEW'
                    event_type = 'RECONCILE_APPLIED'
            else:
                cur_idem = self.conn.execute("UPDATE idempotency SET status='RECONCILED_UNKNOWN',result_ref=?,version=version+1 WHERE logical_key=? AND status='CLAIMED' AND version=?", (evidence_ref, checkpoint['idempotency_key'], idem_version))
                if cur_idem.rowcount != 1:
                    raise OptimisticLockError(f"concurrency conflict reconciling idempotency key {checkpoint['idempotency_key']}", table="idempotency", entity_id=checkpoint['idempotency_key'], expected_version=idem_version)
                next_state = 'HUMAN_REVIEW'
                event_type = 'RECONCILE_UNKNOWN'
            cur = self.conn.execute('UPDATE tasks SET state=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?', (next_state, now_iso(), task_id, task['version']))
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict reconciling task {task_id}")
            active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (task_id,)).fetchall()
            if active_leases:
                self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (task_id,))
                for _ in active_leases:
                    self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
            if hasattr(self, '_bound_leases'):
                self._bound_leases.pop(task_id, None)
            self._append_event(task_id, event_type, old_state, next_state, verifier_id or 'provider-state-reader', 'reconcile_outcome_recorded', {'checkpoint_id': checkpoint_id, 'outcome': outcome, 'evidence_ref': evidence_ref, 'verifier_id': verifier_id})
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def validate_checkpoint(self, checkpoint_id: str, planned_action: Any) -> dict[str, Any]:
        row = self.conn.execute('SELECT * FROM checkpoints WHERE checkpoint_id=?', (checkpoint_id,)).fetchone()
        if not row:
            raise CheckpointCorrupt(checkpoint_id)
        if row['planned_action_hash'] != stable_hash(planned_action):
            raise CheckpointCorrupt('planned action hash mismatch')
        try:
            tool_result = json.loads(row['tool_result_json']) if row['tool_result_json'] is not None else None
        except (TypeError, ValueError) as exc:
            raise CheckpointCorrupt('checkpoint tool result is not valid JSON') from exc
        payload = {'task_id': row['task_id'], 'attempt_id': row['attempt_id'], 'step_id': row['step_id'], 'state': row['state'], 'planned_action': planned_action, 'capability_epoch': row['capability_epoch'], 'idempotency_key': row['idempotency_key'], 'pre_observation_ref': row['pre_observation_ref'], 'post_observation_ref': row['post_observation_ref'], 'tool_result': tool_result, 'verifier_verdict': row['verifier_verdict']}
        if row['payload_hash'] != stable_hash(payload):
            raise CheckpointCorrupt('checkpoint payload hash mismatch')
        return dict(row)

    def idempotency_claim(
        self,
        task_id: str,
        step_id: str,
        action_type: str,
        resource_identity: str,
        expected_version: int | None = None,
    ) -> tuple[str, bool]:
        return self._idempotency.claim(task_id, step_id, action_type, resource_identity, expected_version)

    def idempotency_complete(
        self,
        logical_key: str,
        result_ref: str,
        expected_version: int | None = None,
    ) -> None:
        return self._idempotency.complete(logical_key, result_ref, expected_version)

    def idempotency_status(self, logical_key: str) -> dict[str, Any]:
        return self._idempotency.status(logical_key)

    def commit_verification_result(self, task_id: str, lease_id: str, verification_result: Any) -> dict[str, Any]:
        from scp.core.verifier_receipt import (
            InvalidReceiptSignatureError,
            VerifierReceipt,
            verify_verifier_receipt,
        )

        if not task_id or not str(task_id).strip():
            raise KernelError("task_id is required")
        if not lease_id or not str(lease_id).strip():
            raise KernelError("lease_id is required")

        self._assert_lease(lease_id, task_id)
        is_system = getattr(self, "_system_authority", False)
        bound = getattr(self, "_bound_leases", {}).get(task_id)
        if not is_system:
            if not bound:
                raise StaleLease(f"kernel instance does not possess active lease authority to complete task {task_id}")
            if bound != lease_id:
                raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")

        task = self._task(task_id)
        if task['state'] != 'VERIFYING':
            raise InvalidTransition(f"{task['state']}->COMPLETED")

        if not isinstance(verification_result, (VerifierReceipt, dict)):
            raise InvalidReceiptSignatureError("verification_result must be a VerifierReceipt or dict (R3/FA-04)")

        verify_verifier_receipt(verification_result, task_id=task_id)
        return self.commit_completed(task_id, lease_id, receipt=verification_result)

    def commit_completed(
        self,
        task_id: str,
        lease_id: str,
        verifier_verdict: Any = 'VERIFIED',
        evidence_ref: str | None = None,
        *,
        receipt: Any = None,
    ) -> dict[str, Any]:
        from scp.core.verifier_receipt import (
            VerifierReceipt,
            verify_verifier_receipt,
        )

        if receipt is None and isinstance(verifier_verdict, (VerifierReceipt, dict)):
            receipt = verifier_verdict

        if receipt is not None:
            verify_verifier_receipt(receipt, task_id=task_id)
            if hasattr(receipt, "verifier_id"):
                actual_verifier_id = receipt.verifier_id
                actual_evidence_ref = receipt.evidence_ref
                actual_verdict = receipt.verdict
                sig = receipt.signature
                issued_at = receipt.issued_at
            else:
                actual_verifier_id = str(receipt.get("verifier_id", "")).strip()
                actual_evidence_ref = str(receipt.get("evidence_ref", "")).strip()
                actual_verdict = str(receipt.get("verdict", "")).strip()
                sig = str(receipt.get("signature", "")).strip()
                issued_at = float(receipt.get("issued_at", 0.0))
            signature_digest = f"sha256:{sig[:16]}..." if sig else None
        else:
            if verifier_verdict != 'VERIFIED' or not evidence_ref:
                raise KernelError('completion requires independent VERIFIED verdict and evidence')
            actual_verifier_id = 'verifier'
            actual_evidence_ref = str(evidence_ref).strip()
            actual_verdict = 'VERIFIED'
            signature_digest = None
            issued_at = None

        self._begin()
        try:
            self._assert_lease(lease_id, task_id)
            task = self._task(task_id)
            if task['state'] != 'VERIFYING':
                raise InvalidTransition(f"{task['state']}->COMPLETED")
            if task['active_lease_id'] != lease_id:
                raise StaleLease(f"completion lease {lease_id} does not match active task lease {task['active_lease_id']}")
            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority to complete task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")
            old = task['state']
            cur = self.conn.execute("UPDATE tasks SET state='COMPLETED',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?", (now_iso(), task_id, task['version']))
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict completing task {task_id}")

            event_payload = {
                'evidence_ref': actual_evidence_ref,
                'verifier_verdict': actual_verdict,
                'lease_id': lease_id,
                'verifier_id': actual_verifier_id,
            }
            if signature_digest:
                event_payload['signature_digest'] = signature_digest
            if issued_at is not None:
                event_payload['issued_at'] = issued_at

            self._append_event(
                task_id,
                'TASK_COMPLETED',
                old,
                'COMPLETED',
                actual_verifier_id,
                'postcondition_verified',
                event_payload,
            )
            self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0', (lease_id,))
            self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
            if hasattr(self, '_bound_leases'):
                self._bound_leases.pop(task_id, None)
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def commit_approval(
        self,
        task_id: str,
        approval_token: Any,
        actor: str = "operator",
        details: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """Atomically commit an authenticated approval to transition WAITING_APPROVAL -> READY.

        Enforces:
        - Task existence and state == WAITING_APPROVAL.
        - Global kill switch check.
        - Strict cryptographic verification of approval_token (CapabilityToken or operator signature).
        - Scope authorization for 'approval:grant'.
        - OCC version check at database level.
        - Append-only event journaling ('TASK_APPROVED').
        - WAL disk durability commit.
        """
        from scp.core.capability_token import InvalidTokenSignatureError, get_capability_secret

        if not task_id or not str(task_id).strip():
            raise KernelError("task_id is required")
        if approval_token is None or approval_token == "":
            raise InvalidTokenSignatureError("approval_token is required")
        if isinstance(approval_token, str) and not approval_token.strip():
            raise InvalidTokenSignatureError("approval_token is required")
        if not actor or not str(actor).strip():
            raise KernelError("actor is required")

        self._begin()
        try:
            self._assert_not_killed()
            task = self._task(task_id)
            current_state = task["state"]

            if current_state in TERMINAL:
                raise InvalidTransition("terminal task is immutable")
            if current_state != "WAITING_APPROVAL":
                raise InvalidTransition(
                    f"task {task_id} in state '{current_state}' cannot be approved; task must be in WAITING_APPROVAL"
                )

            cur_version = int(task["version"])
            if expected_version is not None and cur_version != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict approving task {task_id}: expected version {expected_version}, found {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=expected_version,
                )

            # Cryptographic verification via capability secret
            secret = get_capability_secret()
            verification_meta = verify_approval_authority(approval_token, task_id, secret)

            # Atomic SQLite OCC Mutation
            now_str = now_iso()
            cur = self.conn.execute(
                "UPDATE tasks SET state='READY', version=version+1, updated_at=? WHERE task_id=? AND version=? AND state='WAITING_APPROVAL'",
                (now_str, task_id, cur_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict committing approval on task {task_id}: expected version {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=cur_version,
                )

            # Immutable Event Journaling
            event_payload = {
                "token_type": verification_meta["token_type"],
                "token_id": verification_meta["token_id"],
                "scope": verification_meta["scope"],
                "signature_digest": (
                    verification_meta["signature"][:16] + "..."
                    if verification_meta["signature"]
                    else ""
                ),
                "actor": actor,
                "details": details or {},
            }
            self._append_event(
                task_id,
                "TASK_APPROVED",
                "WAITING_APPROVAL",
                "READY",
                actor,
                "approval_granted",
                event_payload,
            )

            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def auto_resolve_human_review(
        self,
        task_id: str,
        reason: str = "autonomous_verification_passed",
    ) -> dict[str, Any]:
        """Atomically transition a task from HUMAN_REVIEW to READY in autonomous mode.

        Records an audit event 'AUTONOMOUS_HUMAN_REVIEW_RESOLVED' in the immutable journal.
        Precondition: task state must be 'HUMAN_REVIEW'.
        Postcondition: task state is 'READY', version incremented, active lease cleared.
        """
        if not getattr(self, "autonomous_mode", False):
            raise InvalidTransition("auto_resolve_human_review can only be called when autonomous_mode is enabled")
        if not task_id or not str(task_id).strip():
            raise KernelError("task_id is required")
        self._begin()
        try:
            task = self._task(task_id)
            if task["state"] != "HUMAN_REVIEW":
                raise InvalidTransition(
                    f"cannot auto-resolve task {task_id} in state {task['state']}; expected HUMAN_REVIEW"
                )
            cur_version = int(task["version"])
            cur = self.conn.execute(
                "UPDATE tasks SET state='READY',version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                (now_iso(), task_id, cur_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict auto-resolving human review on task {task_id}: expected version {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=cur_version,
                )
            self._append_event(
                task_id,
                "AUTONOMOUS_HUMAN_REVIEW_RESOLVED",
                "HUMAN_REVIEW",
                "READY",
                "kernel:autonomous",
                reason,
                {"task_id": task_id, "reason": reason, "resolved_at": now_iso()},
            )
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def fail_task_fail_closed(
        self,
        task_id: str,
        reason: str = "autonomous_fail_closed",
        error_payload: dict[str, Any] | None = None,
        actor: str = "kernel:autonomous",
    ) -> dict[str, Any]:
        """Atomically transition a non-terminal task to FAILED in autonomous mode (fail-closed).

        Releases any active leases, decrements active queue counter, and appends a TASK_FAILED event.
        """
        if not task_id or not str(task_id).strip():
            raise KernelError("task_id is required")
        self._begin()
        try:
            task = self._task(task_id)
            old_state = task["state"]
            if old_state in TERMINAL:
                self._rollback()
                return task
            if "FAILED" not in ALLOWED_TRANSITIONS.get(old_state, set()):
                raise InvalidTransition(f"cannot fail-closed from {old_state}->FAILED")
            cur_version = int(task["version"])
            cur = self.conn.execute(
                "UPDATE tasks SET state='FAILED',error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                (reason, now_iso(), task_id, cur_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict failing task {task_id}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=cur_version,
                )
            active_leases = self.conn.execute(
                "SELECT lease_id FROM leases WHERE task_id=? AND released=0",
                (task_id,),
            ).fetchall()
            if active_leases:
                self.conn.execute(
                    "UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0",
                    (task_id,),
                )
                for _ in active_leases:
                    self.conn.execute(
                        "UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?",
                        (task["owner"],),
                    )
            if hasattr(self, "_bound_leases"):
                self._bound_leases.pop(task_id, None)
            self._append_event(
                task_id,
                "TASK_FAILED",
                old_state,
                "FAILED",
                actor,
                reason,
                error_payload or {"error": reason},
            )
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def commit_failed(
        self,
        task_id: str,
        lease_id: str,
        actor: str,
        failure_classification: str,
        indictment_ref: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Commit an authenticated, verified failure or route to retry/recovery.

        Enforces:
        - Input validation: non-empty task_id, lease_id, actor, failure_classification, indictment_ref.
        - Strict lease validity and worker actor ownership matching.
        - Retry budget preservation: if failure is retryable and attempts < max_attempts,
          transitions to RETRY_SCHEDULED (or UNKNOWN); otherwise transitions to FAILED.
        - Atomic SQLite persistence: updates tasks, appends immutable journal event,
          releases lease, and decrements queue active count with OCC version checks.
        """
        if not task_id or not str(task_id).strip():
            raise KernelError("task_id is required")
        if not lease_id or not str(lease_id).strip():
            raise StaleLease("lease_id is required")
        if not actor or not str(actor).strip():
            raise KernelError("actor is required")
        if not failure_classification or not str(failure_classification).strip():
            raise KernelError("failure_classification is required")
        if not indictment_ref or not str(indictment_ref).strip():
            raise KernelError("indictment_ref is required; failure commitment requires verifiable failure evidence")

        self._begin()
        try:
            task = self._task(task_id)
            _lease = self._assert_lease(lease_id, task_id, actor=actor)  # [hygiene F841] giữ call _assert_lease (invariant gate), biến đổi _lease

            old_state = task["state"]
            if old_state in TERMINAL:
                raise InvalidTransition("terminal task is immutable")
            if old_state not in {"RUNNING", "WAITING_TOOL", "VERIFYING", "LEASED", "CHECKPOINTED", "UNKNOWN"}:
                raise InvalidTransition(f"{old_state}->commit_failed")
            if task["active_lease_id"] != lease_id:
                raise StaleLease(f"failure lease {lease_id} does not match active task lease {task['active_lease_id']}")

            is_system = getattr(self, "_system_authority", False)
            bound = getattr(self, "_bound_leases", {}).get(task_id)
            if not is_system:
                if not bound:
                    raise StaleLease(f"kernel instance does not possess active lease authority to fail task {task_id}")
                if bound != lease_id:
                    raise StaleLease(f"caller lease {lease_id} does not match bound instance lease {bound}")

            cur_version = int(task["version"])
            current_attempts = int(task["attempts"]) if ("attempts" in task.keys() and task["attempts"] is not None) else 0
            max_attempts = int(task["max_attempts"]) if ("max_attempts" in task.keys() and task["max_attempts"] is not None) else 3
            new_attempts = current_attempts + 1

            classification_upper = failure_classification.strip().upper()
            retryable_classes = {"RETRYABLE", "TRANSIENT", "TIMEOUT", "NETWORK_ERROR", "TEMPORARY"}
            uncertain_classes = {"UNKNOWN", "UNCERTAIN", "LOST_RESPONSE", "CRASH_AFTER_SUBMIT"}

            if classification_upper in uncertain_classes:
                target_state = "UNKNOWN"
                event_type = "TASK_UNKNOWN_STATE"
                reason = f"uncertain_state:{classification_upper.lower()}"
            elif (classification_upper in retryable_classes) and (new_attempts < max_attempts):
                target_state = "RETRY_SCHEDULED"
                event_type = "TASK_RETRY_SCHEDULED"
                reason = f"retryable_failure:{classification_upper.lower()}"
            else:
                target_state = "FAILED"
                event_type = "TASK_FAILED"
                reason = f"terminal_failure:{classification_upper.lower()}"

            # [Agent2 2026-09-29] Map authority: never journal an edge outside
            # ALLOWED_TRANSITIONS (rebuild_projection would inherit it blindly).
            # A rerouted decision keeps the caller's intent visible: the reason
            # carries the reroute and the payload keeps the planned target.
            planned_target = target_state
            target_state, reason = self._legal_or_nearest(old_state, target_state, reason)
            if target_state == "FAILED" and event_type != "TASK_FAILED":
                event_type = "TASK_FAILED"

            error_payload = {
                "classification": classification_upper,
                "indictment_ref": indictment_ref,
                "details": details or {},
                "attempts": new_attempts,
                "max_attempts": max_attempts,
                "planned_retry": planned_target if planned_target in {"RETRY_SCHEDULED", "UNKNOWN"} else None,
            }
            error_json = json.dumps(error_payload, ensure_ascii=False, sort_keys=True)

            cur = self.conn.execute(
                "UPDATE tasks SET state=?,attempts=?,error=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                (target_state, new_attempts, error_json, now_iso(), task_id, cur_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict failing task {task_id}: expected version {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=cur_version,
                )

            event_payload = {
                "lease_id": lease_id,
                "actor": actor,
                "failure_classification": classification_upper,
                "indictment_ref": indictment_ref,
                "details": details or {},
                "attempts": new_attempts,
                "max_attempts": max_attempts,
                # [Agent2 2026-09-29] reroute visibility in the journal
                "planned_retry": planned_target if planned_target in {"RETRY_SCHEDULED", "UNKNOWN"} else None,
            }
            self._append_event(
                task_id,
                event_type,
                old_state,
                target_state,
                actor,
                reason,
                payload=event_payload,
            )

            self.conn.execute(
                "UPDATE leases SET released=1,version=version+1 WHERE lease_id=? AND released=0",
                (lease_id,),
            )
            self.conn.execute(
                "UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?",
                (task["owner"],),
            )
            if hasattr(self, "_bound_leases"):
                self._bound_leases.pop(task_id, None)

            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def _legal_or_nearest(self, from_state: str, target: str, note: str) -> tuple[str, str]:
        """[Agent2 2026-09-29] Transition-map authority: raw-commit helpers
        (commit_failed / set_task_kill) must never journal an edge outside
        ALLOWED_TRANSITIONS. rebuild_projection replays the journal with no map
        validation, so one out-of-law edge poisons every projection rebuild and
        breaks the map contract (code must agree with the documented machine).

        If the requested target is illegal from from_state, reroute to the
        NEAREST LEGAL edge — but ONLY when ALLOWED_TRANSITIONS already contains
        such an edge for from_state; the reroute NEVER invents a new edge:

        - kills become FAILED where CANCELLED is illegal but FAILED is legal
          (fail-closed is the intent of a kill);
        - UNKNOWN-class failures become RECOVERING where RECOVERING is legal
          (RUNNING / LEASED / WAITING_TOOL / UNKNOWN);
        - planned RETRY_SCHEDULED is honoured by bookkeeping (attempts /
          planned_retry in the event payload) and committing FAILED now.

        When NO nearest legal edge exists, this RAISES InvalidTransition
        (fail-closed) instead of fabricating one.

        [SECOND-PASS DECISION 2026-09-30 — probe-verified reality] An
        UNKNOWN-class commit_failed from VERIFYING or CHECKPOINTED raises
        InvalidTransition here: those map entries carry no UNKNOWN/RECOVERING
        edge. This is intentional, not a bug. Caller census at 38562c26:
        adapter finalize sends only RETRYABLE/VERIFICATION_FAILED from
        VERIFYING (-> RETRY_SCHEDULED/FAILED), adapter fail() and the hands
        bridge send FATAL from RUNNING/VERIFYING (-> FAILED) — no runtime
        caller sends the raising shape. Widening the machine (e.g. adding
        VERIFYING->RECOVERING or a reroute to HUMAN_REVIEW) would change
        documented state-machine behavior WITHOUT evidence, so the docstring
        was fixed to match the code instead. If a caller that produces this
        shape ever appears, the fix is a map change through the
        transition-map-authority process (or an explicit caller-side reroute
        to a legal target such as HUMAN_REVIEW) — never a silent edge
        invention here.

        Returns (final_state, reason_note); the reroute is always recorded in
        the journal event reason so audits can see it.
        """
        if target in ALLOWED_TRANSITIONS.get(from_state, set()):
            return target, note
        if target == "CANCELLED" and "FAILED" in ALLOWED_TRANSITIONS.get(from_state, set()):
            return "FAILED", f"{note}:kill_reroute:{from_state}->FAILED"
        if target == "UNKNOWN" and "RECOVERING" in ALLOWED_TRANSITIONS.get(from_state, set()):
            return "RECOVERING", f"{note}:transition_reroute:{from_state}->RECOVERING"
        if target == "RETRY_SCHEDULED" and "FAILED" in ALLOWED_TRANSITIONS.get(from_state, set()):
            return "FAILED", f"{note}:transition_reroute:{from_state}->FAILED(planned_retry={target})"
        raise InvalidTransition(f"{from_state}->{target}")

    def set_global_kill(self, active: bool, actor: str='operator') -> int:
        self._begin()
        try:
            c = self._control()
            epoch = int(c['global_kill_epoch']) + (1 if active else 0)
            self.conn.execute('UPDATE control SET global_kill=?,global_kill_epoch=? WHERE id=1', (1 if active else 0, epoch))
            self._append_event('__global__', 'GLOBAL_KILL_ON' if active else 'GLOBAL_KILL_OFF', None, None, actor, 'operator_toggle', {'epoch': epoch})
            self._commit()
            return epoch
        except Exception:
            self._rollback()
            raise

    def set_task_kill(self, task_id: str, actor: str='operator') -> dict[str, Any]:
        self._begin()
        try:
            task = self._task(task_id)
            if task['state'] in TERMINAL:
                raise InvalidTransition('terminal task is immutable')
            active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (task_id,)).fetchall()
            # [Agent2 2026-09-29] Map authority: a kill from a state whose map
            # entry lacks CANCELLED (VERIFYING/RECOVERING) must not journal an
            # out-of-law edge; fail-closed reroute to FAILED keeps the kill
            # effective and the journal legal.
            kill_target, kill_reason = self._legal_or_nearest(
                task['state'], 'CANCELLED', 'task_kill'
            )
            cur = self.conn.execute(
                "UPDATE tasks SET state=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?",
                (kill_target, now_iso(), task_id, task['version']),
            )
            if cur.rowcount != 1:
                raise StaleLease(f"concurrency conflict cancelling task {task_id}")
            self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (task_id,))
            for _ in active_leases:
                self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task['owner'],))
            self._append_event(task_id, 'TASK_KILLED', task['state'], kill_target, actor, kill_reason, {})
            if hasattr(self, '_bound_leases'):
                self._bound_leases.pop(task_id, None)
            self._commit()
            return self.get_task(task_id)
        except Exception:
            self._rollback()
            raise

    def cancel(self, task_id: str, actor: str = 'operator') -> dict[str, Any]:
        """Cancel a task atomically with lease release and queue decrement (alias of set_task_kill)."""
        return self.set_task_kill(task_id, actor=actor)

    def auto_reconcile_orphans(self, actor: str='kernel_watchdog', stale_seconds: float=60.0, now: float | None=None) -> list[str]:
        """Tự động rà soát các task bị mồ côi (chết do crash, mất kết nối) và đưa vào RECONCILING.

        [P1 FIX 2026-09-05] Watchdog phải tôn trọng lease authority:
        - Gate trên lease còn hạn (leases.expires_at do heartbeat refresh cùng
          heartbeat_at), KHÔNG gate trên tasks.updated_at — worker sống có thể
          ở lại RUNNING lâu mà không đổi state; heartbeat không đụng vào
          tasks.updated_at nên cờ cũ từng bắt worker hợp lệ thành mồ côi.
        - Chuyển state chỉ qua ALLOWED_TRANSITIONS + version increment
          (LEASED/RUNNING -> RECOVERING -> RECONCILING); cựu bản ghi raw
          'UPDATE ... state=UNKNOWN' từng ghi transition ngoài luật vào journal.
        """
        orphans: list[str] = []
        now = time.time() if now is None else float(now)
        cutoff = int(now - float(stale_seconds))
        try:
            self._begin()
            rows = self.conn.execute(
                "SELECT task_id, state FROM tasks "
                "WHERE state IN ('LEASED', 'RUNNING', 'WAITING_TOOL') "
                "AND CAST(strftime('%s', updated_at) AS INTEGER) < ?",
                (cutoff,),
            ).fetchall()
            for r in rows:
                tid = r['task_id']
                # Lease authority gate: an unreleased lease with expires_at in
                # the future still belongs to a live worker (heartbeat refreshes
                # heartbeat_at/expires_at together) — the watchdog must not
                # hijack it, fail-closed instead.
                lease = self.conn.execute(
                    'SELECT * FROM leases WHERE task_id=? AND released=0 ORDER BY fencing_token DESC LIMIT 1',
                    (tid,),
                ).fetchone()
                if lease is not None and float(lease['expires_at']) > now:
                    continue
                task = self._task(tid)
                # LOST_RESPONSE with action_dispatched=True is the fail-closed
                # assumption for an orphan: route through the reconcile path.
                decision = self.recovery_decision('LOST_RESPONSE', True, 'UNKNOWN')
                plan = [('RECOVERING', 'ORPHAN_TIMEOUT')]
                if decision.next_state == 'RECONCILING':
                    plan.append(('RECONCILING', 'AUTO_RECONCILE_INITIATED'))
                payload = {
                    'lease_id': lease['lease_id'] if lease is not None else None,
                    'heartbeat_at': float(lease['heartbeat_at']) if lease is not None else None,
                    'expires_at': float(lease['expires_at']) if lease is not None else None,
                    'watchdog_now': now,
                    'stale_seconds': float(stale_seconds),
                }
                current = task['state']
                cur_version = task['version']
                moved = False
                for target, reason in plan:
                    # Never write a transition outside the map (no free-form state).
                    if target not in ALLOWED_TRANSITIONS.get(current, set()):
                        break
                    cur = self.conn.execute(
                        'UPDATE tasks SET state=?,version=version+1,active_lease_id=NULL,active_fencing_token=0,updated_at=? WHERE task_id=? AND version=?',
                        (target, now_iso(), tid, cur_version),
                    )
                    if cur.rowcount != 1:
                        break
                    cur_version += 1
                    self._append_event(tid, 'STATE_TRANSITION', current, target, actor, reason, dict(payload))
                    current = target
                    moved = True
                if not moved:
                    continue
                active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (tid,)).fetchall()
                if active_leases:
                    self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (tid,))
                    for _ in active_leases:
                        self.conn.execute(
                            'UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?',
                            (task['owner'],),
                        )
                if hasattr(self, '_bound_leases'):
                    self._bound_leases.pop(tid, None)
                orphans.append(tid)
            self._commit()
        except Exception:
            self._rollback()
            raise
        return orphans

    def verify_integrity(self) -> dict[str, Any]:
        """[C3 — Gemini indictment: SQLite SPOF] Kiểm tra sức khoẻ DB.

        PRAGMA quick_check + verify hash-chain toàn bộ journal. KHÔNG tự sửa
        gì — chỉ báo cáo (fail-closed với bằng chứng). Đây là durability
        single-node; HA đa node (Raft/etcd) là kiến trúc khác, không claim."""
        quick = self.conn.execute('PRAGMA quick_check').fetchone()[0]
        chains = {'checked': 0, 'invalid': []}
        for row in self.conn.execute('SELECT DISTINCT task_id FROM events').fetchall():
            chains['checked'] += 1
            result = self.verify_journal(row['task_id'])
            if not result['hash_chain_valid']:
                chains['invalid'].append({'task_id': row['task_id'], 'errors': result['errors'][:3]})
        return {'quick_check': quick, 'tasks': chains['checked'], 'invalid_chains': chains['invalid']}

    def backup(self, backup_dir: str | Path, retain: int=7) -> dict[str, Any]:
        """Online backup qua sqlite3 backup API (an toàn khi đang chạy WAL) +
        prune giữ lại `retain` bản mới nhất. Đây là giảm thiểu thiệt hại khi
        hỏng sector — KHÔNG phải High Availability đa node."""
        import time as _time
        dest = Path(backup_dir)
        dest.mkdir(parents=True, exist_ok=True)
        import uuid
        stamp = f"{_time.strftime('%Y%m%d-%H%M%S')}-{_time.time_ns() % 10 ** 9:09d}-{uuid.uuid4().hex[:6]}"
        target = dest / f'kernel-backup-{stamp}.sqlite3'
        self._storage.backup_to(target)
        backups = sorted(dest.glob('kernel-backup-*.sqlite3'))
        pruned = 0
        for old in backups[:max(0, len(backups) - int(retain))]:
            old.unlink(missing_ok=True)
            pruned += 1
        return {'backup': str(target), 'size_bytes': target.stat().st_size, 'pruned': pruned, 'retained': len(backups) - pruned}

    def recover_on_boot(self, actor: str='boot_recovery') -> dict[str, Any]:
        """[Cổng F — Event-Sourcing Crash Recovery] Máy tự replay journal.

        Audit Cổng F/C: TraceLedger từng chỉ là immutable log cho NGƯỜI đọc.
        Hàm này biến journal thành replay engine: lúc boot, mọi task non-
        terminal được dựng lại state từ journal (hash-chain được verify
        trước), rồi đưa về trạng thái an toàn theo luật chuyển đổi:

          LEASED/WAITING_TOOL -> RECOVERING (đuợc ALLOWED_TRANSITIONS cho phép)
          RUNNING/VERIFYING   -> HUMAN_REVIEW
          CHECKPOINTED        -> QUEUED (resume được)
          UNKNOWN/RECONCILING/... -> giữ nguyên + báo cáo (cần luồng reconcile)

        Fail-closed tuyệt đối: journal hash-chain HỎNG → KHÔNG tự sửa, chỉ
        báo cáo corrupted (nhẹ tay với bằng chứng hơn là tiện tay "khắc phục").
        """
        report: dict[str, Any] = {'recovered': [], 'corrupted': [], 'left_as_is': []}
        self._system_authority = True
        try:
            rows = self.conn.execute('SELECT task_id, state FROM tasks').fetchall()
            for row in rows:
                task_id, state = (row['task_id'], row['state'])
                journal = self.verify_journal(task_id)
                if not journal['hash_chain_valid']:
                    report['corrupted'].append({'task_id': task_id, 'errors': journal['errors'][:5]})
                    continue
                if state in TERMINAL:
                    continue
                self.rebuild_projection(task_id)
                task_row = self._task(task_id)
                current = task_row['state']
                active_leases = self.conn.execute('SELECT lease_id FROM leases WHERE task_id=? AND released=0', (task_id,)).fetchall()
                if active_leases:
                    self.conn.execute('UPDATE leases SET released=1,version=version+1 WHERE task_id=? AND released=0', (task_id,))
                    for _ in active_leases:
                        self.conn.execute('UPDATE queue_accounts SET active=CASE WHEN active>0 THEN active-1 ELSE 0 END,version=version+1 WHERE owner=?', (task_row['owner'],))
                if current == 'RUNNING' or current == 'VERIFYING':
                    self.transition(task_id, 'HUMAN_REVIEW', actor=actor, reason='boot_recovery_in_flight')
                    report['recovered'].append({'task_id': task_id, 'from': current, 'to': 'HUMAN_REVIEW'})
                elif current in {'LEASED', 'WAITING_TOOL'}:
                    self.transition(task_id, 'RECOVERING', actor=actor, reason='boot_recovery_in_flight')
                    report['recovered'].append({'task_id': task_id, 'from': current, 'to': 'RECOVERING'})
                elif current == 'CHECKPOINTED':
                    self.transition(task_id, 'QUEUED', actor=actor, reason='boot_recovery_resume')
                    report['recovered'].append({'task_id': task_id, 'from': current, 'to': 'QUEUED'})
                else:
                    report['left_as_is'].append({'task_id': task_id, 'state': current})
            return report
        finally:
            self._system_authority = False

    def in_flight_count(self) -> int:
        """[CHAIN-AUDIT: backpressure] Số task chưa tới quyết định cuối —
        dùng làm admission control chống ngập kernel dưới tải đồng thời.

        [FIX 2026-09-29] HUMAN_REVIEW là trạng thái ĐÃ CÓ quyết định (answer
        withheld, chờ human flow) — chính adapter tôn trọng điều đó qua
        ``_duplicate_is_reaskable`` (dedupe chỉ chặn task thật sự đang chạy),
        nhưng bộ đếm admission lại tính HUMAN_REVIEW là in-flight. 200 task
        withheld tích lũy từ 09-21 đã bóp nghẹt mọi /ask mới (observed:
        audit 20260929, ask bị chặn 'backpressure ... at cap 200' vĩnh viễn
        dù load hiện tại = 0). Admission control phải đếm như dedupe:
        loại cả TERMINAL lẫn HUMAN_REVIEW; nếu cần đếm review backlog,
        dùng pending_review_count().
        """
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM tasks "
            "WHERE state NOT IN ('COMPLETED','FAILED','CANCELLED','HUMAN_REVIEW')"
        ).fetchone()
        return int(row['n'])

    def pending_review_count(self) -> int:
        """Số task HUMAN_REVIEW chờ human flow — telemetry, không dùng để
        chặn intake (HUMAN_REVIEW đã là quyết định fail-closed recorded)."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM tasks WHERE state = 'HUMAN_REVIEW'").fetchone()
        return int(row['n'])

    def get_task(self, task_id: str) -> dict[str, Any]:
        return dict(self._task(task_id))

    def get_events(self, task_id: str) -> list[dict[str, Any]]:
        return [dict(x) for x in self.conn.execute('SELECT * FROM events WHERE task_id=? ORDER BY seq', (task_id,)).fetchall()]

    def get_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        row = self.conn.execute('SELECT * FROM checkpoints WHERE checkpoint_id=?', (checkpoint_id,)).fetchone()
        if not row:
            raise CheckpointCorrupt(checkpoint_id)
        return dict(row)

    def verify_journal(self, task_id: str) -> dict[str, Any]:
        events = self.get_events(task_id)
        prev = None
        errors = []
        for i, e in enumerate(events, 1):
            if e['seq'] != i:
                errors.append(f"sequence:{e['seq']} expected {i}")
            if e['prev_event_hash'] != prev:
                errors.append(f"prev_hash:{e['seq']}")
            try:
                payload = json.loads(e['payload_json'])
            except (TypeError, ValueError):
                errors.append(f"payload_json:{e['seq']}")
                prev = e['event_hash']
                continue
            body = {'event_id': e['event_id'], 'task_id': e['task_id'], 'seq': e['seq'], 'type': e['type'], 'from_state': e['from_state'], 'to_state': e['to_state'], 'actor': e['actor'], 'reason': e['reason'], 'payload': payload, 'policy_hash': e['policy_hash'], 'prev_event_hash': e['prev_event_hash']}
            if stable_hash(body) != e['event_hash']:
                errors.append(f"event_hash:{e['seq']}")
            prev = e['event_hash']
        return {'task_id': task_id, 'event_count': len(events), 'hash_chain_valid': not errors, 'errors': errors}

    def rebuild_projection(self, task_id: str, expected_version: int | None = None) -> dict[str, Any]:
        self._begin()
        try:
            journal = self.verify_journal(task_id)
            if not journal['hash_chain_valid']:
                details = ';'.join(journal['errors'])
                raise KernelError(f'journal integrity invalid: {details}')
            events = self.get_events(task_id)
            if not events:
                raise NotFound(task_id)
            state = events[0]['to_state']
            for event in events[1:]:
                if event['to_state']:
                    state = event['to_state']
            task = self._task(task_id)
            cur_version = int(task['version'])
            if expected_version is not None and cur_version != expected_version:
                raise OptimisticLockError(
                    f"concurrency conflict rebuilding projection for task {task_id}: expected version {expected_version}, found {cur_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=expected_version,
                )
            target_version = expected_version if expected_version is not None else cur_version
            if state in {"LEASED", "RUNNING", "WAITING_TOOL", "VERIFYING", "CHECKPOINTED", "UNKNOWN"}:
                lease_row = self.conn.execute(
                    'SELECT lease_id, fencing_token FROM leases WHERE task_id=? AND released=0 ORDER BY fencing_token DESC LIMIT 1',
                    (task_id,),
                ).fetchone()
                active_lease_id = lease_row['lease_id'] if lease_row else None
                active_fencing_token = int(lease_row['fencing_token']) if lease_row else 0
            else:
                active_lease_id = None
                active_fencing_token = 0
            cur = self.conn.execute(
                'UPDATE tasks SET state=?,version=version+1,active_lease_id=?,active_fencing_token=?,updated_at=? WHERE task_id=? AND version=?',
                (state, active_lease_id, active_fencing_token, now_iso(), task_id, target_version),
            )
            if cur.rowcount != 1:
                raise OptimisticLockError(
                    f"concurrency conflict rebuilding projection for task {task_id}: expected version {target_version}",
                    table="tasks",
                    entity_id=task_id,
                    expected_version=target_version,
                )
            self._commit()
        except Exception:
            self._rollback()
            raise
        return self.get_task(task_id)

    @staticmethod
    def recovery_decision(reason: str, action_dispatched: bool=False, side_effect_risk: str='R0') -> RecoveryDecision:
        if action_dispatched or reason in {'TOOL_UNKNOWN_STATE', 'LOST_RESPONSE', 'WORKER_CRASH_AFTER_SUBMIT'}:
            return RecoveryDecision('RECONCILE', 'ACTION_DISPATCHED_WITHOUT_RESULT', False, ('provider_request_status', 'read_only_state'), 'RECONCILING', 'human_review_if_unknown')
        if reason in {'PROVIDER_TIMEOUT', 'DEPENDENCY_NOT_READY', 'TRANSIENT_NETWORK'} and side_effect_risk in {'R0', 'R1'}:
            return RecoveryDecision('RETRY', 'TRANSIENT_FAILURE', True, (), 'QUEUED', 'bounded_backoff')
        if reason in {'POLICY_DENIED', 'INVALID_CAPABILITY', 'CHECKPOINT_CORRUPT'}:
            return RecoveryDecision('STOP', 'NON_RETRYABLE_POLICY_OR_INTEGRITY_FAILURE', False, (), 'FAILED', 'none')
        return RecoveryDecision('REVIEW', 'INSUFFICIENT_STATE_EVIDENCE', False, ('last_checkpoint', 'event_journal'), 'HUMAN_REVIEW', 'human_required')
