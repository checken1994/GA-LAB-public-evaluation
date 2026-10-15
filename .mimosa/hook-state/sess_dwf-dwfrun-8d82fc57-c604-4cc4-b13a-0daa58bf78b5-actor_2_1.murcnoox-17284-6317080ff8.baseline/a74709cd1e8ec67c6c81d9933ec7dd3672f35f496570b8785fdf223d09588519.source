"""SCP database manager compatibility wrapper.

The heavy schema and connection operations live in focused part modules. This
module remains the single owner of process-wide SQLite state so splitting does
not create duplicate locks/connections or alter transaction semantics.
"""
from __future__ import annotations

import gzip  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import json  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import logging
import os
import sqlite3
import threading
import time
import types
from datetime import datetime  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from typing import Optional  # noqa: F401  # [hygiene-keep] wire-parent namespace injection

logger = logging.getLogger(__name__)
from scp.core.runtime_paths import runtime_data_dir, runtime_path

_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = str(runtime_data_dir())
DB_PATH = str(runtime_path("SCP_DB_PATH", "v13.db"))

_persistent_conn = None
_db_lock = threading.RLock()
_path_conns: dict[str, sqlite3.Connection] = {}
_batch_buffer: list[tuple[str, tuple]] = []
_batch_lock = threading.Lock()
_BATCH_SIZE = 100
_BATCH_TIMEOUT = 1.0
_last_batch_flush = time.time()
_read_lock = threading.Lock()

_VERDICT_CACHE_CANONICAL_COLS = {
    "cache_key", "question_hash", "question_text", "verdict", "confidence",
    "final_answer", "domain", "reasoning", "evidence_json", "timestamp",
    "cached_at", "expires_at", "times_used",
}
_VERDICT_CACHE_CANONICAL_DDL = """
CREATE TABLE verdict_cache (
    cache_key TEXT PRIMARY KEY,
    question_hash TEXT UNIQUE,
    question_text TEXT,
    verdict TEXT,
    confidence REAL,
    final_answer TEXT,
    domain TEXT,
    reasoning TEXT,
    evidence_json TEXT,
    timestamp REAL,
    cached_at TEXT,
    expires_at TEXT,
    times_used INTEGER DEFAULT 1
)
"""
_KNOWLEDGE_CANONICAL_COLS = {
    "entity", "attribute", "value", "value_type", "confidence", "source",
    "timestamp", "times_verified", "times_wrong", "last_verified",
    "bias_correction", "notes",
}
_KNOWLEDGE_CANONICAL_DDL = """
CREATE TABLE IF NOT EXISTS knowledge (
    entity TEXT, attribute TEXT, value TEXT, value_type TEXT,
    confidence REAL, source TEXT, timestamp TEXT, times_verified INTEGER DEFAULT 1,
    times_wrong INTEGER DEFAULT 0,
    last_verified TEXT,
    bias_correction REAL DEFAULT 0.0,
    notes TEXT DEFAULT '',
    PRIMARY KEY (entity, attribute)
)
"""

from .db_manager_parts import _get_path_conn as _p_get_path_conn
from .db_manager_parts import _init_all_module_tables as _p_init_tables
from .db_manager_parts import _migrate_knowledge_schema as _p_migrate_knowledge
from .db_manager_parts import _migrate_reverify_schema as _p_migrate_reverify
from .db_manager_parts import _migrate_verdict_cache_schema as _p_migrate_vc
from .db_manager_parts import _preflight_integrity_check as _p_preflight
from .db_manager_parts import db_batch_flush as _p_batch_flush
from .db_manager_parts import db_exec as _p_db_exec
from .db_manager_parts import get_db as _p_get_db
from .db_manager_parts import init_db as _p_init_db

_PARTS = (
    _p_get_path_conn, _p_get_db, _p_preflight, _p_db_exec, _p_batch_flush,
    _p_init_db, _p_init_tables, _p_migrate_vc, _p_migrate_knowledge,
    _p_migrate_reverify,
)


def _wire_parts() -> None:
    shared = dict(globals())
    for part in _PARTS:
        part.__dict__.update(shared)


def _rebind_part_function(fn):
    """Execute extracted DB code against this module's one authoritative state."""
    rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
    rebound.__kwdefaults__ = fn.__kwdefaults__
    rebound.__annotations__ = dict(getattr(fn, "__annotations__", {}))
    rebound.__doc__ = fn.__doc__
    rebound.__module__ = __name__
    return rebound


_wire_parts()

_get_path_conn = _rebind_part_function(_p_get_path_conn._get_path_conn)
get_db = _rebind_part_function(_p_get_db.get_db)
_preflight_integrity_check = _rebind_part_function(_p_preflight._preflight_integrity_check)
db_exec = _rebind_part_function(_p_db_exec.db_exec)
db_batch_flush = _rebind_part_function(_p_batch_flush.db_batch_flush)
init_db = _rebind_part_function(_p_init_db.init_db)
_init_all_module_tables = _rebind_part_function(_p_init_tables._init_all_module_tables)
_migrate_verdict_cache_schema = _rebind_part_function(_p_migrate_vc._migrate_verdict_cache_schema)
_migrate_knowledge_schema = _rebind_part_function(_p_migrate_knowledge._migrate_knowledge_schema)
_migrate_reverify_schema = _rebind_part_function(_p_migrate_reverify._migrate_reverify_schema)

# Sibling functions are part of the historical module-global namespace used by
# extracted implementations, so re-wire once all bindings exist.
_wire_parts()


def db_batch_exec(sql: str, params: tuple) -> None:
    global _last_batch_flush
    with _batch_lock:
        _batch_buffer.append((sql, params))
        should_flush = (
            len(_batch_buffer) >= _BATCH_SIZE
            or time.time() - _last_batch_flush > _BATCH_TIMEOUT
        )
    if should_flush:
        db_batch_flush()


def db_query_all(sql: str, params=(), db_path: str | None = None) -> list[dict]:
    if db_path:
        with _db_lock:
            conn = _get_path_conn(db_path)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    else:
        with _read_lock, _db_lock:
            conn = get_db()
            return [dict(r) for r in conn.execute(sql, params).fetchall()]


def db_query_one(sql: str, params=(), db_path: str | None = None) -> dict | None:
    if db_path:
        with _db_lock:
            conn = _get_path_conn(db_path)
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
    else:
        with _read_lock, _db_lock:
            conn = get_db()
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None


def checkpoint_wal():
    try:
        with _db_lock:
            get_db().execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception as exc:
        logger.debug("[V104.37] core/db_manager.py: e=%s", exc, exc_info=True)


def vacuum_db():
    try:
        with _db_lock:
            get_db().execute("VACUUM")
        logger.info("DB VACUUM complete")
        return True
    except Exception as exc:
        logger.warning("VACUUM error: %s", exc, exc_info=True)
        return False


def get_db_size_mb() -> float:
    try:
        return os.path.getsize(str(DB_PATH)) / (1024 * 1024)
    except Exception as exc:
        logger.warning("db_manager: get_db_size failed for %s, reporting 0.0: %s", DB_PATH, exc, exc_info=True)
        return 0.0

# Final wiring exposes the local query/batch helpers too.
_wire_parts()
