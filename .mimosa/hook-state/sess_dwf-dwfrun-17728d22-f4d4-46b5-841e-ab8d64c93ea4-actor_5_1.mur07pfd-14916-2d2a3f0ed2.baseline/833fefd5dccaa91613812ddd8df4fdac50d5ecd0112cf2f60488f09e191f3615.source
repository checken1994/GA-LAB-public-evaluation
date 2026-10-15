from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from scp.contracts.time import now_utc_iso
from scp.self_model.capability_map import CapabilityMap, CapabilityStatus


class DoubtType(str, Enum):
    OPEN_QUESTION = "OPEN_QUESTION"
    CONTRADICTION = "CONTRADICTION"
    BLIND_SPOT = "BLIND_SPOT"

@dataclass
class MissingPiece:
    description: str
    needed_capability_id: str
    discriminating_observation: str

@dataclass
class DoubtRecord:
    id: str
    type: DoubtType | str
    what_we_dont_know: str
    why_cannot_know_now: str
    dependent_claims: list[str] = field(default_factory=list)
    missing_pieces: list[MissingPiece] = field(default_factory=list)
    capability_can_obtain: bool = False
    hypotheses: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.type, str):
            self.type = DoubtType(self.type.upper())
        if not self.created_at:
            self.created_at = now_utc_iso()


class DoubtAuthority:
    """
    The Doubt Engine / Open-Question Authority.
    It manages the creation of DoubtRecords and evaluates if SCP's Self-Model
    allows resolving the missing piece.
    """

    def __init__(self, capability_map: CapabilityMap, current_sha: str):
        self.capability_map = capability_map
        self.current_sha = current_sha

    def formulate_doubt(
        self,
        doubt_id: str,
        doubt_type: DoubtType,
        unknown_statement: str,
        blocking_reason: str,
        dependent_claims: list[str],
        missing_pieces: list[MissingPiece],
        hypotheses: list[str] = None
    ) -> DoubtRecord:
        """
        Formulates a formal DoubtRecord.
        Interrogates the Self-Model to determine if SCP can currently obtain the needed observation.
        """
        can_obtain_all = True

        for piece in missing_pieces:
            req_capability = piece.needed_capability_id
            if not self._check_capability(req_capability):
                can_obtain_all = False
                # If we cannot observe this, register it as a blindspot in the self-model
                if doubt_type != DoubtType.BLIND_SPOT:
                    self.capability_map.add_blindspot(
                        capability_id=req_capability,
                        unobservable=piece.discriminating_observation,
                        reason=blocking_reason,
                        affected_claims=dependent_claims,
                        needed_evidence=[piece.description]
                    )
                break

        return DoubtRecord(
            id=doubt_id,
            type=doubt_type,
            what_we_dont_know=unknown_statement,
            why_cannot_know_now=blocking_reason,
            dependent_claims=dependent_claims,
            missing_pieces=missing_pieces,
            capability_can_obtain=can_obtain_all,
            hypotheses=hypotheses or []
        )

    def _check_capability(self, capability_id: str) -> bool:
        """
        Strict mapping against the system capability map.
        A capability is considered 'obtainable' if it has been integrated 
        or verified in reality.
        """  # noqa: W291,W293  # [hygiene-keep] whitespace inside string/docstring - keep content verbatim
        result = self.capability_map.recompute_capability(capability_id, self.current_sha)
        valid_statuses = {
            CapabilityStatus.INTEGRATED.value,
            CapabilityStatus.RUNTIME_VERIFIED.value,
            CapabilityStatus.RECOVERY_VERIFIED.value
        }
        return result.get("status") in valid_statuses
