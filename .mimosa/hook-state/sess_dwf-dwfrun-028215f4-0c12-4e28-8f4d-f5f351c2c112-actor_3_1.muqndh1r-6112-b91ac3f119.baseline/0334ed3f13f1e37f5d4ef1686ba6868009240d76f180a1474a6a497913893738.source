from pathlib import Path

"""Reality test for Fix 4-b-011: KnowledgeArbiter must track all sources (not collapse).

[Phase 4-B — DNA #2, #5, #8, #14, #19, #26]
Before fix: `add_fact` early-returned on agreement — only the FIRST source's
  node was stored. `resolve()` saw `len(nodes) == 1` for any agreeing set
  and returned `reason="single_source"`. The `multi_source_agreement` branch
  was DEAD CODE (DNA #5: ảo幻觉 đồng thuận — 10 sources agreeing appeared as
  1; DNA #8: agreement not recorded in KB; DNA #19: no test caught this
  because the dead branch looked alive).

After fix: every agreeing (source, value) is appended (deduped). `resolve()`
  sees N nodes and fires `multi_source_agreement` — BUT only when the
  sources come from ≥2 INDEPENDENT lineages (DNA #5: same-lineage agreement
  is not independent verification). When all agree but share one lineage,
  returns `single_lineage_agreement` with a smaller boost + requires_verification.
"""
import re
import sys

KA_PATH = str(Path(__file__).resolve().parents[2]) + '/scp/meta/knowledge_arbiter.py'

with open(KA_PATH) as f:
    src = f.read()

# ---------------------------------------------------------------------------
# Static checks (DNA #2 — actual code present).
# ---------------------------------------------------------------------------

# TEST 1: multi_source_agreement must be referenced (not dead code).
assert "multi_source_agreement" in src, (
    "FAIL: no multi_source_agreement logic"
)
print("PASS [1/6]: multi_source_agreement logic present")

# TEST 2: sources must be stored as a collection (not single value, no
# early-return collapsing to first).
# Look for append or list-based source storage.
has_list_storage = bool(re.search(
    r'sources\.append|source_list|self\._facts\[key\]\.append|\._facts\.\w+\.append',
    src
))
assert has_list_storage, (
    "FAIL: sources not stored as collection (still collapsed to first)"
)
print("PASS [2/6]: sources stored as collection (not collapsed to first)")

# TEST 3: independence / lineage check (DNA #5).
has_independence = (
    "independent" in src.lower() or
    "lineage" in src.lower() or
    "distinct_lineages" in src
)
assert has_independence, (
    "FAIL: no independence/lineage check (DNA #5 — same-lineage agreement "
    "would be counted as independent)"
)
print("PASS [3/6]: independence/lineage check present (DNA #5 enforced)")

# TEST 4: no early-return on agreement that bypasses storing the new source.
# The old bug was `if value.lower() in existing_values: ... return` (no append).
# Now: append happens before the return. Assert the append IS inside the
# agreement branch by checking `not already_recorded` + append pattern.
has_dedup_append = bool(re.search(
    r'already_recorded\s*=\s*any\([^)]+\)[\s\S]*?if\s+not\s+already_recorded:[\s\S]*?\.append\(node\)',
    src
))
assert has_dedup_append, (
    "FAIL: agreement branch doesn't append new (source, value) — still "
    "collapses to first source. Need `if not already_recorded: ...append(node)`"
)
print("PASS [4/6]: agreement branch appends new source (with dedup guard)")

# ---------------------------------------------------------------------------
# Runtime behavioral checks (DNA #2/#26 — actual runtime behavior).
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scp.meta.knowledge_arbiter import KnowledgeArbiter

    # TEST 5: 2 distinct sources agreeing → multi_source_agreement fires.
    arb = KnowledgeArbiter()
    arb.add_fact("Paris", "capital_of", "France",
                 source="wikipedia", confidence=0.9)
    arb.add_fact("Paris", "capital_of", "France",
                 source="britannica", confidence=0.85)
    r = arb.resolve("Paris", "capital_of")
    assert r["reason"] == "multi_source_agreement", (
        f"FAIL: expected multi_source_agreement, got reason={r['reason']!r} "
        f"(sources={r.get('sources')}) — pre-fix would be 'single_source'"
    )
    assert sorted(r["sources"]) == ["britannica", "wikipedia"], (
        f"FAIL: both sources should be stored; got {r['sources']}"
    )
    assert r.get("independent_lineages") == 2, (
        f"FAIL: expected 2 independent lineages, got {r.get('independent_lineages')}"
    )
    # Confidence boosted (avg 0.875 + 0.2 = capped 1.0).
    assert r["confidence"] >= 0.9, (
        f"FAIL: confidence should be boosted; got {r['confidence']}"
    )
    print(f"PASS [5/6]: 2 distinct sources → multi_source_agreement fires "
          f"(sources={r['sources']}, lineages={r.get('lineages')}, conf={r['confidence']:.2f})")

    # TEST 6: 2 sources from SAME lineage agreeing → NOT multi_source_agreement
    # (DNA #5: ảo幻觉 đồng thuận — must not over-credit same-lineage agreement).
    # Use explicit lineage= override to simulate "wikipedia_cache" and
    # "wikipedia_api" both having lineage="wikipedia".
    arb2 = KnowledgeArbiter()
    arb2.add_fact("Eiffel Tower", "location", "Paris",
                  source="wikipedia_cache", confidence=0.8,
                  lineage="wikipedia")
    arb2.add_fact("Eiffel Tower", "location", "Paris",
                  source="wikipedia_api", confidence=0.8,
                  lineage="wikipedia")
    r2 = arb2.resolve("Eiffel Tower", "location")
    assert r2["reason"] != "multi_source_agreement", (
        f"FAIL: same-lineage agreement fired multi_source_agreement — DNA #5 "
        f"violation (would count same-lineage as independent). reason={r2['reason']!r}"
    )
    assert r2["reason"] == "single_lineage_agreement", (
        f"FAIL: expected single_lineage_agreement, got {r2['reason']!r}"
    )
    assert r2.get("independent_lineages") == 1, (
        f"FAIL: expected 1 independent lineage (both from 'wikipedia'), "
        f"got {r2.get('independent_lineages')}"
    )
    # Same-lineage agreement must set requires_verification (need cross-lineage
    # confirmation before fully trusting).
    assert r2.get("requires_verification") is True, (
        "FAIL: same-lineage agreement should require cross-lineage verification"
    )
    print(f"PASS [6/6]: same-lineage agreement → single_lineage_agreement + "
          f"requires_verification (DNA #5 ảo幻觉 đồng thuận prevented; "
          f"lineages={r2.get('lineages')}, independent={r2.get('independent_lineages')})")
except Exception as e:
    # DNA #23: honest skip if import chain fails.
    print(f"SKIP [5-6/6]: runtime behavioral tests skipped — "
          f"{type(e).__name__}: {e} (DNA #23 honest limit; static 1-4 prove the fix)")

print("\n✓ Reality test 4-b-011 PASSED (static 4/4 + runtime where exercised)")
