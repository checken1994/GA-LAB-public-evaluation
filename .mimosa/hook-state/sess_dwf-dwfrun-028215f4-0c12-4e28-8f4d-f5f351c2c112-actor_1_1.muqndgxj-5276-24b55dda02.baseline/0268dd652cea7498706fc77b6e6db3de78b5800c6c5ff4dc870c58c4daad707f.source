from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    verifier_id: str
    evidence_ref: str | None
    checked: tuple[dict[str, Any], ...]
    failures: tuple[str, ...]


class IndependentVerifier:
    """Pure verifier. It never asks a model whether the task is complete."""

    verifier_id = "scp-independent-postcondition-verifier-v1"

    def verify(self, postcondition: dict[str, Any] | None, observation: dict[str, Any] | None) -> VerificationResult:
        from scp.core.postcondition_schema import SchemaValidationError, validate_postcondition_dict
        try:
            validate_postcondition_dict(postcondition)
        except SchemaValidationError as e:
            return VerificationResult("INSUFFICIENT", self.verifier_id, None, tuple(), (f"schema_error:{e}",))

        postcondition = postcondition or {}
        observation = observation or {}
        evidence_ref = observation.get("evidence_ref")
        failures: list[str] = []
        checked: list[dict[str, Any]] = []
        if postcondition.get("evidence_required") and not evidence_ref:
            return VerificationResult("INSUFFICIENT", self.verifier_id, None, tuple(), ("missing_evidence_ref",))
        conditions = postcondition.get("all") or []
        if not isinstance(conditions, list) or not conditions:
            return VerificationResult("INSUFFICIENT", self.verifier_id, evidence_ref, tuple(), ("missing_postconditions",))
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                failures.append(f"condition_{index}_not_object")
                continue
            kind = condition.get("kind")
            if kind == "url_matches":
                expected = condition.get("value")
                actual = observation.get("url")
                ok = bool(actual and expected and actual == expected)
            elif kind == "text_contains":
                expected = condition.get("value")
                actual = observation.get("text") or ""
                ok = bool(expected and expected in actual)
            elif kind == "network_response":
                expected_method = condition.get("method")
                expected_status = condition.get("status")
                responses = observation.get("network_responses") or []
                ok = any(r.get("method") == expected_method and r.get("status") == expected_status for r in responses if isinstance(r, dict))
            elif kind == "artifact_hash":
                ok = observation.get("artifact_hash") == condition.get("value")
            else:
                failures.append(f"condition_{index}_unknown_kind")
                continue
            checked.append({"index": index, "kind": kind, "ok": ok})
            if not ok:
                failures.append(f"condition_{index}_failed")
        if any("unknown_kind" in item for item in failures):
            verdict = "UNKNOWN"
        elif failures:
            verdict = "CONTRADICTED"
        else:
            verdict = "VERIFIED"
        return VerificationResult(verdict, self.verifier_id, evidence_ref, tuple(checked), tuple(failures))

    @staticmethod
    def to_dict(result: VerificationResult) -> dict[str, Any]:
        return asdict(result)
