"""Reality test for Fix 4-a-011: vector_db uses actual store file mtime.

Behavioral execution test: verifies that VectorStore records actual file mtime
on inserted vector records, rather than os.path.getmtime('.').
"""
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

def test_vector_store_records_actual_file_mtime(tmp_path):
    from scp.capabilities.vector_db import VectorStore

    db_file = tmp_path / "test_vectors.db"
    store = VectorStore(db_path=str(db_file))

    # Mock embedding model to isolate from heavy third-party models
    store._get_model = MagicMock(return_value=MagicMock(encode=lambda text: MagicMock(tolist=lambda: [0.1, 0.2, 0.3])))

    added = store.add("quantum mechanics", metadata={"tag": "physics"})
    assert added is True

    # Read row and check timestamp matches store file mtime
    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute("SELECT text, timestamp FROM vectors WHERE text='quantum mechanics'").fetchone()
        assert row is not None
        actual_mtime = os.path.getmtime(str(db_file))
        assert float(row[1]) == pytest.approx(actual_mtime, rel=1e-2)

if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        test_vector_store_records_actual_file_mtime(Path(tmp))
    print("PASS: reality_4-a-011 behavioral tests passed")
