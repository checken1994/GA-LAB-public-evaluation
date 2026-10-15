import dataclasses
import logging
from pathlib import Path
from typing import Any

from scp.knowledge.learning_db import LearningDB
from scp.knowledge.open_question_authority import (
    MissingPieceKind,
    MissingPieceRecord,
    OpenQuestionAuthority,
    OpenQuestionRecord,
    QuestionStatus,
    QuestionTrigger,
)


@dataclasses.dataclass
class MissingPieceFinding:
    blind_spot: str
    affected_coverage: str
    evidence_refs: list[str]

class EpistemicBoundary:
    """
    Real Epistemic Boundary linking Reality (P0 Execution) to Cognition (P1 Learning).
    """
    def __init__(self, db_path: str = "data/cognitive/learning.sqlite"):
        self.learning_db = LearningDB(Path(db_path))
        self.open_question_authority = OpenQuestionAuthority(self.learning_db)
        self.logger = logging.getLogger("EpistemicBoundary")

        # Compatibility properties for the T07 test:
        self.findings: list[MissingPieceFinding] = []
        self.verdict: str | None = None
        self.known_independent_lineages = 0

    def evaluate_lineage(self, source_a_lineage: str, source_b_lineage: str) -> None:
        if source_a_lineage != source_b_lineage:
            self.known_independent_lineages = 2
        else:
            self.known_independent_lineages = 1
            self.verdict = "UNVERIFIED"

    def is_support_condition_satisfied(self) -> bool:
        return self.known_independent_lineages >= 2

    def record_contradiction(self, finding: MissingPieceFinding) -> None:
        """
        Records the contradiction to the DB and formulates an Open Question.
        """
        self.verdict = "CONTRADICTED"
        self.findings.append(finding)

        # 1. Transform to P1 Record
        mp = MissingPieceRecord(
            question_id="",
            description=f"Blind spot: {finding.blind_spot}. Coverage: {finding.affected_coverage}",
            kind=MissingPieceKind.MISSING_EVIDENCE,
            blocks_claims=[finding.affected_coverage],
            blocks_decisions=[],
            needed_evidence=finding.evidence_refs,
            discovered_by="epistemic_boundary"
        )

        # 2. Formulate Open Question
        oq = OpenQuestionRecord(
            title="Reality Contradicts Clean Scan",
            question=f"Why did reality contradict coverage '{finding.affected_coverage}' due to blind spot '{finding.blind_spot}'?",
            trigger=QuestionTrigger.CONTRADICTION,
            scope={"affected": finding.affected_coverage},
            known_evidence_refs=finding.evidence_refs,
            status=QuestionStatus.OPEN
        )

        qid = self.open_question_authority.formulate_question(oq, [mp])
        self.logger.info(f"Recorded Contradiction -> Open Question {qid}")

    def process_verification_failure(self, task_id: str, result: Any) -> None:
        """
        Hook for HandsExecutor / TaskKernelBridge when a verification fails.
        Handles both VerificationResult object and dict.
        """
        if isinstance(result, dict):
            verdict = result.get("verdict")
            failures = result.get("failures", [])
            evidence_ref = result.get("evidence_ref")
        else:
            verdict = getattr(result, "verdict", None)
            failures = getattr(result, "failures", [])
            evidence_ref = getattr(result, "evidence_ref", None)

        if verdict == "CONTRADICTED":
            finding = MissingPieceFinding(
                blind_spot=f"Failed conditions: {failures}",
                affected_coverage=f"task://{task_id}",
                evidence_refs=[evidence_ref] if evidence_ref else []
            )
            self.record_contradiction(finding)
