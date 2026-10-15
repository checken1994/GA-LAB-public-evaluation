import os
import tempfile

os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")

from scp.persistence import FoundationDB


def test_subsystem_persistence_importable():
    """Persistence layer: verify FoundationDB initialization, migrations, and queries."""
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "foundation_test.db")
        migrations = [("001_init", ["CREATE TABLE item (id INTEGER PRIMARY KEY, name TEXT)"])]
        db = FoundationDB(db_path, migrations)
        try:
            applied = db.applied_migrations()
            assert len(applied) == 1
            assert applied[0]["migration_id"] == "001_init"
            
            db.execute("INSERT INTO item (name) VALUES (?)", ("widget",))
            rows = db.query("SELECT * FROM item WHERE name = ?", ("widget",))
            assert len(rows) == 1
            assert rows[0]["name"] == "widget"
        finally:
            db.close()
