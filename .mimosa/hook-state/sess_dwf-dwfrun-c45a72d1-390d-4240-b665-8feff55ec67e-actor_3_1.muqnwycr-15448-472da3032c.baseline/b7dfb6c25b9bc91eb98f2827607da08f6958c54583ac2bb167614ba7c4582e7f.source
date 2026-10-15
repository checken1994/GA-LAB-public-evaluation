import sqlite3

from scp.experience.experience import ExperienceEngine, init_experience_db


def test_experience_db_initialization_creates_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "test_exp.db"
    monkeypatch.setenv("SCP_DB_PATH", str(db_file))
    import scp.core.db_manager as dbm
    monkeypatch.setattr(dbm, "DB_PATH", str(db_file))
    monkeypatch.setattr(dbm, "_persistent_conn", None)

    dbm.init_db()
    init_experience_db()

    with sqlite3.connect(str(db_file)) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "experiences" in tables
        assert "knowledge_canonical" in tables or "knowledge" in tables or "memory" in tables
        cols = [r[1] for r in conn.execute("PRAGMA table_info(experiences)").fetchall()]
        assert "lesson_type" in cols
        assert "policy_action" in cols
        assert "sha256" in cols

def test_experience_learn_and_deduplicate(tmp_path, monkeypatch):
    db_file = tmp_path / "test_exp2.db"
    monkeypatch.setenv("SCP_DB_PATH", str(db_file))
    import scp.core.db_manager as dbm
    monkeypatch.setattr(dbm, "DB_PATH", str(db_file))
    monkeypatch.setattr(dbm, "_persistent_conn", None)

    dbm.init_db()
    exp = ExperienceEngine()

    lessons = [
        {
            "lesson_type": "SOURCE_RELIABILITY",
            "lesson_description": "Source PubChem is reliable",
            "policy_action": "PRIORITY_HIGH",
            "policy_target": "PubChem",
            "policy_value": "0.95",
        }
    ]
    saved1 = exp.learn(lessons)
    assert saved1 == 1

    # Learning same lesson again should deduplicate via sha256
    saved2 = exp.learn(lessons)
    assert saved2 == 1

    with sqlite3.connect(str(db_file)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
        assert count == 1
