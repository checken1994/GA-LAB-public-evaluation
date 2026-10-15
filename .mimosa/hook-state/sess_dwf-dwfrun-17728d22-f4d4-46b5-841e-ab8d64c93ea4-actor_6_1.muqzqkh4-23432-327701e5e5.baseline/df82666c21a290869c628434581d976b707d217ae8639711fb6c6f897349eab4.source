# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
# Auto-extracted from why_engine.py
from __future__ import annotations

import logging

from scp.core.db_manager import db_exec

# [M12-FIX PF-1] logger was USED here (except handler) but NEVER defined ->
# WhyEngine.__init__ crashed with NameError on every fresh DB (CREATE TABLE
# already ships claimed_by/claimed_at, so the ALTER TABLE migration below
# always hits "duplicate column" and the handler referenced the missing
# logger). WhyEngine was 100% un-instantiable on fresh environments.
logger = logging.getLogger("scp.meta.why_engine.init_why_db")

def init_why_db():
    """Tạo WHY Engine tables."""
    db_exec("\n        CREATE TABLE IF NOT EXISTS why_verification_plans (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            timestamp TEXT NOT NULL,\n            question TEXT NOT NULL,\n            target TEXT,\n            evidence_type TEXT,\n            proof_criteria TEXT,\n            falsification_criteria TEXT,\n            verification_strategy TEXT,\n            sources_to_query TEXT,\n            status TEXT DEFAULT 'pending',\n            verdict TEXT,\n            executed_at TEXT,\n            confidence_threshold REAL,\n            claimed_by TEXT,\n            claimed_at REAL\n        )\n    ")
    db_exec('CREATE INDEX IF NOT EXISTS idx_why_status ON why_verification_plans(status)')
    try:
        db_exec('ALTER TABLE why_verification_plans ADD COLUMN claimed_by TEXT')
    except Exception as e:
        logger.debug(f'[why_engine.py:130] silenced: {e}', exc_info=True)
    try:
        db_exec('ALTER TABLE why_verification_plans ADD COLUMN claimed_at REAL')
    except Exception as e:
        # [M12-FIX PF-1b/D6] was bare `except Exception: pass` (fail-silently,
        # D6 violation in scope). "duplicate column" is the EXPECTED idempotent
        # migration outcome — log it at debug so it stays observable.
        logger.debug(f'[init_why_db] claimed_at column already present (idempotent): {e}', exc_info=True)
    try:
        # [M12-FIX PF-6] execute_pending_plans claims rows with
        # `RETURNING ... confidence_threshold` (and the fallback SELECT reads
        # it), but this table NEVER had that column -> every claim raised
        # "no such column: confidence_threshold" and the background WHY
        # verification loop executed 0 plans, 100% of the time (fail-silently
        # behind the run_pending_verification_cycle guard).
        db_exec('ALTER TABLE why_verification_plans ADD COLUMN confidence_threshold REAL')
    except Exception as e:
        logger.debug(f'[init_why_db] confidence_threshold column already present (idempotent): {e}', exc_info=True)
    db_exec('CREATE INDEX IF NOT EXISTS idx_why_claimed ON why_verification_plans(claimed_by)')
