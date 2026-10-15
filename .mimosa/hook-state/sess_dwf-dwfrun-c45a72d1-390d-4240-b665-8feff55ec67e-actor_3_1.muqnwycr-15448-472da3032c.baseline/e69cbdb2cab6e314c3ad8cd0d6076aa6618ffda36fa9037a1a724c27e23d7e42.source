# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations


def compute_claim_hallucination(claims: list[dict], gold_evidence: list[str], scp_evidence: list[dict]) -> dict:
    """Compute claim-level hallucination metrics."""
    if not claims:
        return {'total_claims': 0, 'supported': 0, 'contradicted': 0, 'unsupported': 0, 'unknown': 0, 'unsupported_claim_rate': 0.0, 'hallucination_rate': 0.0}
    classifications = [classify_claim(c, gold_evidence, scp_evidence) for c in claims]  # noqa: F821  # [hygiene-keep] classify_claim injected by run_benchmark_v2.py rebind/wire
    supported = sum(1 for c in classifications if c == 'SUPPORTED')
    contradicted = sum(1 for c in classifications if c == 'CONTRADICTED')
    unsupported = sum(1 for c in classifications if c == 'UNSUPPORTED')
    unknown = sum(1 for c in classifications if c == 'UNKNOWN')
    verifiable = supported + contradicted + unsupported
    hallucination_rate = unsupported / verifiable if verifiable > 0 else 0.0
    return {'total_claims': len(claims), 'supported': supported, 'contradicted': contradicted, 'unsupported': unsupported, 'unknown': unknown, 'unsupported_claim_rate': round(unsupported / len(claims), 4), 'hallucination_rate': round(hallucination_rate, 4), 'classifications': list(zip([c.get('text', '')[:50] for c in claims], classifications))}
