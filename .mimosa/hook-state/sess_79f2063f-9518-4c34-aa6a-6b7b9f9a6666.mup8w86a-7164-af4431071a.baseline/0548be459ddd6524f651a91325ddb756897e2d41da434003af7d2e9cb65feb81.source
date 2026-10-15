"""
SCP V100 — Trust Hierarchy + TTL System
=========================================
Phân tier nguồn dữ liệu + TTL (time-to-live) cho từng tier.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger("scp.knowledge.trust_hierarchy")


class TrustTier(IntEnum):
    """Trust hierarchy — tier thấp hơn = authoritative hơn.

    [Fix 4-b-015 / Phase 3-A — DNA #6, #22, #19]
    Valid tiers: 0-4 ONLY. Tier 5 was previously used in UNIFIED_SOURCE_REGISTRY
    for "slm_self" and as the default-unknown in `get_unified_source_info` —
    but `TrustTier(5)` raises `ValueError: 5 is not a valid TrustTier`. This
    silently broke any caller that did `TrustTier(info["tier"])`. Fixed: any
    source previously assigned tier 5 now uses tier 4 (LEARNED, the lowest
    legitimate tier).
    """
    AXIOMATIC = 0
    AUTHORITATIVE = 1
    CONSENSUS = 2
    REALTIME = 3
    LEARNED = 4


TIER_TTL = {
    TrustTier.AXIOMATIC: 0,
    TrustTier.AUTHORITATIVE: 0,
    TrustTier.CONSENSUS: 30 * 86400,
    TrustTier.REALTIME: 5 * 60,
    TrustTier.LEARNED: 90 * 86400,
}

SOURCE_TIER = {
    "codata": TrustTier.AXIOMATIC, "nist": TrustTier.AXIOMATIC,
    "python_ast": TrustTier.AXIOMATIC, "python_math": TrustTier.AXIOMATIC,
    "fda": TrustTier.AUTHORITATIVE, "who": TrustTier.AUTHORITATIVE,
    "drugbank": TrustTier.AUTHORITATIVE, "icd10": TrustTier.AUTHORITATIVE,
    "law_vn": TrustTier.AUTHORITATIVE, "uscode": TrustTier.AUTHORITATIVE,
    "wikipedia": TrustTier.CONSENSUS, "wikidata": TrustTier.CONSENSUS,
    "arxiv": TrustTier.CONSENSUS, "crossref": TrustTier.CONSENSUS,
    "coingecko": TrustTier.REALTIME, "binance": TrustTier.REALTIME,
    "open_meteo": TrustTier.REALTIME, "wttr_in": TrustTier.REALTIME,
    "restcountries": TrustTier.REALTIME, "frankfurter": TrustTier.REALTIME,
    # [Fix 4-b-015] PubChem was tier 3 (REALTIME) here but tier 1
    # (AUTHORITATIVE) in UNIFIED_SOURCE_REGISTRY below — divergent.
    # Canonical resolution: tier 1 (AUTHORITATIVE) — PubChem is NIH's
    # peer-reviewed chemical database, an authoritative scientific source.
    # DNA #6 (Gốc tin cậy): ONE trust root per source.
    "pubchem": TrustTier.AUTHORITATIVE,
    "scp_learned": TrustTier.LEARNED, "experience": TrustTier.LEARNED,
    "curiosity": TrustTier.LEARNED,
}

REALTIME_OVERRIDES = {
    "coingecko": 5 * 60, "binance": 1 * 60, "open_meteo": 30 * 60,
    "wttr_in": 30 * 60, "frankfurter": 24 * 3600,
}


@dataclass
class KnowledgeRecord:
    """1 record trong KnowledgeStore — SHA-256 + TTL + Trust Tier."""
    id: str
    hash: str
    question: str
    answer: str
    domain: str
    source: str
    source_url: str = ""
    source_tier: int = 4
    collected_at: float = 0.0
    source_published_at: float = 0.0
    expires_at: float = 0.0
    verified_by: list[str] = field(default_factory=list)
    verification_count: int = 0
    confidence: float = 0.5
    collected_by: str = "on_demand"
    parent_id: str | None = None
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "hash": self.hash,
            "question": self.question[:500], "answer": self.answer[:500],
            "domain": self.domain, "source": self.source,
            "source_url": self.source_url, "source_tier": self.source_tier,
            "collected_at": self.collected_at,
            "source_published_at": self.source_published_at,
            "expires_at": self.expires_at,
            "verified_by": self.verified_by,
            "verification_count": self.verification_count,
            "confidence": self.confidence,
            "collected_by": self.collected_by,
            "parent_id": self.parent_id, "version": self.version,
        }


def get_tier(source: str) -> TrustTier:
    return SOURCE_TIER.get(source.lower(), TrustTier.CONSENSUS)


def get_ttl(source: str) -> float:
    if source.lower() in REALTIME_OVERRIDES:
        return REALTIME_OVERRIDES[source.lower()]
    return TIER_TTL.get(get_tier(source), 30 * 86400)


def compute_hash(question: str, answer: str, source: str, timestamp: float) -> str:
    data = f"{question}|{answer}|{source}|{timestamp}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def is_expired(record: KnowledgeRecord, now: float = 0) -> bool:
    if record.expires_at == 0:
        return False
    now = now or time.time()
    return now > record.expires_at


def resolve_conflict(records: list[KnowledgeRecord]) -> KnowledgeRecord | None:
    if not records:
        return None
    valid = [r for r in records if not is_expired(r)]
    if not valid:
        return None
    valid.sort(key=lambda r: (r.source_tier, -r.confidence, -r.collected_at))
    return valid[0]


__all__ = [
    "TrustTier", "KnowledgeRecord", "TIER_TTL", "SOURCE_TIER",
    "get_tier", "get_ttl", "compute_hash", "is_expired", "resolve_conflict",
]

# [V104.47 #2] TẠI SAO: SOURCE_WEIGHTS (conflict_resolver) và SOURCE_TIER
# (trust_hierarchy) dùng tên source khác nhau → cùng nguồn 2 kết quả.
# Fix: UNIFIED_SOURCE_REGISTRY — 1 registry cho cả 2.
# Key = canonical lowercase name. Value = {weight, tier, ttl, aliases}.

UNIFIED_SOURCE_REGISTRY = {
    # AXIOMATIC (tier 0, weight 0.99)
    "codata":        {"weight": 0.99, "tier": 0, "ttl": 999999999, "aliases": ["CODATA", "NIST CODATA"]},
    "nist":          {"weight": 0.99, "tier": 0, "ttl": 999999999, "aliases": ["NIST"]},
    "python_ast":    {"weight": 0.99, "tier": 0, "ttl": 999999999, "aliases": ["PythonAST", "python_math"]},
    "python_math":   {"weight": 0.99, "tier": 0, "ttl": 999999999, "aliases": ["PythonMath"]},

    # AUTHORITATIVE (tier 1, weight 0.95)
    "pubchem":       {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["PubChem", "PubChem API", "pubchem api"]},
    "fda":           {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["FDA", "fda_approval"]},
    "who":           {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["WHO", "World Health Organization"]},
    "drugbank":      {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["DrugBank"]},
    "icd10":         {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["ICD-10", "ICD10"]},
    "law_vn":        {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["Vietnamese Law"]},
    "uscode":        {"weight": 0.95, "tier": 1, "ttl": 604800, "aliases": ["US Code"]},

    # CONSENSUS (tier 2, weight 0.70)
    "wikipedia":     {"weight": 0.70, "tier": 2, "ttl": 604800, "aliases": ["Wikipedia", "wiki", "wiki_en", "wiki_vi"]},
    "wikidata":      {"weight": 0.75, "tier": 2, "ttl": 604800, "aliases": ["Wikidata"]},
    "arxiv":         {"weight": 0.75, "tier": 2, "ttl": 604800, "aliases": ["arXiv"]},
    "crossref":      {"weight": 0.75, "tier": 2, "ttl": 604800, "aliases": ["CrossRef"]},
    "duckduckgo":    {"weight": 0.60, "tier": 2, "ttl": 86400, "aliases": ["DuckDuckGo", "ddg"]},

    # REALTIME (tier 3, weight 0.85, short TTL)
    "coingecko":     {"weight": 0.85, "tier": 3, "ttl": 300, "aliases": ["CoinGecko", "coingecko api"]},
    "binance":       {"weight": 0.90, "tier": 3, "ttl": 300, "aliases": ["Binance"]},
    "coinbase":      {"weight": 0.85, "tier": 3, "ttl": 300, "aliases": ["Coinbase"]},
    "kraken":        {"weight": 0.85, "tier": 3, "ttl": 300, "aliases": ["Kraken"]},
    "open_meteo":    {"weight": 0.85, "tier": 3, "ttl": 300, "aliases": ["Open-Meteo", "OpenMeteo"]},
    "wttr_in":       {"weight": 0.75, "tier": 3, "ttl": 300, "aliases": ["wttr.in"]},
    "restcountries": {"weight": 0.85, "tier": 3, "ttl": 86400, "aliases": ["REST Countries", "REST Countries API"]},
    "frankfurter":   {"weight": 0.85, "tier": 3, "ttl": 300, "aliases": ["Frankfurter", "Frankfurter API"]},

    # LOCAL (tier 4, weight varies)
    "localdb":       {"weight": 0.80, "tier": 4, "ttl": 999999999, "aliases": ["LocalDB", "Local Database", "Local Geography Database", "Local Medical Database", "Local Chemistry Database"]},
    "slm_consensus": {"weight": 0.65, "tier": 4, "ttl": 999999999, "aliases": ["SLM Consensus"]},
    # [Fix 4-b-015] The self-answer entry previously used an unsupported
    # numeric enum value. It now uses level 4 (LEARNED), the lowest legitimate
    # level, because self-reports are the least trustworthy source by design.
    "slm_self":      {"weight": 0.30, "tier": 4, "ttl": 0, "aliases": ["SLM Self-Answered"]},
}


def get_unified_source_info(source_name: str) -> dict:
    """Look up source by any alias → return {weight, tier, ttl, canonical}.

    [Fix 4-b-015 / Phase 3-A — DNA #6, #22, #19]
    PREVIOUSLY: default-unknown returned `tier: 5` — but `TrustTier(5)`
    raises ValueError, silently breaking any caller that did
    `TrustTier(info["tier"])`. NOW: default-unknown returns `tier: 4`
    (LEARNED — the lowest legitimate tier). Also `get_tier()` returns
    `TrustTier.CONSENSUS` (tier 2) for unknown — the inconsistency
    between the two APIs for the same unknown source is documented as
    an open question; both now return VALID enum values.
    """
    if not source_name:
        return {"weight": 0.5, "tier": 4, "ttl": 86400, "canonical": "unknown"}
    key = source_name.lower().strip()
    # Direct lookup
    if key in UNIFIED_SOURCE_REGISTRY:
        info = UNIFIED_SOURCE_REGISTRY[key]
        return {**info, "canonical": key}
    # Alias lookup
    for canonical, info in UNIFIED_SOURCE_REGISTRY.items():
        if key in [a.lower() for a in info.get("aliases", [])]:
            return {**info, "canonical": canonical}
    # Unknown → default (tier 4 LEARNED — was tier 5, invalid)
    return {"weight": 0.5, "tier": 4, "ttl": 86400, "canonical": key}
