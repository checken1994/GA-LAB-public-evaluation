"""PR0-PR5 risk classifier (26-P0.10 / S10).

Owner-locked rules encoded here:
  - syndication/post volume NEVER decides PR4/PR5 (1000 copies of one source
    are ONE lineage);
  - PR4/PR5 requires >=1 official source OR >=2 truly independent lineages,
    AND freshness AND location validation - except hazards directly observed
    by sensors/systems SCP itself owns;
  - insufficient evidence caps the level and flags pending verification
    (UNKNOWN/WATCH), it never manufactures an emergency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    PR0 = "PR0"
    PR1 = "PR1"
    PR2 = "PR2"
    PR3 = "PR3"
    PR4 = "PR4"
    PR5 = "PR5"


@dataclass
class RiskSignal:
    source_id: str
    kind: str  # official | independent | syndicated | social | owned_sensor
    lineage_id: str | None = None
    fresh: bool = True
    location_validated: bool = False
    observed_directly: bool = False  # sensor/system owned by SCP


@dataclass
class RiskAssessment:
    level: RiskLevel | None  # None = UNDETERMINED / WATCH
    pending_verification: bool
    reasons: list = field(default_factory=list)
    official_sources: int = 0
    independent_lineages: int = 0
    social_volume: int = 0


class RiskClassifier:
    """Grade risk PR0-PR5. Evidence quality gates the ceiling; desired
    severity from hazard analysis can only be LOWERED by weak evidence."""

    def classify(self, signals, *, desired_level: RiskLevel | str = RiskLevel.PR2,
                 hazard_severity: str = "moderate") -> RiskAssessment:
        signals = list(signals or [])
        official = [s for s in signals if s.kind == "official"]
        owned = [s for s in signals if s.kind == "owned_sensor" and s.observed_directly]
        lineages = {s.lineage_id for s in signals if s.lineage_id and s.kind in {"official", "independent", "owned_sensor"}}
        _stale = [s for s in signals if not s.fresh]
        _unlocated = [s for s in signals if not s.location_validated]

        independent_lineages = len(lineages)
        official_count = len(official)
        social_volume = sum(1 for s in signals if s.kind == "social")

        reasons: list = []
        qualified = (official_count >= 1 or independent_lineages >= 2 or bool(owned))
        # The evidence BASE is fresh/located when the qualifying sources are -
        # weak background signals without location do not invalidate them.
        freshness_ok = any(s.fresh for s in signals if s.kind in {"official", "independent", "owned_sensor"}) or bool(owned)
        location_ok = any(s.location_validated for s in signals if s.kind in {"official", "independent", "owned_sensor"}) or bool(owned)

        desired = RiskLevel(str(desired_level)) if not isinstance(desired_level, RiskLevel) else desired_level
        if not qualified:
            reasons.append(
                f"insufficient qualification: official={official_count} "
                f"independent_lineages={independent_lineages} owned_direct={len(owned)}"
            )
        if not freshness_ok:
            reasons.append("stale evidence present")
        if not location_ok:
            reasons.append("location not validated")

        if not qualified:
            return RiskAssessment(
                level=None if desired in (RiskLevel.PR4, RiskLevel.PR5) else RiskLevel.PR1,
                pending_verification=True, reasons=reasons,
                official_sources=official_count, independent_lineages=independent_lineages,
                social_volume=social_volume,
            )

        # Evidence-qualified: ceiling by strongest supporting evidence class.
        if owned:
            ceiling = RiskLevel.PR4 if hazard_severity != "critical" else RiskLevel.PR5
            reasons.append("directly observed by owned sensors/systems")
        elif official_count >= 1:
            ceiling = desired
            reasons.append(f"official source count={official_count}")
        elif independent_lineages >= 2:
            ceiling = desired if desired != RiskLevel.PR5 else RiskLevel.PR4
            reasons.append(f"independent lineages={independent_lineages}")
            if desired == RiskLevel.PR5:
                reasons.append("PR5 additionally requires official confirmation")
        else:
            ceiling = RiskLevel.PR1

        if not freshness_ok or not location_ok:
            ceiling = min(ceiling, RiskLevel.PR3, key=lambda x: x.value)
            reasons.append("freshness/location validation failure caps level at PR3")

        level = desired if _le(desired, ceiling) else ceiling
        pending = False
        return RiskAssessment(
            level=level, pending_verification=pending, reasons=reasons,
            official_sources=official_count, independent_lineages=independent_lineages,
            social_volume=social_volume,
        )


def _le(a: RiskLevel, b: RiskLevel) -> bool:
    order = list(RiskLevel)
    return order.index(a) <= order.index(b)
