import re
import sqlite3
from pathlib import Path
from typing import Any

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

ALLOWED_TABLE_COLUMNS: dict[str, set[str]] = {
    "open_questions": {
        "question_id", "title", "question", "scope_json", "trigger",
        "related_claim_refs_json", "related_knowledge_refs_json",
        "known_evidence_refs_json", "needed_observations_json",
        "needed_capabilities_json", "status", "created_at",
    },
    "missing_pieces": {
        "missing_piece_id", "question_id", "kind", "description",
        "blocks_claims_json", "blocks_decisions_json",
        "needed_evidence_json", "discovered_by", "created_at",
    },
    "hypotheses": {
        "hypothesis_id", "question_ref", "hypothesis", "mechanism",
        "predictions_json", "assumptions_json",
        "needed_capabilities_json", "status", "created_at",
    },
    "benchmark_runs": {
        "run_id", "benchmark_id", "target_capabilities_json",
        "status", "score", "regression_detected",
        "evidence_refs_json", "created_at",
    },
    "experiments": {
        "experiment_id", "hypothesis_ref", "setup_instructions_json",
        "sandbox_requirements_json", "execution_status",
        "resulting_evidence_refs_json", "started_at", "completed_at",
        "created_at",
    },
    "lessons": {
        "lesson_id", "experiment_refs_json", "insights_json",
        "knowledge_updates_json", "capability_updates_json",
        "created_at",
    },
}

class LearningDB:
    """
    Manages the data/cognitive/learning.sqlite database.
    Stores open_questions, missing_pieces, hypotheses, experiments, lessons.
    Append-only principle for all historical truth logs.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS open_questions (
                    question_id TEXT PRIMARY KEY,
                    title TEXT,
                    question TEXT,
                    scope_json TEXT,
                    trigger TEXT,
                    related_claim_refs_json TEXT,
                    related_knowledge_refs_json TEXT,
                    known_evidence_refs_json TEXT,
                    needed_observations_json TEXT,
                    needed_capabilities_json TEXT,
                    status TEXT,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS missing_pieces (
                    missing_piece_id TEXT PRIMARY KEY,
                    question_id TEXT NOT NULL,
                    kind TEXT,
                    description TEXT,
                    blocks_claims_json TEXT,
                    blocks_decisions_json TEXT,
                    needed_evidence_json TEXT,
                    discovered_by TEXT,
                    created_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS hypotheses (
                    hypothesis_id TEXT PRIMARY KEY,
                    question_ref TEXT NOT NULL,
                    hypothesis TEXT,
                    mechanism TEXT,
                    predictions_json TEXT,
                    assumptions_json TEXT,
                    needed_capabilities_json TEXT,
                    status TEXT,
                    created_at TEXT
                );
            """)  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim

    def execute_insert(self, table: str, data: dict[str, Any]):
        if not isinstance(table, str) or not _IDENTIFIER_RE.match(table):
            raise ValueError(f"Invalid table identifier format: {table!r}")
        if table not in ALLOWED_TABLE_COLUMNS:
            raise ValueError(f"Table not permitted in LearningDB allowlist: {table!r}")
        if not data:
            return

        allowed_cols = ALLOWED_TABLE_COLUMNS[table]
        for col in data.keys():
            if not isinstance(col, str) or not _IDENTIFIER_RE.match(col):
                raise ValueError(f"Invalid column identifier format: {col!r}")
            if col not in allowed_cols:
                raise ValueError(f"Column '{col}' is not allowed for table '{table}'")

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = tuple(data.values())

        with sqlite3.connect(self.db_path) as conn:
            # `table` and every column are regex-validated AND checked against the
            # hardcoded ALLOWED_TABLE_COLUMNS allowlist above; values are bound via
            # `?` placeholders (identifiers cannot be parameterized in SQLite).
            conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)  # nosec B608 — table/cols allowlisted above, values bound via `?` placeholders
