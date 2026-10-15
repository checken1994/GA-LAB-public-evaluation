"""Common event envelope (26-P0.2): every P0 subsystem emits this shape.

Unknown schema_version fails closed; serialization is canonical (stable JSON)
so envelopes can be hashed, chained or compared.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from scp.contracts.data_class import DataClass, parse_data_class
from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso

SCHEMA_VERSION = 1


@dataclass
class EventEnvelope:
    event_type: str
    actor_type: str
    actor_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None
    subject_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    policy_hash: str | None = None
    data_class: DataClass | str = DataClass.PUBLIC
    schema_version: int = SCHEMA_VERSION
    event_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unknown envelope schema_version {self.schema_version!r} - fail closed"
            )
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("event_type is required")
        self.data_class = parse_data_class(self.data_class)
        self.event_id = self.event_id or new_id("evt")
        self.timestamp = self.timestamp or now_utc_iso()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data_class"] = self.data_class.value
        payload["subject_refs"] = list(self.subject_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        return payload

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
