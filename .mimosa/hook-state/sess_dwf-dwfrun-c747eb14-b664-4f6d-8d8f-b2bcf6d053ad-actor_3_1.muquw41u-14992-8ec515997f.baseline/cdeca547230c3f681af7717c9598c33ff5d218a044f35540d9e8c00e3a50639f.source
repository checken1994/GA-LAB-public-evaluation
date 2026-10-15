"""Canonical SCP release and terminology identity.

This module is the Python source of truth for current public identity.
Historical audit rounds and protocol paths are compatibility metadata, not
product versions. Legacy names remain only at explicit compatibility
boundaries and must not be used for new outward-facing responses.
"""
from __future__ import annotations

from typing import Final

PRODUCT_NAME: Final[str] = "SCP"
RELEASE_VERSION: Final[str] = "14.0.0"
RELEASE_LABEL: Final[str] = f"{PRODUCT_NAME} {RELEASE_VERSION}"

# OpenAI-compatible model identity. The old IDs are aliases for clients that
# have not migrated yet; the canonical ID must be used for new requests.
CANONICAL_MODEL_ID: Final[str] = f"scp-{RELEASE_VERSION}"
LEGACY_MODEL_IDS: Final[tuple[str, ...]] = ("scp-v99",)

# These are protocol/path generations, not release versions. They stay live
# for compatibility and are deliberately labeled as legacy protocols.
LEGACY_PROTOCOLS: Final[tuple[str, ...]] = ("v98", "v100", "v102", "v103", "v104", "v105")

DOMAIN_EXPERT_TERM: Final[str] = "Domain Expert"
DOMAIN_EXPERT_ENSEMBLE_TERM: Final[str] = "Domain Expert Ensemble"
RED_TEAM_PAYLOAD_TERM: Final[str] = "Red-Team Payload Mutation"
LEGACY_SLM_TERM: Final[str] = "SLM"


def model_id_candidates() -> tuple[str, ...]:
    """Return canonical model ID followed by compatibility aliases."""
    return (CANONICAL_MODEL_ID, *LEGACY_MODEL_IDS)


def public_release_metadata() -> dict[str, object]:
    """Return JSON-safe identity metadata for health/status endpoints."""
    return {
        "product": PRODUCT_NAME,
        "version": RELEASE_VERSION,
        "release": RELEASE_LABEL,
        "model_id": CANONICAL_MODEL_ID,
        "legacy_model_ids": list(LEGACY_MODEL_IDS),
        "legacy_protocols": list(LEGACY_PROTOCOLS),
        "expert_term": DOMAIN_EXPERT_TERM,
        "ensemble_term": DOMAIN_EXPERT_ENSEMBLE_TERM,
    }
