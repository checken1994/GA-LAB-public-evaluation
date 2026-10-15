import pytest

from scp.knowledge.experiment_authority import (
    ExperimentAuthority,
    ExperimentRecord,
    ExperimentStatus,
)
from scp.knowledge.learning_db import LearningDB
from scp.knowledge.lesson_authority import LessonAuthority, LessonRecord


@pytest.fixture
def db(tmp_path):
    return LearningDB(tmp_path / "test_learning.sqlite")

def test_experiment_authority(db):
    auth = ExperimentAuthority(db)
    rec = ExperimentRecord(
        hypothesis_ref="hyp_123",
        setup_instructions=["run network check"],
        execution_status=ExperimentStatus.PLANNED
    )
    e_id = auth.plan_experiment(rec)
    assert e_id.startswith("exp_")

def test_lesson_authority(db):
    auth = LessonAuthority(db)
    rec = LessonRecord(
        experiment_refs=["exp_123"],
        insights=["DNS is indeed broken"]
    )
    l_id = auth.record_lesson(rec)
    assert l_id.startswith("lsn_")
