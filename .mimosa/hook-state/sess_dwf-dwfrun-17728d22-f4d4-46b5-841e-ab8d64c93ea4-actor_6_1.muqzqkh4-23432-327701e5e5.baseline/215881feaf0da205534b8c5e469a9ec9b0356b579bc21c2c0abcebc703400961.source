"""Keyword search implementation for the canonical domain registry."""
from __future__ import annotations

import re


def search_domains_by_keyword(query: str) -> list[str]:
    """Return matching domain ids sorted by weighted keyword score.

    The canonical ``DOMAINS`` object remains owned by the public registry
    module. It is imported lazily here so extraction preserves the historical
    single source of truth without a circular import during module loading.
    """
    if not query:
        return []

    from scp.data_sources.domain_registry import DOMAINS

    q_lower = query.lower()
    scores: dict[str, int] = {}
    for domain_id, meta in DOMAINS.items():
        score = 0
        for kw in meta.get("keywords", []):
            kw_lower = kw.lower()
            if len(kw_lower) <= 4:
                pattern = r"\b" + re.escape(kw_lower) + r"\b"
                if re.search(pattern, q_lower):
                    score += len(kw_lower)
            elif kw_lower in q_lower:
                score += len(kw_lower)
        if score > 0:
            scores[domain_id] = score
    return sorted(scores.keys(), key=lambda d: -scores[d])


# This function was historically defined by the public registry module. Keep
# that stable import identity even though its implementation now lives here.
search_domains_by_keyword.__module__ = "scp.data_sources.domain_registry"
