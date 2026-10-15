import sqlite3

from scp.core import db_manager
from scp.prediction.predictive import init_predictions_db


def test_prediction_db_schema_and_constraints(tmp_path, monkeypatch):
    db_file = tmp_path / "v14.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_file))
    # Order/state isolation: db_manager owns ONE process-wide connection
    # (_persistent_conn) bound to whatever DB_PATH was current at its first
    # use. In the full suite, an earlier file (e.g. T03 flow_06's m6_engine
    # fixture calling init_predictions_db() on the shared DB) leaves that
    # cache bound to a foreign path, so patching DB_PATH alone is a silent
    # no-op: init_predictions_db() writes the schema into the foreign DB and
    # this test's tmp file stays empty. Reset the cached connection so the
    # patched path is actually honored; monkeypatch restores the previous
    # connection object afterwards, preserving the rest of the suite's state.
    monkeypatch.setattr(db_manager, "_persistent_conn", None)
    init_predictions_db()
    with sqlite3.connect(str(db_file)) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "predictions" in tables
        cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
        assert "id" in cols
        assert "status" in cols
        assert "check_date" in cols
