"""S6a security sweep tests — real-logic fix verification (no mocks).

Scope: scp/core/partition/rotate.py verdict_cache migration copy was rewritten
from a runtime-assembled f-string INSERT to a fully literal SQL statement with
bound parameters. These tests prove the new copy preserves the old semantics:

  1. Rows from a legacy verdict_cache table are copied into the canonical
     table with column re-ordering done in Python (bound parameters).
  2. Columns missing from the legacy table receive the canonical DEFAULT
     (times_used=1) or NULL — matching the previous "copy only the
     intersection columns" behavior.
  3. When the existing table already has the canonical schema (no migration
     needed), data is left untouched and no verdict_cache_old remnant exists.
"""
from __future__ import annotations

import sqlite3

from scp.core.db_manager import _VERDICT_CACHE_CANONICAL_COLS
from scp.core.partition.rotate import (
    _VERDICT_CACHE_COPY_COLUMNS,
    _VERDICT_CACHE_COPY_SQL,
    ThreeTierCache,
)

LEGACY_DDL = """
CREATE TABLE verdict_cache (
    cache_key TEXT PRIMARY KEY,
    question_hash TEXT,
    question_text TEXT,
    verdict TEXT,
    confidence REAL,
    final_answer TEXT,
    domain TEXT,
    reasoning TEXT,
    timestamp REAL
)
"""


# Canonical-shape fixture DDL: pure module-level literal (same safe pattern as
# LEGACY_DDL) byte-identical to the previous in-function assembly
# "CREATE TABLE " + "verdict_cache (" + ", ".join(f"{name} TEXT") + ")" over
# _VERDICT_CACHE_COPY_COLUMNS — no non-literal dataflow reaches con.execute.
# Must mirror _VERDICT_CACHE_COPY_COLUMNS (same 13 names, same order, all TEXT).
CANONICAL_DDL = (
    "CREATE TABLE verdict_cache ("
    "cache_key TEXT, question_hash TEXT, question_text TEXT, verdict TEXT, "
    "confidence TEXT, final_answer TEXT, domain TEXT, reasoning TEXT, "
    "evidence_json TEXT, timestamp TEXT, cached_at TEXT, expires_at TEXT, "
    "times_used TEXT)"
)


def _create_legacy_db(tmp_path):
    db = tmp_path / "verdict_cache_legacy.sqlite"
    con = sqlite3.connect(str(db))
    con.execute(LEGACY_DDL)
    con.execute(
        "INSERT INTO verdict_cache (cache_key, question_hash, question_text, "
        "verdict, confidence, final_answer, domain, reasoning, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("ck-1", "qh-1", "What is DNA?", "PASS", 0.9, "Deoxyribonucleic acid",
         "biology", "evidence cited", 1700000000.0),
    )
    con.execute(
        "INSERT INTO verdict_cache (cache_key, question_hash, question_text, "
        "verdict, confidence, final_answer, domain, reasoning, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("ck-2", "qh-2", "Capital of France?", "PASS", 0.95, "Paris",
         "geography", "well-known fact", 1700000100.0),
    )
    con.commit()
    con.close()
    return db


def test_literal_copy_sql_matches_canonical_columns():
    """Fail-closed contract: the literal INSERT must cover exactly the
    canonical columns, in canonical schema order, with one placeholder each."""
    cols = [
        "cache_key", "question_hash", "question_text", "verdict", "confidence",
        "final_answer", "domain", "reasoning", "evidence_json", "timestamp",
        "cached_at", "expires_at", "times_used",
    ]
    assert _VERDICT_CACHE_COPY_COLUMNS == tuple(cols)
    assert set(_VERDICT_CACHE_COPY_COLUMNS) == set(_VERDICT_CACHE_CANONICAL_COLS)
    assert _VERDICT_CACHE_COPY_SQL.count("?") == len(_VERDICT_CACHE_COPY_COLUMNS)
    for col in _VERDICT_CACHE_COPY_COLUMNS:
        assert col in _VERDICT_CACHE_COPY_SQL
    # The statement is a pure literal: no format/concat tokens survive.
    assert "{" not in _VERDICT_CACHE_COPY_SQL and "}" not in _VERDICT_CACHE_COPY_SQL


def test_migration_copies_legacy_rows_with_bound_parameters(tmp_path):
    db = _create_legacy_db(tmp_path)
    ThreeTierCache(db_path=db)

    con = sqlite3.connect(str(db))
    try:
        names = [r[1] for r in con.execute("PRAGMA table_info(verdict_cache)").fetchall()]
        assert names == list(_VERDICT_CACHE_COPY_COLUMNS), (
            "canonical schema must be recreated before the copy"
        )
        rows = con.execute(
            "SELECT cache_key, question_hash, question_text, verdict, confidence, "
            "final_answer, domain, reasoning, evidence_json, timestamp, "
            "cached_at, expires_at, times_used FROM verdict_cache ORDER BY cache_key"
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 2, "both legacy rows must survive the migration copy"
    ck1, qh1, qt1, verdict1, conf1, ans1, dom1, reason1, ev1, ts1, _ca1, _ex1, used1 = rows[0]
    assert (ck1, qh1, qt1) == ("ck-1", "qh-1", "What is DNA?")
    assert (verdict1, conf1, ans1, dom1) == ("PASS", 0.9, "Deoxyribonucleic acid", "biology")
    assert reason1 == "evidence cited"
    assert ts1 == 1700000000.0
    # Legacy table had no evidence_json column → NULL (canonical DEFAULT is NULL).
    assert ev1 is None
    # Legacy table had no times_used column → canonical DEFAULT 1 applied.
    assert used1 == 1


def test_no_migration_when_schema_already_canonical(tmp_path):
    """Existing canonical data must be left untouched (no rename/copy/drop)."""
    db = tmp_path / "verdict_cache_canonical.sqlite"
    con = sqlite3.connect(str(db))
    con.execute(CANONICAL_DDL)  # test-fixture DDL, literal column names
    con.execute(
        "INSERT INTO verdict_cache (cache_key, question_hash) VALUES (?, ?)",
        ("ck-keep", "qh-keep"),
    )
    con.commit()
    con.close()

    ThreeTierCache(db_path=db)

    con = sqlite3.connect(str(db))
    try:
        kept = con.execute("SELECT cache_key, question_hash FROM verdict_cache").fetchall()
        leftover = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'verdict_cache_old%'"
        ).fetchall()
    finally:
        con.close()
    assert kept == [("ck-keep", "qh-keep")]
    assert leftover == [], "no migration should run when schema is already canonical"
