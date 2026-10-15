# Auto-extracted from db_manager.py
import logging
import time

logger = logging.getLogger(__name__)
def db_batch_flush() -> int:
    """Flush buffered writes to DB in 1 transaction."""
    global _last_batch_flush
    with _batch_lock:  # noqa: F821  # [hygiene-keep] _batch_lock injected by db_manager.py rebind/wire
        if not _batch_buffer:  # noqa: F821  # [hygiene-keep] _batch_buffer injected by db_manager.py rebind/wire
            return 0
        to_flush = _batch_buffer[:]  # noqa: F821  # [hygiene-keep] _batch_buffer injected by db_manager.py rebind/wire
        _batch_buffer.clear()  # noqa: F821  # [hygiene-keep] _batch_buffer injected by db_manager.py rebind/wire
        _last_batch_flush = time.time()
    _db_lock.acquire()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
    try:
        conn = get_db()  # noqa: F821  # [hygiene-keep] get_db injected by db_manager.py rebind/wire
        count = 0
        try:
            for sql, params in to_flush:
                conn.execute(sql, params)
                count += 1
            conn.commit()
            logger.debug(f'Batch flushed: {count} writes')
            return count
        except Exception:
            try:
                conn.rollback()
            except Exception as e:
                logger.debug(f'[V104.37] core/db_manager.py: e={e}', exc_info=True)
            raise
    finally:
        _db_lock.release()  # noqa: F821  # [hygiene-keep] _db_lock injected by db_manager.py rebind/wire
