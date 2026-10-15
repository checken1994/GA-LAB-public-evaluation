from .models import EvidenceRecord, OracleVerdict


class IndependentOracle:
    """
    Returns OracleVerdict. Evaluates execution traces without assuming success.
    NOT_FALSIFIED != EVIDENCE_VERIFIED
    """
    def __init__(self):
        self._tampered = False

    def tamper(self) -> None:
        """For mutation testing: simulate tampering with the oracle."""
        self._tampered = True

    def evaluate(self, execution_trace: str, challenge_id: str, observer_coverage_hash: str) -> EvidenceRecord:
        if self._tampered:
            # A tampered oracle should fail-closed
            return EvidenceRecord(
                record_id="record_tampered",
                verdict=OracleVerdict.CONTAMINATED,
                challenge_id=challenge_id,
                observer_coverage_hash=observer_coverage_hash
            )

        if not execution_trace:
            return EvidenceRecord(
                record_id="record_no_trace",
                verdict=OracleVerdict.OBSERVABILITY_INSUFFICIENT,
                challenge_id=challenge_id,
                observer_coverage_hash=observer_coverage_hash
            )

        if "FAIL" in execution_trace:
            verdict = OracleVerdict.FALSIFIED
        elif "INVALID" in execution_trace:
            verdict = OracleVerdict.INVALID_TEST_SETUP
        else:
            verdict = OracleVerdict.NOT_FALSIFIED

        return EvidenceRecord(
            record_id=f"record_{challenge_id}",
            verdict=verdict,
            challenge_id=challenge_id,
            observer_coverage_hash=observer_coverage_hash
        )
