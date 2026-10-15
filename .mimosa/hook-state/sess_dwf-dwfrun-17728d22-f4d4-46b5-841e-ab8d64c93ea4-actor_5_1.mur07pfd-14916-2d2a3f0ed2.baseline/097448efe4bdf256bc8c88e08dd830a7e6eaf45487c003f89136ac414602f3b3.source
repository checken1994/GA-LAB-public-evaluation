from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLICY_KEYS = (
    "source_priorities",
    "domain_tolerances",
    "kb_priorities",
    "recurring_errors",
    "confidence_adjustments",
)
SUPPORTED_LESSON_TYPES = {
    "SOURCE_RELIABILITY",
    "DOMAIN_BIAS",
    "ERROR_FREQUENCY",
    "CONFIDENCE_TUNING",
    "ROUTE_OPTIMIZATION",
}


class PolicyMaterializerError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PolicyMaterializer:
    """Build and promote ExperienceEngine policy without touching production implicitly.

    The materializer intentionally does not mark lessons as applied during normal
    materialization. Promotion and application are separate auditable operations.
    """

    def __init__(self, db_path: str | Path, data_dir: str | Path):
        self.db_path = Path(db_path)
        self.data_dir = Path(data_dir)
        self.active_path = self.data_dir / "active_policies.json"
        self.candidate_path = self.data_dir / "active_policies.candidate.json"
        self.ledger_path = self.data_dir / "policy_handoff_ledger.jsonl"

    def _read_lessons(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            raise PolicyMaterializerError(f"learning DB does not exist: {self.db_path}")
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, lesson_type, policy_action, policy_target, policy_value,
                           lesson_description
                    FROM experiences
                    WHERE applied = 0
                    ORDER BY timestamp DESC, id DESC
                    """
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise PolicyMaterializerError(f"cannot read experiences: {type(exc).__name__}") from exc

    @staticmethod
    def _float_value(value: Any, lesson_id: Any) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise PolicyMaterializerError(f"invalid policy value for lesson {lesson_id}") from exc
        if result != result or result in (float("inf"), float("-inf")):
            raise PolicyMaterializerError(f"non-finite policy value for lesson {lesson_id}")
        return result

    def build(self) -> dict[str, Any]:
        lessons = self._read_lessons()
        policy: dict[str, Any] = {
            "source_priorities": {},
            "domain_tolerances": {},
            "kb_priorities": [],
            "recurring_errors": [],
            "confidence_adjustments": {},
        }
        eligible_ids: list[int] = []
        skipped: list[dict[str, Any]] = []

        for lesson in lessons:
            lesson_id = int(lesson["id"])
            lesson_type = str(lesson.get("lesson_type") or "")
            action = str(lesson.get("policy_action") or "")
            target = str(lesson.get("policy_target") or "")
            value = lesson.get("policy_value")
            if lesson_type not in SUPPORTED_LESSON_TYPES:
                skipped.append({"id": lesson_id, "reason": "unsupported_lesson_type", "lesson_type": lesson_type})
                continue
            if not target:
                skipped.append({"id": lesson_id, "reason": "empty_policy_target", "lesson_type": lesson_type})
                continue

            eligible_ids.append(lesson_id)
            if lesson_type == "SOURCE_RELIABILITY":
                policy["source_priorities"][target] = {
                    "action": action,
                    "reliability": self._float_value(value, lesson_id),
                }
            elif lesson_type == "DOMAIN_BIAS":
                if action == "INCREASE_TOLERANCE":
                    policy["domain_tolerances"][target] = 2.0
                elif action == "ADD_BIAS_CORRECTION":
                    policy["domain_tolerances"][target] = 1.5
                else:
                    skipped.append({"id": lesson_id, "reason": "unsupported_domain_action", "action": action})
                    eligible_ids.pop()
            elif lesson_type == "ROUTE_OPTIMIZATION":
                if action == "USE_KB_FIRST":
                    policy["kb_priorities"].append(target)
                else:
                    skipped.append({"id": lesson_id, "reason": "unsupported_route_action", "action": action})
                    eligible_ids.pop()
            elif lesson_type == "ERROR_FREQUENCY":
                if action == "FLAG_RECURRING":
                    policy["recurring_errors"].append(target)
                else:
                    skipped.append({"id": lesson_id, "reason": "unsupported_error_action", "action": action})
                    eligible_ids.pop()
            elif lesson_type == "CONFIDENCE_TUNING":
                if action == "LOWER_CONFIDENCE":
                    policy["confidence_adjustments"][target] = 0.5
                else:
                    skipped.append({"id": lesson_id, "reason": "unsupported_confidence_action", "action": action})
                    eligible_ids.pop()

        meta = {
            "schema_version": 1,
            "materializer": "PolicyMaterializer-R43",
            "generated_at": _utc_now(),
            "source_db": str(self.db_path),
            "eligible_lesson_ids": eligible_ids,
            "skipped_lessons": skipped,
            "lesson_count_seen": len(lessons),
            "eligible_lesson_count": len(eligible_ids),
            "policy_key_counts": {key: len(policy[key]) for key in POLICY_KEYS},
        }
        payload = dict(policy)
        payload["_meta"] = meta
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        meta["policy_sha256"] = hashlib.sha256(canonical).hexdigest()
        return payload

    def materialize_candidate(self) -> dict[str, Any]:
        payload = self.build()
        _atomic_json_write(self.candidate_path, payload)
        self._append_ledger("materialized", payload, self.candidate_path)
        return payload

    def validate(self, path: str | Path | None = None) -> dict[str, Any]:
        target = Path(path) if path else self.candidate_path
        if not target.exists():
            raise PolicyMaterializerError(f"policy artifact missing: {target}")
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyMaterializerError(f"policy artifact unreadable: {target.name}") from exc
        missing = [key for key in POLICY_KEYS if key not in payload]
        if missing or not isinstance(payload.get("_meta"), dict):
            raise PolicyMaterializerError(f"policy artifact contract invalid: missing={missing}")
        stored_hash = payload["_meta"].get("policy_sha256")
        if not isinstance(stored_hash, str) or len(stored_hash) != 64:
            raise PolicyMaterializerError("policy artifact hash missing")
        check_payload = json.loads(json.dumps(payload, ensure_ascii=False))
        check_payload["_meta"].pop("policy_sha256", None)
        canonical = json.dumps(check_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != stored_hash:
            raise PolicyMaterializerError("policy artifact hash mismatch")
        return payload

    def promote(self, candidate: str | Path | None = None) -> dict[str, Any]:
        source = Path(candidate) if candidate else self.candidate_path
        payload = self.validate(source)
        eligible_count = int(payload.get("_meta", {}).get("eligible_lesson_count", 0))
        if eligible_count <= 0:
            raise PolicyMaterializerError("refusing to promote an empty policy candidate")
        backup = None
        if self.active_path.exists():
            backup = self.active_path.with_name(f"{self.active_path.name}.bak.{time.time_ns()}")
            shutil.copy2(self.active_path, backup)
        else:
            # First promotion must still be reversible: record that active was absent.
            backup = self.active_path.with_name(f"{self.active_path.name}.bak.{time.time_ns()}.absent")
            backup.write_text(json.dumps({"_rollback_absent": True}) + "\n", encoding="utf-8")
        _atomic_json_write(self.active_path, payload)
        self._append_ledger("promoted", payload, self.active_path, backup)
        return {"event": "promoted", "active": str(self.active_path), "backup": str(backup) if backup else None,
                "policy_sha256": payload["_meta"].get("policy_sha256"),
                "eligible_lesson_count": payload["_meta"].get("eligible_lesson_count", 0)}

    def mark_applied(self, lesson_ids: list[int]) -> int:
        if not lesson_ids:
            return 0
        with sqlite3.connect(str(self.db_path), timeout=10) as conn:
            placeholders = ",".join("?" for _ in lesson_ids)
            params: list[Any] = [datetime.now(timezone.utc).isoformat(), *lesson_ids]
            result = conn.execute(
                f"UPDATE experiences SET applied = 1, applied_at = ? WHERE applied = 0 AND id IN ({placeholders})",
                params,
            )
            conn.commit()
            return int(result.rowcount)

    def record_applied(self, lesson_ids: list[int], applied_count: int) -> None:
        payload = self.validate(self.active_path)
        entry = {
            "ts": _utc_now(),
            "event": "applied",
            "artifact": str(self.active_path),
            "artifact_sha256": _sha256_file(self.active_path),
            "backup": None,
            "policy_sha256": payload.get("_meta", {}).get("policy_sha256"),
            "eligible_lesson_count": payload.get("_meta", {}).get("eligible_lesson_count", 0),
            "lesson_ids_count": len(lesson_ids),
            "applied_count": int(applied_count),
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def rollback(self, backup: str | Path | None = None):
        backup_path = Path(backup) if backup else self._latest_backup()
        if backup_path is None or not backup_path.exists():
            raise PolicyMaterializerError("no policy backup available for rollback")
        restored = json.loads(backup_path.read_text(encoding="utf-8"))
        if isinstance(restored, dict) and restored.get("_rollback_absent") is True:
            self.active_path.unlink(missing_ok=True)
            restored_payload: dict[str, Any] = {}
        else:
            _atomic_json_write(self.active_path, restored)
            restored_payload = restored
        self._append_ledger("rollback", restored_payload, self.active_path, backup_path)
        return {"event": "rollback", "active": str(self.active_path), "restored_from": str(backup_path), "active_exists": self.active_path.exists()}

    def _latest_backup(self) -> Path | None:
        backups = sorted(self.data_dir.glob("active_policies.json.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return backups[0] if backups else None

    def _append_ledger(self, event: str, payload: dict[str, Any], artifact: Path, backup: Path | None = None) -> None:
        entry = {
            "ts": _utc_now(),
            "event": event,
            "artifact": str(artifact),
            "artifact_sha256": _sha256_file(artifact),
            "backup": str(backup) if backup else None,
            "policy_sha256": payload.get("_meta", {}).get("policy_sha256"),
            "eligible_lesson_count": payload.get("_meta", {}).get("eligible_lesson_count", 0),
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
