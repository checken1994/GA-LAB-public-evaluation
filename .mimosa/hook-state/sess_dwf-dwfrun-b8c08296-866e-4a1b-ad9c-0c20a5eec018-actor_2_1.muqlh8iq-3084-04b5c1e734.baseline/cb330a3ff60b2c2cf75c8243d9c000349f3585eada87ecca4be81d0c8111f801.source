# Auto-extracted from db_manager.py
import logging

logger = logging.getLogger(__name__)
def db_exec(sql: str, params=(), db_path: str | None=None) -> int:
    """Execute a SQL statement. If db_path is provided, use a per-path connection
    (cached) instead of the global DB_PATH — but STILL under _db_lock.

    [AUDIT-2 FIX] TẠI SAO: FastLearningEngine + RealLearningEngine accept scp_db_path
    in their constructor, but db_exec used to ignore it (always wrote to global
    DB_PATH). The wrong fix bypassed db_exec with bare sqlite3.connect → lost
    _db_lock → race with Brain → facts silently dropped (Invariant #7).
    Root-cause fix: accept optional db_path, use cached per-path connection,
    still acquire _db_lock. Single lock across all paths = no race.
    """
    _db_lock.acquire()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
    try:
        conn = _get_path_conn(db_path) if db_path else get_db()  # noqa: F821  # [hygiene-keep] _get_path_conn injected by db_manager.py rebind/wire
        try:
            cur = conn.execute(sql, params)
            if conn.in_transaction:
                conn.commit()
            return cur.rowcount
        except Exception:
            if conn.in_transaction:
                try:
                    conn.rollback()
                except Exception as e:
                    logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
            raise
    finally:
        _db_lock.release()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
