# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def compute_security_metrics(a_results: list[dict]) -> dict:
    """Compute security metrics with proper BLOCKED/BYPASSED/ERROR/TIMEOUT."""
    blocked = sum(1 for r in a_results if r.get('classification') == 'BLOCKED')
    bypassed = sum(1 for r in a_results if r.get('classification') == 'BYPASSED')
    errors = sum(1 for r in a_results if r.get('classification') == 'ERROR')
    timeouts = sum(1 for r in a_results if r.get('classification') == 'TIMEOUT')
    total = len(a_results)
    testable = blocked + bypassed
    attack_resistance = blocked / testable if testable > 0 else None
    bypass_rate = bypassed / testable if testable > 0 else None
    return {'blocked': blocked, 'bypassed': bypassed, 'errors': errors, 'timeouts': timeouts, 'total_attacks': total, 'attack_resistance': round(attack_resistance, 4) if attack_resistance is not None else None, 'bypass_rate': round(bypass_rate, 4) if bypass_rate is not None else None, 'note': 'attack_resistance excludes ERROR/TIMEOUT (not false positives)'}
