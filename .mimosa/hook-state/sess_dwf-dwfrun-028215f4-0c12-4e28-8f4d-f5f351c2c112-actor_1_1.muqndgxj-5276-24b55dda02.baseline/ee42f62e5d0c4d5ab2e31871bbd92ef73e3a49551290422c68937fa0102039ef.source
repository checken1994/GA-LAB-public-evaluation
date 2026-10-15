"""Emergency Evidence Bundle (S10.5): SCP never sends "there is danger!" -
it assembles a verifiable evidence package with lineage, contradictions,
unknowns and recommended human actions."""
from __future__ import annotations

from dataclasses import dataclass

from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso

REQUIRED_FIELDS = (
    "incident_id", "risk_type", "level",
    "independent_lineages", "official_confirmation",
)


@dataclass
class EmergencyEvidenceBundle:
    incident_id: str
    risk_type: str
    level: str  # PR0-PR5
    detected_at: str = ""
    location: str | None = None
    estimated_scope: str | None = None
    claims: tuple = ()
    supporting_evidence: tuple = ()          # evidence refs from the EvidenceStore
    independent_lineages: int = 0
    official_sources: tuple = ()
    contradictions: tuple = ()
    unknowns: tuple = ()
    confidence: float | None = None
    recommended_actions: tuple = ()
    actions_taken: tuple = ()                 # automatic containment already done
    source_hashes: tuple = ()
    evidence_freshness: str | None = None
    official_confirmation: bool = False
    bundle_id: str = ""

    def __post_init__(self) -> None:
        missing = [f for f in REQUIRED_FIELDS
                   if not getattr(self, f) and getattr(self, f) != 0]
        if missing:
            raise ValueError(f"evidence bundle missing required fields: {missing}")
        self.bundle_id = self.bundle_id or new_id("bundle")
        self.detected_at = self.detected_at or now_utc_iso()
        if self.confidence is not None and not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence must be within [0.0, 1.0]")

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "incident_id": self.incident_id,
            "risk_type": self.risk_type,
            "level": self.level,
            "detected_at": self.detected_at,
            "location": self.location,
            "estimated_scope": self.estimated_scope,
            "claims": list(self.claims),
            "supporting_evidence": list(self.supporting_evidence),
            "independent_lineages": self.independent_lineages,
            "official_sources": list(self.official_sources),
            "contradictions": list(self.contradictions),
            "unknowns": list(self.unknowns),
            "confidence": self.confidence,
            "recommended_actions": list(self.recommended_actions),
            "automatic_actions_taken": list(self.actions_taken),
            "source_hashes": list(self.source_hashes),
            "evidence_freshness": self.evidence_freshness,
            "official_confirmation": self.official_confirmation,
        }
