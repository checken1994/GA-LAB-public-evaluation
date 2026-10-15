"""Canonical data classes + severity composition (26-P0.9 privacy contract).

Derived data can never silently become less sensitive than its inputs:
compose with max_severity() before persisting or exporting.
"""
from __future__ import annotations

from enum import Enum


class DataClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"


_SEVERITY = {member: index for index, member in enumerate(DataClass)}


def parse_data_class(value: object) -> DataClass:
    raw = value.value if isinstance(value, DataClass) else str(value).strip().upper()
    try:
        return DataClass(raw)
    except ValueError as exc:
        raise ValueError(f"invalid data class: {value!r}") from exc


def max_severity(*classes: object) -> DataClass:
    """The most restrictive class among the inputs.

    [P0-12a FIX 2026-09-02] Missing/unknown classification (None) is treated as
    a SENSITIVE floor, not skipped: an unclassified input must never LOWER the
    composed class (PUBLIC + None -> SENSITIVE). Only explicit sanitization with
    declassification evidence may reduce a class.
    """
    worst = DataClass.PUBLIC
    saw_unknown = False
    for value in classes:
        if value is None:
            saw_unknown = True
            continue
        candidate = parse_data_class(value)
        if _SEVERITY[candidate] > _SEVERITY[worst]:
            worst = candidate
    if saw_unknown and _SEVERITY[worst] < _SEVERITY[DataClass.SENSITIVE]:
        worst = DataClass.SENSITIVE
    return worst
