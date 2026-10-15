# Auto-extracted from fast_learning_engine.py
from __future__ import annotations

import asyncio
import logging
import threading
import time

from scp.core.subsystem_telemetry import heartbeat_sleep

logger = logging.getLogger(__name__)
def start_fast_learning_thread(scp_db_path: str='data/v13.db', data_dir: str='data') -> threading.Thread:
    """[G3-MERGE A5] Start V104.2 fast learning thread — adaptive interval.

    IDEMPOTENT: uses module-level _FAST_LEARNING_THREAD guard so calling this
    function multiple times (e.g. once via `start_learning_thread` alias from
    real_learning_engine stub, once via direct `start_fast_learning_thread`
    call in helpers.py:444) will NOT spawn multiple threads writing to the
    same KB. This eliminates the race condition documented in Task 2-B P1-04.
    """
    global _FAST_LEARNING_THREAD
    with _FAST_LEARNING_THREAD_LOCK:  # noqa: F821  # [hygiene-keep] _FAST_LEARNING_THREAD_LOCK injected by fast_learning_engine.py rebind/wire
        if _FAST_LEARNING_THREAD is not None and _FAST_LEARNING_THREAD.is_alive():
            logger.info(f"[G3-MERGE A5] start_fast_learning_thread called again but thread '{_FAST_LEARNING_THREAD.name}' is already running — returning existing handle (idempotent guard prevents race condition).")
            return _FAST_LEARNING_THREAD

        def learning_loop():
            time.sleep(30)
            engine = FastLearningEngine(scp_db_path=scp_db_path, data_dir=data_dir, telemetry_subsystem='fast_learning')  # noqa: F821  # [hygiene-keep] FastLearningEngine injected by fast_learning_engine.py rebind/wire
            logger.info(f'V104.2 FastLearningEngine started (concurrency={PARALLEL_LLM_CONCURRENCY}, interval={LEARN_INTERVAL_FAST}s adaptive)')  # noqa: F821  # [hygiene-keep] PARALLEL_LLM_CONCURRENCY injected by fast_learning_engine.py rebind/wire
            _consecutive_429 = 0
            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    engine._telemetry_timeout_requested = True
                    try:
                        results = loop.run_until_complete(asyncio.wait_for(engine.fast_learning_cycle(count=50), timeout=LEARN_CYCLE_TIMEOUT_SECONDS))  # noqa: F821  # [hygiene-keep] LEARN_CYCLE_TIMEOUT_SECONDS injected by fast_learning_engine.py rebind/wire
                    finally:
                        engine._telemetry_timeout_requested = False
                        loop.close()
                    asked = results.get('asked', 0)
                    verified = results.get('verified', 0)
                    if asked > 0 and verified == 0:
                        _consecutive_429 += 1
                        if _consecutive_429 >= 3:
                            logger.warning(f' {_consecutive_429} consecutive cycles with 0 verified (likely OpenRouter 429) — backing off 10 min')
                            heartbeat_sleep(engine._telemetry, 600, status='IDLE')
                            _consecutive_429 = 0
                            continue
                    else:
                        _consecutive_429 = 0
                    sleep_s = engine.get_adaptive_interval()
                    logger.info(f"V104.2 adaptive sleep: {sleep_s}s (mode={results['adaptive_mode']})")
                    heartbeat_sleep(engine._telemetry, sleep_s, status='IDLE')
                except asyncio.TimeoutError as e:
                    logger.error('V104.2 FastLearning cycle TIMEOUT after %ss: %s', LEARN_CYCLE_TIMEOUT_SECONDS, e)  # noqa: F821  # [hygiene-keep] LEARN_CYCLE_TIMEOUT_SECONDS injected by fast_learning_engine.py rebind/wire
                    engine._telemetry_timeout_requested = False
                    heartbeat_sleep(engine._telemetry, 60, status='TIMEOUT')
                except Exception as e:
                    logger.error(f'V104.2 fast learning loop error: {e}', exc_info=True)
                    if engine._telemetry:
                        engine._telemetry.cycle_failed(f'fast-learning-loop-{time.time_ns()}', e, status='TELEMETRY_DEGRADED')
                    heartbeat_sleep(engine._telemetry, 60, status='TELEMETRY_DEGRADED')
        thread = threading.Thread(target=learning_loop, daemon=True, name='scp-v104-fast-learning')
        thread.start()
        _FAST_LEARNING_THREAD = thread
        return thread
