import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum

from scp.contracts.time import now_utc_iso
from scp.knowledge.learning_db import LearningDB


class ExperimentStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

@dataclass
class ExperimentRecord:
    hypothesis_ref: str
    experiment_id: str = ""
    setup_instructions: list[str] = field(default_factory=list)
    sandbox_requirements: list[str] = field(default_factory=list)
    execution_status: ExperimentStatus | str = ExperimentStatus.PLANNED
    resulting_evidence_refs: list[str] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str = ""

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = f"exp_{uuid.uuid4().hex}"
        if not self.created_at:
            self.created_at = now_utc_iso()
        if isinstance(self.execution_status, str):
            self.execution_status = ExperimentStatus(self.execution_status.upper())

class ExperimentAuthority:
    """
    P1-08 / P1-09 Experiment Authority.
    Manages the planning and tracking of experiments in isolated sandboxes
    to test specific Hypotheses.
    """
    def __init__(self, db: LearningDB):
        self.db = db
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    hypothesis_ref TEXT NOT NULL,
                    setup_instructions_json TEXT,
                    sandbox_requirements_json TEXT,
                    execution_status TEXT,
                    resulting_evidence_refs_json TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT
                );
            """)

    def plan_experiment(self, record: ExperimentRecord) -> str:
        data = {
            "experiment_id": record.experiment_id,
            "hypothesis_ref": record.hypothesis_ref,
            "setup_instructions_json": json.dumps(record.setup_instructions),
            "sandbox_requirements_json": json.dumps(record.sandbox_requirements),
            "execution_status": record.execution_status.value,
            "resulting_evidence_refs_json": json.dumps(record.resulting_evidence_refs),
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "created_at": record.created_at
        }
        self.db.execute_insert("experiments", data)
        return record.experiment_id
