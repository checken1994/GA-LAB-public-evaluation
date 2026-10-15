"""Cognitive layers package — extracted from `meta/cognitive_engine.py` in Task 10-B.

5 tầng nhận thức V37 (Neo's cognitive stack):

  1. meta_falsifier  — MetaFalsifier: plan có thiếu kiểu phản bác?
  2. unknown_state   — UnknownStateClassifier: 3 miền nhận thức (Đúng/Sai/Chưa đủ ĐK)
  3. counter_question — CounterQuestionEngine: phản biện bằng đổi câu hỏi
  4. proof_graph     — ProofGraph + ProofGraphBuilder: DAG phụ thuộc chứng minh
  5. recursive_why   — RecursiveWhyEngine: Neo đệ quy truy tầng nhận thức

All public symbols re-exported here — backward compatible with cognitive_engine.py.
"""
from scp.meta.cognitive_layers.counter_question import (
    CounterQuestion,
    CounterQuestionEngine,
)
from scp.meta.cognitive_layers.meta_falsifier import (
    MetaFalsificationResult,
    MetaFalsifier,
)
from scp.meta.cognitive_layers.proof_graph import (
    ProofGraph,
    ProofGraphBuilder,
    ProofNode,
)
from scp.meta.cognitive_layers.recursive_why import (
    RecursiveWhyEngine,
    RecursiveWhyResult,
    WhyLevel,
)
from scp.meta.cognitive_layers.unknown_state import (
    UnknownState,
    UnknownStateClassifier,
)

__all__ = [
    # Layer 1: MetaFalsifier
    "MetaFalsificationResult",
    "MetaFalsifier",
    # Layer 2: UnknownState
    "UnknownState",
    "UnknownStateClassifier",
    # Layer 3: CounterQuestion
    "CounterQuestion",
    "CounterQuestionEngine",
    # Layer 4: ProofGraph
    "ProofNode",
    "ProofGraph",
    "ProofGraphBuilder",
    # Layer 5: RecursiveWhy
    "WhyLevel",
    "RecursiveWhyResult",
    "RecursiveWhyEngine",
]
