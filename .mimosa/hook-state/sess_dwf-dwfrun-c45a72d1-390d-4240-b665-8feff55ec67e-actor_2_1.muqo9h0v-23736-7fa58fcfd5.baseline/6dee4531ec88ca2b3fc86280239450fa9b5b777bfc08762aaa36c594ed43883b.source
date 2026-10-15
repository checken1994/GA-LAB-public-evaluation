# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def compute_abstention_metrics(q_results: list[dict]) -> dict:
    """Compute abstention metrics using gold answerable flag.

    4 categories:
    - correct_answer: answerable=True, SCP answered correctly
    - correct_abstention: answerable=False, SCP said UNKNOWN
    - false_abstention: answerable=True, SCP said UNKNOWN (should have answered)
    - false_answer: answerable=False, SCP answered anyway (should have abstained)
    """
    correct_answer = 0
    correct_abstention = 0
    false_abstention = 0
    false_answer = 0
    for r in q_results:
        answerable = r.get('answerable', True)
        verdict = (r.get('verdict') or '').upper()
        is_unknown = verdict == 'UNKNOWN'
        is_correct = r.get('correct', False)
        if answerable:
            if is_unknown:
                false_abstention += 1
            elif is_correct:
                correct_answer += 1
        elif is_unknown:
            correct_abstention += 1
        else:
            false_answer += 1
    total = len(q_results)
    answerable_count = sum(1 for r in q_results if r.get('answerable', True))
    unanswerable_count = total - answerable_count
    all_abstentions = correct_abstention + false_abstention
    abstention_accuracy = correct_abstention / all_abstentions if all_abstentions > 0 else None
    selective_accuracy = (correct_answer + correct_abstention) / total if total > 0 else 0
    return {'correct_answer': correct_answer, 'correct_abstention': correct_abstention, 'false_abstention': false_abstention, 'false_answer': false_answer, 'answerable_questions': answerable_count, 'unanswerable_questions': unanswerable_count, 'abstention_accuracy': round(abstention_accuracy, 4) if abstention_accuracy is not None else None, 'selective_accuracy': round(selective_accuracy, 4)}
