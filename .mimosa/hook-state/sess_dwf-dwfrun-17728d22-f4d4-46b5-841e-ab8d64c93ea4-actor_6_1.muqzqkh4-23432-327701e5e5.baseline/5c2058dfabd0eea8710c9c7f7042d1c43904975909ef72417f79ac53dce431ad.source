from __future__ import annotations

import sqlite3

import pytest

from scp.epistemic.lineage import IndependenceStatus, LineageStore
from scp.epistemic.source_identity import SourceKind, SourceStore, canonicalize_url


def test_source_identity_is_conservative_and_stable(tmp_path):
    db = tmp_path / "epistemic.sqlite"
    store = SourceStore(db)
    a = store.register(kind=SourceKind.WEB_DOCUMENT, identity="HTTPS://Example.COM:443/a?b=2&a=1#frag")
    b = store.register(kind=SourceKind.WEB_DOCUMENT, identity="https://example.com/a?b=2&a=1")
    assert a.source_id == b.source_id
    assert a.canonical_identity == "https://example.com/a?b=2&a=1"
    # Query ordering is deliberately preserved; arbitrary query sorting could
    # merge semantically different resources.
    c = store.register(kind=SourceKind.WEB_DOCUMENT, identity="https://example.com/a?a=1&b=2")
    assert c.source_id != a.source_id
    with pytest.raises(ValueError):
        canonicalize_url("https://user:secret@example.com/a")
    store.close()


def test_db_default_is_unknown_independence_not_python_only(tmp_path):
    db = tmp_path / "epistemic.sqlite"
    lineage = LineageStore(db)
    # Bypass the public helper and insert raw SQL WITHOUT status. SQLite itself
    # must still choose UNKNOWN_INDEPENDENCE.
    with lineage.db.transaction() as conn:
        conn.execute(
            "INSERT INTO source_independence(source_a,source_b,evaluated_at) VALUES (?,?,?)",
            ("src_0000000000000001", "src_0000000000000002", "2026-01-01T00:00:00+00:00"),
        )
    row = lineage.db.query("SELECT status FROM source_independence")[0]
    assert row["status"] == IndependenceStatus.UNKNOWN_INDEPENDENCE.value
    # CHECK constraint is machine-enforced too.
    with pytest.raises(sqlite3.IntegrityError):
        with lineage.db.transaction() as conn:
            conn.execute(
                "INSERT INTO source_independence(source_a,source_b,status,evaluated_at) VALUES (?,?,?,?)",
                ("src_0000000000000003", "src_0000000000000004", "TRUST_ME", "2026-01-01T00:00:00+00:00"),
            )
    lineage.close()


def test_unknown_and_shared_sources_cannot_manufacture_independence(tmp_path):
    lineage = LineageStore(tmp_path / "epistemic.sqlite")
    a = "src_0000000000000011"
    b = "src_0000000000000012"
    c = "src_0000000000000013"

    # A/B are an exact copy, so at most likely-shared. B/C has not been
    # assessed and therefore remains UNKNOWN. Neither relation can create a
    # second independent lineage.
    lineage.resolve_deterministic(a, b, exact_content_copy=True)
    support = lineage.assess_independent_support([a, b, c])
    assert support["source_count"] == 3
    assert support["known_independent_lineages"] == 1
    assert support["unknown_pairs"] >= 1

    # Independence must carry an explicit allowed basis. Different domain or
    # high reputation is not enough.
    with pytest.raises(ValueError):
        lineage.record_relation(a, c, status="INDEPENDENT", basis=[{"type": "different_domain"}])

    lineage.record_relation(
        a,
        c,
        status="INDEPENDENT",
        basis=[{"type": "independent_primary_observation"}],
        evidence_refs=["ev_0000000000000001"],
    )
    lineage.record_relation(
        b,
        c,
        status="INDEPENDENT",
        basis=[{"type": "independent_primary_observation"}],
        evidence_refs=["ev_0000000000000002"],
    )
    support = lineage.assess_independent_support([a, b, c])
    assert support["known_independent_lineages"] == 2
    lineage.close()
