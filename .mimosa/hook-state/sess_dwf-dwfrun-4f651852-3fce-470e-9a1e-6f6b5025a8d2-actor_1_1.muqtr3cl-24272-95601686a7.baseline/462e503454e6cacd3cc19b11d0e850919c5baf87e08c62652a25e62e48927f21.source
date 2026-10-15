"""[V104.34 #42] knowledge_io — SQL identifier sanitization for knowledge DB.

TẠI SAO: Behavioral test test_v10434_42 expects _sanitize_identifier() to
exist AND be called on column names before SQL execution. This prevents
SQL injection via crafted column names (CWE-89).

The function was previously in a larger knowledge_io module that got
deleted during refactor. This restore provides the security-critical
sanitizer + documents the contract.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("scp.core.knowledge_io")

# Allow only alphanumeric + underscore for SQL identifiers (column/table names)
_SAFE_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_SAFE_WHERE = re.compile(
    r'^[A-Za-z_][A-Za-z0-9_]*\s*(?:=|<>|!=|<=|>=|<|>|LIKE|IS(?:\s+NOT)?)\s*\?$',
    re.IGNORECASE,
)


def _sanitize_identifier(identifier: str) -> str:
    """Sanitize a SQL identifier (column/table name) to prevent injection.

    [V104.34 #42] Must be called on ALL dynamic column names before SQL.
    Returns the identifier if safe, raises ValueError if dangerous.

    Safe: alphanumeric + underscore, starts with letter/underscore.
    Dangerous: anything with quotes, semicolons, --, /*, etc.
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError(f"Invalid identifier: {identifier!r}")
    if not _SAFE_IDENTIFIER.match(identifier):
        raise ValueError(
            f"Unsafe SQL identifier rejected: {identifier!r} "
            f"(only [A-Za-z_][A-Za-z0-9_]* allowed)"
        )
    return identifier


def _sanitize_identifier_quoted(identifier: str) -> str:
    """Sanitize + double-quote for use in SQL: `"column_name"`."""
    safe = _sanitize_identifier(identifier)
    return f'"{safe}"'


def build_select_query(table: str, columns: list[str], where: str = "") -> str:
    """Build a safe SELECT query with sanitized table + column names.

    Example:
        build_select_query("knowledge", ["claim", "verified"], "id = ?")
        → 'SELECT "claim", "verified" FROM "knowledge" WHERE id = ?'
    """
    safe_table = _sanitize_identifier_quoted(table)
    safe_cols = ", ".join(_sanitize_identifier_quoted(c) for c in columns)
    # Call _sanitize_identifier(c) explicitly per V104.34 #42 contract
    for c in columns:
        _sanitize_identifier(c)
    query = f"SELECT {safe_cols} FROM {safe_table}"  # nosec B608 — identifiers and WHERE grammar are allowlisted above.
    if where:
        normalized_where = where.strip()
        if not _SAFE_WHERE.fullmatch(normalized_where):
            raise ValueError("Unsafe WHERE clause; use one identifier/operator and a bound ? value")
        query += f" WHERE {normalized_where}"  # nosec B608 — validated placeholder-only predicate.
    return query


__all__ = ["_sanitize_identifier", "_sanitize_identifier_quoted", "build_select_query"]
