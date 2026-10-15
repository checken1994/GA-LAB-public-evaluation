"""[V104.32 #0] Shared token-boundary matching helper.

Extracted to a separate module to avoid circular imports
(was: in scp/data_sources/__init__.py, but arts.py/history.py/legal.py
tried to import it from scp.data_sources while __init__.py was still
loading them).
"""
import re as _re

_MIN_FUZZY_KEY_LEN = 4


def _token_boundary_match(key: str, entity_lower: str) -> bool:
    """Word-boundary match — prevents 'in' matching 'insulin', 'a' matching 'aspirin'.

    Returns True if:
      - key == entity_lower (exact match)
      - key (>=4 chars) appears as a whole word inside entity_lower
      - entity_lower (>=4 chars) appears as a whole word inside key
    """
    if not key or not entity_lower:
        return False
    if key == entity_lower:
        return True
    if len(key) < _MIN_FUZZY_KEY_LEN:
        return False
    pattern = r'(?<![\wÀ-ỹ])' + _re.escape(key) + r'(?![\wÀ-ỹ])'
    if _re.search(pattern, entity_lower):
        return True
    if len(entity_lower) >= _MIN_FUZZY_KEY_LEN:
        pattern_rev = r'(?<![\wÀ-ỹ])' + _re.escape(entity_lower) + r'(?![\wÀ-ỹ])'
        if _re.search(pattern_rev, key):
            return True
    return False
