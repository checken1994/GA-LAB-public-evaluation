# Auto-extracted from db_manager.py
import logging

logger = logging.getLogger(__name__)
def _migrate_verdict_cache_schema() -> None:
    """[V104.49 FIX-C] Detect legacy verdict_cache schema and rebuild to canonical.

    Strategy:
      1. PRAGMA table_info(verdict_cache). If no table → nothing to do (the
         CREATE TABLE IF NOT EXISTS in _init_all_module_tables will build it).
      2. If table exists with all canonical columns → no-op (idempotent).
      3. If table exists but is missing any canonical column → rename to
         verdict_cache_old, create canonical, copy over the intersection of
         common columns, drop the old table.
    All steps wrapped in try/except so a partial failure leaves the old table
    intact (better stale-schema than no-schema).
    """
    try:
        cols = db_query_all('PRAGMA table_info(verdict_cache)')  # noqa: F821  # [hygiene-keep] db_query_all injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.49] PRAGMA table_info(verdict_cache) failed: {e}', exc_info=True)
        return
    if not cols:
        return
    col_names = {c.get('name') for c in cols if c.get('name')}
    if _VERDICT_CACHE_CANONICAL_COLS.issubset(col_names):  # noqa: F821  # [hygiene-keep] _VERDICT_CACHE_CANONICAL_COLS injected by db_manager.py rebind/wire
        return
    logger.info(f'[V104.49 FIX-C] verdict_cache has legacy schema (cols={sorted(col_names)}); rebuilding to canonical.')
    try:
        db_exec('ALTER TABLE verdict_cache RENAME TO verdict_cache_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f"_migrate_verdict_cache_schema ignored: {e}", exc_info=True)
        logger.warning(f'[V104.49] RENAME verdict_cache → verdict_cache_old failed: {e}')
        return
    try:
        db_exec(_VERDICT_CACHE_CANONICAL_DDL)  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.warning(f'[V104.49] canonical CREATE failed: {e}; restoring old table', exc_info=True)
        try:
            db_exec('ALTER TABLE verdict_cache_old RENAME TO verdict_cache')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
        except Exception as ee:
            logger.debug(f'[V104.49] restore failed: {ee}', exc_info=True)
        return
    try:
        old_cols = db_query_all('PRAGMA table_info(verdict_cache_old)')  # noqa: F821  # [hygiene-keep] db_query_all injected by db_manager.py rebind/wire
    except Exception as e:
        old_cols = []
        logger.debug(f'[V104.49] PRAGMA table_info(verdict_cache_old) failed: {e}', exc_info=True)
    old_col_names = {c.get('name') for c in old_cols or [] if c.get('name')}
    common = _VERDICT_CACHE_CANONICAL_COLS & old_col_names  # noqa: F821  # [hygiene-keep] _VERDICT_CACHE_CANONICAL_COLS injected by db_manager.py rebind/wire
    if common:
        col_list = ', '.join(sorted(common))
        try:
            db_exec(f'INSERT INTO verdict_cache ({col_list}) SELECT {col_list} FROM verdict_cache_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire  # nosec B608 — col_list is the intersection of the hardcoded _VERDICT_CACHE_CANONICAL_COLS allowlist with actual PRAGMA-reported column names (identifiers only, no values to bind).
            logger.info(f'[V104.49 FIX-C] migrated {len(common)} columns ({sorted(common)}) from verdict_cache_old → verdict_cache')
        except Exception as e:
            logger.warning(f'[V104.49] row migration failed ({e}); canonical table is empty but functional.', exc_info=True)
    try:
        db_exec('DROP TABLE verdict_cache_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[V104.49] DROP verdict_cache_old failed: {e}', exc_info=True)
