from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidenceContractError(ValueError):
    """Raised when an external evidence record violates the contract."""


@dataclass(frozen=True)
class EvidenceRecord:
    subject_id: str
    lineage: str
    kind: str
    locator: str
    observed_claim: str
    independent_of: str
    status: str = "verified"
    locator_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "lineage": self.lineage,
            "kind": self.kind,
            "locator": self.locator,
            "observed_claim": self.observed_claim,
            "independent_of": self.independent_of,
            "status": self.status,
            "locator_sha256": self.locator_sha256,
        }


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_record(record: EvidenceRecord) -> None:
    if not record.subject_id or not record.lineage or not record.locator:
        raise EvidenceContractError("subject, lineage and locator are required")
    if not record.observed_claim:
        raise EvidenceContractError("observed claim is required")
    if record.independent_of == record.subject_id:
        raise EvidenceContractError("evidence cannot claim independence from itself")
    if record.status != "verified":
        raise EvidenceContractError("only verified records may enter the ledger")
    if record.kind not in {"official_document", "independent_runtime", "independent_adjudication"}:
        raise EvidenceContractError("unsupported evidence kind")


def append_record(path: str | Path, record: EvidenceRecord) -> dict[str, Any]:
    validate_record(record)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    previous_hash = "GENESIS"
    if target.exists():
        last = target.read_text(encoding="utf-8").splitlines()
        if last:
            previous_hash = json.loads(last[-1])["record_hash"]
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "previous_hash": previous_hash,
        "record": record.as_dict(),
    }
    payload["record_hash"] = _hash(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def promotion_evidence(path: str | Path, subject_id: str) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"eligible": False, "reason": "NO_EVIDENCE_LEDGER", "lineages": []}
    rows = [json.loads(line)["record"] for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [row for row in rows if row["subject_id"] == subject_id and row["status"] == "verified"]
    lineages = sorted({row["lineage"] for row in records})
    kinds = sorted({row["kind"] for row in records})
    eligible = len(lineages) >= 2 and "official_document" in kinds and "independent_runtime" in kinds
    return {
        "eligible": eligible,
        "subject_id": subject_id,
        "record_count": len(records),
        "lineages": lineages,
        "kinds": kinds,
        "reason": "OK" if eligible else "NEED_TWO_INDEPENDENT_LINEAGES_AND_EXTERNAL_RUNTIME",
    }


__all__ = ["EvidenceContractError", "EvidenceRecord", "append_record", "promotion_evidence", "validate_record"]
