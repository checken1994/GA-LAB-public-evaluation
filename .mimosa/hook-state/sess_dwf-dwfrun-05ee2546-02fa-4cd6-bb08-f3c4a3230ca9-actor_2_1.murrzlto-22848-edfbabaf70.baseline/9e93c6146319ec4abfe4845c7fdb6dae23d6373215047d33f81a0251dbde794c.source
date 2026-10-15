"""
[Task 8-A] WHY engine CLI — extracted from why_engine.py

TẠI SAO: why_engine.py god file. Tách main() CLI (~60 LOC) vào module riêng.
Backward-compatible — `python -m scp.meta.why_engine` still works via thin
wrapper in why_engine.py.
"""
from __future__ import annotations


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCP V34 WHY Engine")
    parser.add_argument("--question", type=str, help="Question to analyze")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    from scp.meta.why_engine import WhyEngine
    engine = WhyEngine()

    if args.stats:
        stats = engine.get_stats()
        print("\n  WHY Engine Stats:")
        for k, v in stats.items():
            print(f"    {k:25s} {v}")
        return

    if args.question:
        plan = engine.create_verification_plan(args.question)
        print(f"\n  Neo asks: '{args.question}'")
        print("\n  WHY Engine creates VerificationPlan:")
        print(f"    Target:              {plan.target}")
        print(f"    Target type:         {plan.target_type}")
        print(f"    Evidence type:       {plan.evidence_type}")
        print(f"    Answer type:         {plan.expected_answer_type}")
        print(f"    Verification strategy: {plan.verification_strategy}")
        print(f"    Sources to query:    {plan.sources_to_query}")
        print(f"    Confidence threshold: {plan.confidence_threshold}")
        print("\n  Proof criteria:")
        print(f"    {plan.proof_criteria}")
        print("\n  Falsification criteria:")
        print(f"    {plan.falsification_criteria}")
        print(f"\n  Reasoning: {plan.reasoning}")
        return

    # Demo with multiple questions
    print(f"\n{'='*70}")
    print("  WHY ENGINE DEMO — 4 câu hỏi cốt lõi")
    print(f"{'='*70}")

    demo_questions = [
        "Tại sao giá bitcoin hiện tại là $62000?",
        "Tại sao khối lượng phân tử caffeine là 194.19?",
        "Tại sao nhiệt độ tại Hà Nội là 27°C?",
        "Tại sao 2 + 3 = 5?",
        "Tại sao thủ đô của Việt Nam là Hà Nội?",
        "Tại sao tốc độ ánh sáng là 299792458 m/s?",
    ]

    for q in demo_questions:
        print(f"\n  Neo: {q}")
        plan = engine.create_verification_plan(q)
        print("  WHY Engine:")
        print(f"    1. Target: '{plan.target}' (type={plan.target_type})")
        print(f"    2. Evidence type: {plan.evidence_type}")
        print(f"    3. Proof: {plan.proof_criteria[:70]}")
        print(f"    4. Falsification: {plan.falsification_criteria[:70]}")
        print(f"    → Strategy: {plan.verification_strategy}, sources: {plan.sources_to_query[:3]}")


if __name__ == "__main__":
    main()
