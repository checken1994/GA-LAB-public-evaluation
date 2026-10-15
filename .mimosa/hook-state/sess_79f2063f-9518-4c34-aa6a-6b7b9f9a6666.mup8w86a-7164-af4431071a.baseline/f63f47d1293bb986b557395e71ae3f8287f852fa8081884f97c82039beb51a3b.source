from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


ALLOWED_OUTCOME_CODES = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9})
RESOLVED_OUTCOME_CODES = frozenset({1, 2, 3, 4, 5, 6, 7, 8})
REQUIRED_CASE_FIELDS = frozenset(
    {"id", "domain", "claimant", "claim", "date", "url", "verdict", "confidence", "antibodies", "outcome_code"}
)


class ForecastContractError(ValueError):
    """Raised when an operation would create an unverifiable forecast record."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_manifest_bytes(payload: dict[str, Any]) -> bytes:
    copy = dict(payload)
    copy.pop("manifest_sha256", None)
    return _canonical_json(copy)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json_write(path: Path, payload: Any) -> None:
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
            logger.debug('_atomic_json_write: OSError ignored', exc_info=True)
        raise


@dataclass(frozen=True)
class RegistrySnapshot:
    path: str
    raw_sha256: str
    canonical_sha256: str
    embedded_manifest_sha256: str | None
    manifest_status: str
    case_count: int
    lock_date: str | None

    @property
    def integrity_verified(self) -> bool:
        return self.manifest_status in {"MATCH_RAW", "MATCH_CANONICAL"}


@dataclass(frozen=True)
class ForecastRegistry:
    payload: dict[str, Any]
    snapshot: RegistrySnapshot

    @property
    def cases(self) -> list[dict[str, Any]]:
        return self.payload["cases"]

    def case(self, case_id: str) -> dict[str, Any]:
        for item in self.cases:
            if item["id"] == case_id:
                return item
        raise ForecastContractError(f"unknown forecast case: {case_id}")

    @classmethod
    def load(cls, path: str | Path, *, strict_manifest: bool = False) -> ForecastRegistry:
        source = Path(path)
        if not source.exists() or not source.is_file():
            raise ForecastContractError(f"forecast registry missing: {source}")
        raw = source.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ForecastContractError("forecast registry is not valid UTF-8 JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
            raise ForecastContractError("forecast registry must contain a cases array")

        cases = payload["cases"]
        declared_total = payload.get("total_cases")
        if declared_total is not None and declared_total != len(cases):
            raise ForecastContractError("declared total_cases does not match cases length")
        ids: set[str] = set()
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not REQUIRED_CASE_FIELDS.issubset(case):
                raise ForecastContractError(f"case {index} does not satisfy the registry schema")
            case_id = case["id"]
            if not isinstance(case_id, str) or not case_id or case_id in ids:
                raise ForecastContractError(f"duplicate or invalid case id at index {index}")
            ids.add(case_id)
            if case["outcome_code"] not in ALLOWED_OUTCOME_CODES:
                raise ForecastContractError(f"invalid outcome code for {case_id}")
            if case["verdict"] not in {"FRAUD", "REFINE", "LEGITIMATE"}:
                raise ForecastContractError(f"invalid verdict for {case_id}")
            if case["confidence"] not in {"HIGH", "MEDIUM", "LOW"}:
                raise ForecastContractError(f"invalid confidence for {case_id}")
            if not isinstance(case["antibodies"], list):
                raise ForecastContractError(f"antibodies must be a list for {case_id}")

        embedded = payload.get("manifest_sha256")
        embedded = embedded if isinstance(embedded, str) else None
        raw_sha = _sha256_bytes(raw)
        canonical_sha = _sha256_bytes(_canonical_manifest_bytes(payload))
        if embedded is None:
            manifest_status = "MISSING"
        elif embedded == raw_sha:
            manifest_status = "MATCH_RAW"
        elif embedded == canonical_sha:
            manifest_status = "MATCH_CANONICAL"
        else:
            manifest_status = "MISMATCH"
        if strict_manifest and manifest_status not in {"MATCH_RAW", "MATCH_CANONICAL"}:
            raise ForecastContractError(f"registry manifest is not verified: {manifest_status}")
        snapshot = RegistrySnapshot(
            path=str(source),
            raw_sha256=raw_sha,
            canonical_sha256=canonical_sha,
            embedded_manifest_sha256=embedded,
            manifest_status=manifest_status,
            case_count=len(cases),
            lock_date=payload.get("lock_date") if isinstance(payload.get("lock_date"), str) else None,
        )
        return cls(payload=payload, snapshot=snapshot)


class ForecastLedger:
    """Append-only, quarantine-first resolution ledger.

    This class never changes a registry row and never writes SCP knowledge or policy.
    A resolved outcome is accepted only after the registry anchor is verified and an
    evidence digest, source, and adjudicator are supplied. Rejected/unresolved events
    remain auditable but are excluded from scoring.
    """

    def __init__(self, registry: ForecastRegistry, ledger_path: str | Path):
        self.registry = registry
        self.ledger_path = Path(ledger_path)

    def _append(self, entry: dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(self.ledger_path, flags, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def _reject(self, case_id: str, reason: str) -> dict[str, Any]:
        entry = {
            "event": "resolution_rejected",
            "ts": _utc_now(),
            "case_id": case_id,
            "reason": reason,
            "registry_raw_sha256": self.registry.snapshot.raw_sha256,
            "registry_manifest_status": self.registry.snapshot.manifest_status,
        }
        self._append(entry)
        return entry

    def record_unresolved(self, case_id: str, *, reason: str) -> dict[str, Any]:
        self.registry.case(case_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ForecastContractError("unresolved reason is required")
        entry = {
            "event": "outcome_observed",
            "ts": _utc_now(),
            "case_id": case_id,
            "outcome_code": 9,
            "reason": reason.strip(),
            "registry_raw_sha256": self.registry.snapshot.raw_sha256,
            "registry_manifest_status": self.registry.snapshot.manifest_status,
        }
        self._append(entry)
        return entry

    def resolve_case(
        self,
        case_id: str,
        *,
        outcome_code: int,
        evidence_url: str,
        evidence_sha256: str,
        adjudicator_id: str,
        resolved_at: str | None = None,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        self.registry.case(case_id)
        if not self.registry.snapshot.integrity_verified:
            return self._reject(case_id, "registry_anchor_unverified")
        if outcome_code not in RESOLVED_OUTCOME_CODES:
            return self._reject(case_id, "resolved_outcome_code_must_be_1_to_8")
        if not isinstance(evidence_url, str) or not evidence_url.startswith(("http://", "https://")):
            return self._reject(case_id, "evidence_url_required")
        if not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64 or any(c not in "0123456789abcdef" for c in evidence_sha256.lower()):
            return self._reject(case_id, "evidence_sha256_required")
        if not isinstance(adjudicator_id, str) or not adjudicator_id.strip():
            return self._reject(case_id, "adjudicator_required")
        existing = self.current_outcomes().get(case_id)
        if existing and existing.get("outcome_code") != 9 and existing.get("outcome_code") != outcome_code:
            return self._reject(case_id, "conflicting_resolution_is_immutable")
        entry = {
            "event": "outcome_observed",
            "ts": _utc_now(),
            "case_id": case_id,
            "outcome_code": outcome_code,
            "evidence_url": evidence_url,
            "evidence_sha256": evidence_sha256.lower(),
            "adjudicator_id": adjudicator_id.strip(),
            "resolved_at": resolved_at or _utc_now(),
            "rationale": rationale.strip() if isinstance(rationale, str) and rationale.strip() else None,
            "registry_raw_sha256": self.registry.snapshot.raw_sha256,
            "registry_manifest_status": self.registry.snapshot.manifest_status,
        }
        self._append(entry)
        return entry

    def current_outcomes(self) -> dict[str, dict[str, Any]]:
        if not self.ledger_path.exists():
            return {}
        result: dict[str, dict[str, Any]] = {}
        for line_no, line in enumerate(self.ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ForecastContractError(f"ledger line {line_no} is invalid JSON") from exc
            if entry.get("event") != "outcome_observed":
                continue
            case_id = entry.get("case_id")
            if case_id not in {c["id"] for c in self.registry.cases}:
                raise ForecastContractError(f"ledger line {line_no} references unknown case")
            result[case_id] = entry
        return result

    def status(self) -> dict[str, int | str]:
        outcomes = self.current_outcomes()
        ledger_counts = {str(code): 0 for code in sorted(ALLOWED_OUTCOME_CODES)}
        for entry in outcomes.values():
            ledger_counts[str(entry["outcome_code"])] += 1
        registry_counts = {str(code): 0 for code in sorted(ALLOWED_OUTCOME_CODES)}
        for case in self.registry.cases:
            registry_counts[str(case["outcome_code"])] += 1
        return {
            "registry_cases": self.registry.snapshot.case_count,
            "registry_manifest_status": self.registry.snapshot.manifest_status,
            "registry_initial_unresolved": registry_counts["9"],
            "ledger_resolved_events": sum(ledger_counts[str(code)] for code in RESOLVED_OUTCOME_CODES),
            "ledger_unresolved_events": ledger_counts["9"],
            "resolved_events": sum(ledger_counts[str(code)] for code in RESOLVED_OUTCOME_CODES),
            **{f"registry_outcome_{code}": value for code, value in registry_counts.items()},
            **{f"ledger_outcome_{code}": value for code, value in ledger_counts.items()},
        }


__all__ = [
    "ALLOWED_OUTCOME_CODES",
    "ForecastContractError",
    "ForecastLedger",
    "ForecastRegistry",
    "RegistrySnapshot",
]
