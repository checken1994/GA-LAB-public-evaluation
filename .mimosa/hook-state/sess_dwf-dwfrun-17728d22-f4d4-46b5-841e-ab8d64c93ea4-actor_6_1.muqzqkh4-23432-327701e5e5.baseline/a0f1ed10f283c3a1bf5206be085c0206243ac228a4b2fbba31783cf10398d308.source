"""Classify observed learning counters without inventing a cause or success."""
from __future__ import annotations

import sqlite3
from typing import Any

LEARNING_OUTCOME_STATUSES = frozenset({
    "SUCCESS", "NO_NEW_FACTS", "PROVIDER_FAILED", "VERIFY_REJECTED",
    "DB_WRITE_FAILED", "TIMEOUT", "DISABLED", "UNKNOWN",
})


def _count(payload: dict[str, Any], key: str, alias: str | None = None) -> int | None:
    value = payload.get(key, payload.get(alias) if alias else None)
    if value is None or isinstance(value, bool):
        return None
    try:
        count = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if count < 0 or (isinstance(value, float) and count != value):
        return None
    return count


def classify_learning_outcome(
    result: Any, error: BaseException | None = None, *, mode: str | None = None,
) -> str:
    """Classify only what the counters and explicit errors actually prove."""
    if error is not None:
        if isinstance(error, TimeoutError) or "timeout" in str(error).lower():
            return "TIMEOUT"
        if isinstance(error, sqlite3.Error):
            return "DB_WRITE_FAILED"
        return "UNKNOWN"
    if not isinstance(result, dict):
        return "UNKNOWN"
    payload = result
    if payload.get("db_write_failed") or payload.get("ledger_write_error") or payload.get("ledger_status") == "DB_WRITE_FAILED":
        return "DB_WRITE_FAILED"
    declared = payload.get("status")
    if isinstance(declared, str) and declared in LEARNING_OUTCOME_STATUSES - {"SUCCESS", "NO_NEW_FACTS"}:
        return declared
    if payload.get("action") == "skipped":
        return "DISABLED" if payload.get("reason") == "evolution disabled" else "UNKNOWN"
    evolution = mode == "evolution" or "bugs_found" in payload
    verified = _count(payload, "verified", "bugs_fixed" if evolution else None)
    stored = _count(payload, "stored", "lessons_stored" if evolution else None)
    provider_failed = _count(payload, "provider_failed", "provider_errors")
    if provider_failed and not verified:
        return "PROVIDER_FAILED"
    if verified is None or stored is None or stored != verified:
        return "UNKNOWN"
    asked = _count(payload, "bugs_found" if evolution else "asked", None if evolution else "questions")
    if asked is None or verified > asked:
        return "UNKNOWN"
    if verified > 0:
        return "SUCCESS"
    return "VERIFY_REJECTED" if asked > 0 else "NO_NEW_FACTS"
