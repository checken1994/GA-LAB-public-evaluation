# Auto-extracted from api_server.py
from __future__ import annotations

import logging
import time
from collections import deque

from scp.core.streaming_factcheck import StreamingFactChecker

logger = logging.getLogger("scp.api")
_fact_checker = StreamingFactChecker()
_fact_check_retract_queue: deque[dict] = deque(maxlen=1000)

async def _async_fact_check(answer: str, question: str, session_id: str=''):
    """Run fact-check in background │Ă¢â€\x9aÂ¬Ă¢â‚¬Â\x9d update stats + queue retract if FALSE."""
    try:
        results = await _fact_checker.check_text(answer[:500], question)
        if results:
            false_claims = [r for r in results if r.verdict == 'FALSE']
            if false_claims:
                logger.warning(f"[V104.45 #Z] FactCheck: {len(false_claims)} FALSE claims found in answer to '{question[:50]}' │Ă¢â€\x9aÂ¬Ă¢â‚¬Â\x9d queuing retract")
                _fact_check_retract_queue.append({'question': question[:200], 'answer': answer[:200], 'false_claims': len(false_claims), 'session_id': session_id, 'timestamp': time.time()})
    except Exception as e:
        logger.debug(f'V104 async fact-check error: {e}', exc_info=True)
