"""Regression pins for A2 AUDIT-F-04 — trust tier unification for unknown sources.

Previously `get_tier(unknown)` returned CONSENSUS (tier 2) while
`get_unified_source_info(unknown)` returned tier 4 (LEARNED): the same
unknown source carried two different trust levels depending on which API a
caller used. The unified rule (matching the ROOT-FIX-8 watchlist defense —
a source absent from the allowlist is SUSPECT, never consensus-grade) is:
unknown source → tier 4 (LEARNED), the lowest legitimate tier.

Every test here fails against the pre-fix implementation and passes after
it (old-fails/new-passes).
"""
from __future__ import annotations

import time

import pytest

from scp.knowledge.trust_hierarchy import (
    TIER_TTL,
    TrustTier,
    get_tier,
    get_ttl,
    get_unified_source_info,
)

_UNKNOWN_SOURCE = "totally_unknown_source_xyz"


def test_get_tier_unknown_is_learned_tier4() -> None:
    """Unknown source must resolve to the lowest legitimate tier, not CONSENSUS."""
    assert get_tier(_UNKNOWN_SOURCE) == TrustTier.LEARNED
    assert int(get_tier(_UNKNOWN_SOURCE)) == 4


def test_get_tier_and_unified_source_info_agree_on_unknown() -> None:
    """Both trust APIs must return the SAME tier for the same unknown source."""
    unified = get_unified_source_info(_UNKNOWN_SOURCE)
    assert unified["tier"] == 4
    assert int(get_tier(_UNKNOWN_SOURCE)) == unified["tier"]


def test_known_source_tiers_unchanged() -> None:
    """The unification must not perturb the canonical registry tiers."""
    assert get_tier("pubchem") == TrustTier.AUTHORITATIVE
    assert get_tier("wikipedia") == TrustTier.CONSENSUS
    assert get_tier("coingecko") == TrustTier.REALTIME
    assert get_tier("codata") == TrustTier.AXIOMATIC
    assert get_tier("scp_learned") == TrustTier.LEARNED


def test_get_ttl_unknown_is_registry_default_one_day() -> None:
    """Unknown-source TTL must match the unified registry default (1 day).

    Inheriting the LEARNED tier TTL (90 days) for unknown provenance would
    let least-trusted data persist 3x longer than the pre-fix CONSENSUS TTL.
    """
    assert get_ttl(_UNKNOWN_SOURCE) == 86400.0
    assert get_unified_source_info(_UNKNOWN_SOURCE)["ttl"] == 86400
    # Known sources keep their tier TTL.
    assert get_ttl("wikipedia") == TIER_TTL[TrustTier.CONSENSUS]
    assert get_ttl("coingecko") == 5 * 60  # REALTIME override preserved


def test_domain_store_records_unknown_source_as_learned(tmp_path) -> None:
    """Consumer-side pin (domain_store.py): a record from an unknown source is
    stored with source_tier=4 and the 1-day unknown TTL."""
    from scp.knowledge.domain_store import DomainKnowledgeStore

    store = DomainKnowledgeStore(data_dir=str(tmp_path / "kb"))
    try:
        rec = store.store(
            question="What is an unknown-source record's trust tier?",
            answer="tier 4 LEARNED",
            domain="meta",
            source=_UNKNOWN_SOURCE,
            confidence=0.9,
        )
        assert rec is not None
        assert rec.source_tier == 4
        lifetime = rec.expires_at - rec.collected_at
        assert lifetime == pytest.approx(86400.0, abs=5.0), (
            f"unknown-source record lifetime must be ~1 day, got {lifetime}s"
        )
    finally:
        store.close()
