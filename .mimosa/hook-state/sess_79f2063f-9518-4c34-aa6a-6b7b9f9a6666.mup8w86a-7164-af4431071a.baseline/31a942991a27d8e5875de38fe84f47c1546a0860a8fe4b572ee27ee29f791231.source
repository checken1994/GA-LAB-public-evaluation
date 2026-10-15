# SCP CIRCUIT: M14 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M14-closure.json)
"""Evidence Store (26-P0.05) - the strongest P0 authority.

Invariants:
  - occurrence identity != content identity: the same content observed twice
    yields the SAME content_hash/blob but TWO different evidence_ids;
  - the `evidence` table is IMMUTABLE (SQLite trigger aborts UPDATE) - a wrong
    observation is corrected by a NEW evidence + SUPERSEDES relation, never by
    rewriting history;
  - record_hash = sha256 over the canonical immutable metadata, so raw-SQL
    tampering with metadata is detectable by verify_integrity();
  - blob write is crash-ordered: staging -> fsync -> atomic rename -> DB
    transaction, and content blobs are deduplicated while occurrences are not;
  - missing/tampered payload fails CLOSED (never returned as valid evidence);
  - MODEL_RESPONSE evidence proves "the model said X" - never "X is true".
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from scp.contracts.data_class import DataClass, parse_data_class
from scp.contracts.ids import content_id, new_id
from scp.contracts.time import now_utc_iso
from scp.persistence import FoundationDB

EVIDENCE_KINDS = {
    "HTTP_RESPONSE",
    "FILE_OBSERVATION",
    "RUNTIME_OBSERVATION",
    "TEST_RESULT",
    "CONFIG_SNAPSHOT",
    "GIT_SNAPSHOT",
    "MODEL_RESPONSE",   # proves "model said X", never "X is true"
    "HUMAN_ATTESTATION",
}

_IMMUTABLE_FIELDS = (
    "evidence_id", "kind", "content_hash", "source_id", "observed_at",
    "task_id", "attempt_id", "trace_id", "collector_id", "collector_version",
    "policy_hash", "data_class", "retention_policy_id", "valid_from",
    "valid_to", "metadata_json", "created_at",
)

_EVIDENCE_MIGRATIONS = [
    (
        "0001_evidence_core",
        [
            """CREATE TABLE IF NOT EXISTS evidence (
                   evidence_id TEXT PRIMARY KEY,
                   kind TEXT NOT NULL,
                   content_hash TEXT NOT NULL,
                   content_ref TEXT,
                   source_id TEXT,
                   observed_at TEXT NOT NULL,
                   task_id TEXT,
                   attempt_id TEXT,
                   trace_id TEXT,
                   collector_id TEXT NOT NULL,
                   collector_version TEXT NOT NULL,
                   policy_hash TEXT,
                   data_class TEXT NOT NULL,
                   retention_policy_id TEXT,
                   valid_from TEXT,
                   valid_to TEXT,
                   metadata_json TEXT NOT NULL,
                   record_hash TEXT NOT NULL,
                   created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS content_blobs (
                   content_hash TEXT PRIMARY KEY,
                   storage_path TEXT NOT NULL,
                   byte_length INTEGER NOT NULL,
                   mime_type TEXT,
                   created_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS evidence_links (
                   parent_evidence_id TEXT NOT NULL,
                   child_evidence_id TEXT NOT NULL,
                   relation TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   PRIMARY KEY (parent_evidence_id, child_evidence_id, relation))""",
            """CREATE TABLE IF NOT EXISTS evidence_payload_state (
                   evidence_id TEXT PRIMARY KEY,
                   payload_state TEXT NOT NULL DEFAULT 'AVAILABLE',
                   last_checked_at TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS retention_events (
                   retention_event_id TEXT PRIMARY KEY,
                   target TEXT NOT NULL,
                   reason TEXT NOT NULL,
                   policy TEXT,
                   purged_at TEXT NOT NULL)""",
            """CREATE TRIGGER IF NOT EXISTS evidence_no_update
                   BEFORE UPDATE ON evidence
                   BEGIN
                       SELECT RAISE(ABORT, 'evidence is immutable - supersede instead');
                   END;""",
        ],
    ),
]


class EvidenceIntegrityError(RuntimeError):
    """Payload missing/tampered/purged - evidence must NOT be used as valid."""


def _blob_rel_path(digest: str) -> str:
    # Windows forbids ':' in file names (it means Alternate Data Stream), so
    # the blob FILE name is the bare hex digest; the "sha256:" prefix lives in
    # the content_hash column only.
    hex_part = digest.split(":", 1)[1]
    return f"sha256/{hex_part[:2]}/{hex_part[2:4]}/{hex_part}"


class EvidenceStore:
    def __init__(self, db_path: str | Path, objects_dir: str | Path) -> None:
        self.db = FoundationDB(db_path, _EVIDENCE_MIGRATIONS)
        self.objects_dir = Path(objects_dir)
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        staging = self.objects_dir / ".staging"
        staging.mkdir(parents=True, exist_ok=True)
        # C1 reconciliation: a previous process may have died after staging a
        # blob but before the atomic rename - staged files are safe to delete.
        for leftover in staging.iterdir():
            leftover.unlink(missing_ok=True)

    def observe(
        self,
        *,
        kind: str,
        content: bytes,
        collector_id: str,
        collector_version: str,
        source_id: str | None = None,
        task_id: str | None = None,
        attempt_id: str | None = None,
        trace_id: str | None = None,
        policy_hash: str | None = None,
        data_class: DataClass | str = DataClass.INTERNAL,
        retention_policy_id: str | None = None,
        metadata: dict | None = None,
        mime_type: str | None = None,
        observed_at: str | None = None,
    ) -> dict:
        kind = str(kind).strip().upper()
        if kind not in EVIDENCE_KINDS:
            raise ValueError(f"unknown evidence kind: {kind!r}")
        if not isinstance(content, (bytes, bytearray)) or not content:
            raise ValueError("evidence content must be non-empty bytes")
        digest = content_id(bytes(content))
        blob_path = self.objects_dir / _blob_rel_path(digest)

        # C1->C2-safe blob write: stage + fsync, then atomic rename. If the
        # blob already exists, VERIFY it before reuse - never overwrite.
        staging = self.objects_dir / ".staging" / uuid.uuid4().hex
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.write_bytes(bytes(content))
        with staging.open("rb+") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        if blob_path.exists():
            if content_id(blob_path.read_bytes()) != digest:
                raise EvidenceIntegrityError(
                    f"existing blob hash mismatch for {digest} - refusing to overwrite"
                )
            staging.unlink(missing_ok=True)
        else:
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging, blob_path)

        row = {
            "evidence_id": new_id("ev"),
            "kind": kind,
            "content_hash": digest,
            "content_ref": _blob_rel_path(digest),
            "source_id": source_id,
            "observed_at": observed_at or now_utc_iso(),
            "task_id": task_id,
            "attempt_id": attempt_id,
            "trace_id": trace_id,
            "collector_id": collector_id,
            "collector_version": collector_version,
            "policy_hash": policy_hash,
            "data_class": parse_data_class(data_class).value,
            "retention_policy_id": retention_policy_id,
            "valid_from": None,
            "valid_to": None,
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
            "created_at": now_utc_iso(),
        }
        row["record_hash"] = content_id(
            json.dumps({f: row[f] for f in _IMMUTABLE_FIELDS}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO content_blobs (content_hash, storage_path, byte_length, mime_type, created_at) VALUES (?,?,?,?,?)",
                (digest, _blob_rel_path(digest), len(content), mime_type, now_utc_iso()),
            )
            conn.execute(
                """INSERT INTO evidence (evidence_id, kind, content_hash, content_ref, source_id,
                       observed_at, task_id, attempt_id, trace_id, collector_id, collector_version,
                       policy_hash, data_class, retention_policy_id, valid_from, valid_to,
                       metadata_json, record_hash, created_at)
                   VALUES (:evidence_id,:kind,:content_hash,:content_ref,:source_id,:observed_at,
                       :task_id,:attempt_id,:trace_id,:collector_id,:collector_version,
                       :policy_hash,:data_class,:retention_policy_id,:valid_from,:valid_to,
                       :metadata_json,:record_hash,:created_at)""",
                row,
            )
            conn.execute(
                "INSERT INTO evidence_payload_state (evidence_id, payload_state, last_checked_at) VALUES (?, 'AVAILABLE', ?)",
                (row["evidence_id"], now_utc_iso()),
            )
        return self.get(row["evidence_id"])

    def get(self, evidence_id: str) -> dict:
        rows = self.db.query("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,))
        if not rows:
            raise KeyError(f"evidence not found: {evidence_id}")
        record = dict(rows[0])
        integrity = self.verify_integrity(evidence_id)
        if not integrity["ok"]:
            raise EvidenceIntegrityError(
                f"evidence {evidence_id} failed integrity: {integrity['errors']} "
                f"(payload_state={integrity['payload_state']})"
            )
        record["payload_state"] = integrity["payload_state"]
        return record

    def verify_integrity(self, evidence_id: str) -> dict:
        rows = self.db.query("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,))
        if not rows:
            return {"ok": False, "payload_state": "MISSING", "errors": ["evidence row not found"]}
        record = dict(rows[0])
        errors: list[str] = []

        expected_hash = content_id(
            json.dumps({f: record[f] for f in _IMMUTABLE_FIELDS}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        if expected_hash != record["record_hash"]:
            errors.append("record_hash mismatch - immutable metadata was tampered with")

        state_rows = self.db.query(
            "SELECT payload_state FROM evidence_payload_state WHERE evidence_id=?", (evidence_id,)
        )
        state = state_rows[0]["payload_state"] if state_rows else "MISSING"
        if state != "AVAILABLE":
            errors.append(f"payload is {state}")
        else:
            blob_path = self.objects_dir / (record["content_ref"] or "")
            if not blob_path.is_file():
                errors.append("blob file missing (C4)")
                state = "MISSING"
            else:
                if content_id(blob_path.read_bytes()) != record["content_hash"]:
                    errors.append("blob content hash mismatch (C4 tamper)")
                    state = "MISSING"
        if errors:
            self.db.execute(
                "INSERT INTO evidence_payload_state (evidence_id, payload_state, last_checked_at) VALUES (?,?,?) "
                "ON CONFLICT(evidence_id) DO UPDATE SET payload_state=excluded.payload_state, last_checked_at=excluded.last_checked_at",
                (evidence_id, state if state in {"PURGED", "MISSING"} else "MISSING", now_utc_iso()),
            )
            self.db._conn.commit()
        return {"ok": not errors, "payload_state": state, "errors": errors}

    def read_content(self, evidence_id: str) -> bytes:
        record = self.get(evidence_id)  # fail-closed on any integrity problem
        return (self.objects_dir / record["content_ref"]).read_bytes()

    def link(self, parent_evidence_id: str, child_evidence_id: str, relation: str) -> None:
        relation = str(relation).strip().upper()
        if not relation.replace("_", "").isalnum():
            raise ValueError(f"invalid relation: {relation!r}")
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO evidence_links (parent_evidence_id, child_evidence_id, relation, created_at) VALUES (?,?,?,?)",
                (parent_evidence_id, child_evidence_id, relation, now_utc_iso()),
            )

    def supersede(self, old_evidence_id: str, **observe_kwargs) -> dict:
        """A wrong observation is corrected by NEW evidence + SUPERSEDES, never an edit."""
        replacement = self.observe(**observe_kwargs)
        self.link(old_evidence_id, replacement["evidence_id"], "SUPERSEDES")
        return replacement

    def purge_payload(self, evidence_id: str, reason: str, policy: str | None = None) -> str:
        """Retention purge: metadata + hash stay durable forever, payload goes."""
        rows = self.db.query("SELECT content_ref FROM evidence WHERE evidence_id=?", (evidence_id,))
        if not rows:
            raise KeyError(evidence_id)
        blob_path = self.objects_dir / (rows[0]["content_ref"] or "")
        if blob_path.is_file():
            blob_path.unlink()
        event_id = new_id("ret")
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO evidence_payload_state (evidence_id, payload_state, last_checked_at) VALUES (?, 'PURGED', ?) "
                "ON CONFLICT(evidence_id) DO UPDATE SET payload_state='PURGED', last_checked_at=excluded.last_checked_at",
                (evidence_id, now_utc_iso()),
            )
            conn.execute(
                "INSERT INTO retention_events (retention_event_id, target, reason, policy, purged_at) VALUES (?,?,?,?,?)",
                (event_id, evidence_id, reason, policy, now_utc_iso()),
            )
        return event_id

    def scan_orphans(self) -> list[str]:
        """C2 reconciliation: blob files on disk that no evidence row references."""
        referenced = {row["content_hash"] for row in self.db.query("SELECT content_hash FROM content_blobs")}
        orphans: list[str] = []
        root = self.objects_dir / "sha256"
        if root.is_dir():
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if content_id(path.read_bytes()) not in referenced:
                    orphans.append(str(path))
        return orphans
