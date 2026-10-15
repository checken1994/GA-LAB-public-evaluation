import pytest

from scp.knowledge.benchmark_authority import BenchmarkAuthority
from scp.knowledge.cognitive_orchestrator import CognitiveOrchestrator
from scp.knowledge.contradiction_authority import ContradictionAuthority
from scp.knowledge.experiment_authority import ExperimentAuthority
from scp.knowledge.hypothesis_authority import HypothesisAuthority
from scp.knowledge.knowledge_control_db import KnowledgeControlDB
from scp.knowledge.learning_db import LearningDB
from scp.knowledge.lesson_authority import LessonAuthority
from scp.knowledge.open_question_authority import OpenQuestionAuthority
from scp.knowledge.revalidation_authority import RevalidationAuthority


@pytest.fixture
def orchestrator(tmp_path):
    k_db = KnowledgeControlDB(tmp_path / "k.sqlite")
    l_db = LearningDB(tmp_path / "l.sqlite")
    return CognitiveOrchestrator(
        k_db,
        l_db,
        RevalidationAuthority(k_db),
        ContradictionAuthority(k_db),
        OpenQuestionAuthority(l_db),
        HypothesisAuthority(l_db),
        ExperimentAuthority(l_db),
        LessonAuthority(l_db),
        BenchmarkAuthority(l_db)
    )

def test_orchestrator_initializes_and_ticks(orchestrator):
    # Just verifies that it can be instantiated and ticked without crashing
    orchestrator.run_tick()
    assert orchestrator is not None
