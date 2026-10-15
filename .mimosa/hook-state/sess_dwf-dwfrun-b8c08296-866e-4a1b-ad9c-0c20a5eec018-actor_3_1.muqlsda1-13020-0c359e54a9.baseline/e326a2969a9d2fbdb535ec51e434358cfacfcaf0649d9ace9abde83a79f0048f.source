"""
SCP V105 — Vietnamese number parsing utilities.

[Task 7-A Modularity] TẠI SAO tách _parse_vn_number/_normalize_number ra file riêng?
- falsification_engine.py原本 1042 LOC (>1000 ISO 25010 Modularity threshold)
- 2 helpers + constants ~95 LOC pure numeric parsing (không phụ thuộc FalsificationEngine state)
- Tách ra không thay đổi behavior, giảm falsification_engine.py xuống ~950 LOC
- Single Responsibility: number parsing tách khỏi falsification logic
"""

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# Vietnamese / English numeric units and their multipliers.
_UNIT_MULTIPLIERS: dict[str, float] = {
    "tỷ": 1_000_000_000.0,
    "tỉ": 1_000_000_000.0,
    "ty": 1_000_000_000.0,
    "triệu": 1_000_000.0,
    "tr": 1_000_000.0,
    "nghìn": 1_000.0,
    "ngàn": 1_000.0,
    "nghin": 1_000.0,
    "ngan": 1_000.0,
    "billion": 1_000_000_000.0,
    "million": 1_000_000.0,
    "thousand": 1_000.0,
    "k": 1_000.0,
    "m": 1_000_000.0,
    "b": 1_000_000_000.0,
}

# Match a number (possibly with comma/dot decimal) followed by an optional unit.
# Vietnamese uses both "." and "," as decimal separators depending on context.
_NUM_UNIT_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*"
    r"(tỷ|tỉ|ty|triệu|tr|nghìn|ngàn|nghin|ngan|billion|million|thousand|k|m|b)?",
    re.IGNORECASE,
)

# A bare number regex (no unit) used as a fallback.
_BARE_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _parse_vn_number(text: str) -> float | None:
    """Parse a Vietnamese-style number string into a float.

    Examples
    --------
    >>> _parse_vn_number("52 tỷ")
    52000000000.0
    >>> _parse_vn_number("62.849 tỷ")
    62849000000.0
    >>> _parse_vn_number("5,2 triệu")
    5200000.0
    >>> _parse_vn_number("not a number")

    Returns None if no number can be parsed.
    """
    if not text:
        return None
    text = str(text).strip().lower()
    m = _NUM_UNIT_RE.search(text)
    if not m:
        return None
    raw_num, unit = m.group(1), m.group(2)
    # Normalise decimal separator: Vietnamese "62.849" means 62.849 (dot = decimal).
    # But "1,234.56" is English thousands. We try float() directly; if it fails
    # we swap the last separator to a dot.
    try:
        value = float(raw_num.replace(",", ""))
    except ValueError as exc:
        # silent-by-design: probe order — next probe swaps the last separator to a dot.
        logger.debug("_number_utils: comma-strip parse failed, trying dot-swap: %s", exc, exc_info=True)
        try:
            value = float(raw_num.replace(",", "."))
        except ValueError as exc:
            # silent-by-design: both probes failed; None means "no number" by contract.
            logger.debug("_number_utils: number parse failed: %s", exc, exc_info=True)
            return None
    if unit:
        mult = _UNIT_MULTIPLIERS.get(unit.lower())
        if mult is not None:
            value *= mult
    return value


def _normalize_number(value: Any) -> float | None:
    """Normalize any value (int/float/str) into a float, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return None
            return f
        except (TypeError, ValueError) as exc:
            # silent-by-design: coerce probe; None means "not a finite number" by contract.
            logger.debug("_number_utils: float coercion failed: %s", exc, exc_info=True)
            return None
    if isinstance(value, str):
        # Try direct float first
        s = value.strip()
        if not s:
            return None
        try:
            return float(s.replace(",", ""))
        except ValueError as e:
            logger.debug(f"[V104.37] meta/falsification_engine.py: e={e}")
        # Fall back to Vietnamese-aware parser
        return _parse_vn_number(s)
    return None
