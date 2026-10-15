# Auto-extracted from db_manager.py
import os
import sqlite3


def get_db():
    """Persistent connection + thread lock.  SQLite PRAGMA tuned for speed.

    [R16-ROOT-FIX-4] Integrity check on first connect.
    BEFORE: DB corruption ("database disk image is malformed") was only caught
            when a query failed — by then, cascading errors already happened
            (canary scan fails, audit log fails, migrations fail).
    AFTER:  on first get_db() call, run PRAGMA integrity_check. If it fails,
            attempt VACUUM INTO recovery (delegates to storage_manager logic).
            This catches corruption EARLY — before any query runs.
    """
    global _persistent_conn
    _db_lock.acquire()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
    try:
        if _persistent_conn is None:
            os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)  # noqa: F821
            _preflight_integrity_check()  # noqa: F821  # [hygiene-keep] _preflight_integrity_check injected by db_manager.py rebind/wire
            _persistent_conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)  # noqa: F821  # [hygiene-keep] DB_PATH injected by db_manager.py rebind/wire
            _persistent_conn.row_factory = sqlite3.Row
            _persistent_conn.execute('PRAGMA journal_mode=WAL')
            _persistent_conn.execute('PRAGMA synchronous=NORMAL')
            _persistent_conn.execute('PRAGMA cache_size=-128000')
            _persistent_conn.execute('PRAGMA temp_store=MEMORY')
            _persistent_conn.execute('PRAGMA busy_timeout=30000')
            _persistent_conn.execute('PRAGMA mmap_size=268435456')
            _persistent_conn.execute('PRAGMA wal_autocheckpoint=5000')
            _persistent_conn.execute('PRAGMA page_size=4096')
            _persistent_conn.execute('PRAGMA foreign_keys = ON')
        return _persistent_conn
    finally:
        _db_lock.release()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
