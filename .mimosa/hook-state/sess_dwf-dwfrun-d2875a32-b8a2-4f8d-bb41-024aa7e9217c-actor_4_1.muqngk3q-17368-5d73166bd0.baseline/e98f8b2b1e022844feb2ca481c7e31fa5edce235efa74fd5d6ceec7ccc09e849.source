"""Incident state machine (S10.7): OBSERVED -> ... -> RESOLVED with
false-positive and insufficient-evidence escape branches."""
from __future__ import annotations

from enum import Enum


class IncidentState(str, Enum):
    OBSERVED = "OBSERVED"
    SUSPECTED = "SUSPECTED"
    CORROBORATING = "CORROBORATING"
    CONFIRMED = "CONFIRMED"
    CONTAINING = "CONTAINING"
    ESCALATED = "ESCALATED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    CONTRADICTED = "CONTRADICTED"
    CLOSED_FALSE_POSITIVE = "CLOSED_FALSE_POSITIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


TRANSITIONS = {
    "OBSERVED": {"SUSPECTED", "CLOSED_FALSE_POSITIVE"},
    "SUSPECTED": {"CORROBORATING", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"},
    "CORROBORATING": {"CONFIRMED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"},
    "CONFIRMED": {"CONTAINING", "MONITORING"},
    "CONTAINING": {"ESCALATED", "MONITORING", "RESOLVED"},
    "ESCALATED": {"MONITORING", "RESOLVED"},
    "MONITORING": {"RESOLVED", "ESCALATED", "SUSPECTED"},
    "RESOLVED": set(),
    "CONTRADICTED": {"CLOSED_FALSE_POSITIVE"},
    "CLOSED_FALSE_POSITIVE": set(),
    "INSUFFICIENT_EVIDENCE": {"SUSPECTED", "RESOLVED"},
}


class IncidentStateMachine:
    def __init__(self, incident_id: str, state: IncidentState | str = IncidentState.OBSERVED) -> None:
        self.incident_id = incident_id
        self.state = state if isinstance(state, IncidentState) else IncidentState(state)

    def transition(self, next_state: IncidentState | str) -> IncidentState:
        target = next_state if isinstance(next_state, IncidentState) else IncidentState(next_state)
        allowed = TRANSITIONS.get(self.state.value, set())
        if target.value not in allowed:
            raise ValueError(
                f"invalid incident transition {self.state.value} -> {target.value} "
                f"(false-positive and insufficient-evidence branches are the only escapes)"
            )
        self.state = target
        return self.state
