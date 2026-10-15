# Auto-extracted from db_manager.py
import logging

logger = logging.getLogger(__name__)
def _migrate_reverify_schema() -> None:
    """[RUNTIME-FIX-3] Ensure reverify_queue has `notes` column.

    Root cause (runtime log lines 741, 957, 1391, 1406):
      WARNING | scp.reverify | ReVerify process error: no such column: notes
      WARNING | scp.judge | [V104.42 #AV] ReVerify process_pending error: no such column: notes

    Bug: this module's CREATE TABLE reverify_queue (canonical, runs first at
    startup) did NOT include the `notes` column. But reverify_scheduler.py:62
    has `notes TEXT` in its own CREATE TABLE — which is a no-op (IF NOT EXISTS)
    because the table was already created by db_manager. Result: reverify
    UPDATE/SELECT referencing `notes` fails.

    Fix strategy:
      1. PRAGMA table_info(reverify_queue). If no table → no-op (canonical
         CREATE will build it with the new `notes` column).
      2. If table exists but `notes` column missing → ALTER TABLE ADD COLUMN
         (idempotent — only adds if missing).
    """
    try:
        cols = db_query_all('PRAGMA table_info(reverify_queue)')  # noqa: F821  # [hygiene-keep] db_query_all injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[RUNTIME-FIX-3] PRAGMA table_info(reverify_queue) failed: {e}', exc_info=True)
        return
    if not cols:
        return
    col_names = {c.get('name') for c in cols if c.get('name')}
    if 'notes' in col_names:
        return
    try:
        db_exec("ALTER TABLE reverify_queue ADD COLUMN notes TEXT DEFAULT ''")  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
        logger.info("[RUNTIME-FIX-3] reverify_queue: added missing 'notes' column")
    except Exception as e:
        logger.error(f"[RUNTIME-FIX-3] failed to add 'notes' column to reverify_queue: {e}", exc_info=True)
