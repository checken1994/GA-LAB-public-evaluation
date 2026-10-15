"""Foundation DB contract (26-P0.04): create -> migrate -> close -> reopen ->
integrity holds; tampered migration history BLOCKS startup (fail closed).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scp.persistence import FoundationDB, MigrationError

MIGRATIONS = [
    (
        "0001_base",
        [
            "CREATE TABLE things (id TEXT PRIMARY KEY, name TEXT NOT NULL)",
            "INSERT INTO things (id, name) VALUES ('t1', 'first')",
        ],
    ),
    (
        "0002_extra",
        ["CREATE TABLE extras (thing_id TEXT NOT NULL REFERENCES things(id), note TEXT)"],
    ),
]


def test_create_migrate_close_reopen_keeps_schema_and_data(tmp_path):
    db_path = tmp_path / "foundation.sqlite3"

    db = FoundationDB(db_path, MIGRATIONS)
    with db.transaction() as conn:
        conn.execute("INSERT INTO extras (thing_id, note) VALUES ('t1', 'hello')")
    applied = db.applied_migrations()
    assert [row["migration_id"] for row in applied] == ["0001_base", "0002_extra"]
    db.close()

    reopened = FoundationDB(db_path, MIGRATIONS)
    assert reopened.query("SELECT name FROM things") == [{"name": "first"}]
    assert reopened.query("SELECT note FROM extras") == [{"note": "hello"}]
    assert len(reopened.applied_migrations()) == 2
    check = reopened.query("PRAGMA quick_check")
    assert check and check[0].get("quick_check") == "ok"
    reopened.close()


def test_tampered_migration_checksum_blocks_startup(tmp_path):
    db_path = tmp_path / "tampered.sqlite3"
    FoundationDB(db_path, MIGRATIONS).close()

    # An operator/agent edits an ALREADY-APPLIED migration in code: the
    # checksum recorded in the DB no longer matches -> startup BLOCKED.
    edited = [
        (MIGRATIONS[0][0], [MIGRATIONS[0][1][0]]),  # 0001 lost its INSERT
        MIGRATIONS[1],
    ]
    with pytest.raises(MigrationError, match="checksum mismatch"):
        FoundationDB(db_path, edited)


def test_failed_migration_rolls_back_atomically(tmp_path):
    db_path = tmp_path / "rollback.sqlite3"
    bad_migrations = [
        ("0001_ok", ["CREATE TABLE keep_me (id TEXT PRIMARY KEY)"]),
        ("0002_broken", ["CREATE TABLE broken (id TEXT)", "THIS IS NOT SQL"]),
    ]
    with pytest.raises(sqlite3.OperationalError):
        FoundationDB(db_path, bad_migrations)

    # The broken migration left NO partial schema and NO migration record.
    # Reopening with the SAME applied migration (0001_ok) must succeed cleanly.
    db = FoundationDB(db_path, [("0001_ok", ["CREATE TABLE keep_me (id TEXT PRIMARY KEY)"])])
    names = [row["name"] for row in db.query("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "keep_me" in names and "broken" not in names
    assert [row["migration_id"] for row in db.applied_migrations()] == ["0001_ok"]


import sqlite3
