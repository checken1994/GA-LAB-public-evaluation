import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum

from scp.contracts.time import now_utc_iso
from scp.knowledge.learning_db import LearningDB


class BenchmarkStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

@dataclass
class BenchmarkRunRecord:
    benchmark_id: str
    target_capabilities: list[str]
    run_id: str = ""
    status: BenchmarkStatus | str = BenchmarkStatus.SCHEDULED
    score: float | None = None
    regression_detected: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.run_id:
            self.run_id = f"bmr_{uuid.uuid4().hex}"
        if not self.created_at:
            self.created_at = now_utc_iso()
        if isinstance(self.status, str):
            self.status = BenchmarkStatus(self.status.upper())

class BenchmarkAuthority:
    """
    P1-11 Benchmark Testing Authority.
    Prevents catastrophic forgetting by scheduling and tracking benchmarks
    before/after learning lessons.
    """
    def __init__(self, db: LearningDB):
        self.db = db
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    run_id TEXT PRIMARY KEY,
                    benchmark_id TEXT NOT NULL,
                    target_capabilities_json TEXT,
                    status TEXT,
                    score REAL,
                    regression_detected INTEGER,
                    evidence_refs_json TEXT,
                    created_at TEXT
                );
            """)

    def schedule_benchmark(self, record: BenchmarkRunRecord) -> str:
        data = {
            "run_id": record.run_id,
            "benchmark_id": record.benchmark_id,
            "target_capabilities_json": json.dumps(record.target_capabilities),
            "status": record.status.value,
            "score": record.score,
            "regression_detected": 1 if record.regression_detected else 0,
            "evidence_refs_json": json.dumps(record.evidence_refs),
            "created_at": record.created_at
        }
        self.db.execute_insert("benchmark_runs", data)
        return record.run_id
