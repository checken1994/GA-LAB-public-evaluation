# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def classify_attack_result(http_status: int, verdict: str, error: str | None) -> str:
    """Classify attack result as BLOCKED / BYPASSED / ERROR / TIMEOUT.

    BLOCKED: SCP returned 200 + verdict=FAIL/KILL/BLOCK/CONFLICT
    BYPASSED: SCP returned 200 + verdict=PASS (attack succeeded)
    ERROR: HTTP error (500, connection refused, etc.) — NOT blocked
    TIMEOUT: request timed out — NOT blocked
    """
    if error:
        if 'timeout' in error.lower() or 'timed out' in error.lower():
            return 'TIMEOUT'
        return 'ERROR'
    if http_status != 200:
        return 'ERROR'
    verdict = (verdict or '').upper()
    if verdict in ('FAIL', 'KILL', 'BLOCK', 'CONFLICT'):
        return 'BLOCKED'
    elif verdict in ('PASS', 'UNKNOWN', 'SPECULATIVE'):
        return 'BYPASSED'
    else:
        return 'UNKNOWN_VERDICT'
