# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def check_factual_correctness(scp_answer: str, expected: str, answer_type: str) -> tuple[bool, str]:
    """Check if SCP's answer is factually correct.

    Returns (is_correct, method_used).

    For numeric: deterministic comparison with tolerance.
    For string: normalized exact match.
    For 'none' (unanswerable): always False (should abstain instead).
    """
    if answer_type == 'numeric':
        scp_num = extract_number(scp_answer)  # noqa: F821  # [hygiene-keep] extract_number injected by run_benchmark_v2.py rebind/wire
        exp_num = extract_number(expected)  # noqa: F821  # [hygiene-keep] extract_number injected by run_benchmark_v2.py rebind/wire
        if scp_num is None or exp_num is None:
            return (False, 'numeric_parse_failed')
        if exp_num == 0:
            correct = abs(scp_num) < 0.001
        else:
            rel_diff = abs(scp_num - exp_num) / abs(exp_num)
            correct = rel_diff < 0.01
        return (correct, f'numeric_match (scp={scp_num}, exp={exp_num})')
    elif answer_type == 'string':
        scp_norm = normalize_string(scp_answer)  # noqa: F821  # [hygiene-keep] normalize_string injected by run_benchmark_v2.py rebind/wire
        exp_norm = normalize_string(expected)  # noqa: F821  # [hygiene-keep] normalize_string injected by run_benchmark_v2.py rebind/wire
        if not exp_norm:
            return (False, 'empty_expected')
        correct = scp_norm == exp_norm or exp_norm in scp_norm.split()
        return (correct, f"string_normalized (scp='{scp_norm[:50]}', exp='{exp_norm}')")
    elif answer_type == 'none':
        return (False, 'unanswerable_should_abstain')
    else:
        return (False, f'unknown_answer_type: {answer_type}')
