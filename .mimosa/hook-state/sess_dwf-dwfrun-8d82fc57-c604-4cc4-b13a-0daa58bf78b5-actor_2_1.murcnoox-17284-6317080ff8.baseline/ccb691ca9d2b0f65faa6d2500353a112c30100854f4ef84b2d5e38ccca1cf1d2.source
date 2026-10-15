"""Canonical time rules (26-P0.2): UTC ISO-8601 timezone-aware for provenance;
monotonic clocks are for durations/rate limits only and never persisted as wall time.
"""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError(
            "naive datetime rejected - provenance requires timezone-aware UTC timestamps"
        )
    return dt.astimezone(timezone.utc)


def parse_utc_iso(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    return ensure_aware_utc(parsed)
