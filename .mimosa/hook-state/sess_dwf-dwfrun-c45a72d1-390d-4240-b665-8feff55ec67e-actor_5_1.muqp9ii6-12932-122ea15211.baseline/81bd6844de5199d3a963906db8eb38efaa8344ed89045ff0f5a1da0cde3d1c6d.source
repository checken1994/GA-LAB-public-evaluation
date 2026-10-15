"""Governed evidence write facade.

Production callers should use GovernedEvidenceWriter rather than persisting raw
external content directly. EvidenceStore remains the low-level immutable/CAS
storage primitive and existing storage tests can exercise it directly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from scp.contracts.data_class import DataClass
from scp.epistemic.evidence_store import EvidenceStore
from scp.interfaces.governance import IPrivacyWriteGate, PrivacyDecision

if TYPE_CHECKING:
    from scp.governance.privacy import PrivacyWriteGate


class PrivacyWriteDenied(RuntimeError):
    pass


class GovernedEvidenceWriter:
    def __init__(self, store: EvidenceStore, privacy_gate: IPrivacyWriteGate | PrivacyWriteGate) -> None:
        self.store = store
        self.privacy_gate = privacy_gate

    def observe(
        self,
        *,
        kind: str,
        content: bytes,
        collector_id: str,
        collector_version: str,
        data_class: DataClass | str | None,
        input_classes: tuple[object, ...] | list[object] = (),
        sanitized: bool = False,
        metadata: dict | None = None,
        **kwargs,
    ) -> dict:
        decision = self.privacy_gate.evaluate(
            content=content,
            requested_class=data_class,
            input_classes=input_classes,
            sanitized=sanitized,
        )
        if decision.decision is PrivacyDecision.DENY_STORAGE or decision.content is None:
            raise PrivacyWriteDenied(decision.reason)
        safe_metadata = dict(metadata or {})
        if decision.redactions:
            safe_metadata["privacy_redactions"] = [
                {"kind": item.kind, "fingerprint": item.fingerprint}
                for item in decision.redactions
            ]
        safe_metadata["privacy_write_decision"] = decision.decision.value
        return self.store.observe(
            kind=kind,
            content=decision.content,
            collector_id=collector_id,
            collector_version=collector_version,
            data_class=decision.data_class,
            retention_policy_id=decision.retention_policy_id,
            metadata=safe_metadata,
            **kwargs,
        )
