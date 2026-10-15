import os
import sqlite3
from unittest.mock import MagicMock

import pytest

from scp.capabilities.vector_db import VectorStore


def test_vector_store_initialization_and_table_schema(tmp_path):
    db_file = tmp_path / "vectors.db"
    VectorStore(db_path=str(db_file))
    assert db_file.exists()
    with sqlite3.connect(str(db_file)) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(vectors)").fetchall()]
        assert "id" in cols
        assert "text" in cols
        assert "embedding" in cols
        assert "timestamp" in cols

def test_vector_store_add_records_actual_file_mtime(tmp_path):
    db_file = tmp_path / "vectors.db"
    store = VectorStore(db_path=str(db_file))
    store._get_model = MagicMock(return_value=MagicMock(encode=lambda text: MagicMock(tolist=lambda: [0.1, 0.2, 0.3])))
    added = store.add("quantum mechanics", metadata={"tag": "physics"})
    assert added is True
    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute("SELECT text, timestamp, metadata FROM vectors WHERE text='quantum mechanics'").fetchone()
        assert row is not None
        assert float(row[1]) == pytest.approx(os.path.getmtime(str(db_file)), rel=1e-2)
