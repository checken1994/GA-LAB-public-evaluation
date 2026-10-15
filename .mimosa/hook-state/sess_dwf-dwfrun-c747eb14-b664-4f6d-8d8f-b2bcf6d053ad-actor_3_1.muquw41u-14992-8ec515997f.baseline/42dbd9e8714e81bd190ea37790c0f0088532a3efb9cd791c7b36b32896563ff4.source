import pytest

from scp.knowledge.hypothesis_authority import HypothesisAuthority, HypothesisRecord
from scp.knowledge.learning_db import LearningDB
from scp.knowledge.open_question_authority import (
    MissingPieceRecord,
    OpenQuestionAuthority,
    OpenQuestionRecord,
)


@pytest.fixture
def db(tmp_path):
    return LearningDB(tmp_path / "test_learning.sqlite")

def test_open_question_and_missing_piece(db):
    auth = OpenQuestionAuthority(db)
    oq = OpenQuestionRecord(
        title="Why is service down?",
        question="Is it DNS or network?",
        trigger="UNKNOWN"
    )
    mp = MissingPieceRecord(
        question_id="", # will be set
        description="We need DNS resolution logs",
        kind="MISSING_EVIDENCE"
    )
    
    q_id = auth.formulate_question(oq, [mp])
    assert q_id.startswith("oq_")
    assert mp.question_id == q_id

def test_hypothesis(db):
    auth = HypothesisAuthority(db)
    hyp = HypothesisRecord(
        question_ref="oq_123",
        hypothesis="It's DNS",
        mechanism="DNS server timed out"
    )
    h_id = auth.propose(hyp)
    assert h_id.startswith("hyp_")
