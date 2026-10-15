"""Out-of-loop deterministic AutoFix worker.

This worker has no LLM/provider path. It claims bounded jobs from a private
SQLite queue, builds an AST-aware candidate, evaluates the constitutional
policy gate, applies atomically, verifies, records a rollback token and writes
the forensic audit entry. Any uncertainty becomes a non-applied terminal
state; it is never converted into a successful fix.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scp.autofix.audit_log import compute_hashes, write_audit_entry
from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.deterministic_patches import PatchCandidate, build_candidate, candidate_patch_text
from scp.autofix.engine_extensions import RollbackTokenRegistry
from scp.autofix.policy_gate import ImmutableAuditLog, PolicyFix, PolicyGate

logger = logging.getLogger("scp.autofix.deterministic_worker")

TERMINAL_STATES = {"applied", "rejected", "rolled_back", "failed", "expired", "cancelled"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _sandbox_enabled() -> bool:
    """[C3] Opt-in flag đọc từ env SCP_SANDBOX_EVALUATOR (lazy import giữ
    nguyên import surface của worker). Default (env off) = behavior cũ."""
    from scp.sandbox_evaluator.evaluator import sandbox_enabled

    return sandbox_enabled()


@dataclass(frozen=True)
class WorkerConfig:
    data_dir: Path
    allowed_root: Path
    max_jobs: int = 1
    max_retries: int = 2
    lease_seconds: int = 180
    job_timeout_seconds: int = 120
    max_files: int = 5
    auto_apply_risk: str = "low"
    require_baseline: bool = True
    require_tests: bool = False
    allow_network: bool = False
    allow_llm: bool = False
    poll_seconds: int = 30

    @classmethod
    def from_env(cls, *, data_dir: str | Path | None = None, allowed_root: str | Path | None = None) -> WorkerConfig:
        root = Path(allowed_root or os.environ.get("SCP_AUTOFIX_WORKER_ROOT") or Path.cwd()).resolve()
        runtime = Path(data_dir or os.environ.get("SCP_AUTOFIX_WORKER_DATA_DIR") or "data").resolve()
        risk = os.environ.get("SCP_AUTOFIX_WORKER_AUTO_APPLY_RISK", "low").strip().lower()
        if risk not in RISK_ORDER:
            risk = "low"
        return cls(
            data_dir=runtime,
            allowed_root=root,
            max_jobs=max(1, min(20, int(os.environ.get("SCP_AUTOFIX_WORKER_MAX_JOBS", "1")))),
            max_retries=max(0, min(5, int(os.environ.get("SCP_AUTOFIX_WORKER_MAX_RETRIES", "2")))),
            lease_seconds=max(30, min(3600, int(os.environ.get("SCP_AUTOFIX_WORKER_LEASE_SECONDS", "180")))),
            job_timeout_seconds=max(10, min(900, int(os.environ.get("SCP_AUTOFIX_WORKER_JOB_TIMEOUT_SECONDS", "120")))),
            max_files=max(1, min(100, int(os.environ.get("SCP_AUTOFIX_WORKER_MAX_FILES", "5")))),
            auto_apply_risk=risk,
            require_baseline=os.environ.get("SCP_AUTOFIX_WORKER_REQUIRE_BASELINE", "1") == "1",
            require_tests=os.environ.get("SCP_AUTOFIX_WORKER_REQUIRE_TESTS", "0") == "1",
            allow_network=False,
            allow_llm=False,
            poll_seconds=max(5, min(600, int(os.environ.get("SCP_AUTOFIX_WORKER_POLL_SECONDS", "30")))),
        )


class WorkerLedger:
    """SQLite queue plus append-only state transition ledger."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    job_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    lease_owner TEXT,
                    lease_until REAL,
                    result_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_worker_jobs_claim
                    ON worker_jobs(state, lease_until, created_at);
                CREATE TABLE IF NOT EXISTS worker_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _event(conn: sqlite3.Connection, job_id: str, old: str | None, new: str, reason: str, payload: dict[str, Any]) -> None:
        conn.execute(
            "INSERT INTO worker_events(job_id,ts,from_state,to_state,reason,payload_json) VALUES(?,?,?,?,?,?)",
            (job_id, time.time(), old, new, reason[:500], json.dumps(payload, ensure_ascii=False, default=str)),
        )

    def enqueue(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        finding_id = str(payload["finding_id"])
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT * FROM worker_jobs WHERE finding_id=?", (finding_id,)).fetchone()
            if existing:
                conn.execute("COMMIT")
                return dict(existing)
            job_id = str(payload.get("job_id") or uuid.uuid4())
            conn.execute(
                "INSERT INTO worker_jobs(job_id,finding_id,payload_json,state,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (job_id, finding_id, json.dumps(payload, ensure_ascii=False, default=str), "queued", now, now),
            )
            self._event(conn, job_id, None, "queued", "job_enqueued", payload)
            conn.execute("COMMIT")
            return dict(conn.execute("SELECT * FROM worker_jobs WHERE job_id=?", (job_id,)).fetchone())

    def claim(self, owner: str, lease_seconds: int, max_attempts: int = 3) -> dict[str, Any] | None:
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM worker_jobs WHERE (state='queued' OR (state='running' AND lease_until<?)) "
                "AND attempts < ? ORDER BY created_at LIMIT 1",
                (now, max(1, int(max_attempts))),
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            old_state = str(row["state"])
            attempts = int(row["attempts"]) + 1
            lease_until = now + lease_seconds
            conn.execute(
                "UPDATE worker_jobs SET state='running', attempts=?, lease_owner=?, lease_until=?, updated_at=? WHERE job_id=?",
                (attempts, owner, lease_until, now, row["job_id"]),
            )
            self._event(conn, row["job_id"], old_state, "running", "job_claimed", {"attempts": attempts, "lease_until": lease_until})
            conn.execute("COMMIT")
            return dict(conn.execute("SELECT * FROM worker_jobs WHERE job_id=?", (row["job_id"],)).fetchone())

    def transition(self, job_id: str, new_state: str, reason: str, result: dict[str, Any]) -> dict[str, Any]:
        if new_state not in TERMINAL_STATES | {"queued", "running", "candidate"}:
            raise ValueError(f"invalid worker state: {new_state}")
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT state FROM worker_jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                conn.execute("ROLLBACK")
                raise KeyError(job_id)
            old = str(row["state"])
            conn.execute(
                "UPDATE worker_jobs SET state=?, lease_owner=NULL, lease_until=NULL, result_json=?, updated_at=? WHERE job_id=?",
                (new_state, json.dumps(result, ensure_ascii=False, default=str), now, job_id),
            )
            self._event(conn, job_id, old, new_state, reason, result)
            conn.execute("COMMIT")
            return dict(conn.execute("SELECT * FROM worker_jobs WHERE job_id=?", (job_id,)).fetchone())

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM worker_jobs WHERE job_id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM worker_events WHERE job_id=? ORDER BY seq", (job_id,)).fetchall()
            return [dict(row) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT state, COUNT(*) AS n FROM worker_jobs GROUP BY state").fetchall()
            return {str(row["state"]): int(row["n"]) for row in rows}


class DeterministicWorker:
    def __init__(self, config: WorkerConfig | None = None):
        self.config = config or WorkerConfig.from_env()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = WorkerLedger(self.config.data_dir / "autofix_worker.sqlite")
        self.rollback = RollbackTokenRegistry(self.config.data_dir)
        self.policy_audit = ImmutableAuditLog(str(self.config.data_dir / "policy_gate_audit.jsonl"))
        self.policy = PolicyGate(audit_log=self.policy_audit)
        self.owner = f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        # [C3] Event bus (publish-side): False = chưa resolve, None = disabled,
        # PgEventBus = sẵn sàng. Gate verdict KHÔNG phụ thuộc bus (side-channel).
        self._eval_bus: Any = False

    @property
    def eval_event_bus(self):
        """[C3] Lazy PgEventBus cho EVAL_REQUEST/EVAL_RESULT publish-side.

        Fail-loudly, không fail gate: khi SCP_EVENT_BUS_ENABLED=1 nhưng DSN
        thiếu/broken, publish bị tắt với warning rõ ràng — verdict sandbox
        in-process vẫn là gate (known_gap: subscribe-loop chưa wire vào worker
        loop, xem reports/expert-panel/C3-sandbox-evaluator.md).
        """
        if self._eval_bus is False:
            self._eval_bus = None
            try:
                from scp.event_bus_pg import make_event_bus

                self._eval_bus = make_event_bus()
            except Exception as exc:
                logger.warning(
                    "deterministic worker: event bus unavailable — EVAL_REQUEST/"
                    "EVAL_RESULT publish disabled; sandbox gate unaffected: %s",
                    exc, exc_info=True,
                )
        return self._eval_bus

    def enqueue_bug(self, bug: BugReport, *, test_paths: list[str] | None = None) -> dict[str, Any]:
        path = str(Path(bug.file).resolve())
        source = Path(path).read_text(encoding="utf-8")
        source_hash = _sha(source)
        finding_id = hashlib.sha256(
            f"{path}|{source_hash}|{bug.line}|{bug.bug_type}".encode()
        ).hexdigest()
        payload = {
            "job_id": str(uuid.uuid4()),
            "finding_id": finding_id,
            "file": path,
            "line": int(bug.line),
            "bug_type": bug.bug_type,
            "description": bug.description,
            "suggested_fix": bug.suggested_fix or "",
            "tier": int(bug.tier),
            "is_restraint": bool(bug.is_restraint),
            "is_reversible": bool(bug.is_reversible),
            "affects_logic": bool(bug.affects_logic),
            "source_hash": source_hash,
            "created_at": time.time(),
            "expires_at": time.time() + self.config.job_timeout_seconds,
        }
        # [C3] Optional targeted tests for the SandboxEvaluator gate. Absent ->
        # sandbox gate has nothing to run -> fail-closed applies (see process_job).
        if test_paths:
            payload["test_paths"] = [str(tp) for tp in test_paths]
        return self.ledger.enqueue(payload)

    def _path_allowed(self, file_path: str) -> tuple[bool, str]:
        try:
            path = Path(file_path).resolve()
            if not path.is_relative_to(self.config.allowed_root):
                return False, f"path outside allowed root: {path}"
            from scp.autofix.runner_phases.ast_scan import _is_protected_path
            if _is_protected_path(str(path)):
                return False, f"protected path: {path}"
            return True, "path allowed"
        except Exception as exc:
            logger.debug(f"DeterministicWorker._path_allowed: exception ignored: {exc}", exc_info=True)
            return False, f"path check failed: {exc}"

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.autofix-", suffix=".tmp", dir=str(path.parent), text=True)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as tmp_err:
                # silent-by-design: secondary temp cleanup — the main write/replace already completed.
                logger.debug("deterministic_worker: temp-file cleanup failed for %s: %s", tmp, tmp_err, exc_info=True)
                pass

    @staticmethod
    def _sha256_file(path: Path) -> str:
        return _sha(path.read_text(encoding="utf-8"))

    def _decision_is_logged(self, audit_id: str) -> bool:
        try:
            if not self.policy_audit.log_file or not Path(self.policy_audit.log_file).exists():
                return False
            for line in Path(self.policy_audit.log_file).read_text(encoding="utf-8").splitlines()[-5:]:
                try:
                    if json.loads(line).get("audit_id") == audit_id:
                        return True
                except json.JSONDecodeError as line_err:
                    # silent-by-design: corrupt line -> "not logged" (False) keeps the
                    # decision-replay direction conservative; visible at debug level.
                    logger.debug("deterministic_worker: corrupt audit line, treating decision as unlogged: %s", line_err, exc_info=True)
                    return False
            return False
        except OSError as audit_err:
            # fail-loudly (S-B1b): the audit log being unreadable is an audit-path
            # failure; False means "decision unlogged" so it must be visible.
            logger.warning("deterministic_worker: audit log unreadable, treating decision as unlogged: %s", audit_err, exc_info=True)
            return False

    def _bug_from_payload(self, payload: dict[str, Any]) -> BugReport:
        return BugReport(
            file=str(payload["file"]),
            line=int(payload.get("line", 0)),
            bug_type=str(payload["bug_type"]),
            description=str(payload.get("description", "")),
            suggested_fix=str(payload.get("suggested_fix", "")),
            tier=BugTier(int(payload.get("tier", 1))),
            is_restraint=bool(payload.get("is_restraint", False)),
            is_reversible=bool(payload.get("is_reversible", True)),
            affects_logic=bool(payload.get("affects_logic", False)),
        )

    def _reject(self, job: dict[str, Any], reason: str, state: str = "rejected") -> dict[str, Any]:
        result = {"action": "rejected", "job_id": job["job_id"], "reason": reason, "llm_generated": False}
        self.ledger.transition(job["job_id"], state, reason, result)
        return result

    def _sandbox_evaluate(
        self, job: dict[str, Any], candidate: PatchCandidate, path: Path, test_paths: list[str]
    ):
        """[C3] SandboxEvaluator: chạy pytest THẬT trên bản sao workspace trong
        system temp (KHÔNG repo sống). PASS chỉ khi returncode == 0; timeout /
        setup lỗi -> FAIL (fail-closed, DNA #22: không chạy được ≠ đậu).

        Timeout bị chặn bởi job budget (job_timeout_seconds, evaluator clamp
        thêm về [5, 900]). Publish-side event seam chạy ngay trong method này
        (best-effort loud, không ảnh hưởng gate).
        """
        from scp.sandbox_evaluator.evaluator import build_patch_target, evaluate

        patch_target = build_patch_target(
            str(path),
            candidate.source_after,
            test_paths=test_paths,
            allowed_root=str(self.config.allowed_root),
            timeout_seconds=self.config.job_timeout_seconds,
            job_id=str(job["job_id"]),
        )
        # [C3] Publish-side event seam (SCP_EVENT_BUS_ENABLED=1): EVAL_REQUEST
        # tự-đủ cho evaluator service; EVAL_RESULT mang raw verdict in-process.
        # Best-effort loud: lỗi publish KHÔNG bao giờ đổi gate verdict.
        bus = self.eval_event_bus
        request_id = None
        if bus is not None:
            try:
                from scp.sandbox_evaluator.events import build_eval_request_payload

                request_payload = build_eval_request_payload(
                    patch_target, job_id=str(job["job_id"]), producer="deterministic_worker",
                )
                if request_payload is not None:
                    request_id = str(request_payload["request_id"])
                    bus.publish("scp_eval", request_payload, correlation_id=str(job["job_id"]))
            except Exception as exc:
                logger.warning(
                    "deterministic worker: EVAL_REQUEST publish failed (side-channel; "
                    "in-process sandbox gate unaffected): %s", exc, exc_info=True,
                )
        result = evaluate(patch_target)
        if bus is not None:
            try:
                from scp.sandbox_evaluator.events import build_eval_result_payload

                bus.publish(
                    "scp_eval",
                    build_eval_result_payload(
                        result, request_id=request_id, job_id=str(job["job_id"]),
                        evaluator="deterministic_worker-in-process",
                    ),
                    correlation_id=str(job["job_id"]),
                )
            except Exception as exc:
                logger.warning(
                    "deterministic worker: EVAL_RESULT publish failed (side-channel): %s",
                    exc, exc_info=True,
                )
        return result

    def process_job(self, job: dict[str, Any]) -> dict[str, Any]:
        payload = json.loads(job["payload_json"])
        if self.config.allow_llm:
            return self._reject(job, "worker invariant violation: allow_llm must remain false")
        if time.time() > float(payload.get("expires_at", 0) or 0):
            return self._reject(job, "job expired before claim", "expired")
        allowed, reason = self._path_allowed(str(payload["file"]))
        if not allowed:
            return self._reject(job, reason)
        path = Path(str(payload["file"])).resolve()
        if not path.exists() or not path.is_file():
            return self._reject(job, "target file missing")
        before = path.read_text(encoding="utf-8")
        before_hash = _sha(before)
        if self.config.require_baseline and before_hash != payload.get("source_hash"):
            return self._reject(job, "source hash changed since enqueue; refusing stale patch")
        bug = self._bug_from_payload(payload)
        candidate = build_candidate(bug)
        if candidate is None:
            return self._reject(job, "no deterministic recipe matched; no provider fallback")
        if candidate.source_hash_before != before_hash:
            return self._reject(job, "candidate source hash changed during processing")
        if RISK_ORDER[candidate.risk] > RISK_ORDER[self.config.auto_apply_risk]:
            result = {
                "action": "candidate",
                "job_id": job["job_id"],
                "patch_id": candidate.patch_id,
                "risk": candidate.risk,
                "reason": "candidate requires explicit risk policy/approval",
                "before_hash": before_hash,
                "after_hash": candidate.after_hash,
                "diff": candidate.diff[:12000],
                "llm_generated": False,
            }
            self.ledger.transition(job["job_id"], "candidate", result["reason"], result)
            return result

        # [C3] Opt-in SandboxEvaluator gate (env SCP_SANDBOX_EVALUATOR=1):
        # run REAL pytest on a temp-workspace copy of the patched file BEFORE
        # any apply — "autofix không tự chấm bài". Default (env off) keeps the
        # legacy behavior below unchanged.
        _sandbox_tests = [str(tp) for tp in (payload.get("test_paths") or []) if str(tp).strip()]
        if self.config.require_tests:
            if not (_sandbox_enabled() and _sandbox_tests):
                return self._reject(
                    job,
                    "require_tests=1 but no bounded targeted-test command is configured; refusing apply",
                )
        _sandbox_result = None
        if _sandbox_enabled() and _sandbox_tests:
            _sandbox_result = self._sandbox_evaluate(job, candidate, path, _sandbox_tests)
            if _sandbox_result.verdict != "PASS":
                result = {
                    "action": "rejected",
                    "job_id": job["job_id"],
                    "patch_id": candidate.patch_id,
                    "reason": (
                        f"sandbox evaluator gate: verdict={_sandbox_result.verdict} "
                        f"reason={_sandbox_result.reason or 'n/a'} "
                        f"returncode={_sandbox_result.returncode} (no apply)"
                    ),
                    "sandbox_eval": _sandbox_result.to_dict_bounded(),
                    "llm_generated": False,
                }
                self.ledger.transition(job["job_id"], "rejected", result["reason"], result)
                return result

        chain_ok, chain_reason = self.policy_audit.verify_chain()
        if not chain_ok:
            return self._reject(job, f"policy audit chain failed: {chain_reason}")
        policy_fix = PolicyFix(
            fix_id=str(payload["finding_id"]),
            patch=candidate_patch_text(candidate),
            patched_source=candidate.source_after,
            bug_file=str(path),
            bug_line=int(payload.get("line", 0)),
            scanner_name="deterministic_worker",
            extra={"patch_id": candidate.patch_id, "risk": candidate.risk},
        )
        decision = self.policy.evaluate_fix(policy_fix)
        if not self._decision_is_logged(decision.audit_id):
            return self._reject(job, "policy decision was not durably logged")
        if not decision.allowed or decision.severity == "BLOCK":
            return self._reject(job, f"policy gate blocked: {decision.reason}")
        try:
            ast.parse(candidate.source_after, filename=str(path))
        except SyntaxError as exc:
            return self._reject(job, f"candidate syntax invalid before write: {exc}")
        verified, verify_reason = candidate.verify_after(candidate.source_after)
        if not verified:
            return self._reject(job, f"candidate pre-write verification failed: {verify_reason}")

        token = self.rollback.register(
            file_path=str(path), before_content=before, after_content=candidate.source_after,
            patch=candidate.diff, bug_id=str(payload["finding_id"]), bug_type=bug.bug_type,
            tier=int(bug.tier), reality_test_result={"status": "pending", "worker": True},
        )
        try:
            self._atomic_write(path, candidate.source_after)
            after = path.read_text(encoding="utf-8")
            after_hash = _sha(after)
            if after_hash != candidate.after_hash:
                raise RuntimeError("after hash mismatch")
            ast.parse(after, filename=str(path))
            verified, verify_reason = candidate.verify_after(after)
            if not verified:
                raise RuntimeError(verify_reason)
            bh, ah = compute_hashes(before, after)
            audit_ok = write_audit_entry(
                log_path=self.config.data_dir / "autofix_audit.jsonl",
                finding_id=str(payload["finding_id"]), tier=int(bug.tier), action="fixed_deterministic",
                before_hash=bh, after_hash=ah, rollback_token=token,
                reality_test_result="pass", message=f"{candidate.patch_id}: {candidate.reason}",
                extra={
                    "job_id": job["job_id"], "patch_id": candidate.patch_id, "risk": candidate.risk, "llm_generated": False,
                    **({"sandbox_eval": _sandbox_result.to_dict_bounded()} if _sandbox_result is not None else {}),
                },
            )
            if not audit_ok:
                raise RuntimeError("forensic audit write failed after apply")
        except Exception as exc:
            logger.debug(f"DeterministicWorker.process_job: patch apply failed, entering rollback: {exc}", exc_info=True)
            try:
                self._atomic_write(path, before)
                rollback_ok = self._sha256_file(path) == before_hash
            except Exception as rollback_exc:
                rollback_ok = False
                logger.critical("worker rollback failed for %s: %s", path, rollback_exc, exc_info=True)
            result = {
                "action": "rolled_back" if rollback_ok else "failed",
                "job_id": job["job_id"],
                "patch_id": candidate.patch_id,
                "reason": str(exc),
                "rollback_ok": rollback_ok,
                "before_hash": before_hash,
                "after_hash": candidate.after_hash,
                "rollback_token": token,
                "llm_generated": False,
            }
            self.ledger.transition(job["job_id"], "rolled_back" if rollback_ok else "failed", str(exc), result)
            return result

        result = {
            "action": "fixed",
            "job_id": job["job_id"],
            "patch_id": candidate.patch_id,
            "risk": candidate.risk,
            "reason": candidate.reason,
            "before_hash": before_hash,
            "after_hash": candidate.after_hash,
            "rollback_token": token,
            "reality_test_result": "pass",
            "llm_generated": False,
        }
        if _sandbox_result is not None:
            result["reality_test_result"] = "pass:sandbox"
            result["sandbox_eval"] = _sandbox_result.to_dict_bounded()
        self.ledger.transition(job["job_id"], "applied", "deterministic patch applied and verified", result)
        return result

    def status(self, job_id: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "worker": "deterministic",
            "llm_allowed": False,
            "data_dir": str(self.config.data_dir),
            "queue_db": str(self.ledger.db_path),
            "counts": self.ledger.counts(),
            "auto_apply_risk": self.config.auto_apply_risk,
        }
        if job_id:
            row = self.ledger.get(job_id)
            if row is None:
                out["job"] = None
            else:
                row.pop("payload_json", None)
                if row.get("result_json"):
                    try:
                        row["result"] = json.loads(row["result_json"])
                    except json.JSONDecodeError:
                        row["result"] = {"raw": row["result_json"]}  # silent-by-design: degraded record keeps the raw payload visible to the caller
                row.pop("result_json", None)
                row["events"] = self.ledger.list_events(job_id)
                out["job"] = row
        return out

    def run_forever(self) -> None:
        """Keep a bounded worker process alive under the supervisor Job Object."""
        logger.info(
            "deterministic worker started: poll=%ss max_jobs=%s root=%s",
            self.config.poll_seconds,
            self.config.max_jobs,
            self.config.allowed_root,
        )
        while True:
            try:
                self.run_once()
            except Exception:
                logger.exception("deterministic worker cycle failed; continuing after bounded sleep")
            time.sleep(self.config.poll_seconds)

    def run_once(self) -> dict[str, Any]:
        started = time.time()
        results: list[dict[str, Any]] = []
        for _ in range(self.config.max_jobs):
            job = self.ledger.claim(
                self.owner,
                self.config.lease_seconds,
                max_attempts=self.config.max_retries + 1,
            )
            if not job:
                break
            try:
                result = self.process_job(job)
            except Exception as exc:  # worker must not crash the supervisor
                logger.exception("deterministic worker job failed: %s", exc)
                result = self._reject(job, f"worker exception: {exc}", "failed")
            results.append(result)
        return {
            "worker": "deterministic",
            "llm_allowed": False,
            "jobs_claimed": len(results),
            "fixed": sum(r.get("action") == "fixed" for r in results),
            "candidate": sum(r.get("action") == "candidate" for r in results),
            "rejected": sum(r.get("action") == "rejected" for r in results),
            "rolled_back": sum(r.get("action") == "rolled_back" for r in results),
            "failed": sum(r.get("action") == "failed" for r in results),
            "elapsed_seconds": round(time.time() - started, 3),
            "results": results,
        }


def _sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded SCP deterministic AutoFix worker once")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--root", default=None)
    parser.add_argument("--max-jobs", type=int, default=None)
    parser.add_argument("--watch", action="store_true", help="keep polling the private queue")
    parser.add_argument("--poll-seconds", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = WorkerConfig.from_env(data_dir=args.data_dir, allowed_root=args.root)
    overrides = {}
    if args.max_jobs is not None:
        overrides["max_jobs"] = max(1, min(20, args.max_jobs))
    if args.poll_seconds is not None:
        overrides["poll_seconds"] = max(5, min(600, args.poll_seconds))
    if overrides:
        config = WorkerConfig(**{**asdict(config), **overrides})
    worker = DeterministicWorker(config)
    if args.watch:
        worker.run_forever()
        return 0
    result = worker.run_once()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(_main())
