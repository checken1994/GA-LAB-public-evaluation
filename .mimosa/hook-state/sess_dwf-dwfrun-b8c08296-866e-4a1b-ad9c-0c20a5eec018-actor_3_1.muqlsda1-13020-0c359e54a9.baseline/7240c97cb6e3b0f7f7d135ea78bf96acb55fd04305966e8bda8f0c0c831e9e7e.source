import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from scp.knowledge.knowledge_control_db import KnowledgeControlDB

logger = logging.getLogger(__name__)


class VolatilityClass(str, Enum):
    STATIC = "STATIC"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    REALTIME = "REALTIME"
    EVENT_BOUND = "EVENT_BOUND"

@dataclass
class RevalidationPolicy:
    volatility_class: VolatilityClass | str
    review_after_seconds: int
    max_staleness_seconds: int
    required_evidence_type: str = "ANY"
    required_reality_level: str = "ANY"
    on_stale: str = "UNDER_REVIEW"
    policy_id: str = ""

    def __post_init__(self):
        if not self.policy_id:
            self.policy_id = f"revp_{uuid.uuid4().hex}"
        if isinstance(self.volatility_class, str):
            self.volatility_class = VolatilityClass(self.volatility_class.upper())

class RevalidationAuthority:
    """
    P1-05 Revalidation Authority.
    Ensures knowledge doesn't silently stay VERIFIED when it's stale.
    Transitions stale VERIFIED/GOLD knowledge to UNDER_REVIEW.
    """
    def __init__(self, db: KnowledgeControlDB):
        self.db = db
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS revalidation_jobs (
                    job_id TEXT PRIMARY KEY,
                    knowledge_id TEXT NOT NULL,
                    policy_id TEXT,
                    status TEXT,
                    scheduled_for TEXT,
                    executed_at TEXT,
                    new_evidence_refs_json TEXT,
                    result_action TEXT
                );
            """)

    def assess_staleness(self, knowledge_last_verified: str, policy: RevalidationPolicy) -> bool:
        """Returns True if the knowledge should be flagged as stale."""
        try:
            last_dt = datetime.fromisoformat(knowledge_last_verified.replace("Z", "+00:00"))
        except ValueError:
            logger.debug('RevalidationAuthority.assess_staleness: ValueError ignored', exc_info=True)
            return True # Malformed date means we re-verify

        now = datetime.now(timezone.utc)
        age_seconds = (now - last_dt).total_seconds()

        return age_seconds > policy.review_after_seconds

    def schedule_revalidation(self, knowledge_id: str, policy: RevalidationPolicy, scheduled_for: str) -> str:
        job_id = f"revj_{uuid.uuid4().hex}"
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute("""
                INSERT INTO revalidation_jobs (
                    job_id, knowledge_id, policy_id, status, scheduled_for
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                job_id, knowledge_id, policy.policy_id, "SCHEDULED", scheduled_for
            ))
        return job_id
