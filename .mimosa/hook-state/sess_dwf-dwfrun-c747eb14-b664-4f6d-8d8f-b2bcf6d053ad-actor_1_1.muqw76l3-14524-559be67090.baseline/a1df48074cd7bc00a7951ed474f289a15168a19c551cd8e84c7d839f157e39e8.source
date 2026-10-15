"""SCP common contracts (26-P0.2): canonical IDs, verdicts, maturity,
data classes, evidence levels, UTC time and the common event envelope.

Every subsystem imports these instead of inventing parallel semantics.
"""
from scp.contracts.data_class import DataClass, max_severity
from scp.contracts.event_envelope import EventEnvelope
from scp.contracts.evidence_level import EvidenceLevel, parse_evidence_level
from scp.contracts.ids import content_id, is_valid_id, new_id, require_id
from scp.contracts.maturity import Maturity, at_least, parse_maturity
from scp.contracts.time import ensure_aware_utc, now_utc_iso, parse_utc_iso
from scp.contracts.verdicts import Verdict, parse_verdict

__all__ = [
    "Verdict", "parse_verdict",
    "Maturity", "at_least", "parse_maturity",
    "DataClass", "max_severity",
    "EvidenceLevel", "parse_evidence_level",
    "new_id", "is_valid_id", "require_id", "content_id",
    "now_utc_iso", "ensure_aware_utc", "parse_utc_iso",
    "EventEnvelope",
]
