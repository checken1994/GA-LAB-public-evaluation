import sqlite3

import pytest

from scp.persistence import FoundationDB
from scp.world_state.temporal_authority import _MIGRATIONS


def test_temporal_authority_append_only_triggers(tmp_path):
    db_file = tmp_path / "temporal.db"
    FoundationDB(str(db_file), _MIGRATIONS)

    with sqlite3.connect(str(db_file)) as conn:
        conn.execute("""
            INSERT INTO world_assertions(assertion_id, subject, predicate, value_json, epistemic_status, valid_time, system_time, actor_id, evidence_refs_json)
            VALUES ('a1', 'Paris', 'capital_of', '"France"', 'OBSERVED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'actor1', '[]')
        """)
        conn.commit()

        # Update core field must trigger abort
        with pytest.raises(sqlite3.IntegrityError, match="immutable core fields are append-only"):
            conn.execute("UPDATE world_assertions SET subject='London' WHERE assertion_id='a1'")

        # Delete must trigger abort
        with pytest.raises(sqlite3.IntegrityError, match="world assertions are append-only"):
            conn.execute("DELETE FROM world_assertions WHERE assertion_id='a1'")
