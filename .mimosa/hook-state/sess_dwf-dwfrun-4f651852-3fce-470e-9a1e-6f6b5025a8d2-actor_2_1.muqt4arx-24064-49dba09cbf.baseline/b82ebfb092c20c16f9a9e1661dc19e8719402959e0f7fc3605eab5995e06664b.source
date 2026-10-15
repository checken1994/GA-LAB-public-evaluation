
from .models import EvidenceRecord


class JournalRecorder:
    """
    Durable challenge journal.
    """
    def __init__(self):
        self._journal: list[EvidenceRecord] = []

    def record(self, evidence: EvidenceRecord) -> None:
        # machine-enforced: observer coverage must be present
        if not evidence.observer_coverage_hash:
            raise ValueError("Observer coverage hash is required for durability")
        self._journal.append(evidence)

    def get_journal(self) -> list[EvidenceRecord]:
        return list(self._journal)
