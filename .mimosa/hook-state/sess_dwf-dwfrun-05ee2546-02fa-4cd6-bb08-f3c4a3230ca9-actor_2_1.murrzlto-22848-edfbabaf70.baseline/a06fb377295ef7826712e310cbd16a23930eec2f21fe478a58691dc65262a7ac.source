"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V37 — 5 Cognitive Layers (Missing từ V36).

Transform SCP từ "reasoning system" → "proof management system".

5 tầng mới:
    1. MetaFalsifier      — VerificationPlan có thiếu kiểu phản bác?
    2. UnknownState        — 3 miền: Đúng / Sai / Chưa đủ điều kiện
    3. CounterQuestionEngine — phản biện bằng đổi câu hỏi (không đổi data)
    4. ProofGraph          — DAG phụ thuộc chứng minh
    5. RecursiveWhy        — Neo đệ quy truy tầng nhận thức

Triết lý:
    - Neo không chỉ hỏi "Tại sao?" một lần
    - Neo hỏi "Tại sao?" → nhận answer → "Tại sao tin answer?" → ... → axiom
    - Mỗi tầng có thể FAIL → dừng chain → UNKNOWN_WITH_REASON

[Task 10-B Modularity Refactor B] Extracted ~920 LOC into
`scp/meta/cognitive_layers/` sub-package:
  - meta_falsifier.py  (Layer 1: MetaFalsifier)
  - unknown_state.py   (Layer 2: UnknownStateClassifier)
  - counter_question.py (Layer 3: CounterQuestionEngine)
  - proof_graph.py     (Layer 4: ProofGraph + ProofGraphBuilder)
  - recursive_why.py   (Layer 5: RecursiveWhyEngine)

CognitiveEngine orchestrator stays in this file — backward compatible.
"""

import logging
import os
import sys
from typing import Any

logger = logging.getLogger("scp.cognitive")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# [Task 10-B] Re-export extracted layers — backward compat.
from scp.meta.cognitive_layers.counter_question import (  # noqa: F401
    CounterQuestion,
    CounterQuestionEngine,
)
from scp.meta.cognitive_layers.meta_falsifier import (  # noqa: F401
    MetaFalsificationResult,
    MetaFalsifier,
)
from scp.meta.cognitive_layers.proof_graph import (  # noqa: F401
    ProofGraph,
    ProofGraphBuilder,
    ProofNode,
)
from scp.meta.cognitive_layers.recursive_why import (  # noqa: F401
    RecursiveWhyEngine,
    RecursiveWhyResult,
    WhyLevel,
)
from scp.meta.cognitive_layers.unknown_state import (  # noqa: F401
    UnknownState,
    UnknownStateClassifier,
)


# ============================================================
# COGNITIVE ENGINE — orchestrates all 5 layers
# ============================================================
class CognitiveEngine:
    """
    Cognitive Engine — điều phối 5 tầng nhận thức V37.

    Flow:
        1. WHY Engine creates VerificationPlan (V34)
        2.  MetaFalsifier checks plan completeness
        3.  CounterQuestionEngine generates alternative framings
        4. RealityJudge executes (existing)
        5.  UnknownStateClassifier classifies UNKNOWN
        6.  ProofGraphBuilder creates dependency DAG
        7.  RecursiveWhyEngine traces trust to axiom

     Per-layer enable/disable via config hoặc env var:
        SCP_COGNITIVE_LAYERS=meta_falsifier,counter_question,proof_graph,recursive_why,unknown_state
        (default: all enabled)
        SCP_COGNITIVE_LAYERS=none → disable all (raw SLM mode)
    """

    # All available layers
    ALL_LAYERS = {"meta_falsifier", "unknown_state", "counter_question",
                  "proof_graph", "recursive_why"}

    def __init__(self):
        self.meta_falsifier = MetaFalsifier()
        self.unknown_classifier = UnknownStateClassifier()
        self.counter_question = CounterQuestionEngine()
        self.proof_builder = ProofGraphBuilder()
        self.recursive_why = RecursiveWhyEngine()
        #  Per-layer enable/disable
        self.enabled_layers = self._load_layer_config()

    @staticmethod
    def _load_layer_config() -> set:
        """ Load which cognitive layers are enabled.

        Reads SCP_COGNITIVE_LAYERS env var:
            - "all" (default) → all 5 layers
            - "none" → no layers (raw SLM mode, useful for debugging)
            - "meta_falsifier,recursive_why" → only those 2
        """
        import os
        cfg = os.environ.get("SCP_COGNITIVE_LAYERS", "all").lower().strip()
        if cfg == "all":
            return set(CognitiveEngine.ALL_LAYERS)
        if cfg in ("none", "off", "disabled"):
            return set()
        # Comma-separated list
        return {c.strip() for c in cfg.split(",") if c.strip() in CognitiveEngine.ALL_LAYERS}

    def analyze(self, question: str, domain: str, verdict: str,
                confidence: float, sources_succeeded: list[str],
                sources_failed: list[str], why_plan: Any | None,
                reality_check: dict, evidence: dict,
                primary_source: str = "", evidence_type: str = "") -> dict[str, Any]:
        """
        Full cognitive analysis of a verdict.

        Returns:
            {
                "meta_falsification": MetaFalsificationResult,
                "unknown_state": UnknownState or None,
                "counter_questions": List[CounterQuestion],
                "proof_graph": ProofGraph summary,
                "recursive_why": RecursiveWhyResult,
            }
        """
        result: dict[str, Any] = {}

        # 1. Meta-Falsification
        # [V104.42 #AY] TẠI SAO: was `if why_plan:` → MetaFalsifier dead when WHY engine
        # skipped (V90 OPT, now re-enabled via SCP_ENABLE_CLOSED_LOOP but still optional).
        # Fix: run MetaFalsifier even without why_plan — it can analyze verdict+evidence
        # directly (plan_complete check becomes "no plan to falsify" = skip, not "dead").
        if "meta_falsifier" in self.enabled_layers:
            if why_plan:
                mf = self.meta_falsifier.falsify_plan(why_plan)
                result["meta_falsification"] = {
                    "plan_complete": mf.plan_complete,
                    "missing_vectors": mf.missing_attack_vectors,
                    "suggestions": mf.suggested_additions,
                    "reasoning": mf.reasoning,
                }
            else:
                # [V104.42 #AY] No plan to falsify — record that layer is active but idle
                result["meta_falsification"] = {
                    "plan_complete": None,
                    "missing_vectors": [],
                    "suggestions": [],
                    "reasoning": "No WHY plan to falsify (WHY engine not enabled or failed)",
                }

        # 2. Unknown State classification
        if "unknown_state" in self.enabled_layers:
            why_threshold = getattr(why_plan, 'confidence_threshold', 0.5) if why_plan else 0.5
            unknown = self.unknown_classifier.classify(
                verdict=verdict,
                confidence=confidence,
                sources_succeeded=sources_succeeded,
                sources_failed=sources_failed,
                domain=domain,
                why_threshold=why_threshold,
                evidence=evidence,
                question=question,  #  for pending_resolutions enqueue
            )
            if unknown:
                result["unknown_state"] = {
                    "subtype": unknown.subtype,
                    "reason": unknown.reason,
                    "what_is_needed": unknown.what_is_needed,
                    "can_be_resolved": unknown.can_be_resolved,
                    "resolution": unknown.resolution_strategy,
                }

        # 3. Counter-Questions
        if "counter_question" in self.enabled_layers:
            cqs = self.counter_question.generate_counter_questions(question, domain)
            result["counter_questions"] = [
                {
                    "question": cq.counter_question,
                    "type": cq.reframing_type,
                    "why": cq.why_it_matters,
                }
                for cq in cqs
            ]

        # 4. Proof Graph
        if "proof_graph" in self.enabled_layers and why_plan:
            graph = self.proof_builder.build_from_plan(
                plan=why_plan,
                verdict=verdict,
                confidence=confidence,
                sources_succeeded=sources_succeeded,
                sources_failed=sources_failed,
                reality_check=reality_check,
            )
            result["proof_graph"] = {
                "root_claim": graph.root_claim,
                "overall_status": graph.overall_status,
                "nodes": {
                    nid: {
                        "description": n.description,
                        "status": n.status,
                        "verdict": n.verdict,
                    }
                    for nid, n in graph.nodes.items()
                },
            }

        # 5. Recursive Why
        if "recursive_why" in self.enabled_layers and primary_source:
            rw = self.recursive_why.recursive_why(question, primary_source, evidence_type)
            result["recursive_why"] = {
                "depth": rw.depth_reached,
                "terminated_at": rw.terminated_at,
                "final_trust": rw.final_trust,
                "chain": [
                    {
                        "level": lvl.level,
                        "question": lvl.question,
                        "answer": lvl.answer,
                        "is_axiom": lvl.is_axiom,
                    }
                    for lvl in rw.chain
                ],
            }

        return result


# ============================================================
# MAIN
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V37 Cognitive Engine")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        print(f"\n{'='*80}")
        print("  V37 COGNITIVE ENGINE — 5 LAYERS TEST")
        print(f"{'='*80}")

        engine = CognitiveEngine()

        # Test 1: MetaFalsifier
        print("\n[1] MetaFalsifier — 'Plan có thiếu kiểu phản bác?'")
        print("-"*60)
        from scp.meta.why_engine import WhyEngine
        why = WhyEngine()
        plan = why.create_verification_plan("Tại sao giá bitcoin hiện tại là $62000?")
        mf = engine.meta_falsifier.falsify_plan(plan)
        print(f"  Plan complete: {mf.plan_complete}")
        print(f"  Missing vectors: {mf.missing_attack_vectors}")
        for s in mf.suggested_additions:
            print(f"  Suggestion: {s}")

        # Test 2: UnknownState
        print("\n[2] UnknownState — 3 miền nhận thức")
        print("-"*60)
        unknown = engine.unknown_classifier.classify(
            verdict="UNKNOWN", confidence=0.2,
            sources_succeeded=[], sources_failed=["Binance", "Coinbase"],
            domain="finance", why_threshold=0.85, evidence={},
        )
        if unknown:
            print(f"  Subtype: {unknown.subtype}")
            print(f"  Reason: {unknown.reason}")
            print(f"  Needed: {unknown.what_is_needed}")
            print(f"  Resolvable: {unknown.can_be_resolved}")

        # Test 3: CounterQuestions
        print("\n[3] CounterQuestionEngine — đổi câu hỏi")
        print("-"*60)
        cqs = engine.counter_question.generate_counter_questions("giá bitcoin hiện tại", "finance")
        for cq in cqs:
            print(f"  [{cq.reframing_type}] {cq.counter_question}")
            print(f"    Why: {cq.why_it_matters}")

        # Test 4: ProofGraph
        print("\n[4] ProofGraph — DAG phụ thuộc")
        print("-"*60)
        graph = engine.proof_builder.build_from_plan(
            plan=plan, verdict="PASS", confidence=0.95,
            sources_succeeded=["Binance", "Coinbase", "Kraken"],
            sources_failed=[], reality_check={},
        )
        print(f"  Root: {graph.root_claim[:50]}")
        print(f"  Overall: {graph.overall_status}")
        for nid, node in graph.nodes.items():
            print(f"    [{node.status:8s}] {nid:25s} | {node.description[:50]}")

        # Test 5: RecursiveWhy
        print("\n[5] RecursiveWhy — Neo đệ quy truy tầng")
        print("-"*60)
        rw = engine.recursive_why.recursive_why(
            "2+3=5", "PythonAST", "deterministic_calculation"
        )
        print(f"  Depth: {rw.depth_reached}")
        print(f"  Terminated: {rw.terminated_at}")
        print(f"  Final trust: {rw.final_trust}")
        for lvl in rw.chain:
            axiom_mark = " [AXIOM]" if lvl.is_axiom else ""
            print(f"    L{lvl.level}: Q: {lvl.question[:50]}")
            print(f"         A: {lvl.answer[:60]}{axiom_mark}")

        print(f"\n{'='*80}")

    else:
        print("Use --test")


if __name__ == "__main__":
    main()
