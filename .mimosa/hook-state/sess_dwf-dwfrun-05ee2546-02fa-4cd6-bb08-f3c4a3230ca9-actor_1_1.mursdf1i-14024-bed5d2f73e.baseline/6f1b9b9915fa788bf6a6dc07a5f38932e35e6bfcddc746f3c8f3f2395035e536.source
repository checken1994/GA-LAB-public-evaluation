"""Retention worker for governed evidence payloads (26-P0.12c).

Evidence metadata/hash/provenance remain durable. Retention changes only payload
lifecycle state and emits append-only retention events. Active holds block purge.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso
from scp.interfaces.epistemic import IEvidenceStore
from scp.persistence import FoundationDB

logger = logging.getLogger(__name__)


_RETENTION_MIGRATIONS = [
    (
        "0004_retention_holds",
        [
            """CREATE TABLE IF NOT EXISTS retention_holds (
                   hold_id TEXT PRIMARY KEY,
                   target_type TEXT NOT NULL CHECK(target_type IN ('EVIDENCE','CONTENT_HASH')),
                   target_id TEXT NOT NULL,
                   reason TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   released_at TEXT)""",
            "CREATE INDEX IF NOT EXISTS idx_retention_holds_target ON retention_holds(target_type,target_id,released_at)",
        ],
    ),
]


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("retention timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


class RetentionManager:
    def __init__(self, store: IEvidenceStore, policy_path: str | Path) -> None:
        self.store = store
        self.db = FoundationDB(store.db.path, _RETENTION_MIGRATIONS)
        doc = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8")) or {}
        if doc.get("schema_version") != 1:
            raise ValueError("unsupported retention policy schema")
        self.policies = dict(doc.get("policies") or {})

    def add_hold(self, *, evidence_id: str, reason: str) -> str:
        _record = self.store.get(evidence_id)  # [hygiene F841] giữ call .get() (side-effect surface), biến đổi _record
        hold_id = new_id("hold")
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO retention_holds(hold_id,target_type,target_id,reason,created_at) VALUES (?,'EVIDENCE',?,?,?)",
                (hold_id, evidence_id, str(reason), now_utc_iso()),
            )
        return hold_id

    def release_hold(self, hold_id: str) -> None:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "UPDATE retention_holds SET released_at=? WHERE hold_id=? AND released_at IS NULL",
                (now_utc_iso(), hold_id),
            )
            if cur.rowcount != 1:
                raise KeyError(hold_id)

    def _held(self, evidence_id: str, content_hash: str) -> bool:
        rows = self.db.query(
            """SELECT 1 FROM retention_holds
               WHERE released_at IS NULL AND
                 ((target_type='EVIDENCE' AND target_id=?) OR
                  (target_type='CONTENT_HASH' AND target_id=?)) LIMIT 1""",
            (evidence_id, content_hash),
        )
        return bool(rows)

    def purge_evidence(self, evidence_id: str, *, reason: str = "retention_expired") -> str:
        rows = self.db.query("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,))
        if not rows:
            raise KeyError(evidence_id)
        record = rows[0]
        if self._held(evidence_id, record["content_hash"]):
            raise PermissionError("active retention hold blocks purge")

        state_rows = self.db.query(
            "SELECT payload_state FROM evidence_payload_state WHERE evidence_id=?", (evidence_id,)
        )
        if state_rows and state_rows[0]["payload_state"] == "PURGED":
            return "ALREADY_PURGED"

        event_id = new_id("ret")
        # Mark this occurrence PURGED first. The immutable evidence row stays.
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO evidence_payload_state(evidence_id,payload_state,last_checked_at)
                   VALUES (?,'PURGED',?)
                   ON CONFLICT(evidence_id) DO UPDATE SET
                     payload_state='PURGED', last_checked_at=excluded.last_checked_at""",
                (evidence_id, now_utc_iso()),
            )
            conn.execute(
                "INSERT INTO retention_events(retention_event_id,target,reason,policy,purged_at) VALUES (?,?,?,?,?)",
                (event_id, evidence_id, str(reason), record.get("retention_policy_id"), now_utc_iso()),
            )

        # Content-addressed blobs may be shared by multiple observation
        # occurrences. Delete raw bytes only when NO other AVAILABLE occurrence
        # still references that content hash.
        available = self.db.query(
            """SELECT COUNT(*) AS n FROM evidence e
               JOIN evidence_payload_state s ON s.evidence_id=e.evidence_id
               WHERE e.content_hash=? AND s.payload_state='AVAILABLE'""",
            (record["content_hash"],),
        )[0]["n"]
        if int(available) == 0:
            blob_path = self.store.objects_dir / (record.get("content_ref") or "")
            if blob_path.is_file():
                blob_path.unlink()
        return event_id

    def purge_expired(self, *, now: datetime | None = None) -> dict:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        candidates = self.db.query(
            """SELECT e.* FROM evidence e
               JOIN evidence_payload_state s ON s.evidence_id=e.evidence_id
               WHERE s.payload_state='AVAILABLE' ORDER BY e.created_at"""
        )
        purged: list[str] = []
        held: list[str] = []
        errors: list[str] = []
        for record in candidates:
            policy = self.policies.get(record["data_class"])
            if not policy:
                # Missing policy is fail-conservative: do not guess a retention
                # deadline and do not delete evidence.
                errors.append(record["evidence_id"])
                continue
            days = policy.get("raw_retention_days")
            if days is None:
                errors.append(record["evidence_id"])
                continue
            age_days = (current - _parse_time(record["created_at"])).total_seconds() / 86400.0
            if age_days < float(days):
                continue
            if self._held(record["evidence_id"], record["content_hash"]):
                held.append(record["evidence_id"])
                continue
            try:
                self.purge_evidence(record["evidence_id"])
                purged.append(record["evidence_id"])
            except Exception as exc:
                logger.debug(f"RetentionManager.purge_expired: exception ignored: {exc}", exc_info=True)
                # Do not leak record content/secret into logs or return payload.
                errors.append(record["evidence_id"])
        return {"purged": purged, "held": held, "errors": errors}

    def close(self) -> None:
        self.db.close()
