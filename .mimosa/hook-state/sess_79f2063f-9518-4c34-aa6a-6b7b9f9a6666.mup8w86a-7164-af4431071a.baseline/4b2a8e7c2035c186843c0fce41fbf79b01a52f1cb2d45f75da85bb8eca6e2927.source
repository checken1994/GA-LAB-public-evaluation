from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scp.core.knowledge_io import _sanitize_identifier_quoted


class HistoryMigrationError(ValueError):
    """Raised when historical evidence cannot be classified safely."""


@dataclass(frozen=True)
class MigrationConfig:
    """Bounded, read-only migration configuration."""

    max_jsonl_rows: int = 100_000
    max_sqlite_bytes: int = 512 * 1024 * 1024
    strict: bool = True


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    kind: str
    evidence_level: str
    sha256: str
    bytes: int
    rows_or_items: int | None
    disposition: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "evidence_level": self.evidence_level,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "rows_or_items": self.rows_or_items,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, config: MigrationConfig) -> None:
    if not path.exists() or not path.is_file():
        raise HistoryMigrationError(f"historical artifact missing: {path}")
    if path.stat().st_size > config.max_sqlite_bytes:
        raise HistoryMigrationError(f"historical artifact exceeds bound: {path}")


def _jsonl_summary(path: Path, config: MigrationConfig) -> tuple[int, Counter[str], set[str]]:
    rows = 0
    states: Counter[str] = Counter()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if line_no > config.max_jsonl_rows:
                raise HistoryMigrationError(f"JSONL row bound exceeded: {path}")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HistoryMigrationError(f"invalid JSONL at {path}:{line_no}") from exc
            if not isinstance(record, dict):
                raise HistoryMigrationError(f"JSONL record is not an object: {path}:{line_no}")
            rows += 1
            keys.update(record)
            for key in ("status", "verdict", "result", "outcome", "stored", "verified", "self_falsified"):
                if key in record:
                    states[f"{key}={record[key]}"] += 1
    return rows, states, keys


def _table_counts(path: Path, config: MigrationConfig) -> dict[str, int]:
    _require_file(path, config)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise HistoryMigrationError(f"cannot open SQLite read-only: {path}") from exc
    try:
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        result: dict[str, int] = {}
        for name in names:
            safe_name = _sanitize_identifier_quoted(name)
            result[name] = int(
                connection.execute(  # nosec B608 — safe_name is produced by _sanitize_identifier_quoted.
                    f"SELECT COUNT(*) FROM {safe_name}"  # nosec B608 — safe_name is produced by _sanitize_identifier_quoted.
                ).fetchone()[0]
            )
        return result
    finally:
        connection.close()


class HistoryMigration:
    """Scan historical SCP artifacts without mutating runtime state.

    This class deliberately produces a manifest and quarantined candidates. It
    does not write the current KB, experiences, policy files or calibration
    factors. A later R43 handoff must independently validate any candidate.
    """

    def __init__(self, config: MigrationConfig | None = None) -> None:
        self.config = config or MigrationConfig()
        self.artifacts: list[ArtifactRecord] = []
        self.quarantine: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []

    def _add(
        self,
        path: Path,
        kind: str,
        level: str,
        rows_or_items: int | None,
        disposition: str,
        reasons: tuple[str, ...],
    ) -> ArtifactRecord:
        _require_file(path, self.config)
        record = ArtifactRecord(
            path=str(path),
            kind=kind,
            evidence_level=level,
            sha256=_sha256(path),
            bytes=path.stat().st_size,
            rows_or_items=rows_or_items,
            disposition=disposition,
            reasons=reasons,
        )
        self.artifacts.append(record)
        return record

    def scan_sqlite(self, path: str | Path, kind: str = "sqlite_runtime") -> dict[str, int]:
        source = Path(path)
        counts = _table_counts(source, self.config)
        relevant = {name: count for name, count in counts.items() if any(token in name.lower() for token in (
            "knowledge", "memory", "experience", "error", "calibr", "predict", "forecast", "policy", "lesson", "meta", "question", "event", "evolution",
        ))}
        self._add(
            source,
            kind,
            "L1",
            sum(relevant.values()),
            "telemetry_only",
            ("SQLite rows are runtime history; source truth and independent adjudication are not implied.",),
        )
        return relevant

    def scan_jsonl(self, path: str | Path, kind: str = "jsonl_runtime") -> dict[str, Any]:
        source = Path(path)
        _require_file(source, self.config)
        rows, states, keys = _jsonl_summary(source, self.config)
        if "evolution" in source.name.lower() and "reflect" in source.name.lower():
            level, disposition = "L2", "candidate_operational_lessons"
            reasons = ("Reflection lineage is narrow and must remain candidate-only until current tests pass.",)
        elif "learning" in source.name.lower():
            level, disposition = "L1", "operational_reliability_only"
            reasons = ("Run status distinguishes provider, timeout, verification and persistence failures; it is not policy knowledge.",)
        else:
            level, disposition = "L1", "telemetry_only"
            reasons = ("JSONL runtime evidence lacks an external truth contract.",)
        self._add(source, kind, level, rows, disposition, reasons)
        return {"rows": rows, "keys": sorted(keys), "states": dict(states)}

    def scan_evolution_db(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        counts = _table_counts(source, self.config)
        self._add(
            source,
            "evolution_sqlite",
            "L2",
            sum(counts.values()),
            "candidate_operational_lessons",
            ("Only exact bug-pattern lessons with verified fix evidence may become candidates; no automatic policy promotion.",),
        )
        try:
            connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            lessons = []
            if "lessons" in counts:
                for row in connection.execute("SELECT * FROM lessons"):
                    item = dict(row)
                    if int(item.get("fix_verified") or 0) == 1 and float(item.get("success_rate") or 0) >= 0.8:
                        lessons.append({
                            "lesson_id": item.get("lesson_id"),
                            "bug_type": item.get("bug_type"),
                            "bug_file": item.get("bug_file"),
                            "bug_line": item.get("bug_line"),
                            "fix_verified": item.get("fix_verified"),
                            "occurrence_count": item.get("occurrence_count"),
                            "success_rate": item.get("success_rate"),
                            "disposition": "candidate_only",
                        })
            patterns = []
            if "evolved_patterns" in counts:
                for row in connection.execute("SELECT * FROM evolved_patterns"):
                    item = dict(row)
                    patterns.append({
                        "pattern_id": item.get("pattern_id"),
                        "bug_type": item.get("bug_type"),
                        "source_lesson_id": item.get("source_lesson_id"),
                        "occurrence_count": item.get("occurrence_count"),
                        "false_positive_count": item.get("false_positive_count"),
                        "confidence": item.get("confidence"),
                        "disposition": "candidate_only",
                    })
            connection.close()
        except sqlite3.Error as exc:
            raise HistoryMigrationError(f"cannot inspect evolution db: {source}") from exc
        self.candidates.extend(lessons)
        self.quarantine.extend(patterns)
        return {"table_counts": counts, "verified_lesson_candidates": lessons, "patterns_quarantined": patterns}

    def scan_static_knowledge(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        _require_file(source, self.config)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HistoryMigrationError(f"invalid static knowledge JSON: {source}") from exc
        if not isinstance(payload, dict):
            raise HistoryMigrationError(f"static knowledge must be an object: {source}")
        count = sum(len(value) for value in payload.values() if isinstance(value, dict))
        self._add(
            source,
            "static_knowledge_seed",
            "L1",
            count,
            "reference_only",
            ("Facts have no per-fact provenance, verifier, contradiction history or capture contract.",),
        )
        return {"domains": len(payload), "facts": count, "disposition": "reference_only"}

    def scan_reality_results(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        _require_file(source, self.config)
        payload = json.loads(source.read_text(encoding="utf-8"))
        results = payload.get("results") if isinstance(payload, dict) else None
        values = Counter(str(row.get("pass")) for row in results if isinstance(row, dict)) if isinstance(results, list) else Counter()
        valid = bool(results) and set(values) <= {"True", "False"}
        disposition = "regression_evidence" if valid else "contract_invalid_quarantine"
        reasons = ("Result rows have no boolean truth value; header cannot substitute for row-level truth.",) if not valid else ("Row-level boolean result contract is present.",)
        self._add(source, "reality_results", "L1", len(results or []), disposition, reasons)
        return {"row_count": len(results or []), "pass_values": dict(values), "valid_row_contract": valid}

    def manifest(self) -> dict[str, Any]:
        return {
            "schema": "scp-history-migration-r44",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mutating": False,
            "policy_promotion": False,
            "artifacts": [record.to_dict() for record in self.artifacts],
            "candidates": self.candidates,
            "quarantine": self.quarantine,
        }

    def write_manifest(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(self.manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        return target


__all__ = ["HistoryMigration", "MigrationConfig", "HistoryMigrationError"]
