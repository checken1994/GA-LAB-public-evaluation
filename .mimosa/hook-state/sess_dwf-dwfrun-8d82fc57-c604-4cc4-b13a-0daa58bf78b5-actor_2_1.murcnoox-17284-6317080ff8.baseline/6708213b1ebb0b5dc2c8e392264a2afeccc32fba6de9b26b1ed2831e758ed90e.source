import json
import uuid
from dataclasses import dataclass, field
from enum import Enum

from scp.contracts.time import now_utc_iso
from scp.knowledge.learning_db import LearningDB


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    EXPERIMENTING = "EXPERIMENTING"
    SUPPORTED = "SUPPORTED"
    CONTRADICTION = "CONTRADICTION"
    INSUFFICIENT = "INSUFFICIENT"

@dataclass
class HypothesisRecord:
    question_ref: str
    hypothesis: str
    mechanism: str
    hypothesis_id: str = ""
    predictions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    needed_capabilities: list[str] = field(default_factory=list)
    status: HypothesisStatus | str = HypothesisStatus.PROPOSED
    created_at: str = ""

    def __post_init__(self):
        if not self.hypothesis_id:
            self.hypothesis_id = f"hyp_{uuid.uuid4().hex}"
        if not self.created_at:
            self.created_at = now_utc_iso()
        if isinstance(self.status, str):
            # Map CONTRADICTED -> CONTRADICTION if user provided it
            if self.status.upper() == "CONTRADICTED":
                self.status = HypothesisStatus.CONTRADICTION
            else:
                self.status = HypothesisStatus(self.status.upper())

class HypothesisAuthority:
    """
    P1-07 Hypothesis Authority.
    Formalizes testable hypotheses for Open Questions.
    """
    def __init__(self, db: LearningDB):
        self.db = db

    def propose(self, record: HypothesisRecord) -> str:
        h_data = {
            "hypothesis_id": record.hypothesis_id,
            "question_ref": record.question_ref,
            "hypothesis": record.hypothesis,
            "mechanism": record.mechanism,
            "predictions_json": json.dumps(record.predictions),
            "assumptions_json": json.dumps(record.assumptions),
            "needed_capabilities_json": json.dumps(record.needed_capabilities),
            "status": record.status.value,
            "created_at": record.created_at
        }
        self.db.execute_insert("hypotheses", h_data)
        return record.hypothesis_id
