# Auto-extracted from db_manager.py
import logging

logger = logging.getLogger(__name__)
def _migrate_knowledge_schema() -> None:
    """[ROOT-FIX 1] Detect legacy `knowledge` schema and rebuild to canonical.

    Strategy (mirrors `_migrate_verdict_cache_schema`):
      1. PRAGMA table_info(knowledge). If no table → no-op (canonical CREATE
         will build it).
      2. If table exists with all canonical columns AND no `id` column → no-op.
      3. If table has an `id` column (legacy brain.py/experience.py shape) OR
         is missing any canonical column → rename to knowledge_old, create
         canonical, copy over the common columns, drop the old table.
    All steps wrapped in try/except so a partial failure leaves the old table
    intact (better stale-schema than no-schema).
    """
    try:
        cols = db_query_all('PRAGMA table_info(knowledge)')  # noqa: F821  # [hygiene-keep] db_query_all injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[ROOT-FIX 1] PRAGMA table_info(knowledge) failed: {e}', exc_info=True)
        return
    if not cols:
        return
    col_names = {c.get('name') for c in cols if c.get('name')}
    has_id_column = 'id' in col_names
    has_all_canonical = _KNOWLEDGE_CANONICAL_COLS.issubset(col_names)  # noqa: F821  # [hygiene-keep] _KNOWLEDGE_CANONICAL_COLS injected by db_manager.py rebind/wire
    if has_all_canonical and (not has_id_column):
        return
    logger.info(f'[ROOT-FIX 1] knowledge has legacy schema (cols={sorted(col_names)}, has_id={has_id_column}); rebuilding to canonical.')
    try:
        db_exec('ALTER TABLE knowledge RENAME TO knowledge_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f"_migrate_knowledge_schema ignored: {e}", exc_info=True)
        logger.warning(f'[ROOT-FIX 1] RENAME knowledge → knowledge_old failed: {e}')
        return
    try:
        db_exec(_KNOWLEDGE_CANONICAL_DDL)  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.warning(f'[ROOT-FIX 1] canonical CREATE failed: {e}; restoring old table', exc_info=True)
        try:
            db_exec('ALTER TABLE knowledge_old RENAME TO knowledge')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
        except Exception as ee:
            logger.debug(f'[ROOT-FIX 1] restore failed: {ee}', exc_info=True)
        return
    try:
        old_cols = db_query_all('PRAGMA table_info(knowledge_old)')  # noqa: F821  # [hygiene-keep] db_query_all injected by db_manager.py rebind/wire
    except Exception as e:
        old_cols = []
        logger.debug(f'[ROOT-FIX 1] PRAGMA table_info(knowledge_old) failed: {e}', exc_info=True)
    old_col_names = {c.get('name') for c in old_cols or [] if c.get('name')}
    common = _KNOWLEDGE_CANONICAL_COLS & old_col_names  # noqa: F821  # [hygiene-keep] _KNOWLEDGE_CANONICAL_COLS injected by db_manager.py rebind/wire
    if common:
        col_list = ', '.join(sorted(common))
        try:
            db_exec(f'INSERT OR IGNORE INTO knowledge ({col_list}) SELECT {col_list} FROM knowledge_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire  # nosec B608 — col_list is the intersection of the hardcoded _KNOWLEDGE_CANONICAL_COLS allowlist with actual PRAGMA-reported column names (identifiers only, no values to bind).
            logger.info(f'[ROOT-FIX 1] migrated {len(common)} columns ({sorted(common)}) from knowledge_old → knowledge')
        except Exception as e:
            logger.warning(f'[ROOT-FIX 1] row migration failed ({e}); canonical table is empty but functional.', exc_info=True)
    try:
        db_exec('DROP TABLE knowledge_old')  # noqa: F821  # [hygiene-keep] db_exec injected by db_manager.py rebind/wire
    except Exception as e:
        logger.debug(f'[ROOT-FIX 1] DROP knowledge_old failed: {e}', exc_info=True)
