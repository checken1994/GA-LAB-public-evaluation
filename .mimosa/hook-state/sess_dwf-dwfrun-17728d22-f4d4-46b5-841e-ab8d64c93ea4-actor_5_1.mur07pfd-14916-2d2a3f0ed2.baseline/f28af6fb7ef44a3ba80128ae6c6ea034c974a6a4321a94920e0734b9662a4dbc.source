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


def test_run_tick_fail_loud_no_fake_scanning_info(orchestrator, caplog):
    """A2 AUDIT-F-03 pin: run_tick is a structural shell with no production
    caller, so it must log an honest WARNING (fail-loud) stating it is not
    wired into any runtime loop, and must NOT emit the previous fake INFO
    'Scanning for ...' logs that manufactured the appearance of work."""
    import logging

    with caplog.at_level(logging.DEBUG, logger="CognitiveOrchestrator"):
        orchestrator.run_tick()

    messages = [r.getMessage() for r in caplog.records]
    assert any("NOT wired into any runtime loop" in m for m in messages), (
        f"expected fail-loud warning, got: {messages}"
    )
    assert not any("Scanning for" in m for m in messages), (
        f"fake progress logs must be gone, got: {messages}"
    )
