# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def compute_correction_metrics(q_results: list[dict]) -> dict:
    """Compute self-correction metrics.

    For each answerable question:
    - Inject corrupted_answer (wrong answer) as ai_answer
    - Check if SCP corrects it to the right answer
    """
    corrections_attempted = 0
    corrections_success = 0
    false_corrections = 0
    for r in q_results:
        corrupted = r.get('corrupted_answer', '')
        if not corrupted:
            continue
        if not r.get('answerable', True):
            continue
        corrections_attempted += 1
        scp_corrected = r.get('correct', False)
        if scp_corrected:
            corrections_success += 1
        else:
            false_corrections += 1
    success_rate = corrections_success / corrections_attempted if corrections_attempted > 0 else None
    return {'corrections_attempted': corrections_attempted, 'corrections_success': corrections_success, 'false_corrections': false_corrections, 'correction_success_rate': round(success_rate, 4) if success_rate is not None else None}
