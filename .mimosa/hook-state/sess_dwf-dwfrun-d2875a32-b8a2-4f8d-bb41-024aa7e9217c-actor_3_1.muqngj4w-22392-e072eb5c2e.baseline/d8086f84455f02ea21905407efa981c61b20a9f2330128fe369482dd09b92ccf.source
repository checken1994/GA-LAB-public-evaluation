import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from scp.contracts.time import now_utc_iso
from scp.knowledge.learning_db import LearningDB


class QuestionTrigger(str, Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"
    CONTRADICTION = "CONTRADICTION"
    BLIND_SPOT = "BLIND_SPOT"

class QuestionStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    WAITING_EVIDENCE = "WAITING_EVIDENCE"
    EXPERIMENTABLE = "EXPERIMENTABLE"
    RESOLVED = "RESOLVED"

class MissingPieceKind(str, Enum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MISSING_OBSERVABILITY = "MISSING_OBSERVABILITY"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
    AMBIGUOUS_SCOPE = "AMBIGUOUS_SCOPE"

@dataclass
class MissingPieceRecord:
    question_id: str
    description: str
    kind: MissingPieceKind | str = MissingPieceKind.MISSING_EVIDENCE
    missing_piece_id: str = ""
    blocks_claims: list[str] = field(default_factory=list)
    blocks_decisions: list[str] = field(default_factory=list)
    needed_evidence: list[str] = field(default_factory=list)
    discovered_by: str = "open_question_authority"
    created_at: str = ""

    def __post_init__(self):
        if not self.missing_piece_id:
            self.missing_piece_id = f"mp_{uuid.uuid4().hex}"
        if not self.created_at:
            self.created_at = now_utc_iso()
        if isinstance(self.kind, str):
            self.kind = MissingPieceKind(self.kind.upper())

@dataclass
class OpenQuestionRecord:
    title: str
    question: str
    trigger: QuestionTrigger | str
    question_id: str = ""
    scope: dict[str, Any] = field(default_factory=dict)
    related_claim_refs: list[str] = field(default_factory=list)
    related_knowledge_refs: list[str] = field(default_factory=list)
    known_evidence_refs: list[str] = field(default_factory=list)
    needed_observations: list[str] = field(default_factory=list)
    needed_capabilities: list[str] = field(default_factory=list)
    status: QuestionStatus | str = QuestionStatus.OPEN
    created_at: str = ""

    def __post_init__(self):
        if not self.question_id:
            self.question_id = f"oq_{uuid.uuid4().hex}"
        if not self.created_at:
            self.created_at = now_utc_iso()
        if isinstance(self.trigger, str):
            self.trigger = QuestionTrigger(self.trigger.upper())
        if isinstance(self.status, str):
            self.status = QuestionStatus(self.status.upper())

class OpenQuestionAuthority:
    """
    P1-06 Open Question Authority.
    Formalizes unknowns into trackable questions and exact missing pieces,
    ensuring SCP knows *why* it doesn't know something.
    """
    def __init__(self, db: LearningDB):
        self.db = db

    def formulate_question(self, question: OpenQuestionRecord, missing_pieces: list[MissingPieceRecord]) -> str:
        # Link pieces to question
        for piece in missing_pieces:
            piece.question_id = question.question_id

        # Insert question
        q_data = {
            "question_id": question.question_id,
            "title": question.title,
            "question": question.question,
            "scope_json": json.dumps(question.scope),
            "trigger": question.trigger.value,
            "related_claim_refs_json": json.dumps(question.related_claim_refs),
            "related_knowledge_refs_json": json.dumps(question.related_knowledge_refs),
            "known_evidence_refs_json": json.dumps(question.known_evidence_refs),
            "needed_observations_json": json.dumps(question.needed_observations),
            "needed_capabilities_json": json.dumps(question.needed_capabilities),
            "status": question.status.value,
            "created_at": question.created_at
        }
        self.db.execute_insert("open_questions", q_data)

        # Insert pieces
        for piece in missing_pieces:
            p_data = {
                "missing_piece_id": piece.missing_piece_id,
                "question_id": piece.question_id,
                "kind": piece.kind.value,
                "description": piece.description,
                "blocks_claims_json": json.dumps(piece.blocks_claims),
                "blocks_decisions_json": json.dumps(piece.blocks_decisions),
                "needed_evidence_json": json.dumps(piece.needed_evidence),
                "discovered_by": piece.discovered_by,
                "created_at": piece.created_at
            }
            self.db.execute_insert("missing_pieces", p_data)

        return question.question_id
