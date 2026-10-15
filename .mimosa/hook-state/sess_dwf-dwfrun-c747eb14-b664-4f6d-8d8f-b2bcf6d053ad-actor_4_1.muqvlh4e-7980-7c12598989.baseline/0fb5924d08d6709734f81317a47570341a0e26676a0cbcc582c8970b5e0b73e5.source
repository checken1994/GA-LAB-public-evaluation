import hashlib

from .models import AuditChallenge


class ContractAdapter:
    """
    Contract Authority/TCB.
    Binds raw contract + canonical hashes and mutation-test adapter.
    """
    def __init__(self, raw_contract: str):
        if not raw_contract or not raw_contract.strip():
            raise ValueError("Raw contract cannot be empty")
        self._raw_contract = raw_contract
        self._canonical_hash = self._compute_hash(raw_contract)

    def _compute_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def get_canonical_hash(self) -> str:
        return self._canonical_hash

    def generate_challenge(self, challenge_id: str, required_profile: str) -> AuditChallenge:
        return AuditChallenge(
            challenge_id=challenge_id,
            required_profile=required_profile,
            target_contract_hash=self._canonical_hash
        )

    def verify_integrity(self, expected_hash: str) -> bool:
        """Fail-closed integrity check."""
        if getattr(self, '_tampered', False):
            return False
        return expected_hash == self._canonical_hash

    def tamper(self) -> None:
        """Mutation-test adapter to simulate tampering."""
        self._tampered = True
        self._canonical_hash = "tampered_hash"
