"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

#!/usr/bin/env python3
"""
SCP V14 — PHASE 0 (Audit Trail)
=================================
5 tables để track toàn bộ decision trail:
  1. evidences         — mọi evidence thu thập (API values, AI answers, anchor checks)
  2. conclusions       — verdict cuối cùng của mỗi process()
  3. decision_history  — lịch sử decision (chaining conclusions)
  4. reason_chains     — multi-hop reasoning (question → steps → answer)
  5. evidence_links    — link evidence ↔ conclusion (many-to-many)

Quy trình:
  Question → collect evidences → reason_chain → conclusion → link evidences

Query hữu ích:
  - Tại sao FAIL câu X? → SELECT * FROM conclusions WHERE question LIKE '%X%'
    → lấy conclusion_id → SELECT * FROM evidence_links → SELECT * FROM evidences
"""
import hashlib
import json
import os
import sqlite3  # kept for sqlite3.IntegrityError exception class
import uuid
from datetime import datetime
from typing import Any

_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import logging

# [FIX-CRIT-135 BUG 3] TẠI SAO: phase0.py used to define its OWN module-level
# db_exec/db_query_all/db_query_one (lines 53-91) that opened a NEW sqlite3
# connection per call with NO _db_lock. This shadowed db_manager's canonical
# thread-safe versions → every Phase0 write/read raced with Brain writes
# (Invariant #7 violation). Naming collision was also a footgun: callers
# importing `from scp.core.phase0 import db_exec` got the UNSAFE version.
# Fix: re-export the canonical db_manager functions (single global _db_lock,
# cached per-path connection). Phase0's call sites stay the same; only the
# binding changes. FK enforcement: db_manager's persistent/per-path conns
# have PRAGMA foreign_keys=ON (added in BUG 4) so FK constraints still hold.
from scp.core.db_manager import db_exec, db_query_all, db_query_one

# [EXEC-1 B1] TẠI SAO: phase0.py also defined its own `get_db()` (was at the
# bottom of the file) that opened a NEW sqlite3.connect(DB_PATH) per call,
# bypassing _db_lock AND skipping the V42 PRAGMA tuning (WAL, cache_size,
# synchronous=NORMAL, etc.). That shadow made `from scp.core.phase0 import
# get_db` return the SLOW UNSAFE version, while `from scp.core.db_manager
# import get_db` returned the canonical thread-safe one. Two `get_db`s in
# the same package = footgun. Fix: import the canonical get_db from
# db_manager (re-export) so both paths return the same function. Also
# removes the duplicate bare-sqlite3.connect in init_phase0_schema —
# schema init now goes through get_db() (still cached, still WAL-tuned).
from scp.core.db_manager import get_db as _canonical_get_db

logger = logging.getLogger("scp.core.phase0")


def init_phase0_schema():
    """Tạo 5 tables Phase 0 trong v13.db."""
    try:
        # [EXEC-1 B1] was: bare `sqlite3.connect(DB_PATH)` → bypassed _db_lock
        # AND skipped V42 PRAGMA tuning. Now uses canonical get_db() from
        # db_manager (cached persistent conn, WAL, FK enforced, _db_lock held).
        # DDL is idempotent (IF NOT EXISTS) so safe to share the same conn.
        conn = _canonical_get_db()
        cursor = conn.cursor()

        # Table 1: evidences — mọi evidence thu thập (with TEXT id for string keys)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidences (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                source TEXT,
                entity TEXT,
                attribute TEXT,
                value TEXT,
                confidence REAL DEFAULT 0.5,
                raw_data TEXT,
                verification_status TEXT DEFAULT 'UNVERIFIED',
                verification_by TEXT,
                verification_time TEXT,
                sha256 TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidences_type ON evidences(evidence_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidences_entity ON evidences(entity, attribute)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidences_source ON evidences(source)")

        # Table 2: conclusions — verdict cuối cùng
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conclusions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                ai_answer TEXT,
                verdict TEXT NOT NULL,
                confidence REAL,
                domain TEXT,
                reasoning TEXT,
                cycle_count INTEGER,
                current_reason_chain_id TEXT,
                sha256 TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conclusions_verdict ON conclusions(verdict)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conclusions_domain ON conclusions(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conclusions_question ON conclusions(question)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conclusions_sha256 ON conclusions(sha256)")

        # Table 3: decision_history — chaining conclusions (TRIGGER to prevent UPDATE/DELETE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                conclusion_id TEXT NOT NULL,
                action TEXT NOT NULL,
                prev_conclusion_id TEXT,
                notes TEXT,
                FOREIGN KEY (conclusion_id) REFERENCES conclusions(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_conclusion ON decision_history(conclusion_id)")

        # TRIGGER to prevent UPDATE on decision_history
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_update_decision
            BEFORE UPDATE ON decision_history
            BEGIN
                SELECT RAISE(ABORT, 'Updates to decision_history are not allowed');
            END
        """)

        # TRIGGER to prevent DELETE on decision_history
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_delete_decision
            BEFORE DELETE ON decision_history
            BEGIN
                SELECT RAISE(ABORT, 'Deletes from decision_history are not allowed');
            END
        """)

        # Table 4: reason_chains — multi-hop reasoning (with TEXT id and state)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reason_chains (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                conclusion_id TEXT,
                steps_json TEXT NOT NULL,
                total_steps INTEGER,
                verified_by TEXT,
                state TEXT DEFAULT 'WEAKENED',
                FOREIGN KEY (conclusion_id) REFERENCES conclusions(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reason_conclusion ON reason_chains(conclusion_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reason_state ON reason_chains(state)")

        # Table 5: evidence_links — many-to-many evidences ↔ conclusions (with TEXT ids and FK)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_links (
                id TEXT PRIMARY KEY,
                chain_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                role TEXT,
                confidence REAL DEFAULT 0.5,
                note TEXT,
                added_at TEXT,
                added_by TEXT,
                addressed INTEGER DEFAULT 0,
                FOREIGN KEY (chain_id) REFERENCES reason_chains(id),
                FOREIGN KEY (evidence_id) REFERENCES evidences(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elinks_chain ON evidence_links(chain_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_elinks_evidence ON evidence_links(evidence_id)")

        # TRIGGER to update reason_chains.state when evidence_links change
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_chain_state_after_insert
            AFTER INSERT ON evidence_links
            BEGIN
                UPDATE reason_chains SET state = 'WEAKENED' WHERE id = NEW.chain_id;
            END
        """)

        # [EXEC-1 B1] commit but DO NOT close — get_db() returns a SHARED
        # persistent connection (cached in db_manager). Closing it would
        # break every other module that uses db_exec / db_query_*. The
        # connection itself is _db_lock-protected so commit is safe.
        conn.commit()
        logger.info("Phase 0 schema initialized (5 tables)")
    except Exception as e:
        logger.warning(f"Phase 0 init failed: {e}", exc_info=True)


class Phase0Store:
    """Quản lý audit trail Phase 0."""

    @staticmethod
    def add_evidence(evidence_type: str, source: str = "", entity: str = "",
                     attribute: str = "", value: Any = None, confidence: float = 0.5,
                     raw_data: Any = None) -> str:
        """Add evidence to evidences table. Returns evidence_id (UUID)."""
        ts = datetime.now().isoformat()
        value_str = str(value) if value is not None else ""
        raw_str = json.dumps(raw_data, default=str)[:2000] if raw_data else ""
        sha = hashlib.sha256(f"{evidence_type}|{source}|{entity}|{attribute}|{value_str}".encode()).hexdigest()[:16]
        evidence_id = str(uuid.uuid4())
        try:
            db_exec("""
                INSERT INTO evidences
                (id, timestamp, evidence_type, source, entity, attribute, value, confidence, raw_data, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (evidence_id, ts, evidence_type, source, entity, attribute, value_str, confidence, raw_str, sha))
            return evidence_id
        except Exception as e:
            logger.warning(f"add_evidence failed: {e}", exc_info=True)
            return ""

    @staticmethod
    def add_conclusion(question: str, ai_answer: str, verdict: str,
                       confidence: float = 0.0, domain: str = "", reasoning: str = "",
                       cycle_count: int = 0) -> str:
        """Add conclusion to conclusions table. Returns conclusion_id (UUID)."""
        ts = datetime.now().isoformat()
        sha = hashlib.sha256(f"{question}|{ai_answer}|{verdict}|{cycle_count}".encode()).hexdigest()[:16]
        conclusion_id = str(uuid.uuid4())
        try:
            db_exec("""
                INSERT INTO conclusions
                (id, timestamp, question, ai_answer, verdict, confidence, domain, reasoning, cycle_count, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (conclusion_id, ts, question, ai_answer[:500] if ai_answer else "", verdict, confidence,
                  domain, reasoning[:500] if reasoning else "", cycle_count, sha))
            return conclusion_id
        except Exception as e:
            logger.warning(f"add_conclusion failed: {e}", exc_info=True)
            return ""

    @staticmethod
    def link_evidence(conclusion_id, evidence_id, weight: float = 1.0, role: str = "") -> str:
        """Link evidence to conclusion (many-to-many). Returns the link_id (UUID)."""
        conclusion_str = str(conclusion_id) if not isinstance(conclusion_id, str) else conclusion_id
        evidence_str = str(evidence_id) if not isinstance(evidence_id, str) else evidence_id
        if not conclusion_str or not evidence_str or conclusion_str == "-1" or evidence_str == "-1":
            return ""
        link_id = str(uuid.uuid4())
        chain_id = str(uuid.uuid4())
        ts = datetime.now().isoformat()
        try:
            # [FIX] Create a reason_chain first (FK: evidence_links.chain_id → reason_chains.id)
            db_exec("""
                INSERT INTO reason_chains (id, timestamp, question, conclusion_id, steps_json, total_steps)
                VALUES (?, ?, '', ?, '[]', 0)
            """, (chain_id, ts, conclusion_str))
            # Then create the evidence_link referencing the chain
            db_exec("""
                INSERT INTO evidence_links (id, chain_id, evidence_id, weight, role, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (link_id, chain_id, evidence_str, weight, role, ts))
            return link_id
        except Exception as e:
            logger.warning(f"link_evidence failed: {e}", exc_info=True)
            return ""

    @staticmethod
    def add_decision(conclusion_id, action: str, prev_conclusion_id=None, notes: str = ""):
        """Record a decision (e.g., 'promote_to_kb', 'reject', 'flag_for_review')."""
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                INSERT INTO decision_history
                (timestamp, conclusion_id, action, prev_conclusion_id, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (ts, str(conclusion_id), action, str(prev_conclusion_id) if prev_conclusion_id else None, notes[:500]))
        except Exception as e:
            logger.warning(f"add_decision failed: {e}", exc_info=True)

    @staticmethod
    def add_reason_chain(question: str, steps: list[dict], conclusion_id=None) -> str:
        """Record a reasoning chain (multi-hop)."""
        ts = datetime.now().isoformat()
        steps_json = json.dumps(steps, default=str)[:5000]
        chain_id = str(uuid.uuid4())
        try:
            db_exec("""
                INSERT INTO reason_chains
                (id, timestamp, question, conclusion_id, steps_json, total_steps)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chain_id, ts, question, str(conclusion_id) if conclusion_id else None, steps_json, len(steps)))
            return chain_id
        except Exception as e:
            logger.warning(f"add_reason_chain failed: {e}", exc_info=True)
            return ""

    @staticmethod
    def get_conclusion_with_evidences(conclusion_id) -> dict:
        """Get conclusion + all linked evidences (for audit)."""
        try:
            concl = db_query_one("SELECT * FROM conclusions WHERE id = ?", (str(conclusion_id),))
            if not concl:
                return {}
            evidences = db_query_all("""
                SELECT e.* FROM evidences e
                JOIN evidence_links el ON e.id = el.evidence_id
                WHERE el.chain_id = ?
                ORDER BY el.weight DESC
            """, (str(conclusion_id),))
            decisions = db_query_all(
                "SELECT * FROM decision_history WHERE conclusion_id = ? ORDER BY timestamp",
                (str(conclusion_id),)
            )
            return {"conclusion": concl, "evidences": evidences, "decisions": decisions}
        except Exception as e:
            logger.debug(f"get_conclusion_with_evidences ignored: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def get_stats() -> dict:
        """Get Phase 0 stats."""
        try:
            stats = {}
            for table in ['evidences', 'conclusions', 'decision_history', 'reason_chains', 'evidence_links']:
                row = db_query_one(f"SELECT COUNT(*) as cnt FROM {table}")  # nosec B608 — input validated by SCP whitelist  # noqa: S608
                stats[table] = row["cnt"] if row else 0
            verdicts = db_query_all("SELECT verdict, COUNT(*) as cnt FROM conclusions GROUP BY verdict ORDER BY cnt DESC")
            stats['by_verdict'] = {r['verdict']: r['cnt'] for r in verdicts}
            etypes = db_query_all("SELECT evidence_type, COUNT(*) as cnt FROM evidences GROUP BY evidence_type ORDER BY cnt DESC")
            stats['by_evidence_type'] = {r['evidence_type']: r['cnt'] for r in etypes}
            return stats
        except Exception as e:
            logger.debug(f"get_stats ignored: {e}", exc_info=True)
            return {"error": str(e)}


class EvidenceStore:
    """Store for evidences table with string IDs."""

    @staticmethod
    def insert(evidence_id: str, evidence_type: str, raw_data: Any,
               source: str = "", access_method: str = "") -> bool:
        """Insert an evidence record. Returns True if inserted."""
        ts = datetime.now().isoformat()
        raw_str = json.dumps(raw_data, default=str)[:2000] if raw_data else ""
        sha = hashlib.sha256(f"{evidence_id}|{evidence_type}|{raw_str}".encode()).hexdigest()[:16]
        try:
            db_exec("""
                INSERT INTO evidences (id, timestamp, evidence_type, source, raw_data, sha256, verification_status)
                VALUES (?, ?, ?, ?, ?, ?, 'UNVERIFIED')
            """, (evidence_id, ts, evidence_type, source, raw_str, sha))
            return True
        except sqlite3.IntegrityError as exc:
            # silent-by-design: duplicate id is an expected idempotent no-op; False signals "not inserted".
            logger.debug("phase0: insert skipped (integrity conflict): %s", exc, exc_info=True)
            return False
        except Exception as e:
            logger.warning(f"EvidenceStore.insert failed: {e}", exc_info=True)
            return False

    @staticmethod
    def get(evidence_id: str) -> dict | None:
        """Get evidence by ID."""
        return db_query_one("SELECT * FROM evidences WHERE id = ?", (evidence_id,))

    @staticmethod
    def verify(evidence_id: str, by: str = "") -> bool:
        """Mark evidence as VERIFIED."""
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                UPDATE evidences
                SET verification_status = 'VERIFIED', verification_by = ?, verification_time = ?
                WHERE id = ?
            """, (by, ts, evidence_id))
            # Recalculate chain state
            ChainStateService.recalculate_chain_states_for_evidence(evidence_id)
            return True
        except Exception as e:
            logger.warning(f"EvidenceStore.verify failed: {e}", exc_info=True)
            return False

    @staticmethod
    def fail(evidence_id: str) -> bool:
        """Mark evidence as FAILED."""
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                UPDATE evidences
                SET verification_status = 'FAILED', verification_time = ?
                WHERE id = ?
            """, (ts, evidence_id))
            # Recalculate chain state
            ChainStateService.recalculate_chain_states_for_evidence(evidence_id)
            return True
        except Exception as e:
            logger.warning(f"EvidenceStore.fail failed: {e}", exc_info=True)
            return False

    @staticmethod
    def supersede(old_evidence_id: str, new_evidence_id: str) -> bool:
        """Mark old evidence as superseded by new one."""
        # Check if old evidence exists
        old = db_query_one("SELECT id FROM evidences WHERE id = ?", (old_evidence_id,))
        if not old:
            return False
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                UPDATE evidences
                SET verification_status = 'SUPERSEDED', verification_time = ?
                WHERE id = ?
            """, (ts, old_evidence_id))
            ChainStateService.recalculate_chain_states_for_evidence(old_evidence_id)
            return True
        except Exception as e:
            logger.warning(f"EvidenceStore.supersede failed: {e}", exc_info=True)
            return False


# ============================================================
# CONCLUSION STORE — For test compatibility
# ============================================================
class ConclusionStore:
    """Store for conclusions table with string IDs."""

    @staticmethod
    def create(conclusion_id: str, verdict: str, reasoning: str = "",
               description: str = "") -> bool:
        """Create a conclusion. Returns True if created."""
        ts = datetime.now().isoformat()
        sha = hashlib.sha256(f"{conclusion_id}|{verdict}".encode()).hexdigest()[:16]
        try:
            db_exec("""
                INSERT INTO conclusions (id, timestamp, question, verdict, reasoning, sha256)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conclusion_id, ts, description, verdict, reasoning, sha))
            return True
        except sqlite3.IntegrityError as exc:
            # silent-by-design: duplicate id is an expected idempotent no-op; False signals "not inserted".
            logger.debug("phase0: insert skipped (integrity conflict): %s", exc, exc_info=True)
            return False
        except Exception as e:
            logger.warning(f"ConclusionStore.create failed: {e}", exc_info=True)
            return False

    @staticmethod
    def get(conclusion_id: str) -> dict | None:
        """Get conclusion by ID."""
        return db_query_one("SELECT * FROM conclusions WHERE id = ?", (conclusion_id,))

    @staticmethod
    def replace_reason_chain(conclusion_id: str, chain_id: str,
                              by: str = "", reason: str = "") -> bool:
        """Replace the reason chain for a conclusion."""
        # Check if conclusion exists
        conc = db_query_one("SELECT id FROM conclusions WHERE id = ?", (conclusion_id,))
        if not conc:
            return False
        # Check if chain exists (only if chain_id is provided and not empty)
        if chain_id:
            chain = db_query_one("SELECT id FROM reason_chains WHERE id = ?", (chain_id,))
            if not chain:
                return False
        try:
            db_exec("""
                UPDATE conclusions SET current_reason_chain_id = ? WHERE id = ?
            """, (chain_id, conclusion_id))
            ConclusionStore._add_decision_internal(conclusion_id, "reason_chain_replaced", reason)
            return True
        except Exception as e:
            logger.warning(f"ConclusionStore.replace_reason_chain failed: {e}", exc_info=True)
            return False

    @staticmethod
    def get_decision_history(conclusion_id: str) -> list[dict]:
        """Get decision history for a conclusion."""
        return db_query_all(
            "SELECT * FROM decision_history WHERE conclusion_id = ? ORDER BY timestamp",
            (conclusion_id,)
        )

    @staticmethod
    def _add_decision_internal(conclusion_id: str, action: str, notes: str = ""):
        """Internal method to add a decision record."""
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                INSERT INTO decision_history (timestamp, conclusion_id, action, notes)
                VALUES (?, ?, ?, ?)
            """, (ts, conclusion_id, action, notes[:500]))
        except Exception as e:
            logger.warning(f"Decision insert failed: {e}", exc_info=True)


# ============================================================
# REASON CHAIN STORE — For test compatibility
# ============================================================
class ReasonChainStore:
    """Store for reason_chains table with string IDs."""

    @staticmethod
    def create(chain_id: str, conclusion_id: str, total_steps: int = 1,
               verified_by: list[str] | None = None, question: str = "") -> bool:
        """Create a reason chain. Returns True if created."""
        ts = datetime.now().isoformat()
        verified_str = ",".join(verified_by) if verified_by else ""
        steps_json = json.dumps([{"step": i + 1} for i in range(total_steps)])
        try:
            db_exec("""
                INSERT INTO reason_chains (id, timestamp, question, conclusion_id, steps_json, total_steps, verified_by, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'WEAKENED')
            """, (chain_id, ts, question, conclusion_id, steps_json, total_steps, verified_str))
            return True
        except sqlite3.IntegrityError as exc:
            # silent-by-design: duplicate id is an expected idempotent no-op; False signals "not inserted".
            logger.debug("phase0: insert skipped (integrity conflict): %s", exc, exc_info=True)
            return False
        except Exception as e:
            logger.warning(f"ReasonChainStore.create failed: {e}", exc_info=True)
            return False

    @staticmethod
    def get(chain_id: str) -> dict | None:
        """Get reason chain by ID."""
        row = db_query_one("SELECT * FROM reason_chains WHERE id = ?", (chain_id,))
        if row:
            # Recalculate state based on evidence links
            state = ChainStateService.calculate_chain_state(chain_id)
            row_dict = dict(row)
            row_dict['state'] = state
            return row_dict
        return None


# ============================================================
# EVIDENCE LINK STORE — For test compatibility
# ============================================================
class EvidenceLinkStore:
    """Store for evidence_links table with string IDs."""

    @staticmethod
    def link(link_id: str, chain_id: str, evidence_id: str,
             role: str, weight: float = 1.0, confidence: float = 0.9,
             by: str = "") -> bool:
        """Link evidence to a chain. Returns True if linked."""
        ts = datetime.now().isoformat()
        try:
            db_exec("""
                INSERT INTO evidence_links (id, chain_id, evidence_id, role, weight, confidence, added_at, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (link_id, chain_id, evidence_id, role, weight, confidence, ts, by))
            # Recalculate chain state after link
            ChainStateService.recalculate_chain_state(chain_id)
            return True
        except sqlite3.IntegrityError as exc:
            # silent-by-design: duplicate id is an expected idempotent no-op; False signals "not inserted".
            logger.debug("phase0: insert skipped (integrity conflict): %s", exc, exc_info=True)
            return False
        except Exception as e:
            logger.warning(f"EvidenceLinkStore.link failed: {e}", exc_info=True)
            return False

    @staticmethod
    def address_contradicting(link_id: str, by: str = "", reason: str = "") -> bool:
        """Mark a contradicting evidence link as addressed."""
        try:
            db_exec("""
                UPDATE evidence_links SET addressed = 1, note = ? WHERE id = ?
            """, (reason, link_id))
            # Recalculate chain state
            row = db_query_one("SELECT chain_id FROM evidence_links WHERE id = ?", (link_id,))
            if row:
                ChainStateService.recalculate_chain_state(row['chain_id'])
            return True
        except Exception as e:
            logger.warning(f"EvidenceLinkStore.address_contradicting failed: {e}", exc_info=True)
            return False


# ============================================================
# CHAIN STATE SERVICE — Manages reason chain states
# ============================================================
class ChainStateService:
    """
    Manages reason chain states based on evidence links.

    State transitions:
      - All PRIMARY VERIFIED + No CONTRADICTING -> VALID
      - Any PRIMARY UNVERIFIED + No CONTRADICTING -> WEAKENED
      - Any PRIMARY FAILED -> WEAKENED
      - All PRIMARY FAILED -> BROKEN
      - CONTRADICTING unaddressed -> CONTESTED
      - CONTRADICTING addressed -> depends on PRIMARY status
    """

    @staticmethod
    def calculate_chain_state(chain_id: str) -> str:
        """Calculate the current state of a reason chain."""
        links = db_query_all(
            "SELECT * FROM evidence_links WHERE chain_id = ?", (chain_id,)
        )
        if not links:
            return 'WEAKENED'

        primary_verified = 0
        primary_unverified = 0
        primary_failed = 0
        contradicting = 0
        contradicting_addressed = 0

        for link in links:
            role = link.get('role', '')
            status = db_query_one(
                "SELECT verification_status FROM evidences WHERE id = ?",
                (link['evidence_id'],)
            )
            ev_status = status['verification_status'] if status else 'UNVERIFIED'

            if role == 'PRIMARY':
                if ev_status == 'VERIFIED':
                    primary_verified += 1
                elif ev_status == 'UNVERIFIED':
                    primary_unverified += 1
                elif ev_status == 'FAILED':
                    primary_failed += 1
            elif role == 'CONTRADICTING':
                contradicting += 1
                if link.get('addressed', 0):
                    contradicting_addressed += 1

        # Check CONTRADICTING first
        if contradicting > 0 and contradicting_addressed < contradicting:
            return 'CONTESTED'

        # Check PRIMARY status
        if primary_failed == 0 and primary_unverified == 0 and primary_verified > 0:
            return 'VALID'
        elif primary_failed > 0 and primary_failed == (primary_verified + primary_unverified + primary_failed):
            return 'BROKEN'
        else:
            return 'WEAKENED'

    @staticmethod
    def recalculate_chain_state(chain_id: str) -> str:
        """Recalculate and update chain state."""
        state = ChainStateService.calculate_chain_state(chain_id)
        try:
            db_exec("UPDATE reason_chains SET state = ? WHERE id = ?", (state, chain_id))
        except Exception as e:
            logger.warning(f"recalculate_chain_state failed: {e}", exc_info=True)
        return state

    @staticmethod
    def recalculate_chain_states_for_evidence(evidence_id: str):
        """Recalculate all chain states that reference this evidence."""
        chains = db_query_all(
            "SELECT chain_id FROM evidence_links WHERE evidence_id = ?",
            (evidence_id,)
        )
        for row in chains:
            ChainStateService.recalculate_chain_state(row['chain_id'])


# ============================================================
# DB CONNECTION HELPER
# ============================================================
# [EXEC-1 B1] TẠI SAO: the local `def get_db()` that lived here opened a
# NEW bare sqlite3.connect(DB_PATH) per call (no _db_lock, no V42 PRAGMAs).
# It shadowed the canonical scp.core.db_manager.get_db — the SLOW UNSAFE
# twin. Removed; re-export the canonical version so any external code that
# does `from scp.core.phase0 import get_db` gets the SAME thread-safe
# cached persistent connection that db_manager.get_db returns.
get_db = _canonical_get_db


# ============================================================
# ALIAS for backward compatibility
# ============================================================
init_schema = init_phase0_schema


# ============================================================
# AUTO-INIT ON IMPORT
# ============================================================
try:
    init_phase0_schema()
except Exception as e:
    # Fail-loudly: import-time schema init failure must reach structured logs too.
    logger.warning("Phase 0 init failed: %s", e, exc_info=True)
    logger.debug(f"[WARN] Phase 0 init failed: {e}")
