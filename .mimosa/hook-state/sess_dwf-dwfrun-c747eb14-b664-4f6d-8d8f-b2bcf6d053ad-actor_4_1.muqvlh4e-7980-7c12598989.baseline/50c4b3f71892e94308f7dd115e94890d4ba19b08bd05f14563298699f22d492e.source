# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import logging
import re
import sys

logger = logging.getLogger(__name__)


def extract_claims_from_answer(answer: str, question: str='') -> list[dict]:
    """Extract factual claims from answer.

    Uses SCP's ClaimExtractor if available, else simple heuristic.
    """
    try:
        sys.path.insert(0, str(BENCHMARK_DIR.parent))  # noqa: F821  # [hygiene-keep] BENCHMARK_DIR injected by run_benchmark_v2.py rebind/wire
        from scp.knowledge.claim_extractor import ClaimExtractor
        extractor = ClaimExtractor()
        claims = extractor.extract(answer, question)
        return [{'claim_id': c.claim_id, 'claim_type': c.claim_type, 'text': c.text, 'entity': c.entity, 'value': c.value, 'unit': c.unit, 'relation': c.relation, 'target': c.target} for c in claims]
    except Exception:
        logger.warning('extract_claims_from_answer: Exception not handled', exc_info=True)
        sentences = re.split('[.!?]+', answer)
        return [{'claim_id': f'claim_{i}', 'claim_type': 'sentence', 'text': s.strip()} for i, s in enumerate(sentences) if s.strip() and len(s.strip()) > 10]
