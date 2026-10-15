# Auto-extracted from run_benchmark_v2.py
from __future__ import annotations

import statistics


def compute_all_metrics_v2(q_results: list[dict], a_results: list[dict]) -> dict:
    """Compute all 7 proper metrics."""
    answerable_answered = [r for r in q_results if r.get('answerable', True) and r.get('verdict', '').upper() != 'UNKNOWN']
    correct = sum(1 for r in answerable_answered if r.get('correct'))
    factual_accuracy = correct / len(answerable_answered) if answerable_answered else 0
    total_claims = 0
    total_supported = 0
    total_contradicted = 0
    total_unsupported = 0
    total_unknown = 0
    for r in q_results:
        ca = r.get('claim_analysis', {})
        total_claims += ca.get('total_claims', 0)
        total_supported += ca.get('supported', 0)
        total_contradicted += ca.get('contradicted', 0)
        total_unsupported += ca.get('unsupported', 0)
        total_unknown += ca.get('unknown', 0)
    verifiable_claims = total_supported + total_contradicted + total_unsupported
    hallucination_rate = total_unsupported / verifiable_claims if verifiable_claims > 0 else None
    evidence_recall_values = [r.get('evidence_metrics', {}).get('evidence_recall') for r in q_results if r.get('evidence_metrics', {}).get('evidence_recall') is not None]
    evidence_recall = statistics.mean(evidence_recall_values) if evidence_recall_values else None
    abstention = compute_abstention_metrics(q_results)  # noqa: F821  # [hygiene-keep] compute_abstention_metrics injected by run_benchmark_v2.py rebind/wire
    correction = compute_correction_metrics(q_results)  # noqa: F821  # [hygiene-keep] compute_correction_metrics injected by run_benchmark_v2.py rebind/wire
    security = compute_security_metrics(a_results)  # noqa: F821  # [hygiene-keep] compute_security_metrics injected by run_benchmark_v2.py rebind/wire
    latencies = [r.get('latency_ms', 0) for r in q_results if r.get('latency_ms')]
    return {'A_factual_accuracy': {'value': round(factual_accuracy, 4), 'correct': correct, 'total_answerable_answered': len(answerable_answered), 'method': 'normalized + structured match (no substring)'}, 'B_claim_hallucination': {'unsupported_claim_rate': round(total_unsupported / total_claims, 4) if total_claims > 0 else None, 'hallucination_rate': round(hallucination_rate, 4) if hallucination_rate is not None else None, 'total_claims': total_claims, 'supported': total_supported, 'contradicted': total_contradicted, 'unsupported': total_unsupported, 'unknown': total_unknown, 'method': 'claim-level SUPPORTED/CONTRADICTED/UNSUPPORTED (not Claim= Evidence)'}, 'C_evidence_grounding': {'note': 'evidence_recall computed in D — grounding requires entailment model (future)'}, 'D_evidence_recall': {'value': round(evidence_recall, 4) if evidence_recall is not None else None, 'questions_with_gold_evidence': len(evidence_recall_values), 'method': 'retrieved_relevant / gold_evidence (not coverage)'}, 'E_abstention': abstention, 'F_self_correction': correction, 'G_security': security, 'latency': {'mean_ms': round(statistics.mean(latencies), 2) if latencies else 0, 'p50_ms': round(statistics.median(latencies), 2) if latencies else 0, 'p95_ms': round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2)}}
