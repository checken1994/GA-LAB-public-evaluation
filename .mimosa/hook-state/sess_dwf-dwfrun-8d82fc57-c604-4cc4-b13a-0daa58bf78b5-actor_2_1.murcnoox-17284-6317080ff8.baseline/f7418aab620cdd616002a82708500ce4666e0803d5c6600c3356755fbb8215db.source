import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from scp.epistemic.evidence_store import now_utc_iso


class KnowledgeControlDB:
    """
    Append-only authority for Knowledge Status Events and Promotion Decisions (P1-02).
    Enforces immutable history of epistemic state transitions.
    """
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_status_events (
                    event_id TEXT PRIMARY KEY,
                    knowledge_id TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    decision_id TEXT,
                    evidence_refs_json TEXT,
                    reason_codes_json TEXT,
                    timestamp TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS promotion_decisions (
                    decision_id TEXT PRIMARY KEY,
                    knowledge_id TEXT NOT NULL,
                    from_status TEXT,
                    requested_status TEXT,
                    decided_status TEXT,
                    decision_type TEXT NOT NULL,
                    verdict TEXT,
                    reason_codes_json TEXT,
                    evidence_refs_json TEXT,
                    missing_requirements_json TEXT,
                    missing_piece_refs_json TEXT,
                    contract_version TEXT,
                    policy_hash TEXT,
                    evaluated_at TEXT NOT NULL
                );
            """)  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim

    def record_promotion_decision(self, decision: dict[str, Any]) -> str:
        decision_id = decision.get("decision_id") or f"dec_{uuid.uuid4().hex}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO promotion_decisions (
                    decision_id, knowledge_id, from_status, requested_status,
                    decided_status, decision_type, verdict, reason_codes_json,
                    evidence_refs_json, missing_requirements_json, missing_piece_refs_json,
                    contract_version, policy_hash, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id,
                decision["knowledge_id"],
                decision.get("from_status"),
                decision.get("requested_status"),
                decision["decided_status"],
                decision["decision_type"],
                decision.get("verdict"),
                json.dumps(decision.get("reason_codes", [])),
                json.dumps(decision.get("evidence_refs", [])),
                json.dumps(decision.get("missing_requirements", [])),
                json.dumps(decision.get("missing_piece_refs", [])),
                decision.get("contract_version", "1"),
                decision.get("policy_hash", "unknown"),
                now_utc_iso()
            ))
        return decision_id

    def record_status_event(self, event: dict[str, Any]) -> str:
        """
        Append-only transition of a knowledge object.
        Cannot UPDATE historical rows.
        """
        event_id = event.get("event_id") or f"kse_{uuid.uuid4().hex}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO knowledge_status_events (
                    event_id, knowledge_id, from_status, to_status,
                    decision_id, evidence_refs_json, reason_codes_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event["knowledge_id"],
                event.get("from_status"),
                event["to_status"],
                event.get("decision_id"),
                json.dumps(event.get("evidence_refs", [])),
                json.dumps(event.get("reason_codes", [])),
                now_utc_iso()
            ))
        return event_id

    def get_knowledge_history(self, knowledge_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge_status_events WHERE knowledge_id = ? ORDER BY timestamp ASC",
                (knowledge_id,)
            ).fetchall()
            return [dict(r) for r in rows]

