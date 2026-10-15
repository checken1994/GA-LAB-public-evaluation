"""Knowledge Ontology v1 (26-P0.3): the knowledge authority must know WHAT
kind of object it stores. Prevents the warehouse from degrading into a list
of strings or arbitrary vector chunks.

v1 = schema authority + status-transition invariants + round-trip semantics.
The promotion ENGINE (evidence-gated pipeline) is 26-P1; this module already
enforces the hard edges (RAW never jumps to GOLD, GOLD requires evidence).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from scp.contracts.data_class import DataClass, parse_data_class
from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso

ONTOLOGY_VERSION = "1.0"


class KnowledgeType(str, Enum):
    # P0 formalized types
    CLAIM = "CLAIM"
    FACT = "FACT"
    CONCEPT = "CONCEPT"
    PROCEDURE = "PROCEDURE"
    HEURISTIC = "HEURISTIC"
    PATTERN = "PATTERN"
    ANTI_PATTERN = "ANTI_PATTERN"
    FAILURE_MODE = "FAILURE_MODE"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    DECISION_TRACE = "DECISION_TRACE"
    PLAYBOOK = "PLAYBOOK"
    CAUSAL_MODEL = "CAUSAL_MODEL"
    OPEN_QUESTION = "OPEN_QUESTION"
    # IDs reserved now, formalized deeper in 26-P1
    EXPERIMENT = "EXPERIMENT"
    LESSON_LEARNED = "LESSON_LEARNED"
    BENCHMARK = "BENCHMARK"
    HUMAN_WORKFLOW = "HUMAN_WORKFLOW"


class KnowledgeStatus(str, Enum):
    RAW = "RAW"
    CURATED = "CURATED"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"
    GOLD = "GOLD"
    UNDER_REVIEW = "UNDER_REVIEW"
    DEMOTED = "DEMOTED"
    RETIRED = "RETIRED"


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "RAW": {"CURATED", "UNDER_REVIEW", "RETIRED"},
    "CURATED": {"CORROBORATED", "UNDER_REVIEW", "RETIRED"},
    "CORROBORATED": {"VERIFIED", "UNDER_REVIEW", "RETIRED"},
    "VERIFIED": {"GOLD", "UNDER_REVIEW", "RETIRED"},
    "GOLD": {"UNDER_REVIEW", "RETIRED"},
    "UNDER_REVIEW": {"CURATED", "CORROBORATED", "VERIFIED", "GOLD", "DEMOTED", "RETIRED"},
    "DEMOTED": {"CURATED", "UNDER_REVIEW", "RETIRED"},
    "RETIRED": set(),
}


class KnowledgeRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVED_FROM = "DERIVED_FROM"
    SUPERSEDES = "SUPERSEDES"
    APPLIES_TO = "APPLIES_TO"
    COUNTEREXAMPLE_OF = "COUNTEREXAMPLE_OF"
    MITIGATES = "MITIGATES"
    CAUSES = "CAUSES"
    DEPENDS_ON = "DEPENDS_ON"


def parse_type(value: object) -> KnowledgeType:
    raw = value.value if isinstance(value, KnowledgeType) else str(value).strip().upper()
    try:
        return KnowledgeType(raw)
    except ValueError as exc:
        raise ValueError(f"unknown knowledge type: {value!r}") from exc


def parse_status(value: object) -> KnowledgeStatus:
    raw = value.value if isinstance(value, KnowledgeStatus) else str(value).strip().upper()
    try:
        return KnowledgeStatus(raw)
    except ValueError as exc:
        raise ValueError(f"unknown knowledge status: {value!r}") from exc


def parse_relation(value: object) -> KnowledgeRelation:
    raw = value.value if isinstance(value, KnowledgeRelation) else str(value).strip().upper()
    try:
        return KnowledgeRelation(raw)
    except ValueError as exc:
        raise ValueError(f"invalid knowledge relation: {value!r}") from exc


def validate_transition(current: object, next_status: object) -> None:
    current_status = parse_status(current)
    target = parse_status(next_status)
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status.value, set())
    if target.value not in allowed:
        raise ValueError(
            f"invalid knowledge status transition {current_status.value} -> {target.value} "
            f"(RAW can never jump to GOLD; promotion must walk the ladder)"
        )


@dataclass
class KnowledgeObject:
    type: KnowledgeType | str
    title: str
    content: dict[str, Any]
    knowledge_id: str = ""
    ontology_version: str = ONTOLOGY_VERSION
    scope: dict[str, Any] = field(default_factory=dict)
    status: KnowledgeStatus | str = KnowledgeStatus.RAW
    evidence_refs: list[str] = field(default_factory=list)
    independent_lineages: int = 0
    confidence: float | None = None
    validity: dict[str, Any] = field(default_factory=dict)
    data_class: DataClass | str = DataClass.PUBLIC
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.type = parse_type(self.type)
        self.status = parse_status(self.status)
        self.data_class = parse_data_class(self.data_class)
        self.knowledge_id = self.knowledge_id or new_id("kn")
        if not self.created_at:
            self.created_at = now_utc_iso()
        if not self.updated_at:
            self.updated_at = self.created_at
        validate_object(self)


def validate_object(obj: KnowledgeObject) -> None:
    if obj.ontology_version != ONTOLOGY_VERSION:
        raise ValueError(
            f"ontology_version mismatch: object={obj.ontology_version!r}, authority={ONTOLOGY_VERSION!r}"
        )
    if not obj.title or not isinstance(obj.title, str):
        raise ValueError("knowledge object requires a non-empty title")
    if not isinstance(obj.content, dict) or not obj.content:
        raise ValueError("knowledge content must be a non-empty structured object, not free text")
    if obj.status is KnowledgeStatus.GOLD and not obj.evidence_refs:
        raise ValueError("GOLD knowledge requires evidence references (GOLD != eternal truth)")
    if obj.confidence is not None and not (0.0 <= float(obj.confidence) <= 1.0):
        raise ValueError("confidence must be within [0.0, 1.0] or None")
    if int(obj.independent_lineages) < 0:
        raise ValueError("independent_lineages cannot be negative")


def validate_transition_object(obj: KnowledgeObject, next_status: object) -> None:
    validate_transition(obj.status, next_status)


def to_json(obj: KnowledgeObject) -> str:
    payload = asdict(obj)
    # Normalize through the parsers so str-assigned enum fields serialize as
    # canonical values even if callers bypassed __post_init__ normalization.
    payload["type"] = parse_type(obj.type).value
    payload["status"] = parse_status(obj.status).value
    payload["data_class"] = parse_data_class(obj.data_class).value
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def from_json(raw: str | bytes) -> KnowledgeObject:
    payload = json.loads(raw)
    return KnowledgeObject(
        type=payload["type"],
        title=payload["title"],
        content=payload["content"],
        knowledge_id=payload["knowledge_id"],
        ontology_version=payload["ontology_version"],
        scope=payload.get("scope") or {},
        status=payload["status"],
        evidence_refs=list(payload.get("evidence_refs") or []),
        independent_lineages=int(payload.get("independent_lineages") or 0),
        confidence=payload.get("confidence"),
        validity=payload.get("validity") or {},
        data_class=payload["data_class"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
    )
