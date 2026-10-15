"""Source Lineage authority (26-P0.07).

The core safety invariant is machine-enforced at the database layer:
independence defaults to UNKNOWN_INDEPENDENCE and UNKNOWN contributes zero to
independent-support counts. Source popularity/reputation never upgrades it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from scp.contracts.time import now_utc_iso
from scp.persistence import FoundationDB


class IndependenceStatus(str, Enum):
    UNKNOWN_INDEPENDENCE = "UNKNOWN_INDEPENDENCE"
    SAME_LINEAGE = "SAME_LINEAGE"
    LIKELY_SHARED_LINEAGE = "LIKELY_SHARED_LINEAGE"
    INDEPENDENT = "INDEPENDENT"


_LINEAGE_MIGRATIONS = [
    (
        "0003_source_lineage",
        [
            """CREATE TABLE IF NOT EXISTS source_independence (
                   source_a TEXT NOT NULL,
                   source_b TEXT NOT NULL,
                   status TEXT NOT NULL DEFAULT 'UNKNOWN_INDEPENDENCE'
                     CHECK(status IN ('UNKNOWN_INDEPENDENCE','SAME_LINEAGE','LIKELY_SHARED_LINEAGE','INDEPENDENT')),
                   basis_json TEXT NOT NULL DEFAULT '[]',
                   evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                   resolver_version TEXT NOT NULL DEFAULT 'p0-deterministic-v1',
                   evaluated_at TEXT NOT NULL,
                   PRIMARY KEY (source_a, source_b),
                   CHECK(source_a < source_b))""",
            "CREATE INDEX IF NOT EXISTS idx_source_independence_status ON source_independence(status)",
        ],
    ),
]


@dataclass(frozen=True)
class IndependenceRelation:
    source_a: str
    source_b: str
    status: IndependenceStatus
    basis: tuple[dict, ...]
    evidence_refs: tuple[str, ...]
    resolver_version: str
    evaluated_at: str


def canonical_pair(source_a: str, source_b: str) -> tuple[str, str]:
    a = str(source_a or "").strip()
    b = str(source_b or "").strip()
    if not a or not b:
        raise ValueError("source ids cannot be empty")
    if a == b:
        raise ValueError("independence relation requires two distinct source ids")
    return (a, b) if a < b else (b, a)


class LineageStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db = FoundationDB(db_path, _LINEAGE_MIGRATIONS)

    def ensure_relation(self, source_a: str, source_b: str) -> IndependenceRelation:
        """Ensure a pair row exists using the DB DEFAULT (never Python ALLOW)."""
        a, b = canonical_pair(source_a, source_b)
        with self.db.transaction() as conn:
            # status is intentionally omitted so SQLite's DEFAULT is the
            # authority for UNKNOWN_INDEPENDENCE.
            conn.execute(
                """INSERT OR IGNORE INTO source_independence
                   (source_a,source_b,evaluated_at) VALUES (?,?,?)""",
                (a, b, now_utc_iso()),
            )
        return self.get_relation(a, b, create_if_missing=False)

    def get_relation(
        self, source_a: str, source_b: str, *, create_if_missing: bool = True
    ) -> IndependenceRelation:
        a, b = canonical_pair(source_a, source_b)
        rows = self.db.query(
            "SELECT * FROM source_independence WHERE source_a=? AND source_b=?",
            (a, b),
        )
        if not rows and create_if_missing:
            return self.ensure_relation(a, b)
        if not rows:
            raise KeyError((a, b))
        row = rows[0]
        return IndependenceRelation(
            source_a=row["source_a"],
            source_b=row["source_b"],
            status=IndependenceStatus(row["status"]),
            basis=tuple(json.loads(row["basis_json"] or "[]")),
            evidence_refs=tuple(json.loads(row["evidence_refs_json"] or "[]")),
            resolver_version=row["resolver_version"],
            evaluated_at=row["evaluated_at"],
        )

    def record_relation(
        self,
        source_a: str,
        source_b: str,
        *,
        status: IndependenceStatus | str,
        basis: list[dict] | tuple[dict, ...],
        evidence_refs: list[str] | tuple[str, ...] = (),
        resolver_version: str = "p0-deterministic-v1",
    ) -> IndependenceRelation:
        """Persist an evidence-backed relation.

        INDEPENDENT is never inferred from merely being different domains. The
        caller must provide a non-empty deterministic/observational basis.
        """
        a, b = canonical_pair(source_a, source_b)
        st = status if isinstance(status, IndependenceStatus) else IndependenceStatus(str(status).strip().upper())
        basis_list = [dict(item) for item in basis]
        evidence = [str(item) for item in evidence_refs]
        if st is not IndependenceStatus.UNKNOWN_INDEPENDENCE and not basis_list:
            raise ValueError(f"{st.value} requires evidence/basis")
        if st is IndependenceStatus.INDEPENDENT:
            allowed = {
                "independent_primary_observation",
                "explicit_distinct_origin",
                "independent_runtime_observation",
                "human_validated_independence",
            }
            if not any(str(item.get("type", "")).strip() in allowed for item in basis_list):
                raise ValueError("INDEPENDENT requires an explicit independence basis; different domain/reputation is insufficient")
        ts = now_utc_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO source_independence
                   (source_a,source_b,status,basis_json,evidence_refs_json,resolver_version,evaluated_at)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(source_a,source_b) DO UPDATE SET
                     status=excluded.status,
                     basis_json=excluded.basis_json,
                     evidence_refs_json=excluded.evidence_refs_json,
                     resolver_version=excluded.resolver_version,
                     evaluated_at=excluded.evaluated_at""",
                (
                    a,
                    b,
                    st.value,
                    json.dumps(basis_list, ensure_ascii=False, sort_keys=True),
                    json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                    str(resolver_version),
                    ts,
                ),
            )
        return self.get_relation(a, b, create_if_missing=False)

    def resolve_deterministic(
        self,
        source_a: str,
        source_b: str,
        *,
        same_canonical_identity: bool = False,
        same_explicit_upstream: bool = False,
        exact_content_copy: bool = False,
        near_duplicate: bool = False,
        evidence_refs: list[str] | tuple[str, ...] = (),
    ) -> IndependenceRelation:
        """P0 deterministic resolver.

        It can prove/shared-lineage conservatively, but it intentionally cannot
        prove independence from absence of similarity. If no shared-origin
        evidence exists the DB-default UNKNOWN relation is retained.
        """
        if same_canonical_identity:
            return self.record_relation(
                source_a,
                source_b,
                status=IndependenceStatus.SAME_LINEAGE,
                basis=[{"type": "same_canonical_identity"}],
                evidence_refs=evidence_refs,
            )
        if same_explicit_upstream:
            return self.record_relation(
                source_a,
                source_b,
                status=IndependenceStatus.SAME_LINEAGE,
                basis=[{"type": "explicit_shared_upstream"}],
                evidence_refs=evidence_refs,
            )
        if exact_content_copy:
            return self.record_relation(
                source_a,
                source_b,
                status=IndependenceStatus.LIKELY_SHARED_LINEAGE,
                basis=[{"type": "exact_content_copy"}],
                evidence_refs=evidence_refs,
            )
        if near_duplicate:
            return self.record_relation(
                source_a,
                source_b,
                status=IndependenceStatus.LIKELY_SHARED_LINEAGE,
                basis=[{"type": "near_duplicate"}],
                evidence_refs=evidence_refs,
            )
        return self.ensure_relation(source_a, source_b)

    def assess_independent_support(self, source_ids: list[str] | tuple[str, ...]) -> dict:
        """Return a conservative lower bound on independent source groups.

        UNKNOWN contributes zero additional independent support. Shared-lineage
        edges collapse sources. A component is added to the known-independent
        set only when it is explicitly INDEPENDENT from every already-selected
        component. This can under-count; it must never over-count.
        """
        sources = sorted({str(source).strip() for source in source_ids if str(source).strip()})
        if not sources:
            return {
                "source_count": 0,
                "known_independent_lineages": 0,
                "unknown_pairs": 0,
                "shared_lineage_pairs": 0,
            }

        parent = {s: s for s in sources}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)

        unknown_pairs = 0
        shared_pairs = 0
        relations: dict[tuple[str, str], IndependenceStatus] = {}
        for i, a in enumerate(sources):
            for b in sources[i + 1 :]:
                rel = self.get_relation(a, b)
                relations[(a, b)] = rel.status
                if rel.status in {IndependenceStatus.SAME_LINEAGE, IndependenceStatus.LIKELY_SHARED_LINEAGE}:
                    union(a, b)
                    shared_pairs += 1
                elif rel.status is IndependenceStatus.UNKNOWN_INDEPENDENCE:
                    unknown_pairs += 1

        components: dict[str, list[str]] = {}
        for source in sources:
            components.setdefault(find(source), []).append(source)
        component_list = [tuple(sorted(v)) for _, v in sorted(components.items())]

        selected: list[tuple[str, ...]] = []
        for candidate in component_list:
            if not selected:
                selected.append(candidate)
                continue
            can_add = True
            for chosen in selected:
                for a in candidate:
                    for b in chosen:
                        x, y = canonical_pair(a, b)
                        if relations.get((x, y), self.get_relation(x, y).status) is not IndependenceStatus.INDEPENDENT:
                            can_add = False
                            break
                    if not can_add:
                        break
                if not can_add:
                    break
            if can_add:
                selected.append(candidate)

        return {
            "source_count": len(sources),
            "shared_components": [list(c) for c in component_list],
            "known_independent_lineages": len(selected),
            "unknown_pairs": unknown_pairs,
            "shared_lineage_pairs": shared_pairs,
        }

    def close(self) -> None:
        self.db.close()
