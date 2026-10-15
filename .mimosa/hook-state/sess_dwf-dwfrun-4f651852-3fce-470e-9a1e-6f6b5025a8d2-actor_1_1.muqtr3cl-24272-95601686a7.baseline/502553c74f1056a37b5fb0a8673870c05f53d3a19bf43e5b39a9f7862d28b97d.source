# Auto-extracted from db_manager.py
import sqlite3


def _get_path_conn(db_path: str) -> sqlite3.Connection:
    """Get or create a cached connection for a specific db_path.

    [FIX-CRIT-135 BUG 4] TẠI SAO: the docstring used to read "caller must hold
    _db_lock" — but `db_query_one`/`db_query_all` called this function while
    holding ONLY `_read_lock` (NOT `_db_lock`). So `_path_conns` was mutated
    under two DIFFERENT locks:
      - db_exec (writes) held `_db_lock` while mutating `_path_conns`
      - db_query_* (reads)  held `_read_lock` while mutating `_path_conns`
    → two threads could race in `_get_path_conn` (one read, one write) and
    both create a new connection for the same path, or one's mutation could
    clobber the other's `_path_conns[db_path] = conn` assignment.
    Fix: enforce the contract — callers MUST hold `_db_lock` before calling
    this function. `db_query_*` now acquires `_db_lock` for the per-path
    branch (single lock for the per-path dict). The `_read_lock` is kept
    ONLY for the global `_persistent_conn` reads (V89 WAL optimization
    preserved for the no-db_path case).
    """
    conn = _path_conns.get(db_path)  # noqa: F821  # [hygiene-keep] _path_conns injected by db_manager.py rebind/wire
    if conn is None:
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=30000')
        _path_conns[db_path] = conn  # noqa: F821  # [hygiene-keep] _path_conns injected by db_manager.py rebind/wire
    return conn
